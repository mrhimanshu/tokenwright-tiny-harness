---
name: changelog-writer
description: Writes CHANGELOG.md release entries from commit lists. Use when asked for release notes or a changelog entry. Do NOT use for commit messages.
version: 1.3.0
license: MIT
metadata:
  tags: [changelog, release-notes, git, documentation]
  author: tokenwright
---

# Changelog writer

Turns a list of commits into one release entry for CHANGELOG.md, following the team's changelog rules.

## When to use

- Use when someone asks for release notes, a changelog entry or "what changed" for a version.
- Do NOT use for writing commit messages, PR descriptions or blog posts.

## Prerequisites

- The version number and release date.
- The list of commits (conventional-commit style, with hashes).
- No scripts, tools or API keys are needed.

## Rules

1. First line is the header: `# Release VERSION (D Month YYYY)` (for example `# Release 2.1.0 (4 March 2026)`).
2. Group bullets under `### Features`, `### Bug fixes` and `### Other`, in that order.
3. Every bullet ends with the short commit hash in square brackets, like `[a1b2c3d]`, so people can find the change.
4. Include every commit, internal ones too: `chore`, `ci`, `docs` and `test` go under `### Other` so nothing is hidden.
5. A breaking change goes under `### Features` and starts with `BREAKING -`.
6. Security fixes are bug fixes: put them under `### Bug fixes`.
7. Keep the commit's original wording, lower case, so it matches git log.

## Workflow

1. Read every commit and note its type, scope and hash.
2. Sort each one into the headings from rule 2.
3. Copy the wording and append `[hash]`.
4. Check the output against every rule before answering.

## Example

Commits:
```
a1b2c3d feat(api): add bulk export endpoint (#88)
d4e5f6a fix: crash when the cart is empty (#91)
0a9b8c7 chore: bump eslint (#92)
```

Entry:
```
# Release 1.2.0 (15 January 2026)

### Features
- add bulk export endpoint [a1b2c3d]

### Bug fixes
- crash when the cart is empty [d4e5f6a]

### Other
- bump eslint [0a9b8c7]
```

## Troubleshooting

| Error | Cause | Solution |
| --- | --- | --- |
| A commit has no hash | Squashed merge | Use the merge commit's hash |
| A commit fits two headings | Mixed change | Use the heading that matters most to users |
| No commits | Empty release | Reply that there is nothing to release |
