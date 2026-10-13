# What do the ink models see? Answered (2026-10-13)

**Question.** On PHerc0841's human-labelled letters the raw CT is no brighter where the ink is (AUC about 0.5 at every
depth; see `dead-ends/model-free-ink`), yet the models find the letters (AUC 0.77–0.86). So what are they responding to?
We change one thing in the render at a time and see how much the models' score on the real letters drops.

**Code.** `ink_ablation.py` takes a 66-layer control render with human labels and runs one model on variants of it:
the render as it is; one band of the 17 stored layers (26–42) replaced by its own mean; a 0.5 mm high-pass (pattern kept,
slow brightness removed); pixels shuffled inside 8 × 8 px (75 µm) or 32 × 32 px (0.3 mm) blocks. Each variant's
reading-side map is scored against the labels (AUC inside the supervision mask). `texture_signature.py` compares hand-made
texture measures (local contrast, band energy at 20–150 µm, orientation coherence, stripe share, cross-layer correlation)
on ink and on bare papyrus, layer by layer, and fits a logistic model on all of them across the two segments.
Runs: `runs/2026-10-13_ink-ablation/`, `runs/2026-10-13_texture-signature/`.

**Results** (AUC; dense_native / Reader v2):

| variant | PHerc0841 w00 | PHerc0841 ag2814 |
|---|---|---|
| the render as it is | 0.851 / 0.859 | 0.772 / 0.821 |
| stored layers 26–29 flattened | 0.801 / 0.800 | 0.704 / 0.784 |
| layers 30–32 flattened | **0.705 / 0.756** | **0.678 / 0.728** |
| layers 33–35 flattened | 0.772 / 0.796 | 0.724 / 0.742 |
| layers 36–38 flattened | 0.837 / 0.875 | 0.758 / 0.795 |
| layers 39–42 flattened | 0.856 / 0.891 | 0.786 / 0.822 |
| 0.5 mm high-pass | 0.846 / 0.856 | 0.768 / 0.819 |
| pixels shuffled within 75 µm | **0.601 / 0.602** | **0.536 / 0.563** |
| pixels shuffled within 0.3 mm | 0.487 / 0.515 | 0.461 / 0.459 |

- The models read **fine texture**: destroy the structure inside 75 µm and most of the signal goes; inside 0.3 mm, all of it.
- They do **not** read slow brightness: a 0.5 mm high-pass changes nothing.
- The signal sits in the layers **just inside the written face** (stored 30–32, then 26–29 and 33–35); the outer layers
  36–42 hardly matter (flattening them even helps Reader v2 on w00).
- No hand-made texture measure captures it: the best single measure reaches AUC 0.56–0.58 (slightly more 20–40 µm band
  energy and a smaller share of horizontal fibre stripes on ink, in layers 26–32), and a logistic model on all of them,
  trained on one segment and tested on the other, reaches 0.60 and 0.57, against 0.82–0.86 for the models.

**What it means.** The ink shows up as a subtle change in the fine papyrus texture a few voxels under the written surface,
combined over space in a way simple measures do not reproduce. Two consequences:
- A render that is off the written face by a few voxels loses the signal, so depth (geometry) matters more than model
  choice; the depth sweep in every deep look stays.
- Synthetic letters painted with hand-made texture changes will probably not look like ink to the models. The first gate
  of `experiments/synthetic-letters` is to check whether the models respond to painted letters at all; learning the change
  from the model itself is the alternative.
