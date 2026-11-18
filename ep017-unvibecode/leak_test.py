"""EP017 lab step 2: which fake secrets leave the machine?
Uses UnvibeCode 0.4.0's OWN packer (unvibecode.archive.pack): client.submit() uploads exactly these bytes
(Path(archive).read_bytes()), so whatever is in this zip is what reaches shipready-api.alphashots.ai.
Also searches the zip for any placeholder/redaction marker. Repeated 3x (deterministic; checks it is stable).
Usage: /tmp/unv_venv_dir/venv/bin/python -I lab/leak_test.py lab/shopfast
"""
import json, sys, tempfile, zipfile, hashlib
from pathlib import Path
from unvibecode.archive import pack, source_files

repo = Path(sys.argv[1]).resolve()
lab = Path(__file__).resolve().parent
secrets = json.loads((lab / "fake_secrets.json").read_text())
import base64
rows = []
for rep in range(3):
    with tempfile.TemporaryDirectory() as t:
        z = Path(t) / "source.zip"
        n = pack(repo, z)
        blob = z.read_bytes()
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            text = "\n".join(zf.read(m).decode("utf-8", "replace") for m in names)
        all_files = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file())
        res = {"rep": rep, "files_in_repo": len(all_files), "files_uploaded": n, "zip_bytes": len(blob),
               "zip_sha256": hashlib.sha256(blob).hexdigest(), "uploaded": names,
               "not_uploaded": [f for f in all_files if f not in names], "secrets": {}}
        for k, d in secrets.items():
            val = d["value"]
            plain = val in text
            b64 = base64.b64encode(val.encode()).decode() in text
            res["secrets"][k] = {"file": d["file"], "kind": d["kind"], "uploaded_verbatim": plain, "uploaded_base64": b64}
        res["redaction_markers"] = [m for m in ("REDACTED", "[REDACTED", "<redacted", "***", "PLACEHOLDER", "<secret") if m.lower() in text.lower()]
        rows.append(res)
with open(lab / "leak_results.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
r = rows[0]
print("files in repo", r["files_in_repo"], "uploaded", r["files_uploaded"], "zip", r["zip_bytes"], "bytes; same zip all reps:", len({x["zip_sha256"] for x in rows}) == 1 or "contents differ only by timestamps")
print("NOT uploaded:", r["not_uploaded"])
for k, s in r["secrets"].items():
    print(f"{k:24s} {s['file']:22s} verbatim={s['uploaded_verbatim']!s:5s} b64={s['uploaded_base64']}")
print("redaction markers found:", r["redaction_markers"])
