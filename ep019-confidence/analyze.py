"""EP019: score results.jsonl -> scored.jsonl + summary.json + prints a table.
Metrics per model: accuracy, mean stated confidence, ECE (10 bins, in points), share auto-approved (conf >= 90), error rate inside the
auto-approved set, made-up values on absent fields, and the same with agreement-across-3-runs as the confidence."""
import collections
import json
import os
import re
import sys

TAG = sys.argv[1] if len(sys.argv) > 1 else ""

HERE = os.path.dirname(os.path.abspath(__file__))
docs = {d["doc_id"]: d for d in map(json.loads, open(os.path.join(HERE, f"docs{TAG}.jsonl")))}


def norm(v, kind):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("", "null", "none", "not found", "n/a"):
        return None
    if kind == "money":
        s = re.sub(r"[^\d.,-]", "", s)
        if re.search(r",\d{2}$", s):
            s = s.replace(".", "").replace(",", ".")
        s = s.replace(",", "")
        try:
            return f"{float(s):.2f}"
        except ValueError:
            return s
    if kind == "int":
        m = re.search(r"-?\d+", s)
        return m.group(0) if m else s
    return s.upper().replace(" ", "")


def score():
    rows = []
    for l in open(os.path.join(HERE, f"results{TAG}.jsonl")):
        r = json.loads(l)
        if not r.get("parsed"):
            continue
        d = docs[r["doc_id"]]
        for q in d["questions"]:
            a = r["parsed"].get(q["id"], {}) or {}
            ans = norm(a.get("answer"), q["kind"])
            truth = norm(q["truth"], q["kind"])
            try:
                conf = float(a.get("confidence"))
            except (TypeError, ValueError):
                conf = None
            rows.append({"doc_id": r["doc_id"], "model": r["model"], "rep": r["rep"], "qid": q["id"], "truth": truth, "answer": ans,
                         "correct": ans == truth, "conf": conf, "absent": truth is None, "traits": d["traits"]})
    return rows


def ece(pairs, bins=10):
    pairs = [(c, k) for c, k in pairs if c is not None]
    if not pairs:
        return None
    tot = 0
    for b in range(bins):
        lo, hi = b * 100 / bins, (b + 1) * 100 / bins
        sel = [(c, k) for c, k in pairs if (lo <= c < hi) or (b == bins - 1 and c == 100)]
        if sel:
            tot += len(sel) * abs(sum(c for c, _ in sel) / len(sel) - 100 * sum(k for _, k in sel) / len(sel))
    return round(tot / len(pairs), 1)


def main():
    rows = score()
    with open(os.path.join(HERE, f"scored{TAG}.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    out = {}
    models = sorted({r["model"] for r in rows}, key=lambda m: ["haiku", "sonnet", "opus"].index(m.split("-")[1]))
    # agreement: share of the model's runs giving the same answer as this run
    grp = collections.defaultdict(list)
    for r in rows:
        grp[(r["model"], r["doc_id"], r["qid"])].append(r["answer"])
    for r in rows:
        g = grp[(r["model"], r["doc_id"], r["qid"])]
        r["agree"] = 100 * g.count(r["answer"]) / len(g)
    for m in models:
        R = [r for r in rows if r["model"] == m]
        n = len(R)
        acc = sum(r["correct"] for r in R) / n
        confs = [r["conf"] for r in R if r["conf"] is not None]
        hi = [r for r in R if r["conf"] is not None and r["conf"] >= 90]
        wrong = [r for r in R if not r["correct"]]
        absent = [r for r in R if r["absent"]]
        madeup = [r for r in absent if r["answer"] is not None]
        missed = [r for r in R if not r["absent"] and r["answer"] is None]
        by_q = {}
        for q in sorted({r["qid"] for r in R}):
            Q = [r for r in R if r["qid"] == q]
            by_q[q] = {"n": len(Q), "acc": round(100 * sum(r["correct"] for r in Q) / len(Q), 1),
                       "mean_conf": round(sum(r["conf"] or 0 for r in Q) / len(Q), 1),
                       "wrong": sum(not r["correct"] for r in Q),
                       "wrong_conf_ge90": sum((not r["correct"]) and (r["conf"] or 0) >= 90 for r in Q)}
        # agreement-based: a 3/3 agreement auto-approves
        agree_hi = [r for r in R if r["agree"] == 100]
        out[m] = {
            "n": n, "accuracy": round(100 * acc, 1), "mean_conf": round(sum(confs) / len(confs), 1),
            "ece": ece([(r["conf"], r["correct"]) for r in R]),
            "wrong": len(wrong), "wrong_conf_mean": round(sum(r["conf"] or 0 for r in wrong) / max(1, len(wrong)), 1),
            "wrong_conf_ge90": sum((r["conf"] or 0) >= 90 for r in wrong),
            "auto_approved": len(hi), "auto_share": round(100 * len(hi) / n, 1),
            "auto_error_rate": round(100 * sum(not r["correct"] for r in hi) / max(1, len(hi)), 2),
            "absent_n": len(absent), "made_up": len(madeup), "made_up_conf_mean": round(sum(r["conf"] or 0 for r in madeup) / max(1, len(madeup)), 1),
            "missed_present": len(missed),
            "agree_auto": len(agree_hi), "agree_auto_error_rate": round(100 * sum(not r["correct"] for r in agree_hi) / max(1, len(agree_hi)), 2),
            "agree_ece": ece([(r["agree"], r["correct"]) for r in R]),
            "conf_hist": collections.Counter(int(c // 10 * 10) if c < 100 else 100 for c in confs).most_common(),
            "by_question": by_q,
        }
    json.dump(out, open(os.path.join(HERE, f"summary{TAG}.json"), "w"), indent=1)
    for m, s in out.items():
        print(f"\n== {m}  n={s['n']}  acc {s['accuracy']}%  mean conf {s['mean_conf']}  ECE {s['ece']}  wrong {s['wrong']} (mean conf {s['wrong_conf_mean']}, {s['wrong_conf_ge90']} at >=90)")
        print(f"   auto-approved {s['auto_approved']} ({s['auto_share']}%), error inside {s['auto_error_rate']}%  | made-up on absent {s['made_up']}/{s['absent_n']} (conf {s['made_up_conf_mean']}) | missed {s['missed_present']}")
        print(f"   3/3 agreement auto {s['agree_auto']}, error inside {s['agree_auto_error_rate']}%, agree-ECE {s['agree_ece']}")
        for q, b in s["by_question"].items():
            print(f"     {q:15} acc {b['acc']:5}  conf {b['mean_conf']:5}  wrong {b['wrong']:3} (>=90: {b['wrong_conf_ge90']})")


if __name__ == "__main__":
    main()


def sweep():
    rows = score()
    res = {}
    for m in sorted({r["model"] for r in rows}):
        R = [r for r in rows if r["model"] == m and r["conf"] is not None]
        res[m] = []
        for th in (50, 60, 70, 75, 80, 85, 90, 95):
            A = [r for r in R if r["conf"] >= th]
            res[m].append({"th": th, "auto_share": round(100 * len(A) / len(R), 1), "errors_auto": sum(not r["correct"] for r in A),
                           "correct_sent_to_human": sum(r["correct"] and r["conf"] < th for r in R)})
    json.dump(res, open(os.path.join(HERE, f"sweep{TAG}.json"), "w"), indent=1)
    for m, s in res.items():
        print(m, " | ".join(f"{x['th']}: auto {x['auto_share']}% err {x['errors_auto']} humanOK {x['correct_sent_to_human']}" for x in s))


if __name__ == "__main__" and os.environ.get("SWEEP"):
    sweep()
