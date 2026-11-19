"""Pack brief loader + planner.

The planner mirrors the Lux3D skill's own plan->quote->authorize flow:
it never calls the API, it computes what a pack *would* cost before a
single credit is spent (epidemiology: screening before confirmatory).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

# Field-calibrated credit estimate (A Moment in Bloom: 860 credits / 43 jobs).
DEFAULT_CREDITS_PER_JOB = 20.0
DEFAULT_SECONDS_PER_JOB = 90.0

VALID_LUX3D_STYLES = ("photorealistic", "cartoon", "anime", "hand_painted",
                      "cyberpunk", "fantasy", "glass")


@dataclass
class Slot:
    slot: str
    prompt: str
    position: List[float]
    rotation: List[float]


@dataclass
class Pack:
    name: str
    target: str
    engine: str
    style_bible: Dict[str, Any]
    budget: Dict[str, Any]
    slots: List[Slot]
    path: str

    @property
    def lux3d_style(self) -> Optional[str]:
        style = self.style_bible.get("lux3d_style")
        if style and style in VALID_LUX3D_STYLES:
            return style
        return None

    @property
    def version(self) -> str:
        return str(self.budget.get("version", "G1-Turbo"))

    @property
    def face_count(self) -> int:
        return int(self.budget.get("face_count", 60000))

    @property
    def max_retries(self) -> int:
        return int(self.budget.get("max_retries", 1))


def load_pack(path: str) -> Pack:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    name = data.get("name") or os.path.splitext(os.path.basename(path))[0]
    slots = []
    for s in data.get("slots", []):
        slots.append(Slot(
            slot=str(s["slot"]),
            prompt=str(s["prompt"]),
            position=[float(x) for x in s.get("position", [0, 0, 0])][:3],
            rotation=[float(x) for x in s.get("rotation", [0, 0, 0])][:3],
        ))
    if not slots:
        raise ValueError(f"pack {path} has no slots")
    return Pack(
        name=name,
        target=data.get("target", "game"),
        engine=data.get("engine", "threejs"),
        style_bible=data.get("style", {}) or {},
        budget=data.get("budget", {}) or {},
        slots=slots,
        path=path,
    )


def quote_rows(pack: Pack) -> List[Dict[str, Any]]:
    rows = []
    for s in pack.slots:
        rows.append({
            "slot": s.slot,
            "version": pack.version,
            "face_count": pack.face_count,
            "style": pack.lux3d_style or "-",
            "credits_est": DEFAULT_CREDITS_PER_JOB,
            "seconds_est": DEFAULT_SECONDS_PER_JOB,
        })
    return rows


def quote_totals(pack: Pack) -> Dict[str, float]:
    n = len(pack.slots)
    retries = sum(pack.max_retries for _ in pack.slots)
    return {
        "assets": n,
        "credits_best": n * DEFAULT_CREDITS_PER_JOB,
        "credits_worst": (n + retries) * DEFAULT_CREDITS_PER_JOB,
        "seconds_best": n * DEFAULT_SECONDS_PER_JOB,
        "prompt": pack.name,
    }


def render_plan(pack: Pack) -> str:
    lines = []
    lines.append(f"AssetForge plan — pack '{pack.name}' (target={pack.target})")
    lines.append(f"  style bible : {pack.style_bible.get('palette', '-')}")
    lines.append(f"  avoid       : {', '.join(pack.style_bible.get('avoid', []))}")
    lines.append(f"  lux3d_style : {pack.lux3d_style or 'default'}   version: {pack.version}   face_count: {pack.face_count}")
    lines.append("")
    lines.append(f"  {'slot':<10} {'style':<14} {'credits':>8} {'~sec':>6}  prompt")
    for r in quote_rows(pack):
        slot = next(s for s in pack.slots if s.slot == r["slot"])
        prompt = slot.prompt if len(slot.prompt) <= 58 else slot.prompt[:55] + "..."
        lines.append(f"  {r['slot']:<10} {r['style']:<14} {r['credits_est']:>8.0f} {r['seconds_est']:>6.0f}  {prompt}")
    t = quote_totals(pack)
    lines.append("")
    lines.append(f"  quote: {t['assets']} assets · ~{t['credits_best']:.0f} credits best case "
                 f"(~{t['credits_worst']:.0f} with 1 retry each) · ~{t['seconds_best']/60:.0f} min")
    lines.append("  gates : face_count in [10000, 300000] · texture present · sane bbox"
                 + (" · watertight (print)" if pack.target == "print" else ""))
    return "\n".join(lines)
