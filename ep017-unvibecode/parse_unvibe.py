"""EP017: parse the 3 UnvibeCode report folders -> unvibe_results.jsonl (findings, workflows, secrets echoed back)."""
import json, re, html, zipfile, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
S = json.load(open(HERE / "fake_secrets.json"))
def text_of(p):
    t = p.read_text("utf-8", "replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
out = open(HERE / "unvibe_results.jsonl", "w")
for i in (1, 2, 3):
    d = next((HERE / f"unvibe_run{i}").glob("shopfast-*"))
    log = (HERE / f"unvibe_run{i}.log").read_text()
    secs = re.findall(r"REVIEW COMPLETE · (\d+)s", log)
    echoes = {}
    for p in d.rglob("*"):
        if not p.is_file(): continue
        parts = [(p.name, p.read_bytes().decode("utf-8", "replace"))]
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                parts = [(p.name + ":" + m, z.read(m).decode("utf-8", "replace")) for m in z.namelist()]
        for name, b in parts:
            for k, v in S.items():
                if v["value"] in b: echoes.setdefault(k, []).append(name)
    risk = text_of(d / "report-support/risk-findings.html")
    wf = text_of(d / "report-support/business-workflows.html")
    m = re.search(r"(\d+) reportable findings", risk)
    row = {"run": i, "review_secs": int(secs[0]) if secs else None,
           "reportable_findings": int(m.group(1)) if m else None,
           "candidates": (re.search(r"(\d+) candidate", risk) or [None, None])[1],
           "workflows_listed": re.findall(r"^\s*\d+\. (.+)$", log, re.M),
           "secrets_echoed_back": echoes, "risk_text": risk[:3000], "workflow_text": wf[:6000]}
    out.write(json.dumps(row) + "\n")
    print(i, row["review_secs"], "findings", row["reportable_findings"], "cand", row["candidates"], row["workflows_listed"], {k: v for k, v in echoes.items()})
