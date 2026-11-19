# AssetForge — Skill entry

**One YAML pack brief in — a style-locked, machine-verified, engine-ready
3D asset pack out, with receipts.** Generation via Aholo Lux3D through the
official `manycore-aholo-sdk-lux3d`.

## Capabilities
- `af plan <pack.yaml>` — plan + credit quote before spending (no API calls)
- `af build <pack.yaml>` — concurrent Lux3D generation → deterministic gates
  (face-count bounds, texture, sane bbox; watertight for print targets) →
  one targeted repair mutation per failure → GLBs + manifests + receipts
- `af verify` — offline re-verification of every receipt: no API key,
  no credits, no network
- `af bench` — capability-boundary sweep with per-run task IDs

## Requirements
- Python 3.9+; deps: `pyyaml`, `trimesh`, `numpy`, `manycore-aholo-sdk-lux3d`
- `AHOLO_API_KEY` (international: https://labs.aholo.ai/api-keys) for any
  generation; `plan`, `verify`, and receipt inspection work keyless.

## Composability
AssetForge adopts the official skill's plan→quote→REPORT conventions and
calls Lux3D through the official SDK. It is a layer on the Aholo stack,
not a reimplementation.

## Outputs
- `artifacts/<pack>/glbs/*.glb` — gated, sha-pinned assets
- `artifacts/<pack>/receipts.json` — the evidence trail (see RECEIPTS-SPEC.md)
- `web/manifests/<pack>.json` — engine import manifests (Three.js-ready)
- `bench/benchmark.md` — measured capability table rendered from results.json
