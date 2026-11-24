"""Ask Claude the same Stack Overflow questions a human answered (pre-ChatGPT accepted answers).
Models: Opus 5.5, Haiku 5.5. System prompts: default (none), concise ("Be concise."), plain (one-line plain-English ask).
Writes gen.jsonl (one line per answer). Resumable."""
import json, os, sys, concurrent.futures as cf
from pathlib import Path
import anthropic

os.environ.setdefault("ANTHROPIC_API_KEY", Path("~/.config/anthropic/key").expanduser().read_text().strip())
client = anthropic.Anthropic(max_retries=6)
HERE = Path(__file__).parent
OPUS, HAIKU = "claude-opus-5-5", "claude-haiku-5-5"
PRICE = {OPUS: (4.0, 20.0), HAIKU: (0.10, 0.50)}
SYSTEM = {
    "default": None,
    "concise": "Be concise.",
    "plain": "Write the way a helpful colleague talks: short sentences, people (you, I, we) as the subject, everyday words.",
}
OUT = HERE / "gen.jsonl"
Q = [q for q in json.load(open(HERE / "questions.json")) if q["human_words"] <= 1000]

def done():
    if not OUT.exists(): return set()
    return {(r["qid"], r["model"], r["cond"]) for r in map(json.loads, OUT.open())}

def run(q, model, cond):
    kw = dict(model=model, max_tokens=4000,
              messages=[{"role": "user", "content": f"{q['title']}\n\n{q['question']}"}])
    if SYSTEM[cond]: kw["system"] = SYSTEM[cond]
    r = client.messages.create(**kw)
    text = "".join(b.text for b in r.content if b.type == "text")
    pi, po = PRICE[model]
    return dict(qid=q["qid"], model=model, cond=cond, text=text, usage=r.usage.model_dump(),
                cost=(r.usage.input_tokens * pi + r.usage.output_tokens * po) / 1e6)

if __name__ == "__main__":
    have = done()
    jobs = [(q, m, c) for q in Q for m in (OPUS, HAIKU) for c in SYSTEM if (q["qid"], m, c) not in have]
    print("questions", len(Q), "jobs", len(jobs), flush=True)
    tot = 0.0
    with cf.ThreadPoolExecutor(6) as ex, OUT.open("a") as f:
        futs = {ex.submit(run, *j): j for j in jobs}
        for i, fu in enumerate(cf.as_completed(futs)):
            try:
                rec = fu.result(); tot += rec["cost"]
                f.write(json.dumps(rec) + "\n"); f.flush()
            except Exception as e:
                print("ERR", futs[fu][1:], repr(e)[:200], flush=True)
            if i % 20 == 0: print(i, f"${tot:.3f}", flush=True)
    print("done", f"${tot:.3f}")
