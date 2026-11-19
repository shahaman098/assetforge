"""Deterministic prompt mutation — the Repairer.

When a gate fails, the prompt is mutated ONCE with a targeted, explainable
change derived from the failed gate + the pack's style bible. No magic,
no LLM in the loop: every mutation is a rule you can read here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

SIMPLIFY = "very simple low-poly shapes, minimal surface detail"


def _failed_gates(gate_results: Dict[str, Any]) -> List[str]:
    return [c["gate"] for c in gate_results.get("checks", []) if not c.get("passed")]


def mutate(prompt: str, gate_results: Dict[str, Any],
           style_bible: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Return (mutated_prompt, reason). Idempotent-ish: never repeats a clause."""
    style_bible = style_bible or {}
    clauses: List[str] = []
    reasons: List[str] = []
    failed = _failed_gates(gate_results)

    if "face_count" in failed:
        clauses.append(SIMPLIFY)
        reasons.append("face_count gate failed -> demand simpler geometry")
    if "texture" in failed:
        materials = style_bible.get("materials") or ["stone"]
        clauses.append(f"made of {materials[0]} with a strong distinct visible base color")
        reasons.append(f"texture gate failed -> anchor a bold material ({materials[0]})")
    if "bbox_sane" in failed:
        clauses.append("one single solid free-standing object, centered, not flat")
        reasons.append("bbox gate failed -> forbid degenerate/flat output")
    if "glb_parse" in failed:
        clauses.append("a single simple solid object")
        reasons.append("output unparseable -> maximally simple subject")

    if not clauses:
        # gates failed for other reasons: generic simplification
        clauses.append("clean bold silhouette, solid single-material look")
        reasons.append("generic retry -> simplify the subject")

    base = prompt.rstrip(" .,")
    for c in clauses:
        if c.lower() not in base.lower():
            base = f"{base}, {c}"
    return base + ". The object should be the only subject, fully visible. " \
        f"Keep it in the style of: {style_bible.get('palette', 'clean and simple')}.", \
        "; ".join(reasons)
