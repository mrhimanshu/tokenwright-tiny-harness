"""Single-call baseline: same raw materials + same template, ONE model call writes the whole paper (LaTeX + BibTeX).
usage: baseline.py <out_dir> <gemini-3.8-flash|claude-sonnet-5-5>"""
import sys, os, json, time, re
HERE = os.path.dirname(os.path.abspath(__file__))
out, model = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
rd = lambda p: open(os.path.join(HERE, p)).read()
prompt = f"""You are writing a complete research paper for submission to ICLR from the raw materials below.
Write the full paper in LaTeX using the given template (keep its preamble and style files), with an abstract, introduction,
related work with real citations, method, experiments, discussion and conclusion. Include the figure figures/solve_rates.png.
Then write the BibTeX file with every reference you cite.
Return exactly two fenced blocks: ```latex ... ``` (the full template.tex) and ```bibtex ... ``` (references.bib).

## Idea
{rd('raw_materials/idea_sparse.md')}

## Experimental log
{rd('raw_materials/experimental_log.md')}

## Figure
figures/solve_rates.png: {json.load(open(os.path.join(HERE,'raw_materials/figures/info.json')))[0]['caption']}

## Template (template.tex)
{rd('po/templates/iclr2025/template.tex')}
"""
t0 = time.time()
if model.startswith("gemini"):
    from google import genai
    from google.genai import types
    c = genai.Client()
    r = c.models.generate_content(model=model, contents=prompt,
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
    text = r.text; u = r.usage_metadata
    usage = dict(inp=u.prompt_token_count, out=u.candidates_token_count, think=u.thoughts_token_count or 0, tool=u.tool_use_prompt_token_count or 0)
else:
    import anthropic
    c = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip())
    with c.messages.stream(model=model, max_tokens=32000, messages=[{"role": "user", "content": prompt}]) as s:
        r = s.get_final_message()
    text = "".join(b.text for b in r.content if b.type == "text")
    usage = dict(inp=r.usage.input_tokens, out=r.usage.output_tokens)
secs = round(time.time() - t0, 1)
tex = re.search(r"```latex\n(.*?)```", text, re.S); bib = re.search(r"```bibtex\n(.*?)```", text, re.S)
import shutil
w = os.path.join(out, "latex"); shutil.copytree(os.path.join(HERE, "po/templates/iclr2025"), w, dirs_exist_ok=True)
shutil.copytree(os.path.join(HERE, "raw_materials/figures"), os.path.join(w, "figures"), dirs_exist_ok=True)
open(os.path.join(w, "template.tex"), "w").write(tex.group(1) if tex else "")
open(os.path.join(w, "references.bib"), "w").write(bib.group(1) if bib else "")
open(os.path.join(out, "raw_response.md"), "w").write(text)
json.dump(dict(model=model, secs=secs, usage=usage, got_tex=bool(tex), got_bib=bool(bib)), open(os.path.join(out, "run_meta.json"), "w"), indent=1)
print(model, secs, usage)
