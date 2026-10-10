# Overnight 2026-10-10 (≈05:10–11:05 UTC): Phase A3 on the clear band

## What ran (home box, free)
- Phase A3 of `notes/research-plan-2026-10-10.md`: full four-model ensemble (ink_9um seeds 42/43, dense_native, Hecate) on
  the 7 windings picked with Ted (w070, w071, w072, w073, w074, w087, w089) of fit exp30k-z11200 (band z 11,200–12,200),
  depth tiers 0/+1, then −1/+2, then −2/+3. Scripts `bin/deep_look.sh` (GPUs 0, 2, 3) and `bin/deep_score.sh` (CPU scorer,
  packaged `tools/stroke-score`). Logs and run record: `runs/2026-10-10_deeplook-exp30k-z11200/`.
- At 11:04 UTC: 158 of 168 units done, 0 failed; 37 of 42 winding-depths scored. The rest (depth +3) is running.
- Speed: Hecate ~22–23 min per unit (both sides), the other models ~2.2 min per unit, on the home 3060s.
- The PHerc0813 band download finished before the night (75 GB, 0 failed files); nothing was started on it (Phase B2+ waits for Ted).

## Results so far (four models, reading side vs blind side)
- The clear band scores higher than the old band: reading-side stroke area 0.0065–0.0115 (old band four models ≤ 0.0073),
  reading minus blind up to +0.0100, best 4 cm² window up to 0.038. The control (PHerc. 0343, real letters) is 0.0335,
  +0.031 and 0.048.
- Two rows crossed the flag line, both at depth +2: w074 (area 0.0115, R − B +0.0100, window 0.0381 vs 0.0038 blind) and
  w073 (0.0114, +0.0100, 0.0295 vs 0.0026).
- By eye (row-scale views, top crops reading | blind | CT, for w073 d+1 and d+2, w074 d0 and d+2): the high scores come from
  one cluster of soft, rounded blobs (about 1–1.5 mm) in the upper right of both windings, sitting along a horizontal crack
  band with voids that the CT shows in the same place; the cluster is present at depths 0, +1 and +2. No elongated strokes,
  no letter shapes, no rows. The blind side has the same texture, only dimmer. The crescent arcs on w073's blind side at d+1
  are fragment edges inside the recurring folded zone (CT: air with papyrus fragments).
- Verdict: no letters so far in the clear band. The crack-band cluster is the strongest PHerc. 0191 signal yet; it is
  worth showing Ted, but it does not look like writing.

## Other notes
- Several SSH sessions over Tailscale timed out or hung overnight, most likely transient internet trouble (Ted). Box jobs were
  unaffected (they are detached). Long transfers now run with timeouts and detached builds.
- The known-text positives agent (stroke-score validation, Phase C2) had not reported back by 11:05.
- NVMe at 89 % (104 GB free).

Images: `data/PHerc0191/reviews/2026-10-10_clearband-deeplook/` (Mac, not in git).
