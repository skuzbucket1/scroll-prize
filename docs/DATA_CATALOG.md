# Data catalog (generated)

Generated 2026-10-13 03:47 UTC by `scripts/catalog.py` (one scan per host) and `scripts/results_db.py`, merged on the laptop into `data/catalog/catalog.sqlite` and `data/catalog/results.sqlite`. Do not edit by hand: re-run the scans. Layout and rules: `docs/DATA_LAYOUT.md`. Backup set: `scripts/backup_r2.sh` (private object storage).

## Artifacts by host and kind

| host | kind | items | GiB | critical items |
|---|---|---:|---:|---:|
| GPU machine | render | 316 | 569.31 | 0 |
| GPU machine | other | 2182 | 41.82 | 204 |
| GPU machine | ink-map | 4058 | 27.02 | 640 |
| GPU machine | fit-input | 61 | 18.35 | 10 |
| GPU machine | ensemble-image | 2889 | 11.52 | 766 |
| GPU machine | mesh-flattened | 5126 | 10.86 | 5126 |
| GPU machine | fit | 14324 | 8.24 | 14324 |
| GPU machine | score-figure | 3439 | 2.44 | 3439 |
| GPU machine | geometry-qa | 482 | 2.01 | 482 |
| GPU machine | control-ink-map | 45 | 0.63 | 45 |
| GPU machine | mesh-snapped | 4221 | 0.35 | 4221 |
| GPU machine | control-ensemble-image | 13 | 0.23 | 0 |
| GPU machine | control-other | 12 | 0.10 | 12 |
| GPU machine | control-reference | 5 | 0.08 | 5 |
| GPU machine | reference | 53 | 0.04 | 53 |
| GPU machine | log | 3908 | 0.01 | 862 |
| GPU machine | preview-image | 16 | 0.01 | 0 |
| GPU machine | score | 847 | 0.01 | 847 |
| GPU machine | control-mesh | 3 | 0.00 | 0 |
| GPU machine | mesh | 2 | 0.00 | 0 |
| GPU machine | ranking | 11 | 0.00 | 11 |
| GPU machine | run-record | 15 | 0.00 | 15 |
| GPU machine | geometry | 1 | 0.00 | 0 |
| GPU machine | control-score | 1 | 0.00 | 1 |
| GPU machine | public-input | 24 | 0.00 | 0 |
| laptop | ensemble-image | 830 | 3.93 | 830 |
| laptop | other | 3282 | 3.02 | 1507 |
| laptop | ink-map | 170 | 1.38 | 170 |
| laptop | control-ink-map | 72 | 0.85 | 72 |
| laptop | score-figure | 902 | 0.57 | 902 |
| laptop | control-ensemble-image | 26 | 0.32 | 0 |
| laptop | review-image | 133 | 0.15 | 133 |
| laptop | control-ranking | 8 | 0.13 | 8 |
| laptop | control-other | 71 | 0.08 | 71 |
| laptop | control-reference | 5 | 0.08 | 5 |
| laptop | preview-image | 26 | 0.03 | 26 |
| laptop | scan-quality | 338 | 0.03 | 338 |
| laptop | reference | 57 | 0.02 | 57 |
| laptop | log | 2165 | 0.00 | 2141 |
| laptop | score | 577 | 0.00 | 577 |
| laptop | control-score-figure | 2 | 0.00 | 0 |
| laptop | memory | 26 | 0.00 | 26 |
| laptop | ranking | 3 | 0.00 | 3 |
| laptop | control-score | 11 | 0.00 | 11 |
| laptop | run-record | 8 | 0.00 | 8 |

Public inputs (scan volumes, Lasagna, tracks, surface predictions, normal grids) are listed per store without sizes; they are re-downloadable.

## Geometry and ink by scroll and fit

| scroll | fit | meshes (snapped / flattened) | renders | ink maps | ensemble images |
|---|---|---:|---:|---:|---:|
| PHerc0191 | community-z11600 | 10 / 10 | 0 | 0 | 0 |
| PHerc0191 | exp30k-z11200 | 120 / 100 | 97 | 2228 | 2594 |
| PHerc0191 | exp30k-z9000 | 100 / 99 | 0 | 344 | 283 |
| PHerc0191 | oldphase30k-z9000 | 100 / 3 | 3 | 0 | 0 |
| PHerc0343 | control | 0 / 0 | 1 | 18 | 12 |
| PHerc0813 | exp30k-z10500 | 120 / 76 | 76 | 608 | 0 |
| PHerc0813 | exp30k-z12000 | 120 / 80 | 63 | 400 | 0 |
| PHerc0813 | exp30k-z8000 | 120 / 76 | 76 | 28 | 0 |

