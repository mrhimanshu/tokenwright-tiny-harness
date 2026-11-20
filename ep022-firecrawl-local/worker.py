"""EP022 worker for the Python tools (run by bench.py so its whole process tree can be measured).
Prints READY after start-up (imports + browser launch), waits 5 s (parent measures idle), then scrapes and prints JSON rows."""
import os, sys, json, time, asyncio

HERE = os.path.dirname(os.path.abspath(__file__))
URLS = json.load(open(os.path.join(HERE, "urls.json")))
tool, rnd = sys.argv[1], int(sys.argv[2])
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


def emit(u, dt, md, **extra):
    open(os.path.join(HERE, "md", f"{tool}__{u['id']}__r{rnd}.md"), "w").write(md)
    print(json.dumps(dict(tool=tool, round=rnd, id=u["id"], kind=u["kind"], secs=round(dt, 3), chars=len(md), **extra)), flush=True)


if tool == "trafilatura":
    import requests, trafilatura
    sess = requests.Session(); sess.headers["User-Agent"] = UA
    print("READY", flush=True); time.sleep(5.5); print("GO", flush=True)
    for u in URLS:
        t = time.time()
        try:
            r = sess.get(u["url"], timeout=45)
            if "pdf" in r.headers.get("content-type", ""):
                md = ""  # trafilatura does not parse PDFs
            else:
                md = trafilatura.extract(r.text, output_format="markdown", include_links=False, include_tables=True, url=u["url"]) or ""
            emit(u, time.time() - t, md, status=r.status_code)
        except Exception as e:
            emit(u, time.time() - t, "", error=repr(e)[:300])
    print("DONE", flush=True)

elif tool == "crawl4ai":
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

    async def main():
        async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as c:
            print("READY", flush=True); await asyncio.sleep(5.5); print("GO", flush=True)
            cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=45000, verbose=False)
            for u in URLS:
                t = time.time()
                try:
                    r = await c.arun(u["url"], config=cfg)
                    md = r.markdown.raw_markdown if r.markdown and hasattr(r.markdown, "raw_markdown") else (r.markdown or "")
                    emit(u, time.time() - t, md or "", status=r.status_code, success=r.success, error=(r.error_message or "")[:300] or None)
                except Exception as e:
                    emit(u, time.time() - t, "", error=repr(e)[:300])
        print("DONE", flush=True)

    import contextlib, io
    asyncio.run(main())
