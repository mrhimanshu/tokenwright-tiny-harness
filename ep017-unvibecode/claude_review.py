"""EP017 lab step 4: the 'just paste the repo into an LLM' baseline that UnvibeCode's README argues against.
Each model gets EXACTLY the files UnvibeCode uploads (built with its own pack(): same 18 files) as one plain text dump,
plus a one-paragraph ask. Haiku / Sonnet / Opus 5.5, adaptive thinking, effort high, n = 3 each.
Usage: ../.venv/bin/python lab/claude_review.py      -> lab/claude_reviews.jsonl  (+ lab/claude_out/<model>-<rep>.md)
"""
import concurrent.futures as cf, json, os, sys, time, zipfile, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "claude-opus-5-5": (4, 20)}  # $/M tokens, same table as EP016
N = 3
ASK = """You are reviewing this repository for an engineering manager who did not write it.
Find the business-logic defects: places where the code's behaviour can cost the business money, give customers something they should not get,
or break a stated business rule. For each finding give: file + function, the trigger (a concrete scenario), what happens, and the business impact.
List every real finding you are confident about, most serious first. Do not pad the list with style issues."""


def dump():
    sys.path.insert(0, "/tmp/unv_venv_dir/venv/lib/python3.11/site-packages")
    from unvibecode.archive import pack
    with tempfile.TemporaryDirectory() as t:
        z = Path(t) / "s.zip"
        pack(HERE / "shopfast", z)
        with zipfile.ZipFile(z) as zf:
            return "\n\n".join(f"===== {m} =====\n{zf.read(m).decode()}" for m in zf.namelist()), len(zf.namelist())


def main():
    import anthropic
    os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.config/anthropic/key")).read().strip()
    client = anthropic.Anthropic()
    text, nfiles = dump()
    prompt = f"<repository files=\"{nfiles}\">\n{text}\n</repository>\n\n{ASK}"
    (HERE / "claude_out").mkdir(exist_ok=True)
    out = open(HERE / "claude_reviews.jsonl", "a")

    def one(model, rep):
        f = HERE / "claude_out" / f"{model}-{rep}.md"
        if f.exists():
            return None
        for k in range(6):
            try:
                t0 = time.time()
                with client.messages.stream(model=model, max_tokens=24000, thinking={"type": "adaptive"}, output_config={"effort": "high"},
                                            messages=[{"role": "user", "content": prompt}]) as s:
                    r = s.get_final_message()
                txt = "".join(b.text for b in r.content if b.type == "text")
                f.write_text(txt)
                pi, po = PRICE[model]
                cost = (r.usage.input_tokens * pi + r.usage.output_tokens * po) / 1e6
                row = {"model": model, "rep": rep, "secs": round(time.time() - t0, 1), "in_tok": r.usage.input_tokens,
                       "out_tok": r.usage.output_tokens, "cost_usd": round(cost, 4), "file": f.name}
                out.write(json.dumps(row) + "\n"); out.flush()
                return row
            except Exception as e:
                print("retry", model, rep, repr(e)[:200], flush=True)
                time.sleep(10 * (k + 1))

    jobs = [(m, r) for m in PRICE for r in range(N)]
    with cf.ThreadPoolExecutor(9) as ex:
        for row in ex.map(lambda a: one(*a), jobs):
            print(row, flush=True)


if __name__ == "__main__":
    main()
