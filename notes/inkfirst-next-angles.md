# Ink first: angles of attack after the clean tests (written 2026-10-12)

## Status
- **Round 1 (clean model, Reader v2).** On PHerc0139 w047 (known text), mesh-free patches correlate with the text at r 0.29–0.44, z +2.4 to +3.2 against 72 shifted references, but at only 9–18 % coverage.
- **Contaminated runs.** Everything later on 0139 used d9v4C, which trained on w047 (`notes/inkfirst-2026-10-11.md`).
- **Queued.**
  1. Reader v2-only rerun on 0139: denser sampling, blending, and the text vs no-text block test against PHerc0813 and PHerc0191.
  2. PHerc0841, a scroll none of the 9 µm models trained on, with human labels: Reader v2 + d9v4C + dense_native.
  3. 0139 clean ensemble: Reader v2 + dense_native.

**Gate for everything below.** Clean-model signal on both controls: z ≥ 4 against shifted references at ≥ 50 % coverage, plus the text block above both no-text blocks in patch contrast. If not met, park ink first and put the GPUs on the tall-band tiling.

## Angle 3: better patches (geometry within a patch)

Problem: a patch is a flat plane through the point. Where the sheet curves or the normal estimate is off, the plane cuts the sheet at a slant. The 17-layer window then sees papyrus at the patch centre but air or the next sheet at its edges: the "shards" in the blended picture.

- **3a. Snap every patch pixel to the surface.** For each pixel of the plane, sample the surface prediction along the normal at offsets −12..+12 and take the centroid of the positive voxels (or the argmax). Smooth the offset map (Gaussian σ ≈ 8 px), clamp it to ±10, and resample the 66 layers around plane + offset·n. This is Nieuwlaar's snap applied inside each patch. Each patch becomes a tiny curved mesh that follows the predicted sheet.
  - Cost: about 25 extra lookups per pixel in a binary uint8 volume; sampling ≈ 1.5× slower.
  - Code: `inkfirst_patches.py --snap R`.
- **3b. Quadratic patches.** Fit z = a u² + b uv + c v² + d u + e v + f to the prediction voxels within ~1.5 patch radii, in the local frame. Sample on that surface, with normals from the fit. 3a covers most of this; 3b is smoother where the prediction is noisy.
- **3c. More context.** 384–512 px patches (3.6–4.8 mm) with the central 256 px kept. The models tile at 256 px, so a bigger patch gives every tile a coherent neighbourhood. This only works with 3a or 3b, because flat planes of that size cut through neighbouring sheets.
- **3d. Consistent orientation.** Sign each normal with the recto prediction (normal pointing from the papyrus body to the recto face) instead of the CT gradient. Then one layer order is the reading side for every patch, and we stop averaging a right and a wrong order. On scrolls without a recto prediction (0813, 0841, 0191), keep both orders and choose per block by the blind/reading contrast.
- **3e. Patch QA.** Reject patches whose snap offsets vary by more than ~6 voxels across the centre (folds, junctions), or whose CT behind the surface is not papyrus. Fewer shards, slightly less coverage.
- **Evaluation.** The same windows (0139 w047, 0841 auto_grown): coverage, r, z against 72 shifted references, AUC against labels, the mesh-based map on the same pixels, and a picture.
- **Effort.** About half a day of code; 2–3 h of box time per rerun.

## Angle 4: other existing models

Training-overlap table: check it before every evaluation (memory `feedback-check-training-overlap`).

| model | licence / source | PHerc0139 w047 | PHerc0841 | notes |
|---|---|---|---|---|
| Reader v2 | MIT, DomRusso2 | clean | clean | our best clean model at 9 µm |
| dense_native | Nieuwlaar rebuild | clean | clean | best on 0139 in run 7 (AUC 0.859) |
| ink_9um s42/s43 | villa | clean | clean | weaker; cheap ensemble members |
| d9v4C (d9v2/d9v3) | MIT, TAUIL | TRAINED ON IT | clean | 0841 only |
| Scheirer ft_s42 | community | TRAINED ON IT | clean | 0841 only |
| Hecate | scrollprize/hecate | check model card | possibly seen | Erwin's strongest on 343; distilled from a Paris 4 2.4 µm model |
| ink_3d_dino_guided | scrollprize | n/a | n/a | 3D UNet for Paris 4 at 2.4 µm with visible ink |

- **Hecate.** run_ink.sh already supports it (hecate_prep resamples to 9.6 µm and writes PNG maps on a 9.6 µm grid). For mosaics, resize its maps back to the mosaic grid before back-projection, which is a ~2.5 % scale change. Check its training data first.
- **ink_3d_dino_guided.** Expects 2.4 µm volumes where the ink is visible. At 9 µm the ink is not visible, so a transfer is unlikely. Try once on a block only for completeness.
- **Ensembles.** Mean of per-model z-scores (Nieuwlaar's normalisation), clean models only per control. Report each model and the ensemble.

## Angle 5: train our own ink-first model

**Idea.** Fine-tune a 9 µm ink model on patches cut exactly as ink first cuts them, so it learns slant, offset and partial sheets instead of clean flattened renders.

- **Base.** Reader v2 (MIT, villa ink path, 17-layer window, step 40000). Alternative: dense_native, after checking its licence.
- **Labels.** For every pixel of a patch mosaic, take its 3D point. Find the nearest point of a labelled segment's mesh within ~3 voxels and copy that mesh pixel's label. Pixels with no mesh point nearby, or outside the supervision mask, are "ignore". This gives a label mosaic aligned with the input mosaic.
  - Sources: PHerc0841 auto_grown (human labels), PHerc0139 w047 (78 keV prediction as a pseudo-label), plus any other public 9 µm segments with `ink-labels/` on S3. Survey before starting: list `*/segments/*/ink-labels/` per scroll.
- **Training.** A patch mosaic plus its label mosaic is just another "segment" to the villa training code (vesuvius/ink_detection/training), so the standard pipeline runs unchanged. Settings: fine-tune from step 40000, lr ~1e-4 → 1e-5, a few thousand steps, augmentation as in Reader v2, on a 3060 12 GB. Roughly hours to a day.
- **Honest test.** Leave one scroll out: train on 0139 (+ other scrolls), test on 0841; then swap. Compare against Reader v2 off the shelf on the same ink-first patches, and against the mesh-based pipeline on the same pixels. The model must never see the test scroll's labels.
- **Risks.**
  - Label noise: the 0139 label is itself a prediction.
  - Only two or three labelled scrolls at 9 µm, so overfitting to their look.
  - A domain gap to the eligible scrolls: different preservation, crushing (0191), cracks (0813).
- **Rules.** First Letters only forbids overlap between training and prediction regions, so training on controls and predicting on eligible scrolls is allowed. The Grand Prize forbids data derived from higher-resolution scans of the submitted scroll only. Training labels are CC BY-NC 4.0, so a released model and dataset carry that licence.
- **Progress Prize angle.** "A 9 µm ink model for mesh-free search" is squarely on the organisers' open-problems list (3D/volumetric ink detection) if it beats off-the-shelf models on held-out text.
- **Effort.** About 1 day for the label-transfer and mosaic code, 1 day of training and evaluation. Only after the gate.

## Order once the gate passes
1. 3a + 3d (snap and orientation) on both controls: the cheapest fix for the shards.
2. Add Hecate (after its training-data check) and ink_9um to the ensembles.
3. The 5-label survey, then training with leave-one-scroll-out.
4. If any version clearly separates text blocks from no-text blocks, try it on one eligible-scroll block next to a tall-band region, where we can check candidates with meshes.
