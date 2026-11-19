# AssetForge — Project Report (source; numbers rendered from receipts, never hand-typed)

> Render notes: every `<RECEIPT-*>` marker below is filled by
> `tools/render_report.py` from `artifacts/*/receipts.json` and
> `bench/benchmark.md` at build time. Convert to PDF as
> `TeamName-AssetForge.pdf`.

## 1. Idea → why this exists
A solo dev who wants a game biome today opens the Lux3D console, burns credits
one asset at a time, eyeballs every mesh, hand-fixes per-engine imports,
retries blind — a week per biome, and nothing is provable afterwards.
AssetForge collapses that into one YAML pack brief:
plan → quote → generate (Lux3D) → deterministic gates → targeted repair →
engine-ready delivery with receipts.

## 2. What it is
- **CLI + library** (`af plan|build|verify|bench`) composing with the official
  Lux3D skill conventions and the official Python SDK.
- **Deterministic gates** (stdlib GLB parser + trimesh): face-count bounds
  (vendor 10k–300k), texture presence, sane bbox; watertight for print targets.
- **The Repairer**: one targeted prompt mutation per failed gate — the rule is
  readable code (`assetforge/mutate.py`), not a black box.
- **Receipts + offline Auditor**: per-asset JSON receipts (prompt, task ID,
  timings, gate values, sha256); `python verify.py` re-derives everything with
  zero credits, no API key, no network.
- **Capability benchmark**: `bench/benchmark.md` measures Lux3D's own published
  boundary claims with N runs and a failure taxonomy.

## 3. The demo (see video / runnable link)
1. `af build packs/cozy-dungeon.yaml` — plan, quote, fan-out, gates, repair,
   delivery on camera.
2. Relic Run — the playable proof: collect verified assets; receipt badges
   flip to PASS ✓.
3. **Pack-swap beat**: `sci-fi-outpost.yaml` re-themes the same level in one
   command.
4. `python verify.py` — every claim re-derives offline.

## 4. Results
<RECEIPT-PACK-TABLE:cozy-dungeon>
<RECEIPT-PACK-TABLE:sci-fi-outpost>
<RECEIPT-BENCH-TABLE>
<RECEIPT-TOTALS: assets, credits, wall-clock, pass rates, repair-recovery count>

## 5. Honest limits
<RECEIPT-FAILURES: recorded failures + mutation reasons + published benchmark
misses — failures are a feature of the receipts design>

## 6. Where Lux3D is load-bearing
Every delivered asset is a Lux3D task ID in our receipts; remove Lux3D and
AssetForge has nothing to orchestrate, gate, or verify. We adopt the skill's
plan→quote→REPORT conventions and the official SDK; we extend the ecosystem
rather than reimplement it.

## 7. The New Species case
The organizer's own rationale — an ecosystem formed around toolchains,
scenarios and developers — names exactly this layer: an installable toolchain,
a measured capability map the whole platform can use, an open receipts format,
and a game proving the loop end-to-end.

## 8. 中文摘要
一个 YAML 输入，产出风格一致、通过确定性质检、可直接进引擎的 3D 资产包。
流水线采用 Lux3D 官方 SDK 与 plan→quote→REPORT 约定；所有产出附回执，
可离线零积分复验（`python verify.py`）；`bench/` 用实测数据量化 Lux3D
官方能力边界并公开失败分类学——工具链、场景与开发者生态，即本次
「3D AI 新物种奖」所指的生态层。
