---
name: changelog-writer
description: Writes a CHANGELOG.md release entry from a list of commits using the team's changelog rules. Use when asked for release notes or a changelog entry.
---

# Changelog writer

Turn a list of commits into one release entry for CHANGELOG.md.

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
