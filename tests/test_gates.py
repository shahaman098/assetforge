"""Gate unit tests — deterministic, offline, fast.

Run:  .venv/bin/python -m unittest discover -s tests -v
These prove the deterministic core works before a single credit is spent.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assetforge import gates, mutate  # noqa: E402
from tests import make_seed_glbs  # noqa: E402

FX = make_seed_glbs.FIXTURES


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        make_seed_glbs.main()

    def test_ok_cube_faces(self):
        stats = gates.glb_stats(os.path.join(FX, "ok_cube.glb"))
        self.assertTrue(stats["valid_glb"])
        self.assertEqual(stats["face_count"], 12)

    def test_ok_cube_bounds(self):
        stats = gates.glb_stats(os.path.join(FX, "ok_cube.glb"))
        dims = stats["dims"]
        self.assertAlmostEqual(dims[0], 1.0, places=1)
        self.assertAlmostEqual(dims[1], 1.0, places=1)
        self.assertAlmostEqual(dims[2], 1.0, places=1)

    def test_texture_absent_is_detected(self):
        stats = gates.glb_stats(os.path.join(FX, "ok_cube.glb"))
        self.assertFalse(stats["has_texture"])

    def test_textured_tetra_json_path(self):
        stats = gates.glb_stats(os.path.join(FX, "textured_tetra.glb"))
        self.assertTrue(stats["valid_glb"])
        self.assertEqual(stats["face_count"], 4)
        self.assertTrue(stats["has_texture"])
        self.assertEqual(stats["materials"], 1)

    def test_full_pass_on_textured_fixture(self):
        g = gates.run_gates(os.path.join(FX, "textured_tetra.glb"),
                            face_count_target=4, face_min=3, face_max=1000)
        self.assertTrue(g["passed"], gates.render_checks(g["checks"]))

    def test_missing_texture_fails_the_gate(self):
        g = gates.run_gates(os.path.join(FX, "ok_cube.glb"),
                            face_count_target=12, face_min=10, face_max=1000)
        self.assertFalse(g["passed"])
        failed = {c["gate"] for c in g["checks"] if not c["passed"]}
        self.assertIn("texture", failed)

    def test_broken_watertight_detected(self):
        g = gates.run_gates(os.path.join(FX, "broken_watertight.glb"),
                            face_count_target=12, face_min=3, face_max=1000,
                            target="print")
        wt = [c for c in g["checks"] if c["gate"] == "watertight"]
        self.assertTrue(wt, "watertight gate must be present for print target")
        self.assertFalse(wt[0]["passed"], "box with a removed face is not watertight")

    def test_watertight_cube_passes(self):
        g = gates.run_gates(os.path.join(FX, "ok_cube.glb"),
                            face_count_target=12, face_min=3, face_max=1000,
                            target="print")
        wt = [c for c in g["checks"] if c["gate"] == "watertight"]
        if wt and not wt[0].get("skipped"):
            self.assertTrue(wt[0]["passed"], "closed box should be watertight")

    def test_sha256_stable(self):
        p = os.path.join(FX, "textured_tetra.glb")
        self.assertEqual(gates.sha256_file(p), gates.sha256_file(p))

    def test_mutation_targets_face_gate(self):
        prompt, reason = mutate.mutate(
            "an ornate carved throne",
            {"checks": [{"gate": "face_count", "passed": False}]},
            {"materials": ["stone"], "palette": "warm stone"})
        self.assertIn("low-poly", prompt.lower())
        self.assertIn("face_count", reason)

    def test_mutation_targets_texture_gate(self):
        prompt, reason = mutate.mutate(
            "a wooden crate",
            {"checks": [{"gate": "texture", "passed": False}]},
            {"materials": ["aged oak", "brass"], "palette": "warm"})
        self.assertIn("aged oak", prompt)
        self.assertIn("texture", reason)


if __name__ == "__main__":
    unittest.main()
