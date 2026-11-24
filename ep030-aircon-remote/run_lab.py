"""Can Claude crack an air-con remote from raw IR captures?
Arms: panasonic_named (told it's a Panasonic), panasonic_blind (same real protocol, brand hidden),
      brandx (invented protocol that exists nowhere online).
Models: Opus 5.5, Sonnet 5.5, Haiku 5.5. n = 3 reps per (model, arm), each rep with a different set of 12 captures.
Loop: model writes encode(settings) -> timings; I run it on the 12 training captures and tell it how many match
(up to 2 repair rounds, training feedback only). Score: exact bits on 60 held-out settings it never saw.
Usage: python run_lab.py [model_short ...]"""
import json, os, re, sys, time, random, subprocess, tempfile, threading, concurrent.futures as cf
from pathlib import Path
import anthropic
import protocols as P

os.environ.setdefault("ANTHROPIC_API_KEY", Path("~/.config/anthropic/key").expanduser().read_text().strip())
client = anthropic.Anthropic(max_retries=6, timeout=900)
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
PRICE = {"opus": (4.0, 20.0), "sonnet": (2.0, 10.0), "haiku": (0.10, 0.50)}  # $/MTok in, out
ARMS = ["panasonic_named", "panasonic_blind", "brandx"]
REPS = 3
ROUNDS = 3
N_TRAIN, N_TEST = 12, 60
HERE = Path(__file__).parent
RES = HERE / "results.jsonl"
LOCK = threading.Lock()


def cost(m, u):
    pi, po = PRICE[m]
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    return (u.input_tokens * pi + cw * pi * 1.25 + cr * pi * 0.1 + u.output_tokens * po) / 1e6


def train_settings(rep):
    """12 captures that cover every mode (x2+), fan speed, vane position and both power states, incl. the
    quirk cases (fan mode at a temp other than 27, dry mode with a non-auto fan)."""
    r = random.Random(100 + rep)
    modes = P.MODES * 2 + [r.choice(P.MODES) for _ in range(2)]
    fans = P.FANS * 2; vanes = P.VANES * 2
    r.shuffle(modes); r.shuffle(fans); r.shuffle(vanes)
    out = []
    for i in range(N_TRAIN):
        out.append(dict(power="off" if i in (3, 8) else "on", mode=modes[i], temp=r.randint(16, 30),
                        fan=fans[i], vane=vanes[i]))
    for s in out:   # force quirk visibility
        if s["mode"] == "fan" and s["temp"] == 27: s["temp"] = 21
        if s["mode"] == "dry" and s["fan"] == "auto": s["fan"] = "high"
    return out


def test_settings():
    r = random.Random(999)
    return [P.random_settings(r) for _ in range(N_TEST)]


def proto_of(arm):
    return "brandx" if arm == "brandx" else "panasonic"


def prompt(arm, captures):
    who = ("a Panasonic air conditioner's IR remote (model CS-NE9PKE)" if arm == "panasonic_named"
           else "an air conditioner's IR remote (brand unknown)")
    lines = []
    for i, (s, t) in enumerate(captures, 1):
        lines.append(f"Capture {i}: display shows {json.dumps(s)}\nraw ({len(t)} values): {','.join(map(str, t))}")
    return f"""I want to control my air conditioner from a microcontroller. I pointed {who} at an IR receiver,
pressed buttons, and after each press wrote down what the remote's display showed. Each capture below is the
raw dump from the receiver: alternating mark/space durations in microseconds, starting with a mark
(receiver jitter is a few percent).

Settings keys and allowed values:
- power: "on" | "off"
- mode: "auto" | "cool" | "heat" | "dry" | "fan"
- temp: integer 16..30
- fan: "auto" | "min" | "low" | "med" | "high" | "max"
- vane: "auto" | "1" | "2" | "3" | "4" | "5"

{chr(10).join(lines)}

Reverse-engineer the protocol and write a Python function `encode(settings: dict) -> list[int]` that returns the
raw timing list the remote would send for ANY valid combination of settings (I will test it on combinations
that are not in these captures, so it must generalise). Standard library only, no I/O.
Reply with your explanation, then the complete code in a single ```python block."""


def extract_code(text):
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    return blocks[-1] if blocks else None


RUNNER = r'''
import json, sys
sys.setrecursionlimit(10000)
ns = {}
exec(open(sys.argv[1]).read(), ns)
out = []
for s in json.load(open(sys.argv[2])):
    try:
        v = ns["encode"](dict(s)); out.append([int(x) for x in v])
    except Exception as e:
        out.append("ERR " + type(e).__name__ + ": " + str(e)[:200])
print(json.dumps(out))
'''


