import json, collections, statistics as st
R = [json.loads(l) for l in open("results.jsonl")]
cache = json.load(open("cache.json"))
def grp(f):
    d = collections.defaultdict(list)
    for r in R:
        if f(r): d[(r["arm"], r.get("split"))].append(r)
    return d
G = grp(lambda r: r["arm"] in ("opus", "haiku", "cache"))
S = {"groups": {}, "fam": {}}
for (arm, sp), rs in sorted(G.items()):
    S["groups"][f"{arm}|{sp}"] = dict(n=len(rs), ok=sum(r["ok"] for r in rs), acc=sum(r["ok"] for r in rs) / len(rs),
        mean_cost=st.mean(r["cost"] for r in rs), mean_secs=st.mean(r["secs"] for r in rs),
        mean_out=st.mean(r["out_tokens"] for r in rs), mean_in=st.mean(r["in_tokens"] for r in rs))
    print(f"{arm:6} {sp:6} {S['groups'][f'{arm}|{sp}']}")
# per family accuracy
for arm in ("opus", "haiku", "cache"):
    for fam in cache:
        for sp in ("same", "shift"):
            rs = [r for r in R if r["arm"] == arm and r["fam"] == fam and r.get("split") == sp]
            if rs: S["fam"][f"{arm}|{fam}|{sp}"] = f"{sum(r['ok'] for r in rs)}/{len(rs)}"
print(json.dumps(S["fam"], indent=0))
C = [r for r in R if r["arm"] == "cache"]
# guard: fits flag
for sp in ("same", "shift"):
    rs = [r for r in C if r["split"] == sp]
    fits = [r for r in rs if r["fits"]]
    print(sp, "routed right", sum(r["routed_right"] for r in rs), "/", len(rs), "fits=True", len(fits),
          "ok&fits", sum(r["ok"] for r in fits), "wrong&fits(silent)", sum(not r["ok"] for r in fits), "errors", sum(1 for r in rs if r["err"]))
# guarded cache: fits -> cache answer, not fits -> opus fresh (same item)
opus = {r["id"]: r for r in R if r["arm"] == "opus"}
for sp in ("same", "shift"):
    rs = [r for r in C if r["split"] == sp]
    ok = sum(r["ok"] if r["fits"] else opus[r["id"]]["ok"] for r in rs)
    c = st.mean(r["cost"] + (0 if r["fits"] else opus[r["id"]]["cost"]) for r in rs)
    S["groups"][f"guarded|{sp}"] = dict(n=len(rs), ok=ok, acc=ok / len(rs), mean_cost=c, fallbacks=sum(not r["fits"] for r in rs))
    print("guarded", sp, S["groups"][f"guarded|{sp}"])
# shift cases where answer equals the no-shift answer would be (cache wrong?)
for r in C:
    if not r["ok"]: print("WRONG", r["id"], r["rep"], "truth", r["truth"], "got", r["got"], "fits", r["fits"], r["unhandled"][:2], r["err"], r["params"][:120])
build = sum(e["build_cost"] for e in cache.values()); seeds = sum(e["source_seed_cost"] for e in cache.values())
S["build_cost_total"] = build; S["seed_cost_total"] = seeds
cpu = [r["cpu_secs"] for r in C if r["cpu_secs"] is not None]
S["cpu_secs_median"] = st.median(cpu); S["cpu_secs_max"] = max(cpu)
o = S["groups"]["opus|same"]["mean_cost"]; h = S["groups"]["cache|same"]["mean_cost"]; hk = S["groups"]["haiku|same"]["mean_cost"]
S["savings_x_vs_opus"] = o / h; S["haiku_vs_cache_x"] = hk / h
S["break_even_calls"] = (build) / (o - h)
S["break_even_incl_seed"] = (build + seeds) / (o - h)
for k in ("build_cost_total", "seed_cost_total", "cpu_secs_median", "cpu_secs_max", "savings_x_vs_opus", "haiku_vs_cache_x", "break_even_calls", "break_even_incl_seed"): print(k, S[k])
print("total spend", sum(r.get("cost", 0) for r in R))
S["total_spend"] = sum(r.get("cost", 0) for r in R)
json.dump(S, open("summary.json", "w"), indent=1)
