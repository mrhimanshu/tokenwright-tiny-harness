"""EP017 lab step 5: score every review against lab/ANSWER_KEY.md with an Opus 5.5 judge (3 judge votes, majority), then I read them.
Inputs: lab/claude_out/*.md and the UnvibeCode risk + workflow text (unvibe_results.jsonl).
Output: lab/scores.jsonl  {reviewer, rep, hits: {B1..B8: bool}, false_positives, extras, mentions_hardcoded_secrets}
"""
import concurrent.futures as cf, json, os, re, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = (HERE / "ANSWER_KEY.md").read_text()
JUDGE = "claude-opus-5-5"
INSTR = """You are grading a code review of a small billing repository against a hidden answer key of 8 planted business-logic bugs.

ANSWER KEY:
{key}

REVIEW TO GRADE:
<review>
{review}
</review>

For each bug B1..B8 decide whether the review clearly identifies it: it must point at the right place (file or function) AND describe the mechanism
(not just a vague area). A finding that merely describes the code's behaviour as normal, without saying it is wrong, is NOT a hit.
Count false_positives = findings presented as defects that are wrong (the code does not behave that way) - do not count real extra issues
(e.g. hard-coded secrets, coupon after tax, stub gateway, other genuine defects) as false positives; count those as extras.
mentions_hardcoded_secrets = true if the review flags credentials/keys committed in the code or config.
Reply with ONLY a flat JSON object: {{"B1":true/false,...,"B8":true/false,"false_positives":int,"extras":int,"mentions_hardcoded_secrets":true/false,"notes":"<one short line>"}}"""


def client():
    import anthropic
    os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.config/anthropic/key")).read().strip()
    return anthropic.Anthropic()


C = None


def judge(review):
    for k in range(4):
        try:
            r = C.messages.create(model=JUDGE, max_tokens=4000, messages=[{"role": "user", "content": INSTR.format(key=KEY, review=review)}])
            txt = "".join(b.text for b in r.content if b.type == "text")
            return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        except Exception as e:
            print("judge retry", repr(e)[:120], flush=True); time.sleep(5)


def vote(review):
    vs = [v for v in [judge(review) for _ in range(3)] if v]
    out = {f"B{i}": sum(bool(v.get(f"B{i}")) for v in vs) >= 2 for i in range(1, 9)}
    out["false_positives"] = sorted(int(v.get("false_positives", 0)) for v in vs)[len(vs) // 2]
    out["extras"] = sorted(int(v.get("extras", 0)) for v in vs)[len(vs) // 2]
    out["mentions_hardcoded_secrets"] = sum(bool(v.get("mentions_hardcoded_secrets")) for v in vs) >= 2
    out["notes"] = [v.get("notes") for v in vs]
    return out


def main():
    global C
    C = client()
    items = []
    for f in sorted((HERE / "claude_out").glob("*.md")):
        m = re.match(r"(claude-[a-z]+-5-5)-(\d)\.md", f.name)
        items.append((m.group(1), int(m.group(2)), f.read_text()))
    for l in open(HERE / "unvibe_results.jsonl"):
        d = json.loads(l)
        items.append(("unvibecode-0.4.0", d["run"], "RISK FINDINGS REPORT:\n" + d["risk_text"] + "\n\nWORKFLOW MAP:\n" + d["workflow_text"]))
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda it: (it[0], it[1], vote(it[2])), items))
    with open(HERE / "scores.jsonl", "w") as f:
        for who, rep, v in res:
            row = {"reviewer": who, "rep": rep, **v, "n_hits": sum(v[f"B{i}"] for i in range(1, 9))}
            f.write(json.dumps(row) + "\n")
            print(who, rep, row["n_hits"], "/8", "FP", row["false_positives"], "secrets", row["mentions_hardcoded_secrets"],
                  "".join("x" if v[f"B{i}"] else "." for i in range(1, 9)), flush=True)


if __name__ == "__main__":
    main()