def run_code(code, settings):
    with tempfile.TemporaryDirectory() as d:
        Path(d, "c.py").write_text(code); Path(d, "s.json").write_text(json.dumps(settings))
        Path(d, "r.py").write_text(RUNNER)
        try:
            p = subprocess.run([sys.executable, "-I", "r.py", "c.py", "s.json"], cwd=d, capture_output=True,
                               text=True, timeout=30)
            return json.loads(p.stdout) if p.returncode == 0 else ["ERR " + p.stderr[-300:]] * len(settings)
        except Exception as e:
            return ["ERR " + str(e)[:200]] * len(settings)


def score(proto, settings, outs):
    return [isinstance(o, list) and P.matches(proto, s, o) for s, o in zip(settings, outs)]


def feedback(proto, settings, outs, ok):
    msg = [f"I ran your encode() on the {len(settings)} captured settings: {sum(ok)}/{len(settings)} reproduce the "
           f"capture exactly (same bits; header within 25%)."]
    shown = 0
    for i, (s, o, k) in enumerate(zip(settings, outs, ok), 1):
        if k or shown >= 3: continue
        shown += 1
        if not isinstance(o, list):
            msg.append(f"Capture {i}: {o}"); continue
        want = P.section_bits(proto, s); got = P.decode_generic(o)
        if len(got) != len(want):
            msg.append(f"Capture {i}: your output decodes to {len(got)} section(s), the capture has {len(want)}.")
            continue
        for j, ((h, gb), wb) in enumerate(zip(got, want), 1):
            if len(gb) != len(wb):
                msg.append(f"Capture {i}, section {j}: {len(gb)} bits vs {len(wb)} in the capture."); break
            diff = [n for n, (a, b) in enumerate(zip(gb, wb)) if a != b]
            if diff:
                msg.append(f"Capture {i}, section {j}: bits differ at positions {diff[:12]} (0-based, in send order)."); break
        else:
            msg.append(f"Capture {i}: bits match but header timing is off.")
    msg.append("Fix the code and reply with the complete corrected code in a single ```python block.")
    return "\n".join(msg)


def call(m, messages):
    with client.messages.stream(model=MODELS[m], max_tokens=48000, messages=messages,
                                output_config={"effort": "high"}) as st:
        return st.get_final_message()


def run_one(m, arm, rep):
    proto = proto_of(arm); rng = random.Random(f"{m}{arm}{rep}")
    tr = train_settings(rep); te = test_settings()
    caps = [(s, P.timings(proto, s, rng)) for s in tr]
    first = {"type": "text", "text": prompt(arm, caps), "cache_control": {"type": "ephemeral"}}
    messages = [{"role": "user", "content": [first]}]
    rounds = []; total = 0.0; t0 = time.time()
    for rd in range(1, ROUNDS + 1):
        r = call(m, messages); c = cost(m, r.usage); total += c
        text = "".join(b.text for b in r.content if b.type == "text")
        code = extract_code(text)
        outs_tr = run_code(code, tr) if code else ["ERR no python block"] * len(tr)
        ok_tr = score(proto, tr, outs_tr)
        outs_te = run_code(code, te) if code else ["ERR no python block"] * len(te)
        ok_te = score(proto, te, outs_te)
        rounds.append(dict(round=rd, train_ok=sum(ok_tr), test_ok=sum(ok_te), cost=c, out_tokens=r.usage.output_tokens,
                           in_tokens=r.usage.input_tokens, cache_read=getattr(r.usage, "cache_read_input_tokens", 0),
                           stop=r.stop_reason, code=code, text=text[-4000:]))
        print(f"{m:6} {arm:16} rep{rep} r{rd}: train {sum(ok_tr)}/{N_TRAIN} test {sum(ok_te)}/{N_TEST} ${c:.3f}", flush=True)
        if sum(ok_tr) == N_TRAIN or rd == ROUNDS:
            break
        messages.append({"role": "assistant", "content": r.content})
        messages.append({"role": "user", "content": feedback(proto, tr, outs_tr, ok_tr)})
    rec = dict(model=m, arm=arm, rep=rep, proto=proto, rounds=rounds, final_train=rounds[-1]["train_ok"],
               final_test=rounds[-1]["test_ok"], first_test=rounds[0]["test_ok"], n_rounds=len(rounds),
               cost=total, secs=time.time() - t0, n_train=N_TRAIN, n_test=N_TEST)
    with LOCK:
        with open(RES, "a") as f: f.write(json.dumps(rec) + "\n")
    return rec


if __name__ == "__main__":
    ms = sys.argv[1:] or list(MODELS)
    done = set()
    if RES.exists():
        for l in RES.read_text().splitlines():
            d = json.loads(l); done.add((d["model"], d["arm"], d["rep"]))
    jobs = [(m, a, r) for m in ms for a in ARMS for r in range(REPS) if (m, a, r) not in done]
    print(len(jobs), "jobs")
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(run_one, *j): j for j in jobs}
        for f in cf.as_completed(futs):
            try: f.result()
            except Exception as e: print("FAIL", futs[f], repr(e)[:300], flush=True)
    R = [json.loads(l) for l in RES.read_text().splitlines()]
    print("total spend $%.2f" % sum(r["cost"] for r in R))
