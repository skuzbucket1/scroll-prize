# Ink first, geometry second: in test

**Question.** Fitting and flattening a band is the slow part. Can we look for ink first and build geometry only where
something shows? Ink first cuts small 66-layer patches along the published surface prediction, with no mesh, inks them,
and maps the hot ones back into the scroll.

**Code.**
- `tool/` is the package (`ink-first`, MIT; README inside).
- `inkfirst_*.py` are the box scripts: planning, block summaries, scroll maps, cluster and sheet views, the tests against
  known text and the re-sort.
- `letters_to_3d.py` puts PHerc. 343's letter boxes back into the scan.
- `viz_glow.py` makes the "glowing sheets" picture.
- `fetch_block.py` downloads the CT chunks of one block.
- `aws/` holds the launchers for a sweep on AWS (they use `../../infra/aws/`).
- Runs: `runs/`.

**Numbers so far.**
- Prototype on PHerc0841 (unseen scroll, 9.36 µm): finds the known text at most of the mesh pipeline's strength.
- PHerc. 343 positive control, 8.64 µm: with one point per 0.8 mm cube, only 13 of 766 patches landed on his letters. A
  sampler with one point on every sheet cuts 4,441 patches. Reading-side hot patches land on the letters about 15 times
  more often than chance (22–24 % of the hot patches against 1.6 % of all patches). But the block as a whole still looks
  like any other block.
- PHerc0175A whole-scroll sweep (199 blocks, 129,125 patches, Reader v2, about $25 on AWS): no text signature. With one
  point per 0.8 mm cube it rules out large, strongly inked areas, not a few lines like 343's.

**What decides it.** We rank clusters of hot patches against the same place on the other face, not whole blocks, and
test that on 343 at home. If 343's letters come out on top, a second PHerc0175A sweep with the per-sheet sampler is worth
quoting. That is paid AWS time, so it is a separate decision. If they don't, ink first stays a coarse pre-filter.

Site: https://skuzbucket1.github.io/scroll-prize/#run-inkfirst-343-control

**Update 2026-10-14: PHerc0841.** Per-sheet ink first on two 1,280³ blocks around labelled segments (runs/2026-10-13_inkfirst-0841):
on ag2814 the patches on letters light up (d9v4C hot fraction 0.20 against 0.09 elsewhere in the block); on w00 they do not
(0.05 against 0.09). One pass, one miss: ink first stays a coarse way to pick places, behind the mesh pipeline.
Site: https://skuzbucket1.github.io/scroll-prize/#run-inkfirst-0841
