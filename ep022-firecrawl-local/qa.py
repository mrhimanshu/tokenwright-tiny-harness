"""EP022 agent test: Claude Haiku 5.5 answers the 2 gold questions per page using ONLY each tool's round-1 markdown.
3 repeats per (tool, page) with the document prompt-cached. Claude Sonnet 5.5 grades each answer vs the gold answer.
-> qa_results.jsonl"""
import os, json, re, time, random, threading
from concurrent.futures import ThreadPoolExecutor
import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
A = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip(), max_retries=6)
TOOLS = ["fc_cloud", "fc_local", "trafilatura", "crawl4ai"]
REPEATS = 3
OUT = os.path.join(HERE, "qa_results.jsonl")
LOCK = threading.Lock()
GOLD = {json.loads(l)["id"]: json.loads(l)["qa"] for l in open(os.path.join(HERE, "gold_qa.jsonl"))}
URLS = {u["id"]: u for u in json.load(open(os.path.join(HERE, "urls.json")))}
MAXC = 600000


def answer(md, qa):
    sys_blocks = [{"type": "text", "text": "You answer questions about a web page using ONLY the scraped page content below. "
                   "If the content does not contain the answer, reply NOT FOUND for that question.\n\n<page>\n" + (md[:MAXC] or "(empty)") + "\n</page>",
                   "cache_control": {"type": "ephemeral"}}]
    q = "\n".join(f"{i+1}. {x['q']}" for i, x in enumerate(qa))
    m = A.messages.create(model="claude-haiku-5-5", max_tokens=400, system=sys_blocks,
                          messages=[{"role": "user", "content": q + '\n\nReply with only JSON: {"1": "<short answer>", "2": "<short answer>"}'}])
    t = "".join(b.text for b in m.content if b.type == "text")
    try:
        j = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
    except Exception:
        j = {"1": t, "2": t}
    u = m.usage
    return [str(j.get(str(i + 1), "")) for i in range(len(qa))], dict(
        input=u.input_tokens, cache_write=u.cache_creation_input_tokens or 0, cache_read=u.cache_read_input_tokens or 0, output=u.output_tokens)


def grade(q, gold, ans):
    m = A.messages.create(model="claude-sonnet-5-5", max_tokens=300, output_config={"effort": "low"},
                          messages=[{"role": "user", "content": f"Question: {q}\nReference answer: {gold}\nCandidate answer: {ans}\n\n"
                                     "Is the candidate answer correct (same fact as the reference; wording, units or formatting may differ)? "
                                     "NOT FOUND counts as incorrect. Reply with only YES or NO."}])
    return "YES" in "".join(b.text for b in m.content if b.type == "text").upper()


def job(tool, pid, rep):
    md = open(os.path.join(HERE, "md", f"{tool}__{pid}__r1.md")).read()
    qa = GOLD[pid]
    for attempt in range(3):
        try:
            ans, usage = answer(md, qa)
            break
        except Exception as e:
            time.sleep(5 + random.random() * 5)
    else:
        return
    marks = [grade(x["q"], x["a"], a) for x, a in zip(qa, ans)]
    rec = dict(tool=tool, id=pid, kind=URLS[pid]["kind"], rep=rep, chars=len(md), answers=ans, correct=marks, usage=usage)
    with LOCK:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    done = set()
    if os.path.exists(OUT):
        done = {(r["tool"], r["id"], r["rep"]) for r in map(json.loads, open(OUT))}
    jobs = [(t, p, r) for r in range(REPEATS) for t in TOOLS for p in GOLD if (t, p, r) not in done]
    t0 = time.time()
    # rep 0 first (writes the cache), then reps 1-2 read it
    for rep in range(REPEATS):
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(lambda a: job(*a), [j for j in jobs if j[2] == rep]))
        print("rep", rep, "done", round(time.time() - t0), "s", flush=True)
