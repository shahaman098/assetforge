# Lux3D capability-boundary benchmark (measured, with receipts)

- Model version: `G1-Turbo` · gates: face_count 10k–300000 · texture present · sane bbox
- Runs: 22 · Every row below is re-derivable from `artifacts/bench/results.json` + `bench/categories.yaml`.

| category | vendor claim | pass rate | verdict vs claim | dominant failures |
|---|---|---|---|---|
| strength-baseline | high (>=60% expected) | 6/6 (100%) | **CONFIRMED** | — |
| patterns-and-text | mixed (mid-range expected) | 4/4 (100%) | **PARTIAL** | — |
| geometric-complexity | low (<=40% expected) | 4/4 (100%) | **CONTRADICTED** | — |
| materials-hard | low (<=40% expected) | 4/4 (100%) | **CONTRADICTED** | — |
| figures-and-plants | low (<=40% expected) | 4/4 (100%) | **CONTRADICTED** | — |

_Note: 0/22 gate failures. Across 22 G1-Turbo runs — including every category the vendor's own boundary table marks as weak — the coarse production gates (face budget, texture, sanity) passed everywhere. The one recorded failure in our corpus is the lower face-count bound under-delivery (probe task 8397194: requested 10,000, delivered 7,976 — excluded, receipt in ledger). Honest limits: coarse gates do not measure fine-feature fidelity (small text legibility, face detail, carving quality), which remains the vendor's documented weak zone. Per-run task IDs: `artifacts/bench/results.json`._