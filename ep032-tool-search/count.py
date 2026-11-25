import json
from common import client
cat = json.load(open("catalog_raw.json"))
tools = [t for s in cat for t in cat[s]["tools"]]
names = {t["name"] for t in tools}
print("tools", len(tools), "unique", len(names))
for s in cat:
    for k in cat[s]["tasks"]:
        bad = [x for x in [k["target"]] + k["also_ok"] if x not in names]
        if bad: print("BAD", s, bad)
msg = [{"role": "user", "content": "hi"}]
base = client.messages.count_tokens(model="claude-opus-5-5", messages=msg).input_tokens
full = client.messages.count_tokens(model="claude-opus-5-5", messages=msg, tools=tools).input_tokens
ts = client.messages.count_tokens(model="claude-opus-5-5", messages=msg, tools=[{"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"}] + [dict(t, defer_loading=True) for t in tools]).input_tokens
print("base", base, "all tools", full, "defs", full - base, "toolsearch upfront", ts)
for s in cat:
    n = client.messages.count_tokens(model="claude-opus-5-5", messages=msg, tools=cat[s]["tools"]).input_tokens - base
    print(s, len(cat[s]["tools"]), n)
