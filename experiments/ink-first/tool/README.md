# ink-first

Look for ink in Herculaneum-scroll CT **without a mesh**. Points are sampled on a published surface prediction. At each
point a 66-layer patch is cut along the local sheet normal, like a tiny render. All patches are tiled into one mosaic,
so any 66-layer ink model can ink them unchanged, and the predictions are mapped back to 3D.

Status: version 0.1 (research prototype), October 2026. Tested on two known-text segments scanned at 9.36 µm and on
null blocks from two scrolls. It finds known text at roughly 60–80 % of the correlation of the full mesh pipeline, with no
geometry work at all (table below). Whether it can tell text-bearing regions from text-free ones across a whole scroll is
not shown yet.

## Why

At 9 µm, finding text means first fitting the sheet geometry: spiral fits, snapping, flattening, rendering. That is the slow and
fragile part of the pipeline, and it limits how much of a scroll gets searched. Running the ink models costs much less.
ink-first skips the geometry for the search step: it scans a block for ink, and careful meshes are only needed where ink
shows up.

## How it works

1. **Surface points.** Voxels of a surface prediction (the organisers' m7 or recto-surface prediction) above a
   threshold, one point per `stride`³ cell.
2. **Normals.** The smallest-variance direction of the prediction within `radius`. Points where the sheet is not clearly
   planar (junctions, noise) are dropped (`--flat`). The sign points out of the papyrus.
3. **Patches.** `size` × `size` pixels in the tangent plane, with the scroll axis vertical. Layer k samples the CT at
   (k − 32.5) voxels along the normal, the convention of Erwin Nieuwlaar's 66-layer renders.
4. **Inking.** The mosaic `mosaic.zarr` (66, H, W) is a surface volume like any render. Ink it with your model. With
   Nieuwlaar's `run_ink.sh`: `run_ink.sh <dir>/mosaic.zarr readerv2 0 <dir>/maps`. Mosaics over ~1,100 patches: `split`, ink the
   quarters, then `stitch`.
5. **Back to 3D.** Every centre pixel of a patch has a 3D position. `back` maps the predictions onto a tifxyz mesh
   window, for evaluation against known text; `within` maps them onto every rendered winding crossing the block, for
   comparison with the mesh pipeline.

```
ink-first fetch  --url <CT zarr> --out ct.zarr --box z0 z1 y0 y1 x0 x1        # only the chunks covering the box
ink-first fetch  --url <surface prediction zarr> --out pred.zarr --box ...
ink-first sample --ct ct.zarr --pred pred.zarr --box ... --out blk --stride 64 --flat 0.5
run_ink.sh blk/mosaic.zarr readerv2 0 blk/maps                                # or split / ink quarters / stitch
ink-first back   --patches blk/patches.npz --maps blk/maps --mesh seg.tifxyz --window r0 r1 c0 c1 --out back.npz
ink-first eval   --back back.npz --reference labels.zarr --mask supervision.zarr --window ... --grid-rows N --shift dy dx
ink-first stats  --patches blk/patches.npz --map blk/maps/mosaic__readerv2__L66s25.tif --label myblock
```

`eval` reports, per model and layer order:
- AUC and correlation with the reference on the covered pixels;
- a null from 72 shifted references, because lines of text repeat and a single far shift is not a valid null;
- the correlation of coarse density maps (0.5 and 1 mm cells).

Give the reference alignment with `--shift`, taken from an independent map such as the mesh-based one. Searching it on
the image being scored is slightly optimistic.

## Results

Only models that never trained on the test segment are used: d9v4C was trained on PHerc0139 w047, so it is left out
there. Coverage = share of the test window with a patch pixel within 8 voxels.

| test | prediction | model(s) | coverage | correlation | AUC | z vs 72 shifts | mesh pipeline, same pixels |
|---|---|---|---|---|---|---|---|
| PHerc0841 auto_grown (unseen scroll, human labels), 1.2 cm window | m7, stride 0.6 mm | Reader v2 | 49 % | 0.45 | 0.76 | +5.1 | r 0.57, AUC 0.81 |
| same | same | d9v4C | 49 % | 0.45 | 0.76 | +5.4 | |
| same, as a 0.5 mm density map | | Reader v2 | | 0.59 | | | |
| PHerc0139 w047 (78 keV reference), 1.2 cm window | recto, stride 0.6 mm | Reader v2 | 50 % | 0.33 | | +3.4 | r 0.57 |
| same, blended (per-patch z-score, Hann weights) | | Reader v2 | 74 % | 0.28 | | +6.1 | r 0.59 |

Blocks without text found, compared with the PHerc0139 text block:

| | PHerc0139 (text) | PHerc0813 | PHerc0191 |
|---|---|---|---|
| share of patches with raw contrast SD > 0.10 | 16 % | 5.4 % | 1.3 % |

This is the setting with the m7 prediction, stride 0.9 mm and Reader v2. The text block stands out, but the two text-free
scrolls also differ from each other by 4×. Scroll-to-scroll differences are as large as the text effect, so this does
not yet show a search signal. Within one scroll, ink first agrees with the mesh pipeline on the same windings (per
winding r 0.2–0.6 on PHerc0813 and PHerc0191). There the shared features are damage, not text.

## Limits

- Coverage. Flat patches cut gently curved sheets at a slant: about half of a test window is covered at stride 0.6 mm,
  three quarters with blending. Per-patch surface snapping and curved patches are the next step
  (in our working notes).
- The patch statistics are not yet comparable across scrolls; a within-scroll test is needed.
- At 1/4 resolution the sheets of a block fuse into one connected component, so ink first does not separate sheets.
  Reading text still needs a mesh where ink shows up.
- It inherits the ink models' blind spots and their training sets. Check which models trained on your test segment.

## Prior art

- The organisers segment ink directly in 3D on PHerc. Paris 4 at 2.4 µm, where the ink deposits are visible in the CT
  (`scrollprize/ink_3d_dino_guided`; arXiv 2606.29085).
- 3D/volumetric ink detection is a Progress Prize target.
- We have not found prior work running the 9 µm surface ink models on patches cut along the published surface
  predictions, without a mesh.

## Credits

- Surface predictions (m7, recto), CT scans and known-text segments: Vesuvius Challenge / EduceLab (CC BY-NC 4.0).
  PHerc0841 human ink labels and the PHerc0139 w047 reference map are by the Vesuvius Challenge team.
- Ink models: Reader v2 (Domenico Russo, DomRusso2/reader-v2, MIT), d9v4C (TAUIL-Abd-Elilah, 9um-reader-letter-shape, MIT),
  dense_native (Erwin Nieuwlaar).
- Nieuwlaar's 66-layer render convention and `run_ink.sh` (github.com/Nieuwlaar/pherc343-first-letters, MIT).

## Licence

MIT
