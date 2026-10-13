# An 8.64 µm ink model from PHerc. 343, v1: didn't work

**Idea.** Most public ink models were trained on other scans. A model fine-tuned on 8.64 µm text could see 8.64 µm ink
better. The only labelled native 8.64 µm text we had was Erwin Nieuwlaar's PHerc. 343 segment.

**What we tried** (2026-10-13; `runs/2026-10-13_model-8um/`):
- `build_dataset.py` takes the 343 render, 65 layers, in reverse order so that the reading side is the face the model
  learns. Its ink labels are the top 20 % of our five-model ensemble inside his letter boxes.
- We held out letters 1–6 for validation and trained on 8–13 and 15–18.
- Fine-tune from dense_native (`train_v1.json`: lr 1e-5, 3,000 steps, batch 32) on the home box, about an hour.
- `eval_8um.py` compares dense_native, the best checkpoint (step 250) and the last one. It scores AUC on held-out and
  training letters, and false alarms on six clean 9.36 µm crops and the w079 false-alarm crop.

**What it showed.**
- Held-out letters: 0.989 → 0.959 → 0.933 (dense_native, best, last). Worse.
- Training letters: 0.970 → 0.992 → 0.999. Memorised.
- Clean papyrus read as ink (≥ 0.5): 0.03–4.9 % → 2.4–10 % → 6–13.5 %. More false alarms.

**Why it failed.** Twelve letters is far too little. The labels were our own ensemble's guesses, so the model learned to
copy the ensemble on those letters, not to see ink.

**What would change it.** Real labels: strokes traced by people on 8.64 µm text, from published sources only. Until then
dense_native as it is beats our fine-tune.
