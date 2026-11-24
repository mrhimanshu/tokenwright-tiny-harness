"""Fetch human Stack Overflow data (public StackExchange API, no key).
1) questions.json: 40 recent, well-received questions with an accepted human answer (prose >= 80 words).
2) ref_corpus.txt: prose of ~3,000 other answers (n-gram reference, like the paper's StackExchange sample).
Answers posted before 30 Nov 2022 (pre-ChatGPT) only, so the human side is human."""
import json, re, time, requests
from pathlib import Path
from bs4 import BeautifulSoup

HERE = Path(__file__).parent
API = "https://api.stackexchange.com/2.3"
S = requests.Session()
CUTOFF = 1669766400  # 2022-11-30

def get(path, **p):
    p.setdefault("site", "stackoverflow")
    for _ in range(5):
        r = S.get(API + path, params=p, timeout=60)
        if r.status_code == 200:
            j = r.json()
            if j.get("backoff"): time.sleep(j["backoff"] + 1)
            return j
        time.sleep(5)
    r.raise_for_status()

def prose(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["pre", "code", "blockquote", "table", "img"]): t.decompose()
    paras = [re.sub(r"\s+", " ", x.get_text(" ")).strip() for x in soup.find_all(["p", "li"])]
    return "\n".join(p for p in paras if len(p.split()) >= 4)

def words(s): return len(s.split())

if __name__ == "__main__":
    # test questions: accepted answers, 2019-2022, mixed tags
    qs, seen = [], set()
    for tag in ["python", "javascript", "git", "sql", "docker", "reactjs", "bash", "typescript"]:
        j = get("/questions", tagged=tag, sort="votes", order="desc", pagesize=40, fromdate=1546300800,
                todate=CUTOFF, filter="withbody")
        for q in j["items"]:
            if not q.get("accepted_answer_id") or q["question_id"] in seen: continue
            seen.add(q["question_id"]); qs.append(q)
        time.sleep(0.5)
    ids = [q["accepted_answer_id"] for q in qs]
    ans = {}
    for i in range(0, len(ids), 100):
        j = get("/answers/" + ";".join(map(str, ids[i:i+100])), filter="withbody", pagesize=100)
        for a in j["items"]: ans[a["answer_id"]] = a
        time.sleep(0.5)
    out = []
    for q in qs:
        a = ans.get(q["accepted_answer_id"])
        if not a or a["creation_date"] > CUTOFF: continue
        p = prose(a["body"])
        qtext = BeautifulSoup(q["body"], "html.parser").get_text("\n").strip()
        if words(p) < 80 or len(qtext) > 4000: continue
        out.append(dict(qid=q["question_id"], tag=q["tags"][0], title=BeautifulSoup(q["title"], "html.parser").get_text(),
                        question=qtext, human=p, human_words=words(p), answer_id=a["answer_id"],
                        link=f"https://stackoverflow.com/a/{a['answer_id']}", answer_date=a["creation_date"]))
    # pick 5 per tag, up to 40
    by = {}
    for o in out: by.setdefault(o["tag"], []).append(o)
    pick = [o for t in by for o in by[t][:5]][:40]
    json.dump(pick, open(HERE / "questions.json", "w"), indent=1)
    print("questions", len(pick), {t: len(v[:5]) for t, v in by.items()})
    # reference corpus: top answers 2015-2022, excluding test answers
    skip = {o["answer_id"] for o in pick}
    texts, n = [], 0
    for page in range(1, 26):
        j = get("/answers", sort="votes", order="desc", pagesize=100, page=page, fromdate=1420070400,
                todate=CUTOFF, filter="withbody")
        for a in j["items"]:
            if a["answer_id"] in skip: continue
            p = prose(a["body"])
            if p: texts.append(p); n += words(p)
        if not j.get("has_more"): break
        time.sleep(0.7)
    (HERE / "ref_corpus.txt").write_text("\n".join(texts))
    print("ref answers", len(texts), "words", n)
