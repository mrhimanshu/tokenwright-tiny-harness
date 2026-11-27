#!/usr/bin/env python3
"""Score every system's output against truth.json -> scores.jsonl + summary.json."""
import json, re, statistics as st
from collections import defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein

HERE = Path(__file__).resolve().parent
truth = json.loads((HERE / "truth.json").read_text())


def nemo_text(raw):
    t = re.sub(r"</?s>|<predict_[a-z_]+>|<output_[a-z_]+>|<no_[a-z]+>", "", raw)
    t = re.sub(r"<x_[0-9.]+><y_[0-9.]+>", "\n", t)
    t = re.sub(r"<class_[A-Za-z-]+>", "\n", t)
    return t


def clean(t):
    t = t.replace("\\$", "$").replace("\\%", "%").replace("\\&", "&")
    t = re.sub(r"\\thead\{([^}]*)\}", r"\1", t)
    t = re.sub(r"\\begin\{tabular\}\{[^}]*\}|\\end\{tabular\}|\\hline", "", t)
    t = re.sub(r"[*#`]", "", t)
    return t


def nows(t):
    return re.sub(r"\s+", "", t)


def cer(pred, ref):
    p, r = nows(pred), nows(ref)
    return Levenshtein.distance(p, r) / max(1, len(r))


def table_lines(t):
    rows = []
    for line in t.splitlines():
        line = line.strip().rstrip("\\").strip()
        if "&" in line:
            cells = [c.strip() for c in line.split("&")]
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
        else:
            continue
        rows.append([c for c in cells])
    return rows


def norm_cell(c):
    return re.sub(r"\s+", " ", c).strip().lower()


def score_table(text, tr):
    rows = table_lines(text)
    cells_ok = cells = rows_ok = 0
    for gt in tr["rows"]:
        best = None
        for r in rows:
            if r and norm_cell(r[0]) == norm_cell(gt[0]):
                best = r
                break
        if best is None:  # fuzzy first-cell match
            cand = [(Levenshtein.normalized_distance(norm_cell(r[0]), norm_cell(gt[0])), r) for r in rows if r]
            if cand:
                d, r = min(cand, key=lambda x: x[0])
                best = r if d < 0.3 else None
        ok = 0
        for j, g in enumerate(gt):
            cells += 1
            if best is not None and j < len(best) and norm_cell(best[j]) == norm_cell(g):
                ok += 1
        cells_ok += ok
        rows_ok += ok == len(gt)
    total_ok = tr["total"].replace(",", "") in nows(text).replace(",", "")
    return dict(cell_acc=cells_ok / cells, rows_ok=rows_ok, rows=len(tr["rows"]), total_ok=total_ok)


def score_chart(text, tr):
    rows = table_lines(text)
    errs, found = [], 0
    for cat, v in zip(tr["categories"], tr["values"]):
        val = None
        for r in rows:
            if r and norm_cell(r[0]) == norm_cell(cat) and len(r) > 1:
                m = re.search(r"-?\d+(\.\d+)?", r[1])
                if m:
                    val = float(m.group())
                break
        if val is None:
            errs.append(None)
        else:
            found += 1
            errs.append(abs(val - v))
    got = [e for e in errs if e is not None]
    return dict(found=found, n=len(tr["values"]), mae=(st.mean(got) if got else None),
                within2=sum(e <= 2 for e in got), exact=sum(e == 0 for e in got), errs=errs)


def main():
    recs = []
    for f in sorted((HERE / "results").glob("*.jsonl")):
        if f.name.startswith("smoke"):
            continue
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r["page"] not in truth:
                continue
            system = r["model"]
            rep = re.search(r"_r(\d)\.jsonl$", f.name)
            text = clean(nemo_text(r["raw"]) if system.startswith("parse") else r["raw"])
            tr = truth[r["page"]]
            s = dict(system=system, rep=int(rep.group(1)) if rep else 1, page=r["page"], kind=tr["kind"],
                     seconds=r["seconds"], cost_usd=r.get("cost_usd", 0.0))
            if tr["kind"] == "table":
                s.update(score_table(text, tr))
            elif tr["kind"] == "chart":
                s.update(score_chart(text, tr))
            else:
                s["cer"] = cer(text, tr["text"])
            recs.append(s)
    with (HERE / "scores.jsonl").open("w") as f:
        for s in recs:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    summ = defaultdict(dict)
    by = defaultdict(list)
    for s in recs:
        by[(s["system"], s["kind"])].append(s)
        by[(s["system"], "_all")].append(s)
    for (sys_, kind), L in sorted(by.items()):
        d = dict(n=len(L), sec_median=st.median(x["seconds"] for x in L),
                 cost_per_page=st.mean(x["cost_usd"] for x in L))
        if kind in ("report", "handwriting", "hindi"):
            d["cer_mean"] = round(st.mean(x["cer"] for x in L), 4)
            d["cer_pages"] = [round(x["cer"], 4) for x in L]
        elif kind == "table":
            d["cell_acc"] = round(st.mean(x["cell_acc"] for x in L), 4)
            d["rows_ok"] = f'{sum(x["rows_ok"] for x in L)}/{sum(x["rows"] for x in L)}'
            d["total_ok"] = f'{sum(x["total_ok"] for x in L)}/{len(L)}'
        elif kind == "chart":
            maes = [x["mae"] for x in L if x["mae"] is not None]
            d["mae"] = round(st.mean(maes), 2) if maes else None
            d["exact"] = f'{sum(x["exact"] for x in L)}/{sum(x["n"] for x in L)}'
            d["within2"] = f'{sum(x["within2"] for x in L)}/{sum(x["n"] for x in L)}'
            d["found"] = f'{sum(x["found"] for x in L)}/{sum(x["n"] for x in L)}'
        summ[sys_][kind] = d
    (HERE / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    for sys_, kinds in summ.items():
        print("==", sys_)
        for k, d in kinds.items():
            print("  ", k, {kk: vv for kk, vv in d.items() if kk not in ("cer_pages",)})


if __name__ == "__main__":
    main()
