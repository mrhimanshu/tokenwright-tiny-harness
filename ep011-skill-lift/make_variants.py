"""Builds the two derived skill variants from A_plain / P_polished.
E_vague  = A_plain body, but a vague description (tests discoverability).
B_bloated = P_polished + ~3,000 words of background, FAQ and a pasted style guide (tests token cost / dilution)."""
from pathlib import Path
L = Path(__file__).parent / "skills"
a = (L / "A_plain/changelog-writer/SKILL.md").read_text()
desc_line = [l for l in a.splitlines() if l.startswith("description:")][0]
(L / "E_vague/changelog-writer/SKILL.md").write_text(a.replace(desc_line, "description: Misc team helpers."))

p = (L / "P_polished/changelog-writer/SKILL.md").read_text()
history = """## Background: why we keep a changelog

A changelog is a file which contains a curated, chronologically ordered list of notable changes for each version of a project. It exists to make it easier for users and contributors to see precisely what notable changes have been made between each release of the project. Our team adopted one in 2023 after a support week in which most tickets were variations of "what changed in the last update?". Since then the changelog has become the first thing support, sales and the docs team read on release day, which is why the format matters so much to us.

People often confuse a changelog with a git log. A git log is written for the people who made the change, in the moment, with their context in their heads. A changelog is written for people who were not there. They do not know what a refactor of the session store means; they want to know whether their saved carts survive the update. Every rule in this skill follows from that one difference in audience.

We also learned that the changelog is read on small screens, in emails and in the in-app "What's new" panel, which renders only a subset of Markdown. Headings, bullets, bold and inline code survive; tables, images and nested lists do not. That is the reason the rules forbid anything fancier than headings and single-level bullets.

## Background: how release day works

On release day the release captain freezes main, tags the version, and runs the changelog step. The entry is pasted at the top of CHANGELOG.md, reviewed by one other engineer, and published to the docs site and the in-app panel. Support then reads it aloud in the afternoon stand-up so that everyone can answer customer questions. Because several teams depend on the entry, a wrong or confusing entry costs far more time than it took to write.

The release captain rotates weekly. Some captains are new to the codebase, which is why the entry must be understandable without reading the code. When in doubt, the captain asks the author of the change in the release channel; it is always better to ask than to guess about user impact.

## Frequently asked questions

**Why not generate the changelog automatically from commit messages?** We tried. Commit messages are written for developers and mention internal names, ticket numbers and half-finished thoughts. Users found the result confusing, so a person (or an assistant) now rewrites each line.

**Why do we drop chores and CI changes?** Users cannot see them and do not care. Including them buries the changes that matter. Internal changes are still visible in git history for anyone who needs them.

**What counts as user-facing?** Anything a customer could notice: new features, changed behaviour, fixed bugs, removed options, and security fixes. Performance changes count if they are large enough to notice.

**How long should a bullet be?** One line. If you need more, the change probably deserves a short paragraph in the docs, and the bullet can link there.

**Can a bullet mention two PRs?** Avoid it. One change, one bullet, one PR number. If two PRs together make one feature, mention the main one.

**What about reverts?** If a change was added and reverted inside the same release, leave both out. If a revert undoes something from a previous release, list it under Removed or Changed.

**Do we credit contributors?** Not in the entry. Contributors are credited in the release announcement instead.

**Who reviews the entry?** One engineer other than the captain, before it is published.

"""
guide = """## Appendix A: house writing style (pasted from the docs handbook)

Write in plain English. Prefer short words to long ones and active verbs to passive ones. Address the reader as "you" in docs pages, but keep changelog bullets impersonal. Avoid jargon, internal code names and ticket numbers. Spell out abbreviations the first time unless they are common (API, URL, PDF). Use British spelling in docs and American spelling in the product UI, matching each surface. Use sentence case for headings. Use numerals for 10 and above and words for one to nine, except in tables and technical values. Dates in prose are written as 4 March 2026; dates in machine-readable places use ISO 8601. Avoid exclamation marks. Avoid "simply", "just" and "easy", which make readers feel bad when something is not easy for them. Never blame the user in error messages. Keep paragraphs under five sentences. Put the most important information first. Use lists for three or more parallel items. Do not use emoji in product copy. Link text must describe the destination, never "click here". Screenshots must be updated when the UI changes. Product names keep their official capitalisation.

"""
extra = history + guide + guide.replace("Appendix A", "Appendix B").replace("(pasted from the docs handbook)", "(older copy, kept for reference)") + history.replace("## Background", "## Background (repeated from the wiki)")
(L / "B_bloated/changelog-writer/SKILL.md").write_text(p.replace("## When to use", extra + "## When to use", 1))
for v in ["A_plain", "P_polished", "C_outdated", "D_sloppy", "B_bloated", "E_vague"]:
    t = (L / v / "changelog-writer/SKILL.md").read_text()
    print(v, len(t.split()), "words")
