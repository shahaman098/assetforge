# AssetForge

**One YAML in — a style-locked, machine-verified, engine-ready 3D asset pack out, with receipts.**

The missing production layer between [Aholo Lux3D](https://lux3d.aholo.ai) and shipping.
Built for the Manycore Aholo Global 3D AI Hackathon (#Manycorehackathon).

## The workflow we collapse

**Before:** a solo dev who wants a game biome opens the Lux3D console, burns
credits one asset at a time, eyeballs every mesh, hand-fixes per-engine imports,
retries blind — a week per biome, and nothing is provable afterwards.

**During:** one YAML pack brief — AssetForge plans, quotes the credits, fans out
Lux3D generation, gates every asset deterministically, repairs failures with one
targeted prompt mutation, and delivers.

**After:** an engine-ready pack (GLB + manifest) in-game in one drop, with
per-asset receipts anyone re-verifies **offline, with zero credits and no API key**.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install pyyaml trimesh numpy manycore-aholo-sdk-lux3d
export AHOLO_API_KEY=...          # international key: https://labs.aholo.ai/api-keys

./af plan  packs/cozy-dungeon.yaml      # plan + credit quote, no API calls
./af build packs/cozy-dungeon.yaml      # generate -> gates -> repair -> deliver
./af verify                             # offline re-verification, zero credits
./af bench --max-jobs 24                # capability-boundary benchmark sweep

python3 -m http.server 8000             # then open http://localhost:8000/web/
```

## The trust layer

- **Deterministic gates** (stdlib GLB parser): face_count within vendor bounds
  (10k–300k), texture present, sane bounding box; watertight for print targets
  (trimesh). No vibes, only computed verdicts.
- **Receipts** (`artifacts/*/receipts.json`): every attempt with prompt, Lux3D
  task ID, timings, per-gate values, sha256 of every delivered file.
- **Offline Auditor** (`python verify.py`): re-derives every claim from receipts
  — no API key, no credits, no network. Judges can re-run everything themselves.
- **The Repairer:** when a gate fails, one targeted, explainable prompt mutation
  (read the rule in `assetforge/mutate.py`) — failures are caught, retried and
  *recorded*, never hidden.
- **Benchmark** (`bench/benchmark.md`): the first measured capability map of
  Lux3D — we quantify the vendor's own published boundary claims with receipts,
  including what the model *cannot* reliably do.

## Composability, not duplication

AssetForge composes with the official agent skill
([manycore-research/Aholo-Lux3D](https://github.com/manycore-research/Aholo-Lux3D)):
we adopt its plan→quote→REPORT conventions, keep Lux3D task IDs inside our
receipts, and call the model through the official
`manycore-aholo-sdk-lux3d`. We are a skill-shaped layer on their stack, not a
reimplementation.

## 中文摘要 (Chinese summary)

AssetForge 是 Aholo Lux3D 与可交付游戏资产之间的生产层：一个 YAML
「美术圣经」输入，流水线规划报价、并发调用 Lux3D 生成、确定性质量门禁
（面数/贴图/包围盒/水密）、失败时定向改写提示词自动修复，并输出带回执
（receipts）的引擎就绪资产包。所有结论可离线复验：`python verify.py`
无需 API Key、不花积分。`bench/` 用回执量化 Lux3D 官方公布的能力边界，
包括它不可靠的场景——失败分类学本身就是生态贡献。

## License

MIT — see `LICENSE`.
