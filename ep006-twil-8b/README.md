# EP006: TwIL-8B (free, local) in the same harness

webAI's TwIL-8B (Q4_K_M balanced GGUF, 4.98 GiB) served by llama.cpp on an M4 Pro (24 GB), plugged into the same 70-line harness and the same 5 tasks as EP005.

- **Result:** 11/15 passed (73%) vs Claude Haiku 5.5 25/25 in the same harness. 65 minutes for 15 tasks vs ~1.6 minutes; $0 vs ~$0.025.
- **All 4 failures were "stopped without acting":** a loop reading an empty file 18 times, a 12,000-token reply cut off before the fix, a tool call written inside its private thinking, and ending a turn with a test still failing.
- Details: `DATA.md`; raw runs: `results.jsonl`; turn-by-turn transcripts for runs 1–2: `transcripts/`.

```bash
llama-server -m TwIL-8B-Q4_K_M-balanced.gguf --jinja -c 65536 -ngl 99 -fa on -ctk q8_0 -ctv q8_0 --reasoning-format deepseek -np 1 --port 8080
cd ../tasks/t3_page && python3 ../../ep006-twil-8b/local_harness.py "Fix the bugs in pager/paginate.py so all the tests pass."
```
Note: TwIL-8B weights are under the webAI Non-Commercial License 1.0.
