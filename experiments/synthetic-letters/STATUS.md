# Synthetic letters on real papyrus: in test (started 2026-10-13)

**Question.** Can a model trained only on letters we paint into real text-free renders of our target scans find real
letters it has never seen? Our first 8.64 µm fine-tune failed because it had 12 letters and its labels came from our own
models. Painted letters are unlimited, their labels are exact, and the papyrus around them is the target scan's own.

**What has to be right is the ink.** Two tests on 2026-10-13 say what real 9.36 µm ink looks like to the models:
- It is not brighter. On PHerc0841's human-labelled letters the raw CT is no brighter at any depth (`dead-ends/model-free-ink`).
- The models read fine texture, about 75 µm, in the layers just above the surface (`experiments/ink-ablation`): a 0.5 mm
  high-pass leaves their score unchanged (0.85), shuffling pixels inside 75 µm squares drops it to 0.60, inside 300 µm
  squares to chance, and flattening layers 30–32 costs the most of any depth band.
So the painting step changes texture with per-layer weights; brightness is off at 9.36 µm. `texture_signature.py` (in
`experiments/ink-ablation`) measures how the texture differs under real ink, and those numbers set the weights.

**Code.** `synth_letters.py`
- `letter_mask`: lines of Greek capitals (DejaVu glyphs), 2–3 mm tall, strokes 0.25–0.45 mm, line spacing 4.5–6 mm,
  small rotations and slant, an elastic warp, broken and faded strokes, a 1.5 px blur.
- `paint`: inside the mask, per weighted layer, blend toward a smoothed copy (`smooth`), damp the along-the-winding fibre
  stripes (`stripes`), or add brightness (`bright`, off at 9.36 µm).
- `preview`: one painted crop, original / painted / difference / mask.
- `dataset`: villa's flat training layout from text-free windings (layers reversed as in `dead-ends/model-8um-v1`), ink
  labels from the mask, supervision on the valid area, the last 15 % of each winding held out for validation.

**Plan.**
1. Set the effect from the texture signature; check previews by eye (the painted letters should be invisible in the
   raw CT, as real ones are).
2. Check that the existing models see the painted letters at all (dense_native, Reader v2 on painted windings): if
   they don't, the painted signal isn't the one they read.
3. Train on ~50 painted windings (PHerc0813 / PHerc0191 nulls); test only on real letters never seen: PHerc0841 w00 and
   ag2814, PHerc0139 w047, PHerc. 343. Compare with dense_native and Reader v2; false alarms on the clean crops.
4. GPU only after agreeing a slot (GPU 0 has the top-30 agreement run, GPU 2 the PHerc1447 block and then the
   official-labels test).

**Status.** Generator written, not yet run.
