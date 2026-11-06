"""A complete coding-agent harness: a loop, 4 tools, and the context. Usage: python3 tiny_harness.py "<task>" [model]"""
import json, os, subprocess, sys
import anthropic

SYSTEM = "You are a coding agent in the current folder. Make the change, run the tests, stop when they pass."
TOOLS = [
    {"name": "list_files", "description": "List the project's files.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_file", "description": "Read a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Overwrite a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "run_tests", "description": "Run the tests.", "input_schema": {"type": "object", "properties": {}}},
]
EDIT = {"name": "edit_file", "description": "Replace one exact snippet in a file (send only the lines that change).",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"},
                         "new": {"type": "string"}}, "required": ["path", "old", "new"]}}
TOOLS_V2 = TOOLS + [EDIT]   # v2 = v1 + one edit tool


def run_tool(name, args):
    if name == "list_files":
        return "\n".join(os.path.join(d, f)[2:] for d, _, fs in os.walk(".") if "__pycache__" not in d for f in fs)
    if name == "read_file":
        return open(args["path"]).read()
    if name == "write_file":
        open(args["path"], "w").write(args["content"])
        return "saved"
    if name == "edit_file":
        src = open(args["path"]).read()
        if args["old"] not in src:
            return "error: snippet not found"
        open(args["path"], "w").write(src.replace(args["old"], args["new"], 1))
        return "edited"
    if name == "run_tests":
        p = subprocess.run([sys.executable, "-B", "run_tests.py"], capture_output=True, text=True, timeout=60)
        return (p.stdout + p.stderr)[-3000:]


def agent(task, model="claude-haiku-5-5", cache=True, tools=TOOLS_V2, max_turns=30):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": [{"type": "text", "text": task}]}]
    usage = []
    for turn in range(1, max_turns + 1):
        if cache:  # one cache marker on the newest message: everything before it is re-read at the cheap cache price
            for m in messages:
                for b in m["content"]:
                    b.pop("cache_control", None)
            messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        r = client.messages.create(model=model, max_tokens=4000, system=SYSTEM, tools=tools, messages=messages)
        usage.append(r.usage.model_dump())
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in r.content]})
        if r.stop_reason != "tool_use":
            return turn, usage
        results = []
        for b in r.content:
            if b.type == "tool_use":
                try:
                    out = run_tool(b.name, b.input)
                except Exception as e:
                    out = f"error: {e}"
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        messages.append({"role": "user", "content": results})
    return max_turns, usage


if __name__ == "__main__":
    turns, usage = agent(sys.argv[1], *sys.argv[2:3])
    print(json.dumps({"turns": turns, "usage": usage}))
