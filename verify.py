#!/usr/bin/env python
"""Judge entrypoint: re-verify every AssetForge claim offline.

    python verify.py            # verify all packs under ./artifacts
    python verify.py --artifacts path/to/artifacts --web path/to/web

No API key. No credits. No network. If this exits 0, every delivered
asset re-passes its gates and every receipt re-derives identically.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assetforge import verifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline receipt verification (zero credits)")
    ap.add_argument("--artifacts", default="artifacts")
    ap.add_argument("--web", default="web")
    args = ap.parse_args()
    ok, lines = verifier.verify_artifacts(args.artifacts, args.web)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
