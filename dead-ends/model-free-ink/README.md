# Seeing ink without a model: didn't work

**Idea.** Carbon ink on carbonised papyrus is close in density, but perhaps not equal. If the raw CT is a little brighter
inside the strokes, a simple, model-free view could show letters. That view could check the models, or find text they
miss. A second try: take out the papyrus weave first, then look again.

**What we tried.**
- `ct_ink_signature.py` (2026-10-12) compares the raw CT inside and between Erwin Nieuwlaar's letter strokes on PHerc. 343,
  layer by layer through the sheet.
- `deweave.py` (2026-10-13; runs in `runs/2026-10-13_deweave/`) removes the weave pattern per layer, then scores raw and
  de-weaved CT against the letters. It does this on 343 (strokes picked by the models) and on PHerc0841 (human labels)
  at every depth from −12 to +12.

**What it showed.**
- On 343 the CT inside the strokes is about 8 units brighter, about 6 % of the scan's range, peaking two voxels into the
  sheet. Where the surface falls inside a voxel matters a little: about 15 % weaker in one quarter of the cases.
- But no plain CT image shows the letters. The weave and cracks swamp them.
- De-weaving does not help: 343 goes from AUC 0.62 to 0.52–0.63.
- On PHerc0841's human-labelled letters the raw CT scores 0.48–0.56 at every depth, which is chance. The models score
  0.82–0.86 on the same letters.

**Why it failed.** At these scan settings the ink is not simply brighter. Whatever the models pick up across the 17
layers is subtler than brightness or weave. The open question of what it is moved to `experiments/ink-ablation`.

**What would change it.** A scan where the ink really is visible, at higher resolution or lower energy. We are not using
those for this search.

Site: https://skuzbucket1.github.io/scroll-prize/#run-raw-ct-ink
