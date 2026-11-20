"""EP022 gold set: render every URL in a real Chromium (Playwright, wait for network idle + 3 s),
save the visible text, then ask Claude Sonnet 5.5 for 2 questions whose answers are in the page's MAIN content.
Independent of every scraper under test. -> gold/<id>.txt, gold_qa.jsonl
"""
import os, json, re, sys, asyncio
import anthropic
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/opt/ms-playwright/chromium-1254/chrome-linux64/chrome"
URLS = json.load(open(os.path.join(HERE, "urls.json")))
os.makedirs(os.path.join(HERE, "gold"), exist_ok=True)
A = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip(), max_retries=5)

SYS = """You write reading-comprehension questions for testing web scrapers.
You get the visible text of a web page. Write exactly 2 questions whose answers are short facts (a name, number, date, word or short phrase)
stated in the page's MAIN content (the article, docs body, listing, README or data the page exists to show), NOT in navigation, footers, cookie banners or ads.
Prefer facts from different parts of the main content (one from the first third, one from later). Avoid facts likely to change within a day.
Reply with only JSON: [{"q": "...", "a": "..."}, {"q": "...", "a": "..."}]"""


async def render_all():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME)
        ctx = await b.new_context(viewport={"width": 1280, "height": 2000})
        for u in URLS:
            path = os.path.join(HERE, "gold", u["id"] + ".txt")
            if os.path.exists(path) and os.path.getsize(path) > 200:
                continue
            if u["kind"] == "pdf":
                continue
            pg = await ctx.new_page()
            try:
                await pg.goto(u["url"], wait_until="networkidle", timeout=45000)
            except Exception as e:
                print("goto", u["id"], e)
            await pg.wait_for_timeout(13000 if "delay" in u["id"] else 3000)
            txt = await pg.evaluate("document.body ? document.body.innerText : ''")
            open(path, "w").write(txt)
            print(u["id"], len(txt))
            await pg.close()
        await b.close()


def pdf_text(u):
    import requests, subprocess, tempfile
    path = os.path.join(HERE, "gold", u["id"] + ".txt")
    if os.path.exists(path):
        return
    r = requests.get(u["url"], timeout=60)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.content); f.flush()
        try:
            txt = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        except FileNotFoundError:
            from pypdf import PdfReader
            txt = "\n".join(p.extract_text() or "" for p in PdfReader(f.name).pages)
    open(path, "w").write(txt)
    print(u["id"], len(txt))


def make_qa():
    out = os.path.join(HERE, "gold_qa.jsonl")
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    for u in URLS:
        if u["id"] in done:
            continue
        txt = open(os.path.join(HERE, "gold", u["id"] + ".txt")).read()[:60000]
        if len(txt) < 200:
            print("SKIP short gold", u["id"]); continue
        m = A.messages.create(model="claude-sonnet-5-5", max_tokens=2000, system=SYS, output_config={"effort": "low"},
                              messages=[{"role": "user", "content": f"URL: {u['url']}\n\nPAGE TEXT:\n{txt}"}])
        t = "".join(b.text for b in m.content if b.type == "text")
        qa = json.loads(re.search(r"\[.*\]", t, re.S).group(0))
        with open(out, "a") as f:
            f.write(json.dumps({"id": u["id"], "qa": qa}) + "\n")
        print(u["id"], qa)


if __name__ == "__main__":
    asyncio.run(render_all())
    for u in URLS:
        if u["kind"] == "pdf":
            pdf_text(u)
    make_qa()
