# First Letters campaign plan — PHerc0191 (drafted 2026-10-08, evening)

Goal: 10 legible letters inside one 4 cm² area of an eligible scroll → $50k First Letters prize; PHerc0191 is also Grand Prize
eligible, so every winding we recover feeds the bigger goal. Principle (Ted): full coverage, deliberate, no sampling-and-praying;
compute, bandwidth and storage are not constraints — the ~10 MB/s link and the model's cross-scroll generalization are.

## Why PHerc0191 (data-driven, not folklore)
- Scan config 9.362 µm / 113 keV / 1200 mm detector — identical to the native-9 µm `ink_9um` training volumes (PHerc0139, PHerc0814);
  the 8.64 µm scrolls were scanned at 116 keV. Volume 18977 × 8387 × 8387 (17.8 cm tall), `left_handed=False`, `z_top_to_bottom=False` → sense "CW".
- Full input set published: spiral tracks (9.9 GB dbm + packed `.vctracks` + 2.4 GB crossings), lasagna normals (nx/ny/grad_mag at 4×),
  surface predictions + normal grids (umbilicus source). Densest tracks per slice of any 9.362 µm eligible scroll (0.52 GB/1000 slices).
- The team used it as the lasagna showcase in the First Letters guide. Fallback/second scroll: PHerc0125 (same config, 20840 slices).
- Unknown and unknowable up front: whether its ink is visible to the 9 µm models. The campaign is designed to answer that with full coverage.

## Prior art on the eligible scrolls (found 2026-10-08 on Hugging Face/GitHub) — what NOT to repeat
- `pscamillo/vesuvius-eligible-meshes` (+ `…-ink9` HF dataset): the team's spiral fitter in its *minimal* configuration ("umbilicus plus
  lasagna, no patches, no winding constraints") over "a grid of z windows" on 8 scrolls (0125: 62 meshes, 0211: 90, 0800: 95, 0813: 75,
  0257/0268: 6 each, 0358/0826: 3 each) = 340 one-winding meshes, 1,935 cm² total (≈ a few % of one scroll's sheet area); ~63% "usable weave";
  rendered 31 slices; `ink_9um` seed43 step-060000, layers 7–24, both directions; "nothing in this set has survived my own screening for text".
  Their `--flip-normals` errata independently matches our orientation finding. PHerc0191 not covered.
- `rodriguescarson/eligible-scroll-atlas`: 2,028 raw ink maps over those 340 meshes with `ink_9um` and `scrollprize/hecate`, a pre-registered
  screen (5/340 pass; maps withheld and sent to the team privately), a reproduction of all 95 PHerc0800 meshes, and **one spiral fit on
  PHerc0191** (tifxyz in `eligible-scroll-spiral-fits`; no ink result described). Notes that the top-scoring meshes include a documented false positive.
- `gmDevi/vesuvius-ink-sweeps`: 32 batch folders incl. `p0191_batch` (246 files), `p0125`, `p0211`, `p0813`, `p0826`, `p0175A`, `p0306B`, `p0343`,
  `p0483A`, `p0490A`; per-winding "letter-like blob" counts of 0–1 everywhere in the logs sampled — i.e. nothing.
- `nestorvfx/vesuvius-ink-training`: community-assembled ink training stacks (3,297) incl. pretraining npz for 0125 — a possible fine-tuning resource.

Implications: (1) the baseline recipe (minimal-route fit on sampled windows + `ink_9um` defaults) has been tried broadly and is not enough;
(2) nobody has done *complete* coverage of a scroll — our plan's whole-scroll band fits are a genuine differentiator (text may simply sit in
unrendered windings/regions); (3) geometry quality (patches/tracks/winding constraints beyond the minimal route) and model iteration
(depth ensembles, fine-tuning, `hecate`/3D models) are where an edge must come from; (4) use their published PHerc0191 fit and the atlas
manifest as free checks on our own fit, not as a substitute.

## Phase 0 — data + environments (running now; link-bound, ~1 day)
| item | size | state |
|---|---|---|
| CT volume mirror, all levels (`bin/mirror_s3.py`, 32 streams, resumable) | ~475 GiB est. (27% chunk occupancy) | running → `data/PHerc0191/volumes/…` |
| spiral tracks dataset (`wget -c -r`) | ~13 GB | running → `data/PHerc0191/spiral/20250821151635/` |
| lasagna normals + grad_mag (nx/ny/grad_mag OME-Zarr, groups 2–4) | est. 3–8 GB | running → `data/PHerc0191/lasagna/…` |
| normal grids `xy/` (for `vc_gen_umbilicus`) | ≤ 19.8 GB | running → `data/PHerc0191/normal-grids/xy` |
| spiral-fitting env (`uv sync`: torch cu128, brook, cupy, cucim) | ~4 GB | running |
| lasagna env (`scripts/bootstrap_venv.py`) | ~3 GB | running |
| VC3D + vc_* tools, vesuvius ink env, ink_9um ckpts (s42 40k/75k, s43 75k) | — | done |