## Scores (results table)

| scroll | fit | source | models | rows | v0.1 LOOK | max row_R |
|---|---|---|---|---:|---:|---:|
|  |  | post | dnative,ink9-42,ink9-43 | 400 | 306 | 1.54 |
| PHerc0191 |  | post | d9v4c,readerv2 | 194 |  | 2.40 |
| PHerc0191 |  | stroke-score | dnative,ink9-42,ink9-43 | 1 | 1 |  |
| PHerc0191 | community-z11600 | stroke-score | dnative,ink9-42,ink9-43 | 20 | 3 |  |
| PHerc0191 | exp30k-z11200 | post | d9v4c,readerv2 | 208 |  | 2.40 |
| PHerc0191 | exp30k-z11200 | rowness | dnative,ink9-42,ink9-43 | 197 |  | 1.45 |
| PHerc0191 | exp30k-z11200 | stroke-score | dnative,hecate,ink9-42,ink9-43 | 42 | 2 |  |
| PHerc0191 | exp30k-z11200 | stroke-score | dnative,ink9-42,ink9-43 | 186 | 60 |  |
| PHerc0191 | exp30k-z9000 | stroke-score | dnative,hecate,ink9-42,ink9-43 | 15 | 0 |  |
| PHerc0191 | exp30k-z9000 | stroke-score | dnative,ink9-42,ink9-43 | 195 | 14 |  |
| PHerc0191 | exp30k-z9000 | stroke-score | hecate | 8 |  |  |
| PHerc0191 | exp30k-z9000 | stroke-score | ink9-42 | 85 |  |  |
| PHerc0191 | exp30k-z9000 | stroke-score | ink9-42,ink9-43 | 2 |  |  |
| PHerc0343 | control | stroke-score | d9v4c,dnative,hecate,ink9-42,ink9-43,readerv2 | 1 | 1 |  |
| PHerc0343 | control | stroke-score | d9v4c,readerv2 | 1 |  |  |
| PHerc0343 | control | stroke-score | dnative,hecate,ink9-42,ink9-43 | 2 | 2 |  |
| PHerc0343 | control | stroke-score | dnative,ink9-42,ink9-43 | 2 | 2 |  |
| PHerc0343 | control | stroke-score | ink9-42 | 1 |  |  |
| PHerc0343 | control | stroke-score | ink9-42,ink9-43 | 1 |  |  |
| PHerc0813 |  | post | d9v4c,readerv2 | 252 |  | 2.63 |
| PHerc0813 | exp30k-z12000 | post | d9v4c,readerv2 | 172 |  | 2.63 |
| PHerc0813 | exp30k-z12000 | stroke-score | dnative,ink9-42,ink9-43 | 20 | 4 |  |
| PHerc0841 | control-ag2814 | post | d9v4c,readerv2 | 1 |  | 4.24 |

## Known-text control AUCs (best depth per model, reading side)

| control | model | best depth | AUC | r |
|---|---|---:|---:|---:|
| c0139_w047_66 | readerv2 | -1 | 0.860 | 0.613 |
| c0139_w047_66 | dnative | -1 | 0.859 | 0.605 |
| c0139_w047_66 | ens3+readerv2 | -1 | 0.854 | 0.596 |
| c0139_w047_66 | ens3 (ink9-42, ink9-43, dnative) | -1 | 0.838 | 0.553 |
| c0139_w047_66 | hybrid_3d2d-seed43 | -1 | 0.757 | 0.422 |
| c0139_w047_66 | hybrid_3d2d-seed42 | -1 | 0.744 | 0.392 |
| c0841_ag2814_66 | readerv2+d9v4c | -1 | 0.828 | 0.570 |
| c0841_ag2814_66 | d9v4c | -1 | 0.822 | 0.562 |
| c0841_ag2814_66 | readerv2 | -1 | 0.821 | 0.561 |
| c0841_ag2814_66 | all5 | +1 | 0.818 | 0.538 |
| c0841_ag2814_66 | ens3+readerv2 | +1 | 0.806 | 0.519 |
| c0841_ag2814_66 | ens3 (ink9-42, ink9-43, dnative) | +1 | 0.783 | 0.482 |
| c0841_ag2814_66 | dnative | +1 | 0.767 | 0.474 |
| c0841_ag2814_66 | hybrid_3d2d-seed43 | -1 | 0.761 | 0.453 |
| c0841_ag2814_66 | hybrid_3d2d-seed42 | +1 | 0.753 | 0.433 |
