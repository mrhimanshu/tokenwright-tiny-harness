"""Audit every number-bearing sentence of a paper .tex against the raw materials, with Claude Sonnet 5.5 as the judge.
usage: check_numbers.py <paper.tex> <out.jsonl>"""
import sys, os, re, json, anthropic
HERE = os.path.dirname(os.path.abspath(__file__))
tex = open(sys.argv[1]).read()
body = tex[tex.find("\\begin{document}"):] if "\\begin{document}" in tex else tex
body = re.sub(r"(?<!\\)%.*", "", body)
body = body.split("\\bibliography")[0]
# split into sentences, keep those with a digit (ignoring \ref/\cite/\label args and section numbers)
clean = re.sub(r"\\(ref|cite[pt]?|citep|citet|label|includegraphics|eqref|url|vspace|hspace)(\[[^\]]*\])?\{[^}]*\}", "", body)
sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\s*\n|\\\\", clean) if re.search(r"\d", s) and len(s.strip()) > 12]
mats = open(os.path.join(HERE, "raw_materials/idea_sparse.md")).read() + "\n\n" + open(os.path.join(HERE, "raw_materials/experimental_log.md")).read()
c = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip())
out = open(sys.argv[2], "w")
B = 15
for i in range(0, len(sents), B):
    chunk = sents[i:i+B]
    listing = "\n".join(f"[{j}] {s[:700]}" for j, s in enumerate(chunk))
    prompt = f"""You are auditing a generated paper against the ONLY source material the authors had (below).
For each numbered sentence, look at every quantitative claim (numbers, percentages, counts, times, costs, ratios).
Label the sentence:
- "supported": every number is in the materials or follows by simple arithmetic from them, and is attributed correctly
  (e.g. our CPU measurements vs the original paper's own numbers).
- "invented": at least one number does not appear in and cannot be derived from the materials (made up).
- "wrong": at least one number contradicts the materials, or is attributed to the wrong thing/model/source.
- "no_claim": the digits are not quantitative claims (equation numbers, years in citations, model names like 'Opus 5.5', section labels, template text).
Return ONLY a JSON list of objects {{"i": <index>, "label": ..., "number": "<the offending or main number>", "why": "<max 25 words>"}}.

=== MATERIALS ===
{mats}

=== SENTENCES ===
{listing}"""
    for attempt in range(3):
        r = c.messages.create(model="claude-sonnet-5-5", max_tokens=8000, messages=[{"role": "user", "content": prompt}])
        t = "".join(b.text for b in r.content if b.type == "text")
        m = re.search(r"\[.*\]", t, re.S)
        try:
            labs = json.loads(m.group(0)); break
        except Exception: labs = []
    for l in labs:
        j = l.get("i")
        if isinstance(j, int) and j < len(chunk):
            l["sentence"] = chunk[j]; l["i"] = i + j
            out.write(json.dumps(l) + "\n")
    out.flush()
print(sys.argv[1], len(sents), "number sentences")
