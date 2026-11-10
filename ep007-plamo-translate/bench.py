"""EP007: a 570 MB local translator (PLaMo 3 Translate 0.8B) vs Claude, scored against human references (WMT24++).
Usage: python bench.py <system> [n]   system = plamo08 | plamo2 | haiku | sonnet   (plamo* needs llama-server on :8000)
Appends to results.jsonl; same sentences for every system and language."""
import json, os, random, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
LANGS = {"hi_IN": ("hi", "Hindi"), "ja_JP": ("ja", "Japanese"), "es_MX": ("es", "Spanish"), "de_DE": ("de", "German"),
         "ar_SA": ("ar", "Arabic"), "zh_CN": ("zh", "Simplified Chinese")}
OUT = os.path.join(HERE, "results.jsonl")


def sample(n):
    rows = [json.loads(l) for l in open(os.path.join(HERE, "data", "en-hi_IN.jsonl"))]
    ok = [r["segment_id"] for r in rows if not r["is_bad_source"] and r["domain"] != "canary" and 8 <= len(r["source"].split()) <= 60]
    random.Random(7).shuffle(ok)
    return sorted(ok[:n])


def load(lang, ids):
    rows = {json.loads(l)["segment_id"]: json.loads(l) for l in open(os.path.join(HERE, "data", f"en-{lang}.jsonl"))}
    return [(i, rows[i]["source"], rows[i]["target"]) for i in ids]


def plamo(src, code):
    prompt = ("<|plamo:tag|>dataset<|plamo:msg|>translation<|plamo:tag|>input<|plamo:msg|>" + src +
              f"<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>{code}<|plamo:msg|>")
    body = json.dumps({"prompt": prompt, "n_predict": 512, "temperature": 0, "cache_prompt": False,
                       "stop": ["<|plamo:tag|>", "<|plamo:bos|>"]}).encode()
    t = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000/completion", body,
                                                               {"Content-Type": "application/json"}), timeout=300))
    return r["content"].strip(), time.time() - t, {"out_tokens": r.get("tokens_predicted"), "in_tokens": r.get("tokens_evaluated")}


CLAUDE = None


def claude(model):
    def f(src, code, name):
        global CLAUDE
        import anthropic
        CLAUDE = CLAUDE or anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip())
        t = time.time()
        for attempt in range(5):
            try:
                r = CLAUDE.messages.create(model=model, max_tokens=1024, messages=[{"role": "user", "content":
                    f"Translate the following English text into {name}. Output only the translation.\n\n{src}"}])
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        return "".join(b.text for b in r.content if b.type == "text").strip(), time.time() - t, {"in_tokens": r.usage.input_tokens, "out_tokens": r.usage.output_tokens}
    return f


def main():
    system = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    ids = sample(n)
    for lang, (code, name) in LANGS.items():
        data = load(lang, ids)
        if system.startswith("plamo"):  # whichever PLaMo GGUF is loaded in llama-server
            res = [plamo(s, code) for _, s, _ in data]
        else:
            fn = claude({"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}[system])
            with ThreadPoolExecutor(6) as ex:
                res = list(ex.map(lambda d: fn(d[1], code, name), data))
        with open(OUT, "a") as f:
            for (i, s, ref), (hyp, secs, u) in zip(data, res):
                f.write(json.dumps({"system": system, "lang": lang, "id": i, "src": s, "ref": ref, "hyp": hyp, "secs": round(secs, 3), **u}) + "\n")
        print(system, lang, len(res), "done", round(sum(r[1] for r in res), 1), "s", flush=True)


if __name__ == "__main__":
    main()
