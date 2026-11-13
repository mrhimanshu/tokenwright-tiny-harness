---
name: changelog-writer
description: Writes CHANGELOG.md release entries from commit lists. Use when asked for release notes or a changelog entry. Do NOT use for commit messages.
version: 2.0.0
license: MIT
metadata:
  tags: [changelog, release-notes, git, documentation]
  author: tokenwright
---

# Changelog writer

Turns a list of commits into one release entry for CHANGELOG.md, following the team's changelog rules (v2).

## When to use

- Use when someone asks for release notes, a changelog entry or "what changed" for a version.
- Do NOT use for writing commit messages, PR descriptions or blog posts.

## Prerequisites

- The version number and release date.
- The list of commits (conventional-commit style, with PR numbers).
- No scripts, tools or API keys are needed.

## Rules

1. First line is the header: `## [VERSION] - YYYY-MM-DD` (for example `## [2.1.0] - 2026-03-04`). Nothing before it: no intro sentence, no code fence.
2. Group bullets under these headings, in this order, and leave out any heading with no bullets:
   `### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Security`.
3. Every bullet ends with the pull request number in brackets, like `(#412)`.
4. Never include commit hashes.
5. Leave out commits whose type is `chore`, `ci`, `docs`, `test`, `style` or `build`: users don't care about them.
6. A breaking change (a `!` after the type, or `BREAKING CHANGE` in the message) goes under `### Changed` and starts with `**BREAKING:**`.
7. Anything that fixes a vulnerability goes under `### Security`, not `### Fixed`.
8. Start each bullet with a capital letter, write it for users (not developers), and don't end it with a full stop.

## Workflow

1. Read every commit and note its type, scope, PR number and any breaking marker.
2. Drop the internal types listed in rule 5.
3. Sort the rest into the headings from rule 2.
4. Rewrite each one as a short user-facing bullet ending in `(#PR)`.
5. Check the output against every rule before answering.

## Example

Commits:
```
a1b2c3d feat(api): add bulk export endpoint (#88)
d4e5f6a fix: crash when the cart is empty (#91)
0a9b8c7 chore: bump eslint (#92)
```

Entry:
```
## [1.2.0] - 2026-01-15

### Added
- Bulk export endpoint for orders (#88)

### Fixed
- Crash when opening an empty cart (#91)
```

## Troubleshooting

| Error | Cause | Solution |
| --- | --- | --- |
| A commit has no PR number | Pushed straight to main | Leave the bullet without a number and mention it to the user |
| A commit fits two headings | Mixed change | Use the heading that matters most to users |
| No user-facing commits | Only chores | Reply that there is nothing to release |
