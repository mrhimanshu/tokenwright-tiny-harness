# EP029 DATA — is Claude's writing harder to read? (my runs, 24 Nov 2026)

39 Stack Overflow questions (8 tags, accepted human answers written 2019–Nov 2022, i.e. before ChatGPT; one 5,168-word outlier dropped).
Claude Opus 5.5 + Haiku 5.5 answered each question under 3 system prompts: none (default), `Be concise.`, and a plain-English line
("Write the way a helpful colleague talks: short sentences, people (you, I, we) as the subject, everyday words.").
Control: each model rewrote the HUMAN answer in its own words (same facts, same length) = rewrite.
Prose only on both sides (code blocks and inline code removed). Parser spaCy en_core_web_md (paper: en_core_web_trf).
Reference corpus for odd word pairs: 2,464 other top Stack Overflow answers, 356,533 words (2015–Nov 2022).
Odd word pair = a two-word sequence (inside one phrase, no punctuation between) that never appears in the reference corpus; per 1,000 pairs.
Mean ± 95% bootstrap CI over questions. n = 39 answers per row. 468 API calls total, $3.75.

| arm | words | words/sentence | dep. length | noun stacks /1k words | inanimate subj.+animate verb /1k | odd word pairs /1k | odd pairs > human (of 39) |
|---|---|---|---|---|---|---|---|
| human|human | 199 | 21.3 | 2.08 | 5.6 [3.3–8.0] | 2.1 [0.9–3.6] | 289.8 [267.1–315.8] | — |
| claude-opus-5-5|default | 273 | 14.6 | 2.07 | 5.4 [3.7–7.3] | 3.5 [2.4–4.7] | 370.8 [347.3–397.4] | 32 |
| claude-opus-5-5|concise | 205 | 14.7 | 2.11 | 4.0 [2.1–6.2] | 2.7 [1.5–4.0] | 370.6 [345.1–395.7] | 31 |
| claude-opus-5-5|plain | 281 | 11.5 | 2.02 | 3.2 [1.9–4.8] | 4.1 [2.6–5.6] | 350.0 [329.3–369.4] | 30 |
| claude-opus-5-5|rewrite | 197 | 17.2 | 2.07 | 5.1 [2.9–7.5] | 2.0 [0.9–3.3] | 320.8 [296.0–345.9] | 29 |
| claude-haiku-5-5|default | 235 | 15.8 | 2.09 | 4.7 [2.6–7.0] | 1.8 [0.8–3.0] | 344.0 [323.9–365.7] | 31 |
| claude-haiku-5-5|concise | 150 | 14.5 | 2.09 | 4.9 [2.4–7.6] | 1.9 [0.8–3.1] | 361.6 [334.1–389.6] | 32 |
| claude-haiku-5-5|plain | 193 | 12.3 | 2.01 | 2.8 [1.4–4.5] | 3.8 [2.3–5.6] | 315.1 [292.6–338.8] | 25 |
| claude-haiku-5-5|rewrite | 189 | 16.5 | 2.08 | 4.6 [2.5–7.2] | 2.7 [1.4–4.2] | 319.3 [295.6–344.1] | 30 |

## Read
- Replicates: odd word pairs. Opus 5.5 default 370.8 vs human 289.8 per 1,000 (+28%), higher on 32/39 questions. Haiku 5.5 344.0 (+19%), 31/39.
- Does NOT replicate here: dependency length (2.07 vs 2.08), noun stacks (5.4 vs 5.6). Claude's sentences are SHORTER (Opus 14.6, Haiku 15.8 vs human 21.3 words).
- Inanimate subject + animate verb: our heuristic (verb list) is noisy; Opus 3.5 vs human 2.1 per 1k, CIs overlap -> not claimed.
- `Be concise.`: Opus unchanged (370.6 vs 370.8); Haiku 361.6 vs 344.0 (+5%, CIs overlap). Answers got shorter (Opus 273 -> 205 words), not plainer.
- Plain-English line: Opus 350.0 (−6%), Haiku 315.1 (−8%); sentences 11.5 / 12.3 words; noun stacks down ~40% (wide CIs). Still above human.
- Rewrite control (same facts, Claude's words): Opus 320.8, Haiku 319.3 = +11% over the human original (higher on 29–30/39). So about a third of the gap is wording alone; the rest comes with what Claude chooses to say.
- Example odd pairs from Opus default answers: "matplotlib picks", "error confirms", "effect closes", "tells react", "lines show" (things doing what people do).
- Caveats: one domain (coding Q&A), English, no human readers, small reference corpus (356k words, so rare-but-fine pairs count as odd on both sides), one sample per question per arm.
