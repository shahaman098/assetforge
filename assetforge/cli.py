"""AssetForge CLI — plan | probe | build | verify | bench.

Pipeline: plan (quote before spending) -> generate (Lux3D, concurrent fan-out)
-> gates (deterministic, stdlib) -> repair (single targeted prompt mutation)
-> deliver (GLBs + manifest + receipts). Everything the report claims is
rendered from receipts.json afterwards.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List

from . import client as client_mod
from . import deliver as deliver_mod
from . import gates as gates_mod
from . import mutate as mutate_mod
from . import planner as planner_mod
from . import receipts as receipts_mod


def cmd_plan(args: argparse.Namespace) -> int:
    pack = planner_mod.load_pack(args.pack)
    print(planner_mod.render_plan(pack))
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    c = client_mod.Lux3DClient(ledger_path=os.path.join(args.artifacts, "ledger.jsonl"))
    c.probe(args.prompt)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    pack = planner_mod.load_pack(args.pack)
    print(planner_mod.render_plan(pack))
    print("")
    if args.dry_run:
        print("dry-run: no API calls made.")
        return 0

    c = client_mod.Lux3DClient(ledger_path=os.path.join(args.artifacts, "ledger.jsonl"))
    lock = threading.Lock()

    def emit(msg: str) -> None:
        with lock:
            print(msg, flush=True)

    def process_slot(slot) -> Dict[str, Any]:
        attempts: List[Dict[str, Any]] = []
        reasons: List[str] = []
        prompt = slot.prompt
        passed = False
        glb_path = ""
        last_gates = None
        for try_i in range(1 + pack.max_retries):
            t0 = time.time()
            task_id = None
            try:
                task_id = c.generate(prompt, version=pack.version,
                                     style=pack.lux3d_style,
                                     face_count=pack.face_count)
                emit(f"  [{slot.slot}] attempt {try_i + 1}: task {task_id} queued "
                     f"({pack.version}, style={pack.lux3d_style or 'default'})")
                result = c.wait(task_id)
                dl_dir = os.path.join(args.artifacts, pack.name, "downloads", f"try{try_i}")
                outs = c.download_outputs(result, dl_dir, slot.slot)
                glb = next((o for o in outs
                            if o.get("status") == "downloaded"
                            and o.get("path", "").endswith(".glb")), None)
                if glb is None:
                    attempts.append(receipts_mod.attempt_receipt(
                        prompt=prompt, task_id=task_id,
                        status=result.get("status"), seconds=time.time() - t0,
                        error=f"no downloadable GLB; outputs={json.dumps(outs)[:300]}"))
                    new_prompt, reason = mutate_mod.mutate(
                        prompt, {"checks": [{"gate": "glb_parse", "passed": False}]},
                        pack.style_bible)
                    reasons.append(reason)
                    emit(f"  [{slot.slot}] attempt {try_i + 1}: NO GLB OUTPUT — mutating prompt")
                    prompt = new_prompt
                    continue
                g = gates_mod.run_gates(glb["path"],
                                         face_count_target=pack.face_count,
                                         target=pack.target)
                attempts.append(receipts_mod.attempt_receipt(
                    prompt=prompt, task_id=task_id, status=result.get("status"),
                    seconds=time.time() - t0, glb_path=glb["path"], gate_results=g))
                stats = g["stats"]
                emit(f"  [{slot.slot}] attempt {try_i + 1}: "
                     f"{'PASS' if g['passed'] else 'FAIL'} "
                     f"faces={stats.get('face_count')} tex={stats.get('has_texture')} "
                     f"dims={stats.get('dims')} ({time.time() - t0:.0f}s, task {task_id})")
                if not g["passed"]:
                    emit("      " + gates_mod.render_checks(g["checks"]).replace("\n", "\n      "))
                last_gates = g
                if g["passed"]:
                    passed = True
                    glb_path = glb["path"]
                    break
                # the Repairer: one targeted, explainable mutation
                prompt, reason = mutate_mod.mutate(prompt, g, pack.style_bible)
                reasons.append(reason)
                emit(f"  [{slot.slot}] repair: {reason}")
            except Exception as exc:  # noqa: BLE001 — record honestly, never hide
                attempts.append(receipts_mod.attempt_receipt(
                    prompt=prompt, task_id=task_id, status="error",
                    seconds=time.time() - t0,
                    error=f"{exc.__class__.__name__}: {exc}") if task_id else {
                        "prompt": prompt, "task_id": None, "status": "error",
                        "seconds": round(time.time() - t0, 1),
                        "error": f"{exc.__class__.__name__}: {exc}"})
                emit(f"  [{slot.slot}] attempt {try_i + 1}: ERROR {exc.__class__.__name__}: {exc}")
                break
        return {"slot": slot.slot, "passed": passed, "glb_path": glb_path,
                "attempts": attempts, "mutation_reasons": reasons,
                "gates": last_gates}

    print(f"building {len(pack.slots)} assets, concurrency={args.concurrency} ...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        results = list(ex.map(process_slot, pack.slots))

    out = deliver_mod.deliver_pack(pack, results, args.artifacts, args.web)
    print("")
    n_pass = sum(1 for r in results if r["passed"])
    print(f"delivered: {out['delivered']}/{len(pack.slots)} assets passed gates "
          f"-> {out['pack_dir']}")
    print(f"manifest  -> {out['manifest_path']}")
    print(f"receipts  -> {out['receipts_path']}")
    print("")
    print(receipts_mod.summary_table(out["receipts"]))
    if n_pass < len(pack.slots):
        print("\nNOTE: failed slots are recorded in receipts and EXCLUDED from the "
              "pack — honesty is a feature, not a bug.")
    return 0 if n_pass == len(pack.slots) else 2


def cmd_verify(args: argparse.Namespace) -> int:
    from . import verifier
    ok, lines = verifier.verify_artifacts(args.artifacts, args.web)
    print("\n".join(lines))
    return 0 if ok else 1


def cmd_bench(args: argparse.Namespace) -> int:
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "bench", "run_sweep.py")
    cmd = [sys.executable, script, "--artifacts", args.artifacts,
           "--max-jobs", str(args.max_jobs), "--version", args.version]
    if args.categories:
        cmd += ["--categories", args.categories]
    return subprocess.call(cmd)


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(prog="assetforge",
                                description="One YAML in — a verified, engine-ready 3D pack out.")
    ap.add_argument("--artifacts", default="artifacts", help="artifacts dir (default ./artifacts)")
    ap.add_argument("--web", default="web", help="web dir for manifests (default ./web)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="show the plan + credit quote (no API calls)")
    p_plan.add_argument("pack")
    p_plan.set_defaults(func=cmd_plan)

    p_probe = sub.add_parser("probe", help="one tiny generation; dump raw API schema")
    p_probe.add_argument("--prompt", default="a small wooden crate, simple game asset")
    p_probe.set_defaults(func=cmd_probe)

    p_build = sub.add_parser("build", help="plan -> generate -> gates -> repair -> deliver")
    p_build.add_argument("pack")
    p_build.add_argument("--concurrency", type=int, default=3)
    p_build.add_argument("--dry-run", action="store_true")
    p_build.set_defaults(func=cmd_build)

    p_verify = sub.add_parser("verify", help="offline re-verification of all receipts")
    p_verify.set_defaults(func=cmd_verify)

    p_bench = sub.add_parser("bench", help="capability-boundary benchmark sweep")
    p_bench.add_argument("--max-jobs", type=int, default=24)
    p_bench.add_argument("--version", default="G1-Turbo")
    p_bench.add_argument("--categories", default="")
    p_bench.set_defaults(func=cmd_bench)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
