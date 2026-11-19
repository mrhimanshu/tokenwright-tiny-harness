"""EP020 lab: does a harness tuned on one model carry over to another, and does a Self-Improvement Memory (SIM) help?
Small-scale replication of arXiv 2611.18856 (Yu et al., Google, 13 Nov 2026) on a ticket-routing task.

One run:
  source stage : policy claude-haiku-5-5, seed harness, SRC_ROUNDS rounds of optimize (proposer = claude-sonnet-5-5)
  transfer     : score seed vs source-evolved harness on the target model(s) (held-out)
  target stage : policy gemini-3.8-flash, start from the source-evolved harness, TGT_ROUNDS rounds, two arms:
                   harness : proposer sees the harness + this stage's own attempts (paper's "Harness Transfer")
                   sim     : same + the source stage's memory, grouped by problem (paper's "Full SIM")
usage: python sim_lab.py <run_id>
"""
import os, sys, json, time, hashlib, re, threading, random
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["GEMINI_API_KEY"] = open(os.path.expanduser("~/.config/gemini/key")).read().strip()
import anthropic
from google import genai
from google.genai import types

A = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip(), max_retries=5)
G = genai.Client()
TASKS = os.environ.get("TASKS", "tasks.json")
OUT = os.environ.get("OUT", "")
T = json.load(open(os.path.join(HERE, TASKS)))
LABELS = T["labels"]
SRC_MODEL = os.environ.get("SRC", "claude-haiku-5-5")
TGT_MODEL = os.environ.get("TGT", "gemini-3.8-flash")
EXTRA_TGT = os.environ.get("EXTRA", "gemini-4-neon")
PROPOSER = "claude-sonnet-5-5"
SRC_ROUNDS, TGT_ROUNDS, K = 4, 3, 2
LOCK = threading.Lock()

SEED = ("You route customer support tickets for a software shop.\n"
        "Labels: spam, legal, priority, billing_dispute, refund_auto, refund_review, bug_critical, bug, account, shipping, feedback.\n"
        "Reply with exactly one label and nothing else.")


