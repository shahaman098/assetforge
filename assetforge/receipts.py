"""Receipts — the Auditor's raw material.

Every claim in the report/README is rendered from these files. Nothing is
hand-typed. A receipt records: the exact prompt(s) tried, the Lux3D task
IDs, timings, per-gate verdicts with values, the sha256 of every delivered
file. `verify.py` re-derives all of it offline, with zero credits.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List

from . import gates as gates_mod


def sha256_file(path: str) -> str:
    return gates_mod.sha256_file(path)


def attempt_receipt(*, prompt: str, task_id: int, status: Any,
                    seconds: float, glb_path: str = "",
                    gate_results: Dict[str, Any] = None,
                    error: str = "") -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "prompt": prompt,
        "task_id": task_id,
        "status": status,
        "seconds": round(seconds, 1),
    }
    if error:
        rec["error"] = error
    if glb_path:
        rec["sha256"] = sha256_file(glb_path)
        rec["bytes"] = os.path.getsize(glb_path)
        rec["gates"] = gate_results or {}
    return rec


def asset_receipt(pack: str, slot: str, attempts: List[Dict[str, Any]],
                  passed: bool, mutation_reasons: List[str]) -> Dict[str, Any]:
    final = attempts[-1] if attempts else {}
    stats = (final.get("gates") or {}).get("stats", {})
    return {
        "pack": pack,
        "slot": slot,
        "passed": passed,
        "attempts": attempts,
        "mutation_reasons": mutation_reasons,
        "final": {
            "task_id": final.get("task_id"),
            "sha256": final.get("sha256"),
            "bytes": final.get("bytes"),
            "face_count": stats.get("face_count"),
            "has_texture": stats.get("has_texture"),
            "dims": stats.get("dims"),
            "seconds": final.get("seconds"),
        },
        "generator": "Aholo Lux3D via official manycore-aholo-sdk-lux3d",
        "ts": int(time.time()),
    }


def pack_receipts(pack_meta: Dict[str, Any], assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "pack": pack_meta.get("name"),
        "target": pack_meta.get("target"),
        "budget": pack_meta.get("budget"),
        "lux3d_style": pack_meta.get("lux3d_style"),
        "assets": assets,
        "ts": int(time.time()),
    }


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def summary_table(pack_data: Dict[str, Any]) -> str:
    """Markdown table — render numbers from receipts, never by hand."""
    assets = pack_data.get("assets", [])
    lines = [
        f"### Pack `{pack_data.get('pack')}` — {sum(1 for a in assets if a['passed'])}/{len(assets)} passed",
        "",
        "| slot | passed | attempts | task_id | faces | texture | sha256 (first 12) | seconds |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in assets:
        f = a.get("final", {})
        sha = (f.get("sha256") or "")[:12] or "-"
        lines.append(
            f"| {a['slot']} | {'YES' if a['passed'] else 'NO'} | {len(a.get('attempts', []))} "
            f"| {f.get('task_id') or '-'} | {f.get('face_count', '-')} "
            f"| {f.get('has_texture', '-')} | `{sha}` | {f.get('seconds', '-')} |")
    total_sec = sum((a.get("final", {}) or {}).get("seconds") or 0 for a in assets)
    lines.append("")
    lines.append(f"_Rendered from receipts.json — re-derive with `python verify.py` "
                 f"(offline, zero credits). Total generation wall-clock: {total_sec:.0f}s._")
    return "\n".join(lines)
