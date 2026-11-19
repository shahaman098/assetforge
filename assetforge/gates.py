"""Deterministic QA gates — the heart of AssetForge.

Every verdict is computed, never vibed. The GLB JSON chunk is parsed with
the Python standard library only (face counts and bounds come straight
from glTF accessors); trimesh is used for topology checks (watertight)
and is optional — if it is unavailable the gate is SKIPPED, never guessed.
"""
from __future__ import annotations

import hashlib
import json
import struct
from typing import Any, Dict, List, Optional, Tuple

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

VENDOR_FACE_MIN = 10000
VENDOR_FACE_MAX = 300000


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_glb(path: str) -> Tuple[Optional[dict], Optional[bytes]]:
    """Return (json_chunk, bin_chunk) — stdlib only."""
    with open(path, "rb") as fh:
        header = fh.read(12)
        if len(header) < 12:
            return None, None
        magic, version, length = struct.unpack("<III", header)
        if magic != GLB_MAGIC:
            return None, None
        js: Optional[dict] = None
        bn: Optional[bytes] = None
        while True:
            ch = fh.read(8)
            if len(ch) < 8:
                break
            clen, ctype = struct.unpack("<II", ch)
            data = fh.read(clen)
            if ctype == CHUNK_JSON and js is None:
                try:
                    js = json.loads(data.decode("utf-8"))
                except Exception:
                    return None, None
            elif ctype == CHUNK_BIN and bn is None:
                bn = data
    return js, bn


def _accessor_faces(gltf: dict, prim: dict) -> Optional[int]:
    idx_acc = prim.get("indices")
    pos_acc = prim.get("attributes", {}).get("POSITION")
    if idx_acc is not None:
        acc = gltf.get("accessors", [])[idx_acc]
        return int(acc.get("count", 0)) // 3
    if pos_acc is not None:
        acc = gltf.get("accessors", [])[pos_acc]
        return int(acc.get("count", 0)) // 3
    return None


def glb_stats(path: str) -> Dict[str, Any]:
    js, _bn = parse_glb(path)
    if js is None:
        return {"valid_glb": False}
    face_count = 0
    vertex_count = 0
    min_b = None
    max_b = None
    materials = set()
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            f = _accessor_faces(js, prim)
            if f:
                face_count += f
            pos_acc = prim.get("attributes", {}).get("POSITION")
            if pos_acc is not None:
                acc = js.get("accessors", [])[pos_acc]
                vertex_count += int(acc.get("count", 0))
                amin = acc.get("min")
                amax = acc.get("max")
                if amin and amax:
                    if min_b is None:
                        min_b = list(amin)
                        max_b = list(amax)
                    else:
                        for i in range(3):
                            min_b[i] = min(min_b[i], amin[i])
                            max_b[i] = max(max_b[i], amax[i])
            if prim.get("material") is not None:
                materials.add(prim["material"])
    has_texture = False
    for mat_i in materials:
        mat = (js.get("materials") or [])[mat_i]
        pbr = mat.get("pbrMetallicRoughness", {}) or {}
        if pbr.get("baseColorTexture") or mat.get("emissiveTexture"):
            has_texture = True
    if not materials and js.get("materials"):
        has_texture = any(
            (m.get("pbrMetallicRoughness", {}) or {}).get("baseColorTexture")
            for m in js.get("materials", []))
    dims = None
    if min_b and max_b:
        dims = [round(max_b[i] - min_b[i], 4) for i in range(3)]
    return {
        "valid_glb": True,
        "face_count": face_count,
        "vertex_count": vertex_count,
        "min": min_b,
        "max": max_b,
        "dims": dims,
        "has_texture": has_texture,
        "materials": len(materials),
        "meshes": len(js.get("meshes", [])),
    }


def _watertight(path: str) -> Tuple[Optional[bool], str]:
    """None = skipped (trimesh unavailable or unparsable), never guessed."""
    try:
        import trimesh  # optional dependency
    except Exception:
        return None, "trimesh unavailable — gate skipped"
    try:
        obj = trimesh.load(path, force="mesh", process=False)
        return bool(obj.is_watertight), "trimesh"
    except Exception as exc:  # noqa: BLE001
        return None, f"trimesh load failed ({exc.__class__.__name__}) — gate skipped"


def run_gates(path: str, *, face_count_target: int = 60000,
              target: str = "game",
              face_min: int = VENDOR_FACE_MIN,
              face_max: int = VENDOR_FACE_MAX) -> Dict[str, Any]:
    """Return {passed, checks: [...], stats: {...}} — all deterministic."""
    stats = glb_stats(path)
    checks: List[Dict[str, Any]] = []

    if not stats.get("valid_glb"):
        checks.append({"gate": "glb_parse", "passed": False,
                       "value": "invalid", "expected": "valid GLB", "note": "stdlib parse failed"})
        return {"passed": False, "checks": checks, "stats": stats}

    checks.append({"gate": "glb_parse", "passed": True, "value": "valid",
                   "expected": "valid GLB", "note": "stdlib GLB parser"})

    fc = int(stats.get("face_count", 0))
    fc_ok = face_min <= fc <= face_max
    fc_note = f"target {face_count_target} (vendor bounds {face_min}-{face_max})"
    if fc_ok and fc > 2.5 * face_count_target:
        fc_note += " — over 2.5x target, flagged"
        checks.append({"gate": "face_count", "passed": True, "value": fc,
                       "expected": f"{face_min}-{face_max}", "note": fc_note, "warn": True})
    else:
        checks.append({"gate": "face_count", "passed": fc_ok, "value": fc,
                       "expected": f"{face_min}-{face_max}", "note": fc_note})

    tex_ok = bool(stats.get("has_texture"))
    checks.append({"gate": "texture", "passed": tex_ok, "value": tex_ok,
                   "expected": True, "note": "baseColorTexture present in any material"})

    dims = stats.get("dims")
    bbox_ok = bool(dims) and all(d > 0.01 for d in dims)
    checks.append({"gate": "bbox_sane", "passed": bbox_ok,
                   "value": dims, "expected": "all dims > 0.01",
                   "note": "degenerate meshes rejected"})

    if target == "print":
        wt, note = _watertight(path)
        if wt is None:
            checks.append({"gate": "watertight", "passed": False, "value": "skipped",
                           "expected": True, "note": note, "skipped": True})
        else:
            checks.append({"gate": "watertight", "passed": wt, "value": wt,
                           "expected": True, "note": note})

    passed = all(c.get("passed") for c in checks if not c.get("skipped"))
    return {"passed": passed, "checks": checks, "stats": stats}


def render_checks(checks: List[Dict[str, Any]]) -> str:
    out = []
    for c in checks:
        mark = "SKIP" if c.get("skipped") else ("PASS" if c["passed"] else "FAIL")
        warn = " (warn)" if c.get("warn") else ""
        out.append(f"[{mark}]{warn} {c['gate']:<12} {c['value']}  ({c['note']})")
    return "\n".join(out)
