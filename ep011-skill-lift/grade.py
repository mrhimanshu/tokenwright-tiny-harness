"""Deterministic grader: 8 checks = the 8 rules of the team's changelog convention (v2)."""
import re

ORDER = ["Added", "Changed", "Fixed", "Removed", "Security"]


def parse(text):
    lines = [l.rstrip() for l in text.strip().splitlines()]
    while lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    secs, cur, bullets = [], None, []
    for l in lines:
        m = re.match(r"^###\s+(.*)$", l.strip())
        if m:
            cur = m.group(1).strip(); secs.append(cur)
        elif re.match(r"^\s*[-*]\s+", l):
            bullets.append((cur, re.sub(r"^\s*[-*]\s+", "", l).strip()))
    return lines, secs, bullets


def prs(s):
    return set(int(x) for x in re.findall(r"#(\d+)", s))


def grade(text, task):
    lines, secs, bullets = parse(text)
    first = next((l for l in text.strip().splitlines() if l.strip()), "")
    all_prs = set(int(re.search(r"\(#(\d+)\)", c).group(1)) for c in task["commits"])
    want = all_prs - set(task["exclude"])
    got = set().union(*[prs(b) for _, b in bullets]) if bullets else set()
    used = [s for s in secs if any(c == s for c, _ in bullets)]
    c = {}
    c["header"] = first.strip() == f"## [{task['version']}] - {task['date']}"
    c["headings"] = bool(secs) and all(s in ORDER for s in secs) and secs == sorted(secs, key=ORDER.index) and used == secs
    c["pr_suffix"] = bool(bullets) and all(re.search(r"\(#\d+\)$", b) for _, b in bullets)
    c["no_hashes"] = not any(re.search(r"\b[0-9a-f]{7}\b", l) for l in lines)
    c["internal_dropped"] = got == want
    br = [(s, b) for s, b in bullets if task["breaking"] in prs(b)]
    c["breaking"] = bool(br) and all(s == "Changed" and b.startswith("**BREAKING:**") for s, b in br)
    sec = [s for s, b in bullets if task["security"] in prs(b)]
    c["security"] = bool(sec) and all(s == "Security" for s in sec)
    c["style"] = bool(bullets) and all(b[:1].isupper() or b.startswith("**") for _, b in bullets) and \
        not any(re.sub(r"\s*\(#\d+\)$", "", b).endswith(".") for _, b in bullets)
    return {"score": sum(c.values()), "checks": c}
