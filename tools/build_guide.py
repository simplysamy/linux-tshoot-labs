#!/usr/bin/env python3
"""Build linux-tshoot-lab-guide.html: one self-contained study guide.

Reads every lab's README.md + SOLUTION.md, adds the hand-written explanations and
quiz questions from tools/content_*.py, and writes a single HTML file (no network needed).

    python tools/build_guide.py            # writes ./linux-tshoot-lab-guide.html
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_easy import CONTENT as C_EASY      # noqa: E402
from content_medium import CONTENT as C_MEDIUM  # noqa: E402
from content_hard import CONTENT as C_HARD      # noqa: E402

from cmds_easy import CMDS as K_EASY            # noqa: E402
try:
    from cmds_medium import CMDS as K_MEDIUM    # noqa: E402
except ImportError:
    K_MEDIUM = {}
try:
    from cmds_hard import CMDS as K_HARD        # noqa: E402
except ImportError:
    K_HARD = {}

CONTENT = {**C_EASY, **C_MEDIUM, **C_HARD}
CMDS = {**K_EASY, **K_MEDIUM, **K_HARD}
LEVELS = ["easy", "medium", "hard"]


# number of command-table rows that belong under each "## N." step of SOLUTION.md (in order)
SPLIT = {
    "e01": [3, 2, 2, 2, 2], "e02": [2, 2, 2, 3], "e03": [3, 3, 5], "e04": [2, 5, 3, 5],
    "e05": [2, 2, 2, 4], "e06": [2, 1, 1, 4, 1], "e07": [2, 2, 4, 2, 0], "e08": [2, 3, 3, 2],
    "e09": [2, 2, 4, 1], "e10": [2, 1, 3, 2, 2],
    "m01": [2, 3, 1, 2], "m02": [3, 2, 3, 2], "m03": [4, 3, 4, 0], "m04": [3, 3, 2, 2],
    "m05": [3, 1, 2, 4, 1], "m06": [3, 3, 3, 5, 0], "m07": [3, 1, 2, 3, 2, 0],
    "m08": [2, 3, 2, 2, 2], "m09": [1, 1, 3, 2, 3, 1], "m10": [2, 4, 5, 1],
    "h01": [6, 3, 2, 3, 0], "h02": [3, 2, 3, 2, 3, 1], "h03": [3, 3, 4, 2, 3],
    "h04": [3, 2, 3, 2, 3], "h05": [3, 5, 3, 1], "h06": [3, 2, 2, 1, 3, 0],
    "h07": [2, 2, 1, 2, 2, 1], "h08": [1, 1, 5, 3, 2, 0], "h09": [3, 4, 2, 2, 2, 0],
    "h10": [2, 4, 3, 3, 1],
}


def solution_html(lab_id, main):
    """Solution markdown with each step followed by its 'commands explained' table."""
    chunks = [c for c in re.split(r"^(?=## )", main, flags=re.M) if c.strip()]
    pre = ""
    if chunks and not chunks[0].startswith("## "):
        pre, chunks = md(chunks[0], h=1), chunks[1:]
    lines = CMDS[lab_id].strip().split("\n")
    head, rows = lines[:2], lines[2:]
    counts = SPLIT[lab_id]
    assert len(chunks) == len(counts) and sum(counts) == len(rows), (lab_id, len(chunks), counts, len(rows))
    out, k = [pre] if pre else [], 0
    for chunk, n in zip(chunks, counts):
        out.append(md(chunk, h=1))
        if n:
            table = "\n".join(head + rows[k:k + n])
            k += n
            out.append('<div class="cmdbox"><div class="cmdhead">Commands in this step - what and why</div>%s</div>' % md(table, h=1))
    return "\n".join(out)


# --------------------------------------------------------------------------- markdown
def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    s = re.sub(r"`([^`]+)`", stash, s)
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)

    def link(m):
        text, url = m.group(1), m.group(2)
        if url.startswith("http"):
            return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (url, text)
        return text

    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % esc(codes[int(m.group(1))]), s)
    return s


def highlight(code):
    out = []
    for ln in code.split("\n"):
        m = re.search(r"(^|\s)#(\s.*)?$", ln)
        if m:
            pre = ln[: m.start() + len(m.group(1))]
            if pre.count("'") % 2 == 0 and pre.count('"') % 2 == 0:
                out.append(esc(pre) + '<span class="c">' + esc(ln[len(pre):]) + "</span>")
                continue
        out.append(esc(ln))
    return "\n".join(out)


def split_row(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"\|(?=(?:[^`]*`[^`]*`)*[^`]*$)", row)]


def md(text, h=0, br=False):
    lines = text.strip("\n").split("\n")
    i, out = 0, []
    n = len(lines)

    def starts_block(k):
        ln = lines[k]
        return bool(
            re.match(r"^```", ln) or re.match(r"^#{1,6}\s", ln) or ln.startswith(">")
            or re.match(r"^(\s*)([-*]|\d+\.)\s+", ln) or re.match(r"^---+\s*$", ln)
            or (ln.lstrip().startswith("|") and k + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[k + 1]))
        )

    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        m = re.match(r"^```(\w*)\s*$", ln)
        if m:
            i += 1
            buf = []
            while i < n and not re.match(r"^```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('<pre><code class="lang-%s">%s</code></pre>' % (m.group(1) or "text", highlight("\n".join(buf))))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            lvl = min(6, len(m.group(1)) + h)
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue
        if re.match(r"^---+\s*$", ln):
            out.append("<hr>")
            i += 1
            continue
        if ln.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>" % md("\n".join(buf), h, br=True))
            continue
        if ln.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            head = split_row(ln)
            i += 2
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            t = ["<div class='tablewrap'><table>"]
            if any(head):
                t.append("<thead><tr>%s</tr></thead>" % "".join("<th>%s</th>" % inline(c) for c in head))
            t.append("<tbody>")
            for r in rows:
                t.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", ln)
        if m:
            ordered = m.group(2)[0].isdigit()
            items = []
            while i < n:
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if mm:
                    items.append(mm.group(3))
                    i += 1
                elif lines[i].strip() and lines[i].startswith("  ") and items:
                    items[-1] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x) for x in items), tag))
            continue
        buf = [ln.strip()]
        i += 1
        while i < n and lines[i].strip() and not starts_block(i):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)) if not br else inline("\n".join(buf)).replace("\n", "<br>\n"))
    return "\n".join(out)


def sections(text):
    """Split on '## ' headings -> (preamble, {heading: body})."""
    parts = re.split(r"^## (.*)$", text, flags=re.M)
    pre = parts[0]
    secs = {}
    for k in range(1, len(parts), 2):
        secs[parts[k].strip()] = parts[k + 1].strip("\n")
    return pre, secs


# --------------------------------------------------------------------------- collect labs
def load_lab(level, d):
    readme = (d / "README.md").read_text(encoding="utf-8")
    solution = (d / "SOLUTION.md").read_text(encoding="utf-8")
    pre, sec = sections(readme)
    first = pre.strip().split("\n")
    m = re.match(r"^#\s+(\w+)\s+-\s+(.*)$", first[0])
    lab_id, title = m.group(1).lower(), m.group(2).strip()
    meta = dict(re.findall(r"\*\*(\w+):\*\*\s*([^·\n]+)", "\n".join(first[1:])))
    meta = {k: v.strip() for k, v in meta.items()}

    hints = [
        {"title": inline(t.strip()), "html": md(b.strip())}
        for t, b in re.findall(r"<details><summary>(.*?)</summary>\s*(.*?)</details>", sec.get("Hints", ""), re.S)
    ]
    wk = next((k for k in sec if k.startswith("Warm-up")), None)
    warmup = md(sec[wk], h=1) if wk else ""
    learn = "\n".join(l for l in sec.get("What you should learn", "").split("\n") if not l.startswith("Solution:"))

    body = solution.split("\n", 1)[1].lstrip("\n")  # drop '# E01 - Solution'
    parts = re.split(r"^## Root cause.*$", body, maxsplit=1, flags=re.M)
    main, root = parts[0], (parts[1] if len(parts) > 1 else "")
    c = CONTENT[lab_id]

    return {
        "id": lab_id,
        "level": level,
        "title": title,
        "time": meta.get("Time", ""),
        "skills": meta.get("Skills", ""),
        "ticket": md(sec.get("Ticket", "")),
        "success": md(sec.get("Success criteria", "")),
        "warmup": warmup,
        "hints": hints,
        "learn": md(learn),
        "solution": solution_html(lab_id, main),
        "root": md(root, h=1),
        "explain": md(c["explain"], h=1),
        "mcq": [{"q": q, "o": o, "why": w} for q, o, w in c["mcq"]],
        "qa": [{"q": q, "a": a} for q, a in c["qa"]],
    }


def build_data():
    labs = []
    for level in LEVELS:
        for d in sorted((ROOT / "labs" / level).iterdir()):
            if d.is_dir():
                labs.append(load_lab(level, d))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    _, rsec = sections(readme)
    method_key = next(k for k in rsec if k.startswith("How a senior SRE"))
    method_body = re.split(r"^---\s*$", rsec[method_key], flags=re.M)[0]
    mc = CONTENT["method"]
    system = md(rsec[next(k for k in rsec if k.startswith("The system you will support"))].split("\n---")[0], h=1)
    run = md(rsec[next(k for k in rsec if k.startswith("How to run a lab"))].split("\n---")[0], h=1)
    return {
        "labs": labs,
        "method": {
            "html": md(method_body, h=0),
            "mcq": [{"q": q, "o": o, "why": w} for q, o, w in mc["mcq"]],
            "qa": [{"q": q, "a": a} for q, a in mc["qa"]],
        },
        "home": {"system": system, "run": run},
    }


def main():
    data = build_data()
    # sanity checks
    for lab in data["labs"]:
        assert len(lab["mcq"]) >= 3 and len(lab["qa"]) >= 2, lab["id"]
        assert lab["ticket"] and lab["solution"] and lab["root"] and lab["hints"], lab["id"]
        for q in lab["mcq"]:
            assert len(q["o"]) == 4, (lab["id"], q["q"])
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028")
    tpl = (Path(__file__).resolve().parent / "guide_template.html").read_text(encoding="utf-8")
    out = tpl.replace("/*__DATA__*/", payload)
    target = ROOT / "linux-tshoot-lab-guide.html"
    target.write_text(out, encoding="utf-8", newline="\n")
    nm = sum(len(l["mcq"]) for l in data["labs"]) + len(data["method"]["mcq"])
    nq = sum(len(l["qa"]) for l in data["labs"]) + len(data["method"]["qa"])
    print("wrote %s  (%d labs, %d multiple-choice, %d Q&A, %d KB)" % (target.name, len(data["labs"]), nm, nq, len(out) // 1024))


if __name__ == "__main__":
    main()
