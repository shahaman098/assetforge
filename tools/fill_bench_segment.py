"""Fill video/bench.html with the real measured table from bench/benchmark.md.

Renders the benchmark segment (SEG G) of the demo video from real data —
never hand-typed.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    src = open(os.path.join(ROOT, "bench", "benchmark.md"), encoding="utf-8").read()
    rows = []
    for line in src.splitlines():
        if not line.startswith("|") or set(line.strip("|").strip()) <= set("-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] in ("category", ""):
            continue
        name, claim, rate, verdict, fails = cells[:5]
        vcls = "ok" if "CONFIRMED" in verdict else ("bad" if "CONTRADICTED" in verdict else "")
        rows.append(
            f"<tr><td>{name}</td><td>{claim}</td><td>{rate}</td>"
            f"<td class='{vcls}'>{verdict.replace('**', '')}</td><td>{fails}</td></tr>")
    html = open(os.path.join(ROOT, "video", "bench.html"), encoding="utf-8").read()
    html = html.replace("<!--ROWS-->", "\n    ".join(rows))
    out = os.path.join(ROOT, "video", "bench-live.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"rows: {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
