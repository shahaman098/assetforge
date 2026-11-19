# AssetForge receipts format (v1)

A minimal, tool-agnostic receipts format for AI-3D generation pipelines.
Any tool generating 3D assets can emit it; any reviewer can verify it
offline. Adopt it, extend it — it is deliberately small.

## Rules of the format
1. Every delivered file is sha256-pinned. No sha, no claim.
2. Every attempt records the vendor task ID, prompt, timings, and gate verdicts.
3. Failed assets are EXCLUDED from the pack and RETAINED in receipts.
4. Verification must require **no API key, no credits, no network**.
5. Numbers in reports are rendered from receipts, never hand-typed.

## Schema (receipts.json per pack)

```json
{
  "pack": "cozy-dungeon",
  "target": "game | print",
  "budget": { "version": "G1-Turbo", "face_count": 60000, "max_retries": 1 },
  "lux3d_style": "fantasy",
  "assets": [
    {
      "slot": "crate",
      "passed": true,
      "attempts": [
        {
          "prompt": "a sturdy wooden storage crate ...",
          "task_id": 8397544,
          "status": 3,
          "seconds": 123.6,
          "sha256": "<sha256 of delivered glb>",
          "bytes": 7386240,
          "gates": { "passed": true, "checks": [ { "gate": "face_count",
                       "passed": true, "value": 53788,
                       "expected": "10000-300000" } ], "stats": {} }
        }
      ],
      "mutation_reasons": [],
      "final": { "task_id": 8397544, "sha256": "...", "bytes": 7386240,
                 "face_count": 53788, "has_texture": true, "dims": [0.45, 0.45, 0.45],
                 "seconds": 123.6 },
      "generator": "Aholo Lux3D via official manycore-aholo-sdk-lux3d",
      "ts": 1795067987
    }
  ],
  "ts": 1795068120
}
```

## Verification contract
A conforming tool ships a `verify.py` that re-opens every delivered file,
re-runs every gate offline, re-hashes every sha, and confirms the pack
manifest contains exactly the passing set. Exit 0 = clean.

Reference implementation: `assetforge/verifier.py` + `verify.py` (MIT).
Worked example: `artifacts/*/receipts.json` (13 gated assets, 35 recorded
Lux3D runs incl. one excluded boundary failure).
