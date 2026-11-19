"""Render the project report from receipts — nothing hand-typed.

Usage: .venv/bin/python tools/render_report.py
Reads: report/report-source.md, artifacts/*/receipts.json,
       bench/benchmark.md
Writes: report/build/report.html (then print to PDF via Edge headless)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from assetforge import receipts as receipts_mod  # noqa: E402

STYLE = """
<style>
 body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color:#1d1a15;
        margin:0; background:#fbf9f4; }
 .page { max-width: 860px; margin: 0 auto; padding: 44px 56px; }
 h1 { font-size: 30px; margin: 0 0 6px; }
 .sub { color:#6b6153; font-size:13px; margin-bottom:26px; }
 h2 { font-size: 19px; margin-top: 30px; border-bottom: 2px solid #e8e1d2;
      padding-bottom: 5px; }
 code { background:#efe9db; padding: 1px 5px; border-radius:3px; font-size: 12.5px; }
 pre { background:#f4efe3; padding: 12px 14px; border-radius:6px; overflow:auto;
       font-size: 12px; }
 table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 13px; }
 th { background:#2f2a22; color:#f5efe1; text-align:left; padding: 7px 10px; }
 td { border-bottom: 1px solid #e2dbc9; padding: 6px 10px; }
 tr:nth-child(even) td { background: #f5f0e4; }
 .pass { color:#2e7d32; font-weight:600; } .fail { color:#b3402a; font-weight:600; }
 .quote { border-left: 4px solid #c8a25a; padding: 8px 16px; background:#f6f1e6;
          color:#5d5343; font-style: italic; margin: 14px 0; }
 .note { font-size: 11.5px; color:#7a705f; }
</style>
"""


def esc(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def pack_table_html(pack_data: Dict[str, Any]) -> str:
    rows = []
    for a in pack_data.get("assets", []):
        f = a.get("final", {}) or {}
        cls = "pass" if a.get("passed") else "fail"
        rows.append(
            f"<tr><td>{esc(a['slot'])}</td>"
            f"<td class='{cls}'>{'PASS' if a.get('passed') else 'FAIL (excluded)'}</td>"
            f"<td>{len(a.get('attempts', []))}</td>"
            f"<td>{esc(f.get('task_id') or '-')}</td>"
            f"<td>{esc(f.get('face_count', '-'))}</td>"
            f"<td>{'yes' if f.get('has_texture') else 'no'}</td>"
            f"<td><code>{esc((f.get('sha256') or '')[:12])}</code></td>"
            f"<td>{esc(f.get('seconds', '-'))}s</td></tr>")
    return (
        f"<h3>Pack <code>{esc(pack_data.get('pack'))}</code> — "
        f"{sum(1 for a in pack_data['assets'] if a.get('passed'))}/{len(pack_data['assets'])} passed</h3>"
        "<table><tr><th>slot</th><th>gates</th><th>attempts</th><th>Lux3D task</th>"
        "<th>faces</th><th>texture</th><th>sha256</th><th>gen time</th></tr>"
        + "".join(rows) + "</table>"
        "<p class='note'>Rendered from receipts.json — re-derive offline with "
        "<code>python verify.py</code> (zero credits, no API key).</p>")


def bench_html() -> str:
    path = os.path.join(ROOT, "bench", "benchmark.md")
    if not os.path.exists(path):
        return "<p class='note'>Benchmark pending — run <code>af bench</code>.</p>"
    lines = open(path, encoding="utf-8").read().splitlines()
    out: List[str] = []
    in_table = False
    for ln in lines:
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not in_table:
                out.append("<table><tr>" + "".join(f"<th>{esc(c)}</th>" for c in cells) + "</tr>")
                in_table = True
            elif set("".join(cells)) <= set("-: "):
                continue
            else:
                out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>")
        else:
            if in_table:
                out.append("</table>")
                in_table = False
            if ln.strip():
                out.append(esc(ln))
    if in_table:
        out.append("</table>")
    return "<br>".join(x for x in out if x)


def failures_html() -> str:
    blocks = []
    for rp in sorted(glob.glob(os.path.join(ROOT, "artifacts", "*", "receipts.json"))):
        data = json.load(open(rp, encoding="utf-8"))
        for a in data.get("assets", []):
            reasons = a.get("mutation_reasons") or []
            if a.get("passed") and not reasons:
                continue
            att = a.get("attempts", [])
            detail = "; ".join(
                f"attempt {i+1}: task {t.get('task_id')} status={t.get('status')} "
                f"error={t.get('error', '-')}" for i, t in enumerate(att))
            blocks.append(
                f"<p><b>{esc(data['pack'])}/{esc(a['slot'])}</b> — "
                f"{'recovered after repair' if a.get('passed') else 'failed honestly, excluded'}"
                + (f"<br><span class='note'>repair: {esc(' | '.join(reasons))}</span>" if reasons else "")
                + (f"<br><span class='note'>{esc(detail)}</span>" if detail else "")
                + "</p>")
    if not blocks:
        blocks = ["<p class='note'>No failures recorded in this build.</p>"]
    return "\n".join(blocks)


def totals_html() -> str:
    n = attempts = 0
    sec = 0.0
    recovered = 0
    for rp in sorted(glob.glob(os.path.join(ROOT, "artifacts", "*", "receipts.json"))):
        data = json.load(open(rp, encoding="utf-8"))
        for a in data.get("assets", []):
            n += 1
            attempts += len(a.get("attempts", []))
            if a.get("passed"):
                sec += (a.get("final", {}) or {}).get("seconds") or 0
                if len(a.get("attempts", [])) > 1:
                    recovered += 1
    bench_runs = []
    bp = os.path.join(ROOT, "artifacts", "bench", "results.json")
    if os.path.exists(bp):
        bench_runs = json.load(open(bp, encoding="utf-8")).get("runs", [])
    return ("<ul>"
            f"<li>Assets delivered through gates: <b>{n}</b> across packs "
            f"({attempts} total Lux3D jobs, {recovered} recovered by the Repairer)</li>"
            f"<li>Successful generation wall-clock: <b>{sec/60:.1f} min</b> (concurrent)</li>"
            f"<li>Benchmark runs recorded: <b>{len(bench_runs)}</b> "
            "(per-run task IDs in artifacts/bench/results.json)</li>"
            "<li>Offline verification: <code>python verify.py</code> — zero credits</li></ul>")


def md_to_html(md: str) -> str:
    md = re.sub(r"^### (.+)$", r"<h3>\1</h3>", md, flags=re.M)
    md = re.sub(r"^## (.+)$", r"<h2>\1</h2>", md, flags=re.M)
    md = re.sub(r"^> (.+)$", r"<p class='quote'>\1</p>", md, flags=re.M)
    md = re.sub(r"^```.*$", "", md, flags=re.M)
    md = re.sub(r"`([^`]+)`", r"<code>\1</code>", md)
    md = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", md)
    md = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", md)
    md = re.sub(r"^(- .+)$", r"<li>\1</li>", md, flags=re.M)
    md = re.sub(r"^(\d+\. .+)$", r"<li>\1</li>", md, flags=re.M)
    md = re.sub(r"^<li>", r"<ul><li>", md, count=1)
    return md


def main() -> int:
    src = open(os.path.join(ROOT, "report", "report-source.md"), encoding="utf-8").read()

    def pack_marker(m: re.Match) -> str:
        rp = os.path.join(ROOT, "artifacts", m.group(1), "receipts.json")
        if not os.path.exists(rp):
            return f"<p class='note'>Pack {m.group(1)} pending build.</p>"
        return pack_table_html(json.load(open(rp, encoding="utf-8")))

    body = re.sub(r"<RECEIPT-PACK-TABLE:([\w-]+)>", pack_marker, src)
    body = body.replace("<RECEIPT-BENCH-TABLE>", bench_html())
    body = body.replace("<RECEIPT-FAILURES:>", failures_html())
    body = body.replace("<RECEIPT-FAILURES>", failures_html())
    body = body.replace("<RECEIPT-TOTALS:>", totals_html())
    body = body.replace("<RECEIPT-TOTALS>", totals_html())
    body = md_to_html(body)

    team = os.environ.get("AF_TEAM_NAME", "TeamName")
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>AssetForge — Project Report</title>" + STYLE + "</head><body><div class='page'>"
            f"<h1>AssetForge</h1>"
            f"<div class='sub'>One YAML in — a style-locked, machine-verified, "
            f"engine-ready 3D asset pack out, with receipts. · {esc(team)} · "
            "Manycore Aholo Global 3D AI Hackathon · #Manycorehackathon</div>"
            + body + "</div></body></html>")

    os.makedirs(os.path.join(ROOT, "report", "build"), exist_ok=True)
    out = os.path.join(ROOT, "report", "build", "report.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"report html -> {out}")
    print("print to PDF:  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge' "
          f"--headless --print-to-pdf={os.path.join(ROOT, 'report', 'build', 'TeamName-AssetForge.pdf')} "
          f"file://{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
