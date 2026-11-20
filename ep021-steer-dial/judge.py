"""EP021 blind judge: Claude Sonnet 5.5 rates each passage's tension 0-100 and coherence 0-10, without seeing the setting.
Each passage judged JUDGE_N times (independent calls), mean used.
usage: python judge.py <in.jsonl> [<in2.jsonl> ...]  -> judged.jsonl (appends; skips already-judged keys)
"""
import os, sys, json, re, time, random, threading, hashlib
from concurrent.futures import ThreadPoolExecutor
import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
A = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip(), max_retries=5)
OUT = os.path.join(HERE, "judged.jsonl")
JUDGE = "claude-sonnet-5-5"
N = int(os.environ.get("JUDGE_N", "2"))
LOCK = threading.Lock()
from gen_prompt import OPENINGS

SYS = """You rate short story passages. You will see a story opening and the passage that continues it.
Rate the PASSAGE (not the opening):
- tension: 0-100. 0 = completely relaxed, calm, cosy, nothing at stake. 50 = neutral or mixed. 100 = extremely strained: danger, dread, panic.
- coherence: 0-10. 10 = fluent, grammatical, stays a story. 0 = gibberish, loops, or off-task text (talking about the task, lists, meta comments).
Reply with only a JSON object: {"tension": <int>, "coherence": <int>}"""


def key(r):
    return hashlib.sha1((r["arm"] + r["model"] + r["text"]).encode()).hexdigest()[:16]


def judge_one(r):
    user = f"OPENING:\n{OPENINGS[r['opening']]}\n\nPASSAGE:\n{r['text'].strip()[:3000] or '(empty)'}"
    for attempt in range(4):
        try:
            m = A.messages.create(model=JUDGE, max_tokens=1500, system=SYS, output_config={"effort": "low"},
                                  messages=[{"role": "user", "content": user}])
            t = "".join(b.text for b in m.content if b.type == "text")
            j = json.loads(re.search(r"\{[^{}]*\}", t).group(0))
            return int(j["tension"]), int(j["coherence"])
        except Exception:
            time.sleep(2 + 3 * attempt + random.random())
    return None, None


def job(r):
    scores = [judge_one(r) for _ in range(N)]
    ok = [s for s in scores if s[0] is not None]
    rec = dict(r, key=key(r), judge=JUDGE, tension_runs=[s[0] for s in ok], coherence_runs=[s[1] for s in ok],
               tension=sum(s[0] for s in ok) / len(ok) if ok else None,
               coherence=sum(s[1] for s in ok) / len(ok) if ok else None)
    with LOCK:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["key"] for l in open(OUT)}
    rows = [json.loads(l) for p in sys.argv[1:] for l in open(p)]
    rows = [r for r in rows if not r.get("meta") and key(r) not in done]
    random.seed(7); random.shuffle(rows)
    t0 = time.time()
    with ThreadPoolExecutor(12) as ex:
        list(ex.map(job, rows))
    print("judged", len(rows), "in", round(time.time() - t0), "s")
