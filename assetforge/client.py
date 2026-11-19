"""Thin wrapper over the official manycore Aholo Lux3D SDK.

Uses the SDK exactly as documented (we compose with the sponsor's stack,
we do not reimplement it). Adds: a task ledger (JSONL, one line per API
action — the audit trail behind our receipts), defensive output
handling, and a `probe` helper that dumps the raw task result so the
response schema is always visible on first run.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from manycore.aholo_sdk_core import AholoClientConfig
from manycore.aholo_sdk_lux3d import create_lux3d_client

STATUS_SUCCESS = 3
STATUS_FAILED = 4
STATUS_CANCELED = 6

LUX3D_STATUS_SUCCESS = 3


class Lux3DClient:
    def __init__(self, region: str = "com", ledger_path: Optional[str] = None):
        key = os.environ.get("AHOLO_API_KEY")
        if not key:
            raise SystemExit("AHOLO_API_KEY is not set. Get an international key at "
                             "https://labs.aholo.ai/api-keys and export it.")
        self.region = region
        self.ledger_path = ledger_path
        self._client = create_lux3d_client(AholoClientConfig(api_key=key, region=region))

    # -- ledger ------------------------------------------------------------
    def _log(self, action: str, **fields: Any) -> None:
        if not self.ledger_path:
            return
        rec = {"ts": int(time.time()), "action": action}
        rec.update(fields)
        with open(self.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # -- generation ---------------------------------------------------------
    def generate(self, prompt: str, *, version: str = "G1-Turbo",
                 style: Optional[str] = None, face_count: int = 60000,
                 output_format: Tuple[str, ...] = ("glb",),
                 enable_pbr: bool = True,
                 ai_predict_size: Optional[bool] = None) -> int:
        kwargs: Dict[str, Any] = {
            "prompt": prompt,
            "version": version,
            "face_count": face_count,
            "output_format": list(output_format),
            "enable_pbr": enable_pbr,
        }
        if style:
            kwargs["style"] = style
        if ai_predict_size is not None:
            kwargs["ai_predict_size"] = ai_predict_size
        task_id = int(self._client.text_to_3d.create(**kwargs))
        self._log("create", task_id=task_id, prompt=prompt, version=version,
                  style=style or "", face_count=face_count)
        return task_id

    def wait(self, task_id: int, timeout_ms: int = 600_000) -> Dict[str, Any]:
        t0 = time.time()
        result = self._client.tasks.wait_for(task_id, timeout_ms=timeout_ms)
        self._log("wait", task_id=task_id, status=result.get("status"),
                  seconds=round(time.time() - t0, 1))
        return dict(result)

    # -- outputs ------------------------------------------------------------
    def download_outputs(self, result: Dict[str, Any], dest_dir: str,
                         base_name: str) -> List[Dict[str, Any]]:
        """Fetch every output content for a finished task.

        Handles http(s) URLs, data: URIs and raw base64 defensively; anything
        unrecognised is saved as .raw.txt so nothing is ever silently lost.
        """
        os.makedirs(dest_dir, exist_ok=True)
        out: List[Dict[str, Any]] = []
        for i, o in enumerate(result.get("outputs") or []):
            content = (o or {}).get("content")
            rec: Dict[str, Any] = {"index": i}
            if not content:
                rec.update(status="empty")
                out.append(rec)
                continue
            if content.startswith("http://") or content.startswith("https://"):
                path = os.path.join(dest_dir, f"{base_name}.glb" if i == 0 else f"{base_name}_{i}.glb")
                req = urllib.request.Request(content, headers={"User-Agent": "assetforge/0.1"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = resp.read()
                with open(path, "wb") as fh:
                    fh.write(data)
                rec.update(status="downloaded", path=path, bytes=len(data), source="url")
            elif content.startswith("data:"):
                b64 = content.split(",", 1)[-1]
                data = base64.b64decode(b64)
                path = os.path.join(dest_dir, f"{base_name}.glb" if i == 0 else f"{base_name}_{i}.glb")
                with open(path, "wb") as fh:
                    fh.write(data)
                rec.update(status="downloaded", path=path, bytes=len(data), source="data-uri")
            else:
                # unknown shape — preserve for inspection, never lose evidence
                raw_path = os.path.join(dest_dir, f"{base_name}_{i}.raw.txt")
                with open(raw_path, "w", encoding="utf-8") as fh:
                    fh.write(str(content)[:200000])
                rec.update(status="raw", path=raw_path, source="unknown")
            out.append(rec)
        self._log("download", task_id=result.get("taskId"),
                  files=[(r.get("path"), r.get("status")) for r in out])
        return out

    # -- probe ---------------------------------------------------------------
    def probe(self, prompt: str) -> Dict[str, Any]:
        """One tiny end-to-end job with the full raw schema dumped."""
        task_id = self.generate(prompt, version="G1-Turbo", face_count=10000)
        print(f"probe: task created taskId={task_id}; polling...")
        result = self.wait(task_id)
        print("probe: raw task result:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:4000])
        outs = self.download_outputs(result, os.path.join("artifacts", "probe"), "probe")
        print("probe: outputs:")
        print(json.dumps(outs, indent=2, ensure_ascii=False)[:4000])
        return {"task_id": task_id, "result": result, "outputs": outs}
