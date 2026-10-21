# Data catalog (generated)

Generated 2026-10-21 15:31 UTC by `infra/backup/catalog.py` (one scan per host) and `infra/backup/results_db.py`, merged on the Mac into `data/catalog/catalog.sqlite` and `data/catalog/results.sqlite`. Do not edit by hand: re-run the scans. Layout and rules: `docs/DATA_LAYOUT.md`. Backup set: `infra/backup/backup_r2.sh` (private object storage).

## Artifacts by host and kind

| host | kind | items | GiB | critical items |
|---|---|---:|---:|---:|
| GPU machine | render | 330 | 606.95 | 0 |
| GPU machine | other | 84254 | 430.04 | 204 |
| GPU machine | ink-map | 24326 | 74.65 | 640 |
| GPU machine | private work (not described here) | 47960 | 20.51 | 875 |
| GPU machine | fit-input | 74 | 18.35 | 23 |
| GPU machine | ensemble-image | 3719 | 15.44 | 766 |
| GPU machine | control-render | 11 | 11.49 | 0 |
| GPU machine | mesh-flattened | 5561 | 11.02 | 5561 |
| GPU machine | site | 11310 | 8.84 | 0 |
| GPU machine | fit | 15328 | 8.36 | 15328 |
| GPU machine | model | 256 | 6.77 | 0 |
| GPU machine | score-figure | 5855 | 4.47 | 5855 |
| GPU machine | geometry-qa | 482 | 2.01 | 482 |
| GPU machine | mesh | 1003 | 1.28 | 0 |
| GPU machine | control-ink-map | 45 | 0.63 | 45 |
| GPU machine | mesh-snapped | 4704 | 0.40 | 4704 |
| GPU machine | control-ensemble-image | 13 | 0.23 | 0 |
| GPU machine | control-other | 42 | 0.11 | 42 |
| GPU machine | control-reference | 5 | 0.08 | 5 |
| GPU machine | log | 17166 | 0.05 | 862 |
| GPU machine | preview-image | 43 | 0.04 | 0 |
| GPU machine | reference | 53 | 0.04 | 53 |
| GPU machine | scan-quality | 338 | 0.03 | 338 |
| GPU machine | control-mesh | 15 | 0.01 | 0 |
| GPU machine | score | 1442 | 0.01 | 1442 |
| GPU machine | ranking | 56 | 0.00 | 56 |
| GPU machine | run-record | 22 | 0.00 | 22 |
| GPU machine | geometry | 1 | 0.00 | 0 |
| GPU machine | control-score | 1 | 0.00 | 1 |
| GPU machine | public-input | 31 | 0.00 | 0 |
| laptop | other | 13828 | 9.27 | 3984 |
| laptop | score-figure | 3879 | 2.46 | 3879 |
| laptop | fit | 12059 | 1.26 | 12059 |
| laptop | control-ink-map | 72 | 0.85 | 72 |
| laptop | mesh-snapped | 6756 | 0.69 | 6756 |
| laptop | mesh-flattened | 2264 | 0.63 | 2264 |
| laptop | mesh | 204 | 0.61 | 203 |
| laptop | ink-map | 194 | 0.54 | 132 |
| laptop | control-ensemble-image | 26 | 0.32 | 0 |
| laptop | ensemble-image | 48 | 0.21 | 48 |
| laptop | review-image | 133 | 0.15 | 133 |
| laptop | control-ranking | 8 | 0.13 | 8 |
| laptop | preview-image | 132 | 0.12 | 130 |
| laptop | control-other | 71 | 0.08 | 71 |
| laptop | control-reference | 5 | 0.08 | 5 |
| laptop | reference | 460 | 0.08 | 460 |
| laptop | score | 2204 | 0.02 | 2204 |
| laptop | log | 6333 | 0.01 | 6271 |
| laptop | geometry | 166 | 0.01 | 166 |
| laptop | fit-input | 61 | 0.00 | 61 |
| laptop | control-score-figure | 2 | 0.00 | 0 |
| laptop | memory | 59 | 0.00 | 59 |
| laptop | control-score | 11 | 0.00 | 11 |
| laptop | ranking | 5 | 0.00 | 5 |
| laptop | run-record | 1 | 0.00 | 1 |

Public inputs (scan volumes, Lasagna, tracks, surface predictions, normal grids) are listed per store without sizes; they are re-downloadable.

## Geometry and ink by scroll and fit

| scroll | fit | meshes (snapped / flattened) | renders | ink maps | ensemble images |
|---|---|---:|---:|---:|---:|
| PHerc0175A | exp30k-z7000 | 120 / 8 | 0 | 0 | 0 |
| PHerc0191 | community-z11600 | 10 / 10 | 0 | 0 | 0 |
| PHerc0191 | exp30k-z11200 | 120 / 100 | 97 | 2228 | 2594 |
| PHerc0191 | exp30k-z9000 | 100 / 99 | 0 | 344 | 283 |
| PHerc0191 | oldphase30k-z9000 | 100 / 3 | 0 | 0 | 0 |
| PHerc0343 | control | 0 / 0 | 1 | 18 | 12 |
| PHerc0343 | exp30k-z9300 | 120 / 120 | 0 | 0 | 0 |
| PHerc0813 | exp30k-z10500 | 120 / 76 | 76 | 608 | 0 |
| PHerc0813 | exp30k-z12000 | 120 / 80 | 63 | 400 | 0 |
| PHerc0813 | exp30k-z8000 | 120 / 76 | 76 | 608 | 0 |

## Scores (results table)

| scroll | fit | source | models | rows | v0.1 LOOK | max row_R |
|---|---|---|---|---:|---:|---:|
|  |  | post | d9v4c | 52 |  | 2.91 |
|  |  | post | d9v4c,dnative,ink9-42,ink9-43,readerv2 | 28 | 22 | 2.28 |
|  |  | post | d9v4c,readerv2 | 805 |  | 3.37 |
|  |  | post | dnative,ink9-42,ink9-43 | 400 | 306 | 1.54 |
|  |  | post | readerv2 | 615 |  | 4.67 |
| PHerc0175A |  | post | d9v4c,readerv2 | 2 |  | 0.00 |
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
| PHerc0343 |  | post | d9v4c,readerv2 | 16 |  | 2.72 |
| PHerc0343 | control | stroke-score | d9v4c,dnative,hecate,ink9-42,ink9-43,readerv2 | 1 | 1 |  |
| PHerc0343 | control | stroke-score | d9v4c,readerv2 | 1 |  |  |
| PHerc0343 | control | stroke-score | dnative,hecate,ink9-42,ink9-43 | 2 | 2 |  |
| PHerc0343 | control | stroke-score | dnative,ink9-42,ink9-43 | 2 | 2 |  |
| PHerc0343 | control | stroke-score | ink9-42 | 1 |  |  |
| PHerc0343 | control | stroke-score | ink9-42,ink9-43 | 1 |  |  |
| PHerc0813 |  | post | d9v4c,readerv2 | 404 |  | 2.67 |
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
