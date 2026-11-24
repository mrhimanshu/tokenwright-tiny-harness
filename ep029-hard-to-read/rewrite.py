"""Control arm (like the paper's round-trip paraphrase, reversed): Claude rewrites the HUMAN answer in its own words,
same facts and topic. If odd word pairs rise, it's the wording, not the topic. Appends to gen.jsonl with cond=rewrite."""
import json, concurrent.futures as cf
from gen import client, OPUS, HAIKU, PRICE, Q, OUT, done

PROMPT = ("Here is an answer someone posted to a programming question. Rewrite it in your own words. Keep every fact, step "
          "and caveat, add nothing new, and keep roughly the same length. Output only the rewritten answer.\n\n"
          "Question: {title}\n\nAnswer:\n{human}")

def run(q, model):
    r = client.messages.create(model=model, max_tokens=4000,
        messages=[{"role": "user", "content": PROMPT.format(title=q["title"], human=q["human"])}])
    text = "".join(b.text for b in r.content if b.type == "text"); pi, po = PRICE[model]
    return dict(qid=q["qid"], model=model, cond="rewrite", text=text, usage=r.usage.model_dump(),
                cost=(r.usage.input_tokens * pi + r.usage.output_tokens * po) / 1e6)

if __name__ == "__main__":
    have = done(); tot = 0
    jobs = [(q, m) for q in Q for m in (OPUS, HAIKU) if (q["qid"], m, "rewrite") not in have]
    with cf.ThreadPoolExecutor(6) as ex, OUT.open("a") as f:
        for fu in cf.as_completed([ex.submit(run, *j) for j in jobs]):
            rec = fu.result(); tot += rec["cost"]; f.write(json.dumps(rec) + "\n"); f.flush()
    print("rewrite done", len(jobs), f"${tot:.3f}")
