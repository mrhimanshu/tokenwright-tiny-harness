# Prompts grouped by the model card's four task types (+ "copy", the most predictable case).
# Each ~150-300 input tokens, asking for ~200+ output tokens.
ARTICLE = (
    "The city council voted on Tuesday to convert two lanes of Harbor Street into protected bike lanes "
    "starting in March. Supporters said the change would cut crashes, which reached 41 last year on the "
    "1.2 mile stretch, and give the 3,000 daily cyclists a safe route to the ferry terminal. Shop owners "
    "worried about losing 60 parking spaces and asked for a loading zone on every block. The council agreed "
    "to add six loading zones and to review the plan after one year using crash data and sales tax receipts. "
    "The project will cost 2.4 million dollars, most of it from a state grant, and construction will close "
    "the street at night for about five weeks. A separate proposal to lower the speed limit to 20 miles per "
    "hour on nearby residential streets was delayed until the transportation department finishes a study."
)
REVIEW = (
    "We shipped the new search page last sprint. Latency went from 900 ms to 310 ms at p50, but p99 is still "
    "around 2.1 seconds because of the cold cache after each deploy. Support tickets about search dropped by "
    "a third. Two customers reported that filters reset when they press back. Mobile conversion is flat."
)

PROMPTS = {
    "summarize": [
        "Summarize this news article in exactly five bullet points, then one sentence on what happens next.\n\n" + ARTICLE,
        "Write a short summary (about 150 words) of this team update for a manager who has no time.\n\n" + REVIEW,
        "Summarize the following text for a ten year old, in two short paragraphs.\n\n" + ARTICLE,
    ],
    "code": [
        "Write a Python function `parse_duration(s)` that turns strings like '1h30m', '45s' or '2h' into seconds. "
        "Include a docstring, type hints, input validation that raises ValueError, and five pytest tests.",
        "Write a JavaScript function `debounce(fn, ms)` with a `cancel()` and a `flush()` method, with JSDoc comments, "
        "then show a short usage example with a search box.",
        "Write a SQL schema for a small library app: books, authors (many-to-many), members and loans with due dates. "
        "Add indexes and three example queries: overdue loans, most borrowed books, and members with no loans.",
    ],
    "rewrite": [
        "Rewrite this team update in a warm, upbeat tone for a company newsletter. Keep every fact and number.\n\n" + REVIEW,
        "Rewrite this news article as a formal press release from the city council. Keep every fact and number.\n\n" + ARTICLE,
        "Rewrite this team update as a polite, professional email to a customer who complained about the filters "
        "resetting. Keep the facts that matter to them.\n\n" + REVIEW,
    ],
    "freeform": [
        "Write a short story (about 250 words) about a lighthouse keeper who finds a phone that only receives "
        "messages from the future.",
        "Give me ten original names for a coffee shop run by retired astronauts, each with a one-line reason.",
        "Write a persuasive speech (about 250 words) arguing that every town should have a public tool library.",
    ],
    "copy": [
        "Repeat the following text exactly, word for word, with no changes and nothing added.\n\n" + ARTICLE,
        "Convert this text to all capital letters. Output only the converted text.\n\n" + REVIEW + " " + REVIEW,
        "Translate this news article into French.\n\n" + ARTICLE,
    ],
}
