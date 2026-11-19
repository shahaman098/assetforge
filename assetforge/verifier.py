"""Offline Auditor — re-derive every claim from receipts, zero credits.

A judge (or teammate) clones the repo, runs `python verify.py`, and watches
every delivered asset re-pass its gates with no API key, no credits, no
network. This module is that guarantee.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Any, Dict, List, Tuple

from . import gates as gates_mod
from . import receipts as receipts_mod


def _check(condition: bool, msg_ok: str, msg_bad: str, lines: List[str],
           failures: List[str]) -> bool:
    if condition:
        lines.append("  [PASS] " + msg_ok)
    else:
        lines.append("  [FAIL] " + msg_bad)
        failures.append(msg_bad)
    return condition


def verify_pack(receipts_path: str, artifacts_dir: str,
                web_dir: str) -> Tuple[bool, List[str]]:
    lines: List[str] = []
    failures: List[str] = []
    with open(receipts_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    pack_name = data.get("pack", "?")
    lines.append(f"PACK {pack_name}  (target={data.get('target')}, "
                 f"style={data.get('lux3d_style') or 'default'})")

    budget = data.get("budget", {}) or {}
    face_target = int(budget.get("face_count", 60000))
    target = data.get("target", "game")

    passed_slots = []
    for a in data.get("assets", []):
        slot = a.get("slot", "?")
        final = a.get("final", {}) or {}
        lines.append(f"  asset '{slot}'")
        if not a.get("passed"):
            _check(True, f"'{slot}' recorded as FAILED honestly — excluded from pack",
                   "", lines, failures)
            continue
        passed_slots.append(slot)
        glb_path = os.path.join(artifacts_dir, pack_name, "glbs", f"{slot}.glb")
        if not _check(os.path.exists(glb_path), f"'{slot}' GLB present",
                      f"'{slot}' GLB MISSING at {glb_path}", lines, failures):
            continue
        _check(receipts_mod.sha256_file(glb_path) == final.get("sha256"),
               f"'{slot}' sha256 matches receipt",
               f"'{slot}' sha256 MISMATCH — file changed after delivery", lines, failures)
        g = gates_mod.run_gates(glb_path, face_count_target=face_target, target=target)
        _check(g["passed"], f"'{slot}' re-passes all gates offline",
               f"'{slot}' FAILS gates on re-run: "
               + str([c for c in g["checks"] if not c.get("passed")]), lines, failures)
        _check(g["stats"].get("face_count") == final.get("face_count"),
               f"'{slot}' face_count re-derived identically "
               f"({g['stats'].get('face_count')})",
               f"'{slot}' face_count DRIFTED: receipt {final.get('face_count')} "
               f"vs re-run {g['stats'].get('face_count')}", lines, failures)
        _check(g["stats"].get("has_texture") == final.get("has_texture"),
               f"'{slot}' texture presence re-derived identically",
               f"'{slot}' texture DRIFTED", lines, failures)

    # manifest must contain exactly the passed slots (no phantom assets)
    manifest_path = os.path.join(web_dir, "manifests", f"{pack_name}.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        m_slots = [s["slot"] for s in manifest.get("slots", [])]
        _check(sorted(m_slots) == sorted(passed_slots),
               f"manifest contains exactly the gated assets ({len(m_slots)})",
               f"manifest/ receipts DISAGREE: manifest={sorted(m_slots)} "
               f"receipts={sorted(passed_slots)}", lines, failures)
        for s in manifest.get("slots", []):
            if not os.path.exists(os.path.join("artifacts", pack_name,
                                               "glbs", f"{s['slot']}.glb")):
                pass  # absolute-path check already covered via glb_path above
    else:
        _check(not passed_slots,
               "no manifest (nothing delivered) — consistent with receipts",
               f"manifest missing for pack with delivered assets: {manifest_path}",
               lines, failures)

    n_assets = len(data.get("assets", []))
    lines.append(f"  -> {sum(1 for a in data['assets'] if a.get('passed'))}/{n_assets} "
                 f"assets verified offline, zero credits, no API key.")
    return (len(failures) == 0), lines


def verify_artifacts(artifacts_dir: str, web_dir: str) -> Tuple[bool, List[str]]:
    all_lines: List[str] = ["AssetForge offline verification — re-deriving every "
                            "claim from receipts (zero credits, no network)...", ""]
    ok_all = True
    found = 0
    for receipts_path in sorted(glob.glob(os.path.join(artifacts_dir, "*", "receipts.json"))):
        found += 1
        ok, lines = verify_pack(receipts_path, artifacts_dir, web_dir)
        all_lines.extend(lines + [""])
        ok_all = ok_all and ok
    if found == 0:
        all_lines.append("No receipts found under artifacts/ — nothing to verify yet. "
                        "Run `af build packs/cozy-dungeon.yaml` first.")
        return True, all_lines
    all_lines.append("VERDICT: " + ("ALL RECEIPTS RE-DERIVED CLEAN" if ok_all
                                    else "DISCREPANCIES FOUND — see FAIL lines above"))
    return ok_all, all_lines
