"""Same 48 DecisionPivot items, asked to Claude as plain text (no read-out API), n runs each.
Usage: ../../.venv/bin/python run_claude.py <model> [runs]   Appends to results_claude.jsonl"""
import json, os, re, sys, time
import anthropic
HERE = os.path.dirname(os.path.abspath(__file__))
client = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip())
ITEMS = [json.loads(l) for l in open(os.path.join(HERE, "items_selected.jsonl"))]
OUT = os.path.join(HERE, "results_claude.jsonl")


def prompt(it):
    q = it["questions"]["q"]
    state = it["state"] if isinstance(it["state"], str) else json.dumps(it["state"], indent=1)
    opts = "\n".join(f"- {k}: {v}" for k, v in q["criteria"].items())
    return (f"STATE:\n{state}\n\nQUESTION: {q['instructions']}\nOPTIONS:\n{opts}\n\n"
            "Decide carefully. End your reply with one final line of the form ANSWER: yes or ANSWER: no")


def main():
    model = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for run in range(runs):
        for it in ITEMS:
            t = time.time()
            rec = {"model": model, "run": run, "id": it["id"], "family": it["family"], "group": it["group"], "gold": it["gold"]}
            try:
                r = client.messages.create(model=model, max_tokens=8000, messages=[{"role": "user", "content": prompt(it)}])
                text = "".join(b.text for b in r.content if b.type == "text")
                m = re.findall(r"ANSWER:\s*\**\s*(yes|no)", text, re.I)
                rec.update(choice=m[-1].lower() if m else None, in_tokens=r.usage.input_tokens, out_tokens=r.usage.output_tokens,
                           stop=r.stop_reason, tail=text[-300:])
            except Exception as e:
                rec["error"] = repr(e)[:300]
            rec["secs"] = round(time.time() - t, 2)
            rec["right"] = rec.get("choice") == it["gold"]
            rec["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            open(OUT, "a").write(json.dumps(rec) + "\n")
            print(model, run, it["id"], it["gold"], rec.get("choice"), "OK" if rec["right"] else "x", rec.get("out_tokens"), rec["secs"], flush=True)


if __name__ == "__main__":
    main()
