# The old-fitter fit of the old band: is it better geometry? (2026-10-10)

While updating the site we found a spiral fit that finished on 2026-10-10 at 01:05 UTC and was never written up: the
PHerc. 343 winner's recipe (surface SDT, phase spacing, no shell, 30k steps) run with the villa fitter from before it was
simplified (commit 0fb38c45 plus our one-line shell-optional patch, `box/patches/`), on PHerc. 0191 band z 9,000–10,000.
Its own metric says 56.3 % of track points satisfied (12.9 % of tracks), against 46–52 % for the current fitter. The old
fitter counts track crossings differently, so the two numbers are not directly comparable. Ted asked us to check it before
judging the PHerc. 0813 fits.

## What we did (home box, free; run record `runs/2026-10-10_oldfit-check/`)

1. **Snap**: the old fit's 100 windings w020–w119 snapped onto the m7 surface prediction with exactly the settings used for
   our current fit of the same band (exp30k-z9000).
2. **Mesh match** (`mesh_match.py`): for every snapped old-fit vertex, the distance to the nearest snapped exp30k-z9000
   surface (densified 5× so the distance is to the surface, not to its 20-voxel vertex grid), and which exp30k winding it
   lands on.
3. **CT previews**: old-fit w070, w067, w073 flattened (Lasagna), rendered (66 layers) and previewed at the surface layer,
   next to the exp30k-z9000 previews of the windings they mostly follow (w073, w070, w077).

## Results

| Snap onto the m7 prediction (100 windings) | old fitter | current (exp30k-z9000) |
|---|---|---|
| vertices with a predicted sheet within reach | 0.882 | 0.890 |
| median move onto the sheet (voxels) | 1.71 | 1.84 |
| 90th percentile move (voxels) | 5.15 | 5.33 |
| vertices rejected as outliers | 0.281 | 0.287 |

- Mesh match: median distance 3.2 voxels; 58 % of old-fit vertices lie within 4 voxels of an exp30k winding. Each old
  winding spreads over several exp30k windings (old w070 lands mostly on exp30k w073, w074 on w078, w090 on w097: the
  offset grows outwards), so the two fitters chain the same sheet pieces into turns differently.
- CT previews: each pair shows the same piece of papyrus (same crack band, same clean central stretch), mirrored left to
  right because the two fitters run the winding in opposite directions. Weave clarity and the distorted ends are the same in
  both. No pair is clearly cleaner on either side.

## Verdict

The old fitter does not give better geometry on this band: snap statistics are level, it lands on the same sheet pieces,
and the CT looks the same. The higher satisfied-track number comes from the different way it counts. We keep the current
fitter (exp-30k recipe) for PHerc. 0813, and the old band stays closed.

Images (Mac, not in git): `data/PHerc0191/reviews/2026-10-10_oldfit-check/oldfit_<old>_vs_<current>.jpg`.
