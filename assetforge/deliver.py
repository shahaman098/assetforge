"""Deliver — engine-ready output: GLBs, the web manifest, receipts.

The deliverable is not "some files": a pack drop that a Three.js scene
loads directly (manifest + glbs + receipts). Everything an engine (or a
judge) needs to trust and use the assets is in the folder.
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List

from . import receipts as receipts_mod


def deliver_pack(pack, slot_results: List[Dict[str, Any]],
                 artifacts_dir: str, web_dir: str) -> Dict[str, Any]:
    name = pack.name
    pack_dir = os.path.join(artifacts_dir, name)
    glb_dir = os.path.join(pack_dir, "glbs")
    os.makedirs(glb_dir, exist_ok=True)
    os.makedirs(os.path.join(web_dir, "manifests"), exist_ok=True)

    manifest_slots = []
    assets_receipts: List[Dict[str, Any]] = []

    for r in slot_results:
        attempts = r.get("attempts", [])
        assets_receipts.append(
            receipts_mod.asset_receipt(name, r["slot"], attempts,
                                       r.get("passed", False),
                                       r.get("mutation_reasons", [])))
        if not r.get("passed"):
            continue  # honest delivery: only gated assets enter the pack
        glb_path = r.get("glb_path")
        if not glb_path or not os.path.exists(glb_path):
            continue
        dest = os.path.join(glb_dir, f"{r['slot']}.glb")
        shutil.copyfile(glb_path, dest)
        slot = next(s for s in pack.slots if s.slot == r["slot"])
        manifest_slots.append({
            "slot": r["slot"],
            "file": f"/artifacts/{name}/glbs/{r['slot']}.glb",
            "position": slot.position,
            "rotation": slot.rotation,
            "fit": 1.2,
            "sha256": receipts_mod.sha256_file(dest)[:12],
            "task_id": attempts[-1].get("task_id") if attempts else None,
            "gates": "passed",
        })

    theme = (pack.style_bible or {}).get("theme", {}) or {}
    manifest = {
        "name": name,
        "style": pack.lux3d_style,
        "theme": {
            "fog": theme.get("fog", "#1a1a1a"),
            "floor": theme.get("floor", "#444444"),
            "accent": theme.get("accent", "#ffffff"),
        },
        "slots": manifest_slots,
    }

    pack_receipt = receipts_mod.pack_receipts({
        "name": name,
        "target": pack.target,
        "budget": pack.budget,
        "lux3d_style": pack.lux3d_style,
    }, assets_receipts)

    receipts_path = os.path.join(pack_dir, "receipts.json")
    receipts_mod.write_json(receipts_path, pack_receipt)

    manifest_path = os.path.join(web_dir, "manifests", f"{name}.json")
    receipts_mod.write_json(manifest_path, manifest)

    return {
        "pack_dir": pack_dir,
        "receipts_path": receipts_path,
        "manifest_path": manifest_path,
        "delivered": len(manifest_slots),
        "receipts": pack_receipt,
    }
