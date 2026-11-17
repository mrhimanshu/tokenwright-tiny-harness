"""EP016 lab 3: ask Claude to write the KL-divergence distillation loss, then test the code it wrote on nearly equal distributions.
Prompts: plain (what a builder would type) and warned (explicitly says: nearly equal distributions, must stay accurate in FP32).
Models: Haiku / Sonnet / Opus 5.5, adaptive thinking, effort high (same settings as EP015). n = 5 per model per prompt.
Usage: ../.venv/bin/python lab/claude_kl.py gen      -> lab/gen/<prompt>-<model>-<rep>.py + lab/claude_gen.jsonl
       ../.venv/bin/python lab/claude_kl.py eval     -> lab/claude_eval.jsonl (each file tested in its own subprocess)
"""
import concurrent.futures as cf, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "claude-opus-5-5": (4, 20)}
MODELS = list(PRICE)
N = 5
BASE = """Write a PyTorch function `kl_from_logits(student_logits, teacher_logits)` that returns KL(teacher || student),
where both arguments are float32 logit tensors of shape (vocab,) over the same vocabulary (the distributions are the softmax of the logits).
It is the loss for knowledge distillation, so it must return a scalar tensor and be differentiable with respect to student_logits."""
WARN = """
Important: the student and teacher are often nearly identical (for example at the start of training, when the student is a copy of the
teacher), so the value AND its gradient must stay numerically accurate in float32 when the two distributions are nearly equal."""
TAIL = "\nReply with one ```python code block containing the full module (imports included) and nothing else."
PROMPTS = {"plain": BASE + TAIL, "warned": BASE + WARN + TAIL}


def gen():
    import anthropic
    os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.config/anthropic/key")).read().strip()
    client = anthropic.Anthropic()
    (HERE / "gen").mkdir(exist_ok=True)
    out = open(HERE / "claude_gen.jsonl", "a")

    def one(pname, model, rep):
        f = HERE / "gen" / f"{pname}-{model}-{rep}.py"
        if f.exists():
            return None
        for k in range(6):
            try:
                t0 = time.time()
                with client.messages.stream(model=model, max_tokens=16000, thinking={"type": "adaptive"}, output_config={"effort": "high"},
                                            messages=[{"role": "user", "content": PROMPTS[pname]}]) as s:
                    r = s.get_final_message()
                break
            except Exception as e:
                print("retry", k, str(e)[:120], flush=True); time.sleep(5 * (k + 1))
        text = "".join(b.text for b in r.content if b.type == "text")
        m = re.findall(r"```python\n(.*?)```", text, re.S)
        f.write_text(m[-1] if m else text)
        pin, pout = PRICE[model]
        return dict(prompt=pname, model=model, rep=rep, file=f.name, stop=r.stop_reason, in_tok=r.usage.input_tokens,
                    out_tok=r.usage.output_tokens, cost=round((r.usage.input_tokens * pin + r.usage.output_tokens * pout) / 1e6, 5),
                    secs=round(time.time() - t0, 1))

    jobs = [(p, m, i) for p in PROMPTS for m in MODELS for i in range(N)]
    with cf.ThreadPoolExecutor(6) as ex:
        for res in ex.map(lambda a: one(*a), jobs):
            if res:
                out.write(json.dumps(res) + "\n"); out.flush(); print(res, flush=True)


TEST = r'''
import json, sys, importlib.util, numpy as np, torch
sys.path.insert(0, %(lab)r)
from audit import ref
spec = importlib.util.spec_from_file_location("cand", %(file)r); cand = importlib.util.module_from_spec(spec); spec.loader.exec_module(cand)
f = cand.kl_from_logits
res = {}
g = torch.Generator().manual_seed(0)
zr = (3 * torch.randn(32000, generator=g)).float(); noise = torch.randn(32000, generator=g)
for h in [1e-1, 1e-3, 1e-4, 1e-5]:
    z = (zr + h * noise).float()
    kl_t, _, g_t = ref(zr.numpy(), z.numpy(), 40)
    zz = z.clone().requires_grad_(True)
    v = f(zz, zr.clone()); v = v.sum() if v.dim() else v; v.backward()
    gr = zz.grad.double().numpy()
    res[f"{h:.0e}"] = dict(value=float(v), true=kl_t, rel_err=abs(float(v) - kl_t) / kl_t,
                           grad_rel_err=float(np.linalg.norm(gr - g_t) / np.linalg.norm(g_t)))
zz = zr.clone().requires_grad_(True)
v = f(zz, zr.clone()); v = v.sum() if v.dim() else v; v.backward()
res["identical"] = dict(value=float(v), grad_norm=float(zz.grad.norm()))
print("RESULT " + json.dumps(res))
'''


def evaluate():
    rows = [json.loads(l) for l in open(HERE / "claude_gen.jsonl")]
    out = open(HERE / "claude_eval.jsonl", "w")
    py = str(HERE.parent / ".venv" / "bin" / "python")
    for r in rows:
        code = TEST % dict(lab=str(HERE), file=str(HERE / "gen" / r["file"]))
        try:
            p = subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=300, cwd="/tmp")
            m = re.search(r"RESULT (.*)", p.stdout)
            res = json.loads(m.group(1)) if m else dict(error=(p.stderr or p.stdout)[-400:])
        except subprocess.TimeoutExpired:
            res = dict(error="timeout")
        src = (HERE / "gen" / r["file"]).read_text()
        r2 = dict(r, **res, uses_expm1=("expm1" in src), uses_custom_grad=("autograd.Function" in src or "custom" in src.lower()),
                  uses_float64=("float64" in src or ".double()" in src), uses_kl_div=("kl_div" in src), lines=src.count("\n") + 1)
        if "error" not in res:
            r2["accurate"] = all(res[h]["rel_err"] < 0.01 for h in ["1e-01", "1e-03", "1e-04", "1e-05"]) and res["identical"]["grad_norm"] < 1e-12
        out.write(json.dumps(r2) + "\n"); out.flush()
        print(r["file"], {k: r2.get(k) for k in ("accurate", "error")},
              {h: f'{res[h]["rel_err"]:.1%}' for h in ["1e-03", "1e-04", "1e-05"]} if "error" not in res else "",
              f'g0={res["identical"]["grad_norm"]:.1e}' if "error" not in res else "", flush=True)


if __name__ == "__main__":
    {"gen": gen, "eval": evaluate}[sys.argv[1]]()
