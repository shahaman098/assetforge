"""Capability-boundary benchmark sweep — the truth engine's data source.

Measures the vendor's OWN published capability claims with receipts:
for each prompt (taxonomy mirrors the official boundary table) we generate
via Lux3D, gate the output, and record pass/fail. The resulting table is
the first measured capability map of Aholo Lux3D — useful to every
developer on the platform (and to the vendor).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402

from assetforge import client as client_mod  # noqa: E402
from assetforge import gates as gates_mod  # noqa: E402
from assetforge import receipts as receipts_mod  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def run_one(c, cat: Dict[str, Any], prompt: str, version: str,
            dl_root: str) -> Dict[str, Any]:
    t0 = time.time()
    task_id = None
    try:
        task_id = c.generate(prompt, version=version, face_count=60000)
        result = c.wait(task_id)
        outs = c.download_outputs(result, dl_root, f"bench_{task_id}")
        glb = next((o for o in outs if o.get("status") == "downloaded"
                    and o.get("path", "").endswith(".glb")), None)
        if glb is None:
            return {"category": cat["name"], "expectation": cat["expectation"],
                    "prompt": prompt, "task_id": task_id, "passed": False,
                    "seconds": round(time.time() - t0, 1),
                    "error": "no GLB output",
                    "outputs": json.dumps(outs)[:200]}
        g = gates_mod.run_gates(glb["path"], face_count_target=60000, target="game")
        stats = g["stats"]
        return {
            "category": cat["name"], "expectation": cat["expectation"],
            "prompt": prompt, "task_id": task_id,
            "passed": bool(g["passed"]),
            "face_count": stats.get("face_count"),
            "has_texture": stats.get("has_texture"),
            "dims": stats.get("dims"),
            "sha256": receipts_mod.sha256_file(glb["path"])[:12],
            "failed_gates": [ch["gate"] for ch in g["checks"] if not ch.get("passed")],
            "seconds": round(time.time() - t0, 1),
        }
    except Exception as exc:  # noqa: BLE001
        return {"category": cat["name"], "expectation": cat["expectation"],
                "prompt": prompt, "task_id": task_id, "passed": False,
                "seconds": round(time.time() - t0, 1),
                "error": f"{exc.__class__.__name__}: {exc}"}


def render_results(results: List[Dict[str, Any]], version: str) -> str:
    by_cat: Dict[str, Dict[str, Any]] = {}
    for r in results:
        d = by_cat.setdefault(r["category"], {"n": 0, "passed": 0, "exp": r["expectation"],
                                              "fails": {}})
        d["n"] += 1
        if r.get("passed"):
            d["passed"] += 1
        else:
            for fg in (r.get("failed_gates") or ["no-output/error"]):
                d["fails"][fg] = d["fails"].get(fg, 0) + 1

    lines = ["# Lux3D capability-boundary benchmark (measured, with receipts)", "",
             f"- Model version: `{version}` · gates: face_count 10k–300000 · texture present · sane bbox",
             f"- Runs: {len(results)} · Every row below is re-derivable from "
             f"`artifacts/bench/results.json` + `bench/categories.yaml`.",
             "", "| category | vendor claim | pass rate | verdict vs claim | dominant failures |",
             "|---|---|---|---|---|"]
    verdicts = {"high": ">=60% expected", "mixed": "mid-range expected", "low": "<=40% expected"}
    for name, d in by_cat.items():
        rate = d["passed"] / d["n"] if d["n"] else 0
        exp = d["exp"]
        if exp == "high":
            verdict = "CONFIRMED" if rate >= 0.6 else ("PARTIAL" if rate >= 0.4 else "CONTRADICTED")
        elif exp == "mixed":
            verdict = "CONFIRMED" if 0.25 <= rate <= 0.75 else "PARTIAL"
        else:
            verdict = "CONFIRMED" if rate <= 0.4 else ("PARTIAL" if rate <= 0.6 else "CONTRADICTED")
        fails = ", ".join(f"{k}×{v}" for k, v in sorted(d["fails"].items(),
                                                        key=lambda kv: -kv[1])) or "—"
        lines.append(f"| {name} | {exp} ({verdicts[exp]}) | {d['passed']}/{d['n']} "
                     f"({rate:.0%}) | **{verdict}** | {fails} |")
    lines += ["", "_Failure taxonomy is a feature: we publish what the model cannot "
                  "reliably do, with per-run task IDs in results.json._"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", default="artifacts")
    ap.add_argument("--max-jobs", type=int, default=24)
    ap.add_argument("--version", default="G1-Turbo")
    ap.add_argument("--categories", default="", help="comma-separated filter")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()

    with open(os.path.join(HERE, "categories.yaml"), "r", encoding="utf-8") as fh:
        cats = yaml.safe_load(fh)["categories"]
    if args.categories:
        keep = set(args.categories.split(","))
        cats = [c for c in cats if c["name"] in keep]

    jobs = []
    for c in cats:
        for p in c["prompts"]:
            jobs.append((c, p))
    jobs = jobs[: args.max_jobs]
    print(f"benchmark sweep: {len(jobs)} jobs, version={args.version}, "
          f"concurrency={args.concurrency}")
    print(f"estimated credits: ~{len(jobs) * 20:.0f}")
    print("")

    c = client_mod.Lux3DClient(ledger_path=os.path.join(args.artifacts, "ledger.jsonl"))
    dl_root = os.path.join(args.artifacts, "bench", "downloads")
    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, c, cat, p, args.version, dl_root): (cat, p)
                for cat, p in jobs}
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            results.append(r)
            print(f"  [{r['category']}] {'PASS' if r.get('passed') else 'FAIL'} "
                  f"task={r.get('task_id')} ({r.get('seconds')}s) "
                  f"{r.get('error', '')}", flush=True)

    out_dir = os.path.join(args.artifacts, "bench")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"version": args.version, "ts": int(time.time()), "runs": results},
                  fh, indent=2, ensure_ascii=False)
    md = render_results(results, args.version)
    with open(os.path.join(HERE, "benchmark.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print("\n" + md)
    print(f"\nresults -> {os.path.join(out_dir, 'results.json')}  ·  "
          f"table -> {os.path.join(HERE, 'benchmark.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
