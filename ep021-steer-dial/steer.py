"""EP021 arm B: REAL activation steering (a vector added to the hidden state) vs the prompt knob, same small model, on CPU.
Model: Qwen/Qwen2.5-1.5B-Instruct (official repo, sha256-checked). Steering vector for tension (relaxed -> strained) =
mean hidden state of strained sentences minus relaxed ones at layer L, unit length; added at every position with
scale = gain x mean activation norm of that layer (same convention as harishkotra/steer).
usage: python steer.py <model_dir>  -> steer_results.jsonl
"""
import os, sys, json, time, torch
from transformers import AutoTokenizer, AutoModelForCausalLM

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_prompt import PLAIN, STEERED, OPENINGS, GRADES

torch.set_num_threads(int(os.environ.get("THREADS", "6")))
MD = sys.argv[1]
OUT = os.path.join(HERE, os.environ.get("OUT", "steer_results.jsonl"))
GAINS = [float(g) for g in os.environ.get("GAINS", "-0.28,-0.16,-0.08,-0.04,0,0.04,0.08,0.16,0.28").split(",")]
SEEDS = [0, 1]
NEW = int(os.environ.get("NEW", "130"))
SIMPLE = "Continue the story in four to six sentences. Output only the continuation."
LAYER_FRAC = 0.55

tok = AutoTokenizer.from_pretrained(MD)
tok.padding_side = "left"
model = AutoModelForCausalLM.from_pretrained(MD, dtype=torch.float32)
model.eval()
layers = model.model.layers
L = round(LAYER_FRAC * len(layers))

TENSE = ["Her heart hammered as the footsteps stopped right outside the locked door.",
         "He held his breath, knowing one wrong move would get them all killed.",
         "The countdown blinked red: ten seconds left, and the wire was still uncut.",
         "Something scraped behind her in the dark, and the flashlight died.",
         "They ran, lungs burning, the dogs getting closer with every second.",
         "The phone rang again at 3 a.m., and this time no one breathed on the line.",
         "Her hands shook so badly she could barely hold the gun steady.",
         "The floor cracked under his weight and the drop below was endless."]
CALM = ["She sipped her tea slowly as the afternoon sun warmed the quiet kitchen.",
        "He stretched out in the hammock, listening to the gentle hum of bees.",
        "The lake was still, and the only sound was a distant, lazy birdsong.",
        "They strolled along the beach with nowhere to be and nothing to worry about.",
        "The cat dozed on the windowsill while soft rain tapped the glass.",
        "Sunday morning drifted by with pancakes, music and an unhurried crossword.",
        "Her shoulders loosened as she sank into the warm, lavender-scented bath.",
        "The old man smiled, folded his newspaper, and watched the clouds drift."]

captured = {}


def cap_hook(mod, inp, out):
    captured["h"] = (out[0] if isinstance(out, tuple) else out).detach()


@torch.no_grad()
def mean_hidden(sents):
    h = layers[L].register_forward_hook(cap_hook)
    vecs, norms = [], []
    for s in sents:
        ids = tok(s, return_tensors="pt")
        model(**ids)
        x = captured["h"][0]
        vecs.append(x.mean(0)); norms.append(x.norm(dim=-1)[1:].mean())
    h.remove()
    return torch.stack(vecs).mean(0), torch.stack(norms).mean()


mu_t, n_t = mean_hidden(TENSE)
mu_c, n_c = mean_hidden(CALM)
direction = mu_t - mu_c
direction = direction / direction.norm()
NORM = float((n_t + n_c) / 2)
STATE = {"add": None}


def steer_hook(mod, inp, out):
    if STATE["add"] is None:
        return out
    if isinstance(out, tuple):
        return (out[0] + STATE["add"],) + tuple(out[1:])
    return out + STATE["add"]


layers[L].register_forward_hook(steer_hook)


def chat(system, user):
    return tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                   tokenize=False, add_generation_prompt=True)


@torch.no_grad()
def generate(prompts, gain, seed):
    STATE["add"] = None if gain == 0 else (gain * NORM) * direction
    torch.manual_seed(seed)
    enc = tok(prompts, return_tensors="pt", padding=True)
    t0 = time.time()
    out = model.generate(**enc, max_new_tokens=NEW, do_sample=True, temperature=0.9, top_p=0.95,
                         pad_token_id=tok.eos_token_id)
    dt = time.time() - t0
    texts = [tok.decode(o[enc["input_ids"].shape[1]:], skip_special_tokens=True) for o in out]
    ntok = sum(int((o[enc["input_ids"].shape[1]:] != tok.eos_token_id).sum()) for o in out)
    return texts, dt, ntok


def write(rec):
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    print(f"layer {L}/{len(layers)}  mean activation norm {NORM:.1f}", flush=True)
    write(dict(meta=True, layer=L, n_layers=len(layers), norm=NORM, model=os.path.basename(MD)))
    # a 1.5B model copies Spaceship's long prompt + example, so it gets a short equivalent; the knob phrase is the same
    plain = [chat(SIMPLE, o) for o in OPENINGS for _ in SEEDS]
    meta = [(oi, sd) for oi in range(len(OPENINGS)) for sd in SEEDS]
    for gain in GAINS:
        texts, dt, ntok = generate(plain, gain, 0)
        for (oi, sd), t in zip(meta, texts):
            write(dict(arm="vector", model="qwen2.5-1.5b", opening=oi, gain=gain, seed=sd, text=t, sec=dt, tok=ntok))
        print("vector", gain, f"{ntok/dt:.1f} tok/s", repr(texts[0][:90]), flush=True)
    for g in ([] if os.environ.get("SKIP_PROMPT") else range(5)):
        ps = [chat(SIMPLE + f" Tension: {GRADES[g]} (strong).", o) for o in OPENINGS for _ in SEEDS]
        texts, dt, ntok = generate(ps, 0, 0)
        for (oi, sd), t in zip(meta, texts):
            write(dict(arm="prompt", model="qwen2.5-1.5b", opening=oi, grade=g, strength="strong", seed=sd, text=t, sec=dt, tok=ntok))
        print("prompt", g, repr(texts[0][:90]), flush=True)
