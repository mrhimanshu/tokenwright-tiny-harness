---
name: changelog-writer
description: I can help you with changelogs
---
header = ## [VERSION] - YYYY-MM-DD, first line, nothing before it, no fence
headings in order Added Changed Fixed Removed Security (### each), skip empty
every bullet ends (#PR)
no hashes
skip chore ci docs test style build
breaking (! or BREAKING CHANGE) -> under Changed, starts **BREAKING:**
vuln fixes -> Security not Fixed
Capital first letter, for users, no full stop at end