def log(rec):
    with LOCK:
        with open(os.path.join(HERE, OUT + "results.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")


def call_policy(model, harness, text):
    for attempt in range(6):
        try:
            if model.startswith("claude"):
                r = A.messages.create(model=model, max_tokens=2000, system=harness, output_config={"effort": "low"},
                                      messages=[{"role": "user", "content": text}])
                out = "".join(b.text for b in r.content if b.type == "text")
                usage = dict(inp=r.usage.input_tokens, out=r.usage.output_tokens)
            else:
                r = G.models.generate_content(model=model, contents=text, config=types.GenerateContentConfig(
                    system_instruction=harness, thinking_config=types.ThinkingConfig(thinking_level="low")))
                out = r.text or ""
                u = r.usage_metadata
                usage = dict(inp=u.prompt_token_count, out=(u.candidates_token_count or 0) + (u.thoughts_token_count or 0))
            return out, usage
        except Exception as e:
            time.sleep(2 + 3 * attempt + random.random())
            err = str(e)[:200]
    return "", dict(error=err)


def parse(out):
    toks = re.findall(r"[a-z_]+", out.lower())
    for t in reversed(toks):
        if t in LABELS:
            return t
    return None


def evaluate(model, harness, items, run, stage, tag):
    def one(t):
        out, usage = call_policy(model, harness, t["text"])
        pred = parse(out)
        rec = dict(run=run, stage=stage, tag=tag, model=model, h=hashlib.sha1(harness.encode()).hexdigest()[:10],
                   item=t["id"], gold=t["gold"], pred=pred, ok=pred == t["gold"], raw=out[-80:], usage=usage)
        log(rec)
        return rec
    with ThreadPoolExecutor(10) as ex:
        recs = list(ex.map(one, items))
    score = round(100 * sum(r["ok"] for r in recs) / len(recs), 2)
    fails = [dict(ticket=t["text"], predicted=r["pred"], correct=t["gold"]) for t, r in zip(items, recs) if not r["ok"]]
    return score, fails


def fmt_memory(entries):
    if not entries:
        return "(none yet)"
    groups = {}
    for e in entries:
        groups.setdefault(e["problem"], []).append(e)
    lines = []
    for prob, es in groups.items():
        lines.append(f"PROBLEM: {prob}")
        for e in es:
            lines.append(f"  - [{e['model']} round {e['round']}] edit: {e['rationale']} | predicted: {e['predicted']} | "
                         f"observed: {e['delta']:+.1f} pts on evolve set ({'kept' if e['kept'] else 'rejected'})")
    return "\n".join(lines)


def own_attempts(entries):
    if not entries:
        return "(none yet)"
    return "\n".join(f"- round {e['round']}: {e['rationale']} -> {e['delta']:+.1f} pts ({'kept' if e['kept'] else 'rejected'})"
                     for e in entries)


def propose(harness, score, fails, model, history_block, cand_no):
    prompt = f"""You are optimizing the HARNESS (system prompt) that a fixed model ({model}) uses to route support tickets.
The company has house routing rules that are NOT written down anywhere; infer them from the failures.
Current harness:
<harness>
{harness}
</harness>
Score on the evolve set: {score}%.
Failures (ticket, what the model answered, correct label):
{json.dumps(fails[:14], indent=1)}

{history_block}

Propose ONE improved harness (candidate #{cand_no}; make it a meaningfully different idea from other candidates).
The model must still reply with exactly one label. Return ONLY a JSON object:
{{"problem": "<short name of the recurring harness problem you are fixing, reuse an existing PROBLEM name if it is the same one>",
"rationale": "<one sentence: what you changed and why>",
"predicted": "<one sentence: expected effect>",
"harness": "<the full new harness text>"}}"""
    for attempt in range(4):
        try:
            with A.messages.stream(model=PROPOSER, max_tokens=16000, output_config={"effort": "medium"},
                                   messages=[{"role": "user", "content": prompt}]) as s:
                r = s.get_final_message()
            text = "".join(b.text for b in r.content if b.type == "text")
            m = re.search(r"\{.*\}", text, re.S)
            d = json.loads(m.group(0))
            assert d["harness"].strip()
            log(dict(kind="proposer", usage=dict(inp=r.usage.input_tokens, out=r.usage.output_tokens)))
            return d
        except Exception as e:
            time.sleep(3)
    return None


def optimize(model, harness, rounds, run, stage, memory_in, sim_mode):
    """greedy RSI loop: K candidates per round, keep the best if it beats the current harness on the evolve set"""
    entries = []  # this stage's own records
    score, fails = evaluate(model, harness, T["evolve"], run, stage, "r0")
    held, _ = evaluate(model, harness, T["heldout"], run, stage, "r0_held")
    traj = [dict(round=0, evolve=score, held=held)]
    for rd in range(1, rounds + 1):
        if sim_mode:
            hist = ("SELF-IMPROVEMENT MEMORY (earlier harness edits, grouped by problem, with their measured outcomes; "
                    "edits made for a different model may not carry over):\n" + fmt_memory(memory_in + entries))
        else:
            hist = "Your earlier attempts in this run:\n" + own_attempts(entries)
        cands = [c for c in (propose(harness, score, fails, model, hist, i + 1) for i in range(K)) if c]
        best = None
        for c in cands:
            s, f = evaluate(model, c["harness"], T["evolve"], run, stage, f"r{rd}_cand")
            c["score"], c["fails"] = s, f
            if best is None or s > best["score"]:
                best = c
        for c in cands:
            kept = c is best and c["score"] > score
            entries.append(dict(problem=c["problem"], rationale=c["rationale"], predicted=c["predicted"], model=model,
                                round=rd, delta=c["score"] - score, kept=kept))
        if best and best["score"] > score:
            harness, score, fails = best["harness"], best["score"], best["fails"]
        held, _ = evaluate(model, harness, T["heldout"], run, stage, f"r{rd}_held")
        traj.append(dict(round=rd, evolve=score, held=held))
        print(run, stage, rd, traj[-1], flush=True)
    return harness, entries, traj


if __name__ == "__main__":
    run = int(sys.argv[1])
    out = dict(run=run, seed=SEED)
    # source stage on Claude Haiku
    h_src, mem_src, traj_src = optimize(SRC_MODEL, SEED, SRC_ROUNDS, run, "source", [], sim_mode=True)
    out.update(h_src=h_src, mem_src=mem_src, traj_src=traj_src)
    # transfer snapshot: seed vs source-evolved on the target models
    snap = {}
    for m in (TGT_MODEL, EXTRA_TGT):
        snap[m] = dict(seed=evaluate(m, SEED, T["heldout"], run, "transfer", "seed")[0],
                       evolved=evaluate(m, h_src, T["heldout"], run, "transfer", "evolved")[0])
    out["transfer"] = snap
    print(run, "transfer", snap, flush=True)
    json.dump(out, open(os.path.join(HERE, f"{OUT}runs/run{run}.json"), "w"), indent=1)
    if os.environ.get("SKIP_TARGET"):
        print(run, "DONE", flush=True); sys.exit(0)
    # target stage, two arms
    for arm in ("harness", "sim"):
        h, ents, traj = optimize(TGT_MODEL, h_src, TGT_ROUNDS, run, f"target_{arm}", mem_src, sim_mode=(arm == "sim"))
        out[f"tgt_{arm}"] = dict(h=h, entries=ents, traj=traj)
        json.dump(out, open(os.path.join(HERE, f"{OUT}runs/run{run}.json"), "w"), indent=1)
    print(run, "DONE", flush=True)
