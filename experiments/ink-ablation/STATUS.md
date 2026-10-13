# What do the ink models see? In test

**Question.** On PHerc0841's human-labelled letters the raw CT is no brighter where the ink is (AUC about 0.5 at every
depth; see `dead-ends/model-free-ink`), yet the models find the letters (AUC 0.82–0.86). So what are they responding to?
We change one thing in the render at a time and see how much the models' score on the real letters drops.

**Code.** `ink_ablation.py` takes a 66-layer control render with human labels and runs one model on variants of it:
- the render as it is
- one band of layers replaced by its own mean (which depths carry the signal)
- a 0.5 mm high-pass (pattern kept, slow brightness removed)
- pixels shuffled inside 8 × 8 px blocks (fine weave destroyed, stroke-scale brightness kept)

Each variant's reading-side map is scored against the labels. The runs are in `runs/2026-10-13_ink-ablation/`: dense_native
and Reader v2 on PHerc0841 w00 and ag2814.

**First numbers** (dense_native on w00, AUC against the labels):
- the render as it is: 0.85
- layers 30–32 flattened: 0.71 (the biggest drop so far)
- layers 33–35 flattened: 0.77
- layers 26–29 flattened: 0.80
- layers 36–38 flattened: 0.84
- layers 39–42 flattened: 0.86 (no change)
- 0.5 mm high-pass: 0.85 (no change)

The pixel shuffle and the other three model/segment pairs were running on 2026-10-13, due late morning CT.

**What it decides.** Nothing in the pipeline. It tells us what a synthetic letter would have to imitate before we try
making training data that way, and which layers matter when a render is off by a voxel.