Order of completion matters little: everything except the final full-scroll fit can start on z-bands as soon as the volume levels for
those bands exist (the mirror pulls pyramid levels 5→0; level 0 last).

## Phase 1 — assemble the spiral dataset (no GPU)
```
data/PHerc0191/spiral-dataset/
├── spiral-scroll.json   {"schema_version":1,"name":"PHerc0191","voxel_size_um":9.362,
│                         "z_direction_is_top_to_bottom":false,"left_handed_coordinates":false,   # → sense CW (derived)
│                         "normal_zarr_group":"2","lasagna_scale":4,
│                         "paths":{"tracks_dbm":"tracks/PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm",
│                                  "normal_x":"lasagna_inputs/PHerc0191_nx.ome.zarr","normal_y":"lasagna_inputs/PHerc0191_ny.ome.zarr",
│                                  "gradient_magnitude":"lasagna_inputs/PHerc0191_grad_mag.ome.zarr"}}
├── umbilicus.json       ← vc_gen_umbilicus -i normal-grids/xy -o umbilicus.json --seed 1 --repeats 3 --threads 4
├── tracks/              ← symlink to the mirrored tracks dir (dbm + .vctracks packed store + crossings.npz; no conversion needed)
└── lasagna_inputs/      ← symlinks to the three mirrored stores, then
                            pack_resident_pools.py lasagna_inputs --what normals,grad_mag --normal-group 2 --ct <volume.zarr> --ct-group 2 --verify 2000
```
Fit overrides for the "minimal route" (inputs 0191 does not ship are disabled): `input_use_verified_patches false`, `input_use_outer_shell false`,
`loss_weight_shell_outer 0`, `loss_weight_shell_patch_radius 0`, `dense_spacing_mode "grad_mag"` (no `winding_inference/`),
`input_use_tracks true`, `input_use_pcl_* false` (no point collections yet). Exact key names verified against `config.py` before use.
Sanity check before any long fit: open a mid-scroll band in VC3D (X-forwarded) with the lasagna normals; confirm the sense and the umbilicus.

## Calibration from the community PHerc0191 fit (rodriguescarson/eligible-scroll-spiral-fits, 2026-09-15)
- Their run `PHerc0191_slice-11600-12400_0-patch_w90`: 800 slices, no patches, 90 windings, 415.6 cm² raw surface, **1.5–1.9 h on one A40**
  → expect ~4–6 h for our 1000-slice pilot on an RTX 3060 and ~10 h per 2000-slice band; a whole-scroll pass on 3 cards ≈ 1.5–2 days.
- **Winding count is threshold-dependent — do not over-trust either side.** Their 12-ray audit at z=12000 found 64–74 fitted windings per ray
  vs 22–42 "strict" CT peaks and called the minimal-route fit 2–3× over-packed; our own ray audit (`bin/ray_peaks.py`, CT level 2, centroid
  center) at the same z counts 74 / 90 / 97 peaks per ray at three prominence levels (sheet period ≈ 0.3 mm), which is consistent with ~90
  windings. Conclusion: the minimal route *may* over-pack, the evidence is not decisive; production bands should still use
  `dense_spacing_mode: "winding_model"` (a learned winding constraint; needs a generated `winding_inference/` from
  `scrollprize/winding_model_9um` via `infer_winding_volume.py` → `export_spiral_supervision.py`; recipe being extracted) **plus tracks**,
  and every fit gets the ray audit against its own winding count. The queued `grad_mag` pilot is the plumbing/comparison run.
- The scroll has **no air core** at z=12000 (dense to the centroid, unequal ray extents 18–30 mm) — the umbilicus check must be "center of the
  spiral" (first-crossing symmetry, agreement with the fit), not "empty core".
- Their umbilicus was a 64-point manual curve (Drobkov). Ours is generated (`vc_gen_umbilicus`); validate it with the same 12-ray
  peak-count method on CT level 2 (already mirrored) before any production fit.
- Their meshes were released as "unvalidated geometry"; none of the community pipelines used tracks or winding inference.

