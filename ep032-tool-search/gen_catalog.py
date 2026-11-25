"""Generate a realistic 5-server MCP tool catalog (the docs' own example: GitHub, Slack, Sentry, Grafana, Splunk)
plus 6 ground-truth tasks per server. One Sonnet 5.5 call per server."""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from common import client, cost
from pathlib import Path
HERE = Path(__file__).parent
SERVERS = ["github", "slack", "sentry", "grafana", "splunk"]
PROMPT = """Write the tool list of a realistic, production-quality MCP server for **{s}**, the way the official/popular
{s} MCP server exposes it. Output ONLY a JSON object: {{"tools": [...], "tasks": [...]}}.

tools: exactly 30 tools. Each tool = {{"name": "{s}_<verb>_<noun>", "description": "...", "input_schema": {{JSON Schema object}}}}.
- Descriptions like real MCP servers: 2-5 sentences (what it does, when to use it vs similar tools, notes on pagination/permissions).
- input_schema: type object, 3-9 properties, each property with type and a 1-sentence description; enums/defaults where real;
  nested objects/arrays where the real API has them; a "required" list.
- Cover the real breadth of the product. Include realistic near-duplicates that real servers have
  (e.g. list vs search, get vs get_details, create vs update).

tasks: exactly 6 user requests a developer would type to an agent, each needing exactly ONE of your tools as the first call.
Each task = {{"prompt": "...", "target": "<tool name>", "also_ok": [<other tool names that would be an equally correct first call>]}}.
- Write prompts in plain user language, never using the tool name or its exact words; include concrete values (repo names,
  channel names, ids, time ranges). Make 2 of the 6 tasks need one of the near-duplicate tools, so picking well matters.
"""
def one(s):
    with client.messages.stream(model="claude-sonnet-5-5", max_tokens=64000,
                                output_config={"effort": "medium"},
                                messages=[{"role": "user", "content": PROMPT.format(s=s)}]) as st:
        m = st.get_final_message()
    txt = "".join(b.text for b in m.content if b.type == "text")
    j = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    print(s, len(j["tools"]), len(j["tasks"]), round(cost("sonnet", m.usage), 3), flush=True)
    return s, j, cost("sonnet", m.usage)
with ThreadPoolExecutor(5) as ex:
    out = list(ex.map(one, SERVERS))
cat = {s: j for s, j, _ in out}
json.dump(cat, open(HERE / "catalog_raw.json", "w"), indent=1)
print("spend", round(sum(c for *_, c in out), 3))
