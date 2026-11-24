"""Measure the paper's difficulty features on human vs Claude answers (prose only, code removed on both sides).
Parser: spaCy en_core_web_md (the paper used en_core_web_trf). Writes metrics.jsonl, summary.json, examples.json."""
import json, re, random, collections, statistics as st
from pathlib import Path
import spacy

HERE = Path(__file__).parent
nlp = spacy.load("en_core_web_md", disable=["lemmatizer"] if False else [])
Q = {q["qid"]: q for q in json.load(open(HERE / "questions.json")) if q["human_words"] <= 1000}
GEN = [json.loads(l) for l in open(HERE / "gen.jsonl")]

ANIMATE = set("""argue claim suggest tell say think believe want know decide try expect assume prefer insist refuse explain ask
promise care complain hate love like understand see remember forget ignore recommend warn describe agree trust respect honor
complain notice guess wish hope intend choose learn admit deny pretend realize consider worry mind""".split())
PERSONAL = set("i you we he she they who me us them someone anyone everyone people user users developer developers team person "
               "author authors maintainer maintainers folks dev devs programmer programmers".split())

def clean_md(t, boundary=" "):
    t = re.sub(r"```.*?```", "\n", t, flags=re.S)
    t = re.sub(r"`[^`\n]*`", boundary, t)
    out = []
    for line in t.split("\n"):
        s = line.strip()
        if not s or s.startswith("|") or set(s) <= set("-=*_ "): continue
        s = re.sub(r"^#+\s*", "", s); s = re.sub(r"^([-*+]|\d+[.)])\s+", "", s)
        s = s.replace("**", "").replace("__", "")
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        s = re.sub(r"\s+", " ", s).strip()
        if len(s.split()) >= 4: out.append(s)
    return "\n".join(out)

def clean_human(t):
    return "\n".join(re.sub(r"\s+", " ", l).strip() for l in t.split("\n") if len(l.split()) >= 4)

BINS = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 30)]
def bin_of(n):
    for i, (a, b) in enumerate(BINS):
        if a <= n <= b: return i

def doc_feats(doc):
    words = [t for t in doc if not t.is_punct and not t.is_space]
    nw = len(words)
    sent_dl = []  # (bin, mean arc length)
    sent_lens = []
    for s in doc.sents:
        toks = [t for t in s if not t.is_punct and not t.is_space]
        n = len(toks)
        if n == 0: continue
        sent_lens.append(n)
        b = bin_of(n)
        if b is None: continue
        pos = {t.i: k for k, t in enumerate(toks)}
        arcs = [abs(pos[t.i] - pos[t.head.i]) for t in toks if t.dep_ != "ROOT" and t.head.i in pos]
        if arcs: sent_dl.append((b, sum(arcs) / len(arcs)))
    # stacked nouns: runs of >=3 adjacent NOUN/PROPN tokens
    stacks, run, stack_ex = 0, [], []
    for t in list(doc) + [None]:
        if t is not None and t.pos_ in ("NOUN", "PROPN") and not t.is_punct:
            run.append(t); continue
        if len(run) >= 3:
            stacks += 1; stack_ex.append(" ".join(x.text for x in run))
        run = []
    # inanimate subject + animate verb (active nsubj)
    inan, inan_ex = 0, []
    for t in doc:
        if t.dep_ == "nsubj" and t.head.pos_ in ("VERB", "AUX") and t.head.lemma_.lower() in ANIMATE:
            w = t.text.lower()
            if w in PERSONAL or t.ent_type_ in ("PERSON", "ORG", "NORP"): continue
            if t.pos_ == "PRON" and w not in ("it", "this", "that", "which"): continue
            inan += 1; inan_ex.append(t.sent.text.strip())
    return dict(words=nw, sent_dl=sent_dl, mean_sent_len=st.mean(sent_lens) if sent_lens else 0,
                stacks=stacks, inan=inan, stack_ex=stack_ex, inan_ex=inan_ex)

def bigrams(text):
    out = []
    for seg in re.split(r"[|\n,;:.()!?\"\[\]{}/→—–]", text.lower()):
        w = re.findall(r"[a-z]+(?:'[a-z]+)?", seg)
        out += list(zip(w, w[1:]))
    return out

