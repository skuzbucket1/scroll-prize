# Data catalog (generated)

Generated 2026-10-11 03:44 UTC by `scripts/catalog.py` (one scan per host) and `scripts/results_db.py`, merged on the Mac into `data/catalog/catalog.sqlite` and `data/catalog/results.sqlite`. Do not edit by hand: re-run the scans. Layout and rules: `docs/DATA_LAYOUT.md`. Backup set: `scripts/backup_r2.sh` (private object storage).

## Artifacts by host and kind

| host | kind | items | GiB | critical items |
|---|---|---:|---:|---:|
| box | render | 141 | 115.22 | 0 |
| box | fit-input | 61 | 18.35 | 10 |
| box | ensemble-image | 2889 | 11.52 | 766 |
| box | ink-map | 1836 | 10.59 | 456 |
| box | fit | 12314 | 4.07 | 12314 |
| box | mesh-flattened | 2998 | 3.85 | 2998 |
| box | geometry-qa | 330 | 1.04 | 330 |
| box | score-figure | 1506 | 1.02 | 1506 |
| box | other | 393 | 0.69 | 0 |
| box | control-ink-map | 25 | 0.49 | 25 |
| box | control-ensemble-image | 13 | 0.23 | 0 |
| box | mesh-snapped | 2775 | 0.17 | 2775 |
| box | control-reference | 5 | 0.08 | 5 |
| box | preview-image | 16 | 0.01 | 0 |
| box | log | 1212 | 0.01 | 0 |
| box | score | 482 | 0.00 | 482 |
| box | ranking | 4 | 0.00 | 4 |
| box | run-record | 10 | 0.00 | 10 |
| box | control-other | 2 | 0.00 | 2 |
| box | geometry | 1 | 0.00 | 0 |
| box | control-score | 1 | 0.00 | 1 |
| box | public-input | 24 | 0.00 | 0 |
| mac | ensemble-image | 830 | 3.93 | 830 |
| mac | ink-map | 170 | 1.38 | 170 |
| mac | control-ink-map | 72 | 0.85 | 72 |
| mac | score-figure | 902 | 0.57 | 902 |
| mac | control-ensemble-image | 26 | 0.32 | 0 |
| mac | review-image | 133 | 0.15 | 133 |
| mac | control-ranking | 6 | 0.13 | 6 |
| mac | other | 344 | 0.10 | 247 |
| mac | control-reference | 5 | 0.08 | 5 |
| mac | preview-image | 26 | 0.03 | 26 |
| mac | scan-quality | 338 | 0.03 | 338 |
| mac | reference | 7 | 0.01 | 7 |
| mac | control-other | 11 | 0.00 | 11 |
| mac | log | 1259 | 0.00 | 1259 |
| mac | score | 327 | 0.00 | 327 |
| mac | control-score-figure | 2 | 0.00 | 0 |
| mac | memory | 16 | 0.00 | 16 |
| mac | ranking | 3 | 0.00 | 3 |
| mac | control-score | 3 | 0.00 | 3 |
| mac | run-record | 7 | 0.00 | 7 |

Public inputs (scan volumes, Lasagna, tracks, surface predictions, normal grids) are listed per store without sizes; they are re-downloadable.

## Geometry and ink by scroll and fit

| scroll | fit | meshes (snapped / flattened) | renders | ink maps | ensemble images |
|---|---|---:|---:|---:|---:|
| PHerc0191 | community-z11600 | 10 / 10 | 0 | 0 | 0 |
| PHerc0191 | exp30k-z11200 | 120 / 100 | 74 | 1452 | 2594 |
| PHerc0191 | exp30k-z9000 | 100 / 99 | 0 | 344 | 283 |
| PHerc0191 | oldphase30k-z9000 | 100 / 3 | 3 | 0 | 0 |
| PHerc0343 | control | 0 / 0 | 1 | 14 | 12 |
| PHerc0813 | exp30k-z12000 | 120 / 80 | 63 | 26 | 0 |

## Scores (results table)

| scroll | fit | source | models | rows | v0.1 LOOK | max row_R |
|---|---|---|---|---:|---:|---:|
| PHerc0191 |  | stroke-score | dnative,ink9-42,ink9-43 | 1 | 1 |  |
| PHerc0191 | community-z11600 | stroke-score | dnative,ink9-42,ink9-43 | 20 | 3 |  |
| PHerc0191 | exp30k-z11200 | rowness | dnative,ink9-42,ink9-43 | 197 |  | 1.45 |
| PHerc0191 | exp30k-z11200 | stroke-score | dnative,hecate,ink9-42,ink9-43 | 42 | 2 |  |
| PHerc0191 | exp30k-z11200 | stroke-score | dnative,ink9-42,ink9-43 | 186 | 60 |  |
| PHerc0191 | exp30k-z9000 | stroke-score | dnative,hecate,ink9-42,ink9-43 | 15 | 0 |  |
| PHerc0191 | exp30k-z9000 | stroke-score | dnative,ink9-42,ink9-43 | 195 | 14 |  |
| PHerc0191 | exp30k-z9000 | stroke-score | hecate | 8 |  |  |
| PHerc0191 | exp30k-z9000 | stroke-score | ink9-42 | 85 |  |  |
| PHerc0191 | exp30k-z9000 | stroke-score | ink9-42,ink9-43 | 2 |  |  |
| PHerc0343 | control | stroke-score | dnative,hecate,ink9-42,ink9-43 | 1 | 1 |  |
| PHerc0343 | control | stroke-score | dnative,ink9-42,ink9-43 | 1 | 1 |  |
| PHerc0343 | control | stroke-score | ink9-42 | 1 |  |  |
| PHerc0343 | control | stroke-score | ink9-42,ink9-43 | 1 |  |  |
| PHerc0813 | exp30k-z12000 | post | d9v4c,readerv2 | 16 |  | 1.47 |
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