## Phase 2 — surface recovery: z-band fits on three Ampere GPUs
- Pilot: one 1000-slice band mid-scroll (`z 9000–10000`, 10k steps) → inspect fitted windings (cross-sections, flat-view fiber continuity).
- Production: bands of ~2000 slices with ~160-slice overlap covering z≈1500–17500 (the capped ends are mostly air/scaffold) → ~9 bands,
  3 at a time (one per RTX 3060 / 3060 Ti; the GTX 1660 S is NOT usable for any of this work — see gpu-box memory), 30k steps each.
  Resident pools scale with the band (Paris4 full ROI ≈ 10 GiB normals), so 2000-slice bands fit a 12 GB card; the Ti may need 1500.
  Runtime unknown for our cards (team: ~30 min per 30k-step fit on 4 datacenter GPUs) → expect hours per band; a full pass ≈ 1–3 days.
- Output per band: `meshes/mesh/wNNN/` tifxyz per winding (column 0 = outermost), checkpoint, satisfaction metrics.

## Phase 3 — flatten → render → ink, exhaustively
Per winding mesh (hundreds across bands; all of them, scripted, resumable):
1. `lasagna fit.py configs/flatten_fast_nofilter.json <winding_input.json> --out-dir … --device cuda` → `flatten.tifxyz`.
2. `vc_render_tifxyz -v <local volume> -s flatten.tifxyz --scale 1 -g 0 --num-slices 28 --slice-step 1 --flip-normals --surface-interpolation smooth --zarr-output …`
   (local mirror: no remote-fetch fragility; `--flip-normals` because `left_handed_coordinates=False`).
3. `ink_9um` inference: seeds 42+43 × steps 40k/60k/75k × `--direction both` × 17-layer windows at 3 depth offsets; also `--tta-mirror`.
   The GTX 1660 S is NOT usable (verified 2026-10-09: ink inference writes all-zero maps in fp16 and fp32). 3 GPUs busy here.
4. Triage: NOT "fraction above threshold" (it rewards blobs). Score row-structure: anisotropy/periodicity along the fiber direction of
   the rescaled probability map, then human review of the top N per winding at ds2. Keep every raw TIFF.
Volumes: a winding of 0191 ≈ (17.8 cm tall × up to ~25 cm long) → ~1e4 × 2.7e4 px at 9.36 µm → ~1e5 patches → ~15 min/GPU per checkpoint
pass; ~100 windings × 6 checkpoints × 2 directions ≈ 300 GPU-hours worst case ≈ 4–5 days on the 3 usable GPUs. Depth-offset sweeps only where
row-like signal appears.

## Phase 4 — iterate toward legibility (the research part)
- Where faint row-aligned signal appears: average nearby depth windows and checkpoints; render at ±1 slice-step offsets; check that
  strokes form rows aligned with fibers and consistent across adjacent windings.
- Conservative labels on the clearest strokes + trustworthy background → fine-tune the 9 µm recipe from `step-075000`
  (`checkpoint` + `weights_only`, SGD recipe, `fixed_scroll_prior` adjusted to include 0191) on 2–3 of our GPUs; re-infer; repeat.
  Never train on the region we intend to claim (prize rule: model outputs must not overlap training data); hold out a region for the
  false-positive mitigation write-up. HF `scrollprize/datasets` (base ink labels) is gated — needs Ted's HF read token.
- If 0191 shows nothing after full coverage: the entire machinery re-targets PHerc0125 at the cost of one more mirror (~18 h).

## Phase 5 — submission
Flattened tifxyz mesh(es); one programmatically generated image with 1 cm scale bar, px/mm dimensions, row annotations, named after
the mesh; methodology (scripts + instructions, or Docker); held-out validation on Paris4 (we already have the known-text pipeline run);
false-positive argument; Discord registration; no publication before the official announcement. Form: https://forms.gle/TM5ao8GwC2mDrdLk9.

## Needs from Ted
1. ~~Ethernet~~ — not available for now (Ted, 2026-10-08); the USB Wi-Fi adapter's ~100 Mbit/s is the accepted ceiling. Phase 0 is sized to it.
2. ~~Discord registration~~ — done 2026-10-08: Skuzbucket (`skuzbucket_79937`).
3. ~~HF read token~~ — provided 2026-10-08 (in `.secrets`, installed on the box). Caveat: `scrollprize/datasets` is private/not found even with the token; Phase 4 labels come from the S3 per-segment `ink-labels/` and nestorvfx/vesuvius-ink-training (CC-BY-NC).
4. Click the staged PR when convenient — link in `notes/pr-install-volcomp.md` (all claims verified, incl. the render).

## Side products (Progress Prize material, keep logging)
`notes/friction-log.md` (5 items; #1 fixed and staged as a PR). Expect more from the spiral/lasagna tooling on a non-showcase run.