def main():
    ref = (HERE / "ref_corpus.txt").read_text()
    REF = set()
    for line in ref.split("\n"): REF.update(bigrams(line))
    items = [dict(kind="human", model="human", cond="human", qid=qid, text=clean_human(q["human"])) for qid, q in Q.items()]
    items += [dict(kind="claude", model=g["model"], cond=g["cond"], qid=g["qid"], text=clean_md(g["text"]), btext=clean_md(g["text"], " | ")) for g in GEN if g["qid"] in Q]
    # bin weights from the human reference corpus (direct standardisation, like the paper's Wikipedia weights)
    cnt = collections.Counter()
    for d in nlp.pipe(ref.split("\n")[:1500], batch_size=64):
        for s in d.sents:
            b = bin_of(len([t for t in s if not t.is_punct and not t.is_space]))
            if b is not None: cnt[b] += 1
    W = [cnt[i] / sum(cnt.values()) for i in range(len(BINS))]
    rows = []
    docs = nlp.pipe([it["text"] for it in items], batch_size=16, n_process=4)
    for it, doc in zip(items, docs):
        f = doc_feats(doc)
        bg = bigrams(it.get("btext", it["text"])); un = [b for b in bg if b not in REF]
        per_bin = collections.defaultdict(list)
        for b, v in f["sent_dl"]: per_bin[b].append(v)
        # standardised DL: weighted mean over bins present (renormalised)
        ws = [(W[b], st.mean(v)) for b, v in per_bin.items()]
        dl = sum(w * v for w, v in ws) / sum(w for w, _ in ws) if ws else None
        r = dict(kind=it["kind"], model=it["model"], cond=it["cond"], qid=it["qid"], words=f["words"],
                 dep_len=dl, sent_len=f["mean_sent_len"],
                 stacks_pk=1000 * f["stacks"] / max(f["words"], 1), inan_pk=1000 * f["inan"] / max(f["words"], 1),
                 unatt_pk=1000 * len(un) / max(len(bg), 1),
                 stack_ex=f["stack_ex"][:5], inan_ex=f["inan_ex"][:5], unatt_ex=[" ".join(b) for b in un[:8]])
        rows.append(r)
    with open(HERE / "metrics.jsonl", "w") as fo:
        for r in rows: fo.write(json.dumps(r) + "\n")
    metrics = ["words", "sent_len", "dep_len", "stacks_pk", "inan_pk", "unatt_pk"]
    groups = collections.defaultdict(list)
    for r in rows: groups[f"{r['model']}|{r['cond']}"].append(r)
    random.seed(7)
    summ = {"bin_weights": W, "n_questions": len(Q), "groups": {}}
    for g, rs in groups.items():
        d = {"n": len(rs)}
        for m in metrics:
            vals = [r[m] for r in rs if r[m] is not None]
            boots = sorted(st.mean(random.choices(vals, k=len(vals))) for _ in range(2000))
            d[m] = dict(mean=st.mean(vals), median=st.median(vals), lo=boots[50], hi=boots[1949])
        summ["groups"][g] = d
    # paired: per question, Claude minus human, share of questions where Claude is higher
    hum = {r["qid"]: r for r in rows if r["kind"] == "human"}
    summ["paired"] = {}
    for g, rs in groups.items():
        if g.startswith("human"): continue
        p = {}
        for m in metrics:
            pairs = [(r[m], hum[r["qid"]][m]) for r in rs if r[m] is not None and hum[r["qid"]][m] is not None]
            p[m] = dict(higher=sum(a > b for a, b in pairs), n=len(pairs))
        summ["paired"][g] = p
    json.dump(summ, open(HERE / "summary.json", "w"), indent=1)
    for g, d in sorted(summ["groups"].items()):
        print(f"{g:28s} n={d['n']:3d} " + " ".join(f"{m}={d[m]['mean']:.2f}[{d[m]['lo']:.2f},{d[m]['hi']:.2f}]" for m in metrics))

if __name__ == "__main__":
    main()
