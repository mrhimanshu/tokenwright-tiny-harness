"""Mini CPU-ARC on the Anthropic API.
Arms: opus (fresh Opus 5.5 every time), haiku (fresh Haiku 5.5 every time, x3),
      cache (Opus builds a Python cache from one solved seed per family; Haiku 5.5 extracts values; CPU runs code; x3).
Usage: python run_lab.py opus|haiku|build|hit|all"""
import json, os, re, sys, time, math, traceback, concurrent.futures as cf
from pathlib import Path
import anthropic
from pydantic import BaseModel

os.environ.setdefault("ANTHROPIC_API_KEY", Path("~/.config/anthropic/key").expanduser().read_text().strip())
client = anthropic.Anthropic(max_retries=6)
OPUS, HAIKU = "claude-opus-5-5", "claude-haiku-5-5"
PRICE = {OPUS: (4.0, 20.0), HAIKU: (0.10, 0.50)}
HERE = Path(__file__).parent
TASKS = json.load(open(HERE / "tasks.json"))
RES = HERE / "results.jsonl"
FMT = {"money": "a number in dollars rounded to cents, no $ sign or commas (e.g. 1234.56)",
       "clock": "a 24-hour time HH:MM", "int": "a whole number of minutes", "date": "a date YYYY-MM-DD"}

def cost(model, u):
    pi, po = PRICE[model]
    return (u.input_tokens * pi + u.output_tokens * po) / 1e6

def log(rec):
    with open(RES, "a") as f: f.write(json.dumps(rec) + "\n")

def norm(kind, s):
    s = str(s).strip().strip("*").strip()
    try:
        if kind == "money": return round(float(re.sub(r"[^0-9.\-]", "", s)), 2)
        if kind == "int": return int(round(float(re.sub(r"[^0-9.\-]", "", s))))
        if kind == "clock":
            m = re.search(r"(\d{1,2}):(\d{2})", s); return int(m.group(1)) * 60 + int(m.group(2))
        if kind == "date": return re.search(r"\d{4}-\d{2}-\d{2}", s).group(0)
    except Exception: return None

def correct(task, got):
    k = task["kind"]; g = norm(k, got); t = norm(k, task["answer"])
    if g is None: return False
    if k == "money": return abs(g - t) <= 0.011
    if k in ("int", "clock"): return abs(g - t) <= 1
    return g == t

def solve_prompt(t):
    return (f"{t['q']}\n\nWork it out carefully. Finish with one final line exactly like:\nANSWER: <{FMT[t['kind']]}>")

def parse_answer(text):
    m = re.findall(r"ANSWER:\s*(.+)", text)
    return m[-1].strip() if m else None

def solve(model, t, effort="medium", summarize=False):
    t0 = time.time()
    kw = dict(model=model, max_tokens=16000, messages=[{"role": "user", "content": solve_prompt(t)}],
              output_config={"effort": effort})
    if summarize: kw["thinking"] = {"type": "adaptive", "display": "summarized"}
    r = client.messages.create(**kw)
    text = "".join(b.text for b in r.content if b.type == "text")
    thinking = "".join(getattr(b, "thinking", "") or "" for b in r.content if b.type == "thinking")
    ans = parse_answer(text)
    return dict(answer=ans, text=text, thinking=thinking, usage=r.usage.model_dump(), cost=cost(model, r.usage),
                secs=time.time() - t0, stop=r.stop_reason)

def arm_solve(arm, model, reps):
    jobs = [(t, rep) for t in TASKS for rep in range(reps)]
    def go(job):
        t, rep = job
        for attempt in range(3):
            try:
                o = solve(model, t, summarize=(arm == "opus"))
                rec = dict(arm=arm, id=t["id"], fam=t["fam"], split=t["split"], rep=rep, model=model, truth=t["answer"],
                           got=o["answer"], ok=correct(t, o["answer"]), cost=o["cost"], secs=o["secs"],
                           out_tokens=o["usage"]["output_tokens"], in_tokens=o["usage"]["input_tokens"],
                           stop=o["stop"], text=o["text"][-1500:], thinking=o["thinking"][:6000])
                log(rec); return rec
            except Exception as e:
                print("retry", t["id"], e); time.sleep(5)
    with cf.ThreadPoolExecutor(8) as ex:
        recs = list(ex.map(go, jobs))
    ok = sum(r["ok"] for r in recs if r); print(arm, ok, "/", len(recs), "cost", round(sum(r["cost"] for r in recs if r), 3))

# ---------------- build ----------------
class Param(BaseModel):
    name: str
    type: str
    description: str
class Entry(BaseModel):
    task_name: str
    description: str
    params: list[Param]
    code: str
    seed_params_json: str

BUILD_PROMPT = """You are building a reusable reasoning cache, like NVIDIA's CPU-ARC.
A strong model solved the problem below. Turn its reasoning into a cache entry that can answer NEW problems
of the same kind on a CPU, with no model doing the maths.

PROBLEM:
{q}

THE MODEL'S REASONING (summary) AND ANSWER:
{trace}
{answer_line}

Return:
- task_name: short snake_case name
- description: one or two sentences saying exactly which kind of problem this entry handles (so a router can match new problems)
- params: the inputs that may change between problems (name, type: number|string, description precise enough for a small model to extract them)
- code: a self-contained Python 3 function `def solve(**p):` (standard library only) that returns the final answer as a string formatted as {fmt}
- seed_params_json: a JSON object with the parameter values for THIS problem
"""

