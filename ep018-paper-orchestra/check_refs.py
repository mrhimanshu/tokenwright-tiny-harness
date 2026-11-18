"""Check every BibTeX entry: does a paper with this title exist, with this first author? Sources: Crossref + arXiv API
(OpenAlex's free daily budget ran out on 18 Nov). usage: check_refs.py <references.bib> <out.jsonl>"""
import sys, re, json, time, requests, unicodedata
import xml.etree.ElementTree as ET
from thefuzz import fuzz
UA = {"User-Agent": "tokenwright-lab/1.0 (mailto:tokenwright.lab@gmail.com)"}
def fold(x):
    x = re.sub(r"\\[a-zA-Z]+\s*|\\.|[{}'`\"^~]", "", x or "")
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().strip()
def field(e, k):
    m = re.search(r"\b" + k + r"\s*=\s*(\{((?:[^{}]|\{[^{}]*\})*)\}|\"([^\"]*)\")", e, re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"[{}]", "", (m.group(2) or m.group(3) or ""))).strip() if m else ""
def get(url, params):
    for i in range(5):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200: return r
        except Exception: pass
        time.sleep(3 * (i + 1))
    return None
def crossref(title):
    r = get("https://api.crossref.org/works", {"query.bibliographic": title[:300], "rows": 5, "select": "title,author,issued"})
    if r is None: return None
    out = []
    for w in r.json()["message"]["items"]:
        out.append(dict(title=(w.get("title") or [""])[0], authors=[(a.get("family") or "") + " " + (a.get("given") or "") for a in w.get("author", [])],
                        year=((w.get("issued") or {}).get("date-parts") or [[None]])[0][0], src="crossref"))
    return out
def arxiv(title):
    q = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", fold(title))).strip()
    r = get("https://export.arxiv.org/api/query", {"search_query": f'ti:"{q}"', "max_results": 5})
    if r is None: return None
    ns = {"a": "http://www.w3.org/2005/Atom"}; out = []
    for e in ET.fromstring(r.text).findall("a:entry", ns):
        out.append(dict(title=re.sub(r"\s+", " ", e.find("a:title", ns).text), authors=[a.find("a:name", ns).text for a in e.findall("a:author", ns)],
                        year=int(e.find("a:published", ns).text[:4]), src="arxiv"))
    return out
def s2(title):
    r = get("https://api.semanticscholar.org/graph/v1/paper/search/match", {"query": title[:300], "fields": "title,authors,year"})
    if r is None: return []
    return [dict(title=w.get("title") or "", authors=[a["name"] for a in w.get("authors", [])], year=w.get("year"), src="s2") for w in r.json().get("data", [])]
bib = open(sys.argv[1]).read()
out = open(sys.argv[2], "w")
for e in re.split(r"\n(?=\s*@)", "\n" + bib):
    m = re.match(r"\s*@(\w+)\s*{\s*([^,]+),", e)
    if not m or m.group(1).lower() in ("comment", "string", "preamble"): continue
    key, title, year, author = m.group(2).strip(), field(e, "title"), field(e, "year"), field(e, "author")
    fa = author.split(" and ")[0]
    surname = fold(fa.split(",")[0] if "," in fa else (fa.split()[-1] if fa.split() else ""))
    rec = dict(key=key, type=m.group(1).lower(), title=title, year=year, first_author=fa[:60])
    cands, err = [], 0
    for fn in (crossref, arxiv, s2):
        c = fn(title) if title else []
        if c is None: err += 1; c = []
        cands += c
        best = max(cands, key=lambda w: fuzz.ratio(fold(title), fold(w["title"])), default=None)
        if best and fuzz.ratio(fold(title), fold(best["title"])) >= 90: break
        time.sleep(1)
    score = fuzz.ratio(fold(title), fold(best["title"])) if best else 0
    rec["match_score"] = score
    if best:
        rec.update(found_title=best["title"], found_year=best["year"], found_src=best["src"], found_authors=best["authors"][:6])
        rec["author_ok"] = bool(surname) and any(fuzz.partial_ratio(surname, fold(a)) >= 85 for a in best["authors"])
    rec["status"] = ("api_error" if err >= 2 else "verified" if score >= 90 and rec.get("author_ok") else
                     "title_ok_author_wrong" if score >= 90 else "not_found")
    out.write(json.dumps(rec) + "\n"); out.flush(); time.sleep(1)
