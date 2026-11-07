"""The same 70-line harness (EP005), pointed at a model running on this Mac via llama-server's OpenAI-style API.
Same system prompt, same 5 tools. Usage: python3 local_harness.py "<task>"   (llama-server on 127.0.0.1:8080)"""
import json, os, re, subprocess, sys, time, urllib.request

URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")
SYSTEM = "You are a coding agent in the current folder. Make the change, run the tests, stop when they pass."
S = lambda props, req=(): {"type": "object", "properties": {p: {"type": "string"} for p in props}, "required": list(req)}
TOOLS = [{"type": "function", "function": f} for f in [
    {"name": "list_files", "description": "List the project's files.", "parameters": S([])},
    {"name": "read_file", "description": "Read a file.", "parameters": S(["path"], ["path"])},
    {"name": "write_file", "description": "Overwrite a file.", "parameters": S(["path", "content"], ["path", "content"])},
    {"name": "edit_file", "description": "Replace one exact snippet in a file (send only the lines that change).",
     "parameters": S(["path", "old", "new"], ["path", "old", "new"])},
    {"name": "run_tests", "description": "Run the tests.", "parameters": S([])},
]]


def run_tool(name, args):
    if name == "list_files":
        return "\n".join(os.path.join(d, f)[2:] for d, _, fs in os.walk(".") if "__pycache__" not in d for f in fs)
    if name == "read_file":
        return open(args["path"]).read()
    if name == "write_file":
        open(args["path"], "w").write(args["content"]); return "saved"
    if name == "edit_file":
        src = open(args["path"]).read()
        if args["old"] not in src:
            return "error: snippet not found"
        open(args["path"], "w").write(src.replace(args["old"], args["new"], 1)); return "edited"
    if name == "run_tests":
        p = subprocess.run([sys.executable, "-B", "run_tests.py"], capture_output=True, text=True, timeout=60)
        return (p.stdout + p.stderr)[-3000:]
    return f"error: unknown tool {name}"


XML_CALL = re.compile(r"<tool_call>\s*<function=([\w-]+)>(.*?)</function>\s*</tool_call>", re.S)
XML_PARAM = re.compile(r"<parameter=([\w-]+)>\n?(.*?)\n?</parameter>", re.S)


def parse_calls(msg):
    """Tool calls come back either parsed by llama-server (tool_calls) or as the model's raw XML in the text."""
    calls = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        a = tc["function"].get("arguments") or "{}"
        calls.append((tc.get("id") or f"call_{i}", tc["function"]["name"], json.loads(a) if isinstance(a, str) else a))
    if not calls:
        for i, m in enumerate(XML_CALL.finditer(msg.get("content") or "")):
            calls.append((f"call_{i}", m.group(1), {k: v for k, v in XML_PARAM.findall(m.group(2))}))
    return calls


def chat(messages, max_tokens):
    body = json.dumps({"messages": messages, "tools": TOOLS, "max_tokens": max_tokens, "temperature": 1.0, "top_p": 0.95,
                       "cache_prompt": True}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))


def agent(task, max_turns=30, max_tokens=12000):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    usage = []
    for turn in range(1, max_turns + 1):
        t = time.time()
        r = chat(messages, max_tokens)
        m = r["choices"][0]["message"]
        u = dict(r.get("usage") or {}, secs=round(time.time() - t, 1), timings=r.get("timings"),
                 finish=r["choices"][0].get("finish_reason"))
        usage.append(u)
        calls = parse_calls(m)
        # keep the answer, drop the private reasoning from the history (it is not re-sent, like most agents do)
        entry = {"role": "assistant", "content": m.get("content") or ""}
        if m.get("tool_calls"):
            entry["tool_calls"] = m["tool_calls"]
        messages.append(entry)
        if os.environ.get("SAVE_TRANSCRIPT"):
            log = {"turn": turn, "reasoning": m.get("reasoning_content") or "", "content": m.get("content") or "",
                   "calls": [(n, a) for _, n, a in calls]}
            open(".transcript.jsonl", "a").write(json.dumps(log) + "\n")
        if not calls:
            return turn, usage
        for cid, name, args in calls:
            try:
                out = run_tool(name, args)
            except Exception as e:
                out = f"error: {e}"
            messages.append({"role": "tool", "tool_call_id": cid, "content": out})
    return max_turns, usage


if __name__ == "__main__":
    turns, usage = agent(sys.argv[1])
    print(json.dumps({"turns": turns, "usage": usage}))
