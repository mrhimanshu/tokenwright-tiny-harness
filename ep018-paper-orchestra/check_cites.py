"""Cite keys used in a .tex vs keys defined in its .bib. usage: check_cites.py <paper.tex> <references.bib>"""
import sys, re, json
tex = open(sys.argv[1]).read(); bib = open(sys.argv[2]).read()
tex = re.sub(r"(?<!\\)%.*", "", tex)
used = []
for m in re.finditer(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", tex):
    used += [k.strip() for k in m.group(1).split(",") if k.strip()]
defined = set(k.strip() for k in re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib))
u = sorted(set(used))
print(json.dumps(dict(cite_calls=len(used), unique_used=len(u), defined=len(defined), missing=[k for k in u if k not in defined],
                      unused=sorted(defined - set(u)))))