def build_entry(fam, seed_rec, seed_task, feedback=None):
    prompt = BUILD_PROMPT.format(q=seed_task["q"], trace=(seed_rec["thinking"] + "\n\n" + seed_rec["text"])[-9000:],
                                 answer_line=f"SOURCE MODEL ANSWER: {seed_rec['got']}", fmt=FMT[seed_task["kind"]])
    msgs = [{"role": "user", "content": prompt}]
    if feedback: msgs[0]["content"] += "\n\nA previous attempt failed this check, fix it:\n" + feedback
    r = client.messages.parse(model=OPUS, max_tokens=16000, messages=msgs, output_format=Entry, output_config={"effort": "high"})
    return r.parsed_output, cost(OPUS, r.usage), r.usage.output_tokens

def run_code(code, params):
    ns = {}
    exec(code, ns)
    t0 = time.perf_counter(); out = ns["solve"](**params); dt = time.perf_counter() - t0
    return str(out), dt

def build():
    seeds = {}
    for l in open(RES):
        r = json.loads(l)
        if r["arm"] == "opus" and r["split"] == "seed": seeds[r["fam"]] = r
    cache = {}
    for fam, sr in seeds.items():
        st = next(t for t in TASKS if t["id"] == f"{fam}_seed")
        total, tries, fb, verified = 0.0, 0, None, False
        while tries < 3:
            tries += 1
            e, c, ot = build_entry(fam, sr, st, fb); total += c
            try:
                out, _ = run_code(e.code, json.loads(e.seed_params_json))
                if norm(st["kind"], out) == norm(st["kind"], sr["got"]): verified = True; break
                fb = f"solve(seed params) returned {out!r} but the source answer is {sr['got']!r}."
            except Exception as ex:
                fb = "solve raised: " + "".join(traceback.format_exception_only(ex))
        cache[fam] = dict(e.model_dump(), build_cost=total, build_tries=tries, source_seed_cost=sr["cost"],
                          verified_vs_source=verified,
                          seed_truth=st["answer"], source_seed_answer=sr["got"])
        log(dict(arm="build", fam=fam, cost=total, tries=tries, task_name=e.task_name))
        print("built", fam, e.task_name, "tries", tries, "cost", round(total, 3))
    json.dump(cache, open(HERE / "cache.json", "w"), indent=1)

# ---------------- hit ----------------
class Hit(BaseModel):
    entry: str
    params_json: str
    unhandled_conditions: list[str]
    fits: bool

def catalog(cache):
    lines = []
    for fam, e in cache.items():
        ps = "; ".join(f"{p['name']} ({p['type']}): {p['description']}" for p in e["params"])
        lines.append(f"- entry `{e['task_name']}`: {e['description']}\n  params: {ps}")
    return "\n".join(lines)

HIT_PROMPT = """You route problems to a cache of solver functions and extract their inputs. Do NOT solve the problem.

CACHE ENTRIES:
{cat}

PROBLEM:
{q}

Return:
- entry: the task_name of the matching entry, or "none"
- params_json: a JSON object with a value for every param of that entry, taken from the problem (numbers as numbers)
- unhandled_conditions: any condition in the problem that the entry's params cannot express (empty list if none)
- fits: true only if the entry and its params capture the WHOLE problem"""

def hit():
    cache = json.load(open(HERE / "cache.json"))
    by_name = {e["task_name"]: (fam, e) for fam, e in cache.items()}
    cat = catalog(cache)
    jobs = [(t, rep) for t in TASKS if t["split"] != "seed" for rep in range(3)]
    def go(job):
        t, rep = job
        for attempt in range(3):
            try:
                t0 = time.time()
                r = client.messages.parse(model=HAIKU, max_tokens=4000, output_format=Hit, output_config={"effort": "low"},
                                          messages=[{"role": "user", "content": HIT_PROMPT.format(cat=cat, q=t["q"])}])
                h = r.parsed_output; c = cost(HAIKU, r.usage); lat = time.time() - t0
                got, cpu, err = None, None, None
                if h.entry in by_name:
                    try: got, cpu = run_code(by_name[h.entry][1]["code"], json.loads(h.params_json))
                    except Exception as ex: err = repr(ex)[:200]
                rec = dict(arm="cache", id=t["id"], fam=t["fam"], split=t["split"], rep=rep, truth=t["answer"], got=got,
                           ok=got is not None and correct(t, got), routed=h.entry,
                           routed_right=(h.entry in by_name and by_name[h.entry][0] == t["fam"]),
                           fits=h.fits, unhandled=h.unhandled_conditions, params=h.params_json, err=err,
                           cost=c, secs=lat, cpu_secs=cpu, out_tokens=r.usage.output_tokens, in_tokens=r.usage.input_tokens)
                log(rec); return rec
            except Exception as e:
                print("retry", t["id"], e); time.sleep(5)
    with cf.ThreadPoolExecutor(8) as ex:
        recs = list(ex.map(go, jobs))
    print("cache", sum(r["ok"] for r in recs), "/", len(recs), "cost", round(sum(r["cost"] for r in recs), 4))

if __name__ == "__main__":
    what = sys.argv[1]
    if what in ("opus", "all"): arm_solve("opus", OPUS, 1)
    if what in ("haiku", "all"): arm_solve("haiku", HAIKU, 3)
    if what in ("build", "all"): build()
    if what in ("hit", "all"): hit()
