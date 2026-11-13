"""Skill Lift on the Anthropic API, Claude-Code style progressive disclosure.
The model only sees each skill's name + description; it must call load_skill to read SKILL.md.
Usage: run.py MODEL CONDITION [REPS]   (CONDITION = none or a folder in skills/)
Appends one JSON line per run to results.jsonl."""
import json, os, re, sys, time
from pathlib import Path
import anthropic

HERE = Path(__file__).parent
client = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip())
TASKS = json.loads((HERE / "tasks.json").read_text())
# two real distractor skills (descriptions copied from github.com/anthropics/skills)
DISTRACT = {}
# DISTRACTORS=all → all 19 official Anthropic skills are listed (a crowded skills folder), default = pdf + xlsx
names = sorted(p.name for p in (HERE / "distractors").iterdir()) if os.environ.get("DISTRACTORS") == "all" else ["pdf", "xlsx"]
for n in names:
    t = (HERE / "distractors" / n / "SKILL.md").read_text()
    DISTRACT[n] = (re.search(r"^description:\s*\"?(.*?)\"?\s*$", t, re.M).group(1), t)


def skill_meta(cond):
    skills = dict(DISTRACT)
    if cond != "none":
        t = next((HERE / "skills" / cond).glob("*/SKILL.md")).read_text()
        name = re.search(r"^name:\s*(.*)$", t, re.M).group(1).strip()
        skills[name] = (re.search(r"^description:\s*(.*)$", t, re.M).group(1), t)
    return skills


TOOLS = [{"name": "load_skill", "description": "Load the full instructions (SKILL.md) of one of the available skills.",
          "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}]


def run_one(model, cond, task):
    skills = skill_meta(cond)
    listing = "\n".join(f"- {n}: {d}" for n, (d, _) in skills.items())
    system = ("You are a coding assistant working in the team's repository. Skills are available; read a skill with the "
              "load_skill tool before relying on it.\n\nAvailable skills:\n" + listing)
    user = (f"We're cutting release {task['version']} today ({task['date']}). Write the CHANGELOG.md entry for these commits. "
            "Reply with only the entry.\n\n" + "\n".join(task["commits"]))
    messages = [{"role": "user", "content": user}]
    usage, loaded = [], []
    t0 = time.time()
    for _ in range(4):
        r = client.messages.create(model=model, max_tokens=2000, system=system, tools=TOOLS, messages=messages)
        usage.append({"in": r.usage.input_tokens, "out": r.usage.output_tokens})
        if r.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": r.content})
        res = []
        for b in r.content:
            if b.type == "tool_use":
                name = b.input.get("name", "")
                loaded.append(name)
                body = skills.get(name, (None, f"No skill named {name}."))[1]
                res.append({"type": "tool_result", "tool_use_id": b.id, "content": body})
        messages.append({"role": "user", "content": res})
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    return text, usage, loaded, time.time() - t0


if __name__ == "__main__":
    model, cond = sys.argv[1], sys.argv[2]
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    from grade import grade
    with open(os.environ.get("OUT", HERE / "results.jsonl"), "a") as f:
        for rep in range(reps):
            for task in TASKS:
                for attempt in range(5):
                    try:
                        text, usage, loaded, secs = run_one(model, cond, task)
                        break
                    except Exception as e:  # overloaded / network: back off and retry
                        print("retry", task["id"], repr(e)[:120], flush=True)
                        time.sleep(15 * (attempt + 1))
                g = grade(text, task)
                row = {"model": model, "cond": cond, "task": task["id"], "rep": rep, "loaded": loaded,
                       "in_tok": sum(u["in"] for u in usage), "out_tok": sum(u["out"] for u in usage),
                       "turns": len(usage), "secs": round(secs, 2), "score": g["score"], "checks": g["checks"], "text": text}
                f.write(json.dumps(row) + "\n"); f.flush()
                print(model, cond, task["id"], rep, loaded, g["score"], flush=True)
