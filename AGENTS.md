# Installing AssetForge as a local Skill

Compatible-host agents (Codex, Claude Code, Cursor, OpenCode, WorkBuddy and
other local-Skill hosts) can install AssetForge alongside the official
Aholo Lux3D skill:

```
Read https://raw.githubusercontent.com/shahaman098/assetforge/main/AGENTS.md
and install AssetForge as a local Skill in the current host.
```

Manual install:

```
git clone https://github.com/shahaman098/assetforge
cd assetforge
python3 -m venv .venv && .venv/bin/pip install pyyaml trimesh numpy manycore-aholo-sdk-lux3d
export AHOLO_API_KEY=...   # international key: https://labs.aholo.ai/api-keys
./af plan recipes/shop-stall.yaml     # quote before spending
./af build recipes/shop-stall.yaml    # generate -> gate -> repair -> deliver
./af verify                           # offline audit, zero credits
```

Entrypoint: `SKILL.md` (this directory's skill contract).
Verification (`af verify`, `python verify.py`) is deliberately keyless —
reviewers never need credentials or credits to re-derive every claim.
