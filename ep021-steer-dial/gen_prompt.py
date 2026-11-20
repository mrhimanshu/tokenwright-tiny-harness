"""EP021 arm A: Spaceship IDE's own steering (prompt-compiled knob) on fast API models.
Every knob setting Spaceship can send = 5 grades x 3 strengths for one axis (tension: relaxed | strained),
plus an unsteered baseline with Spaceship's plain story prompt. 3 openings x REPS repeats.
usage: python gen_prompt.py   -> prompt_results.jsonl
"""
import os, json, time, random, threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["GEMINI_API_KEY"] = open(os.path.expanduser("~/.config/gemini/key")).read().strip()
import anthropic
from google import genai
from google.genai import types

A = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip(), max_retries=5)
G = genai.Client()
LOCK = threading.Lock()
OUT = os.path.join(HERE, os.environ.get("OUT", "prompt_results.jsonl"))
REPS = int(os.environ.get("REPS", "3"))
MODELS = os.environ.get("MODELS", "claude-haiku-5-5,gemini-3.8-flash").split(",")

STEERED = open(os.path.join(HERE, "spaceship_system_prompt.txt")).read()
# Spaceship src/story/prompt.ts (STORY_SYSTEM_PROMPT), used when no knob is set
PLAIN = """Continue the story. The user message is its opening, which may stop mid-sentence.

- Output only the words that come next. Do not repeat the opening.
- Your first word directly follows the opening's last word.
- Plain text only. No title, markdown or commentary.
- At most 400 words. End on a complete sentence.

EXAMPLE
User: The alarm went off, but
Assistant:
it was not the one on her phone. Mara lay still and listened."""

OPENINGS = ["The alarm went off, but", "They told us never to open the door to", "In the quiet hours just before dawn,"]
LOW, HIGH = "relaxed", "strained"
GRADES = ["very " + LOW, "somewhat " + LOW, f"midway between {LOW} and {HIGH}", "somewhat " + HIGH, "very " + HIGH]
STRENGTHS = ["slight", "moderate", "strong"]


def user_msg(opening, grade, strength):
    return f"CONTROLS\ntension: {GRADES[grade]} ({strength})\n\nSTORY SO FAR\n{opening}"


def call(model, system, user):
    err = ""
    for attempt in range(6):
        try:
            if model.startswith("claude"):
                r = A.messages.create(model=model, max_tokens=3000, system=system, output_config={"effort": "low"},
                                      messages=[{"role": "user", "content": user}])
                return "".join(b.text for b in r.content if b.type == "text"), dict(inp=r.usage.input_tokens, out=r.usage.output_tokens)
            r = G.models.generate_content(model=model, contents=user, config=types.GenerateContentConfig(
                system_instruction=system, temperature=0.9, thinking_config=types.ThinkingConfig(thinking_level="low")))
            u = r.usage_metadata
            return r.text or "", dict(inp=u.prompt_token_count, out=(u.candidates_token_count or 0) + (u.thoughts_token_count or 0))
        except Exception as e:
            err = str(e)[:200]
            time.sleep(2 + 3 * attempt + random.random())
    return "", dict(error=err)


def job(spec):
    model, oi, grade, strength, rep = spec
    opening = OPENINGS[oi]
    if grade is None:
        text, usage = call(model, PLAIN, opening)
    else:
        text, usage = call(model, STEERED, user_msg(opening, grade, strength))
    rec = dict(arm="prompt", model=model, opening=oi, grade=grade, strength=strength, rep=rep, text=text, usage=usage)
    with LOCK:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    specs = []
    for m in MODELS:
        for oi in range(len(OPENINGS)):
            for rep in range(REPS):
                specs.append((m, oi, None, None, rep))
                for g in range(5):
                    for s in STRENGTHS:
                        specs.append((m, oi, g, s, rep))
    random.seed(21); random.shuffle(specs)
    t0 = time.time()
    with ThreadPoolExecutor(12) as ex:
        list(ex.map(job, specs))
    print("done", len(specs), "in", round(time.time() - t0), "s")
