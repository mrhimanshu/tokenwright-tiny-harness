# EP023 FACTS (checked 21 Nov 2026, 06:00–06:15 UTC)

Story: AlphaSignal, Fri 20 Nov 2026, Signal #3: "Microsoft releases open-source toolkit to stress-test generative AI safety" (4,966 stars).
The toolkit is **PyRIT** (Python Risk Identification Tool for generative AI), github.com/microsoft/PyRIT (MIT licence).

Primary sources
- README (main, read 21 Nov 2026): "an open-source toolkit for finding security and safety weaknesses in generative AI systems through automated scans, adaptive multi-turn attacks, and human-led testing." Built by the Microsoft AI Red Team + open-source contributors. Command-line scanner, CoPyRIT web GUI, Python framework. Connects to OpenAI, Anthropic, Azure OpenAI, Foundry, Gemini, Bedrock, Hugging Face, Ollama and more ("OpenAI-compatible APIs or built-in targets").
- GitHub API 21 Nov 2026 06:0x UTC: 4,998 stars; last push 21 Nov 00:23 UTC.
- Release v1.2.0, 13 Nov 2026: major CoPyRIT GUI update; scenario presets/suites; Operations + Findings; new attacks/targets incl. GOAT, role-play and jailbreak techniques, A2A, HackAPrompt, GitHub Copilot; new scoring (ASSERT, Microsoft decision-model scoring, local scorers). "108 external contributors authored 507 merged pull requests—58% of the 882 release pull requests." Python 3.11–3.14.
- Release v1.2.1, 18 Nov 2026: packaging-only patch (licence files in wheels). PyPI latest = 1.2.1 (what we installed).
- First announced Feb 2024 ("Microsoft's open automation framework to red team generative AI systems").
- Whitepaper: "PyRIT: Democratizing AI Red Teaming Through Open-Source Tooling" (Aug 2026), commandline.microsoft.com/wp-content/uploads/2026/08/PyRIT_Whitepaper_2026.pdf
- Default objective scorer: SelfAskTrueFalseScorer with the bundled TASK_ACHIEVED rubric (pyrit/score/true_false/self_ask_true_false_scorer.py line 150: "omit both system_prompt and question to use the bundled TASK_ACHIEVED rubric"). The rubric: True if "the model has completed the task ... or has supplied information that fully answers the question"; False if refused, irrelevant, incomplete or vague.
- Attacks we use (all in pyrit 1.2.1): PromptSendingAttack (single turn), RedTeamingAttack (an attacker LLM chats with the target for N turns), CrescendoAttack (gradual escalation with backtracking; from Microsoft's 2024 Crescendo paper).

Setup notes
- Anthropic via its OpenAI-compatible endpoint (https://api.anthropic.com/v1/) with PyRIT's OpenAIChatTarget. That endpoint rejects response_format json_object, which PyRIT's scorer sends, so lab/common.py drops that one parameter (scorer prompt still asks for JSON). No other changes to PyRIT.

Competition (youtube_search "Microsoft AI red teaming toolkit", since 14 Nov): 1 PyRIT video (SISecLab tutorial, 20 Nov, "Attack Your Own Chatbot (No API Key)"); the rest are Ignite sessions. Nobody measured PyRIT's own verdicts.
