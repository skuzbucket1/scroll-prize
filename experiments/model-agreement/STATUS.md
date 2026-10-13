# Six-model agreement: in test

**Question.** Real letters light up in every ink model, but our false alarms (cracks, holes, bright zones) light up in
only one or two. If at least five of the six models agree that a spot is one-sided, with the reading side brighter than
the blind side, is that a filter we can trust before spending hours on a deep look?

**Code.** `model_agreement.py` takes a render, its ink maps and tiles (letter boxes, bare-papyrus boxes or a window), and
counts how many models are one-sided in each tile. `--relative` takes out a render-wide offset between the two faces.
`label_boxes.py` makes letter and bare tiles from human labels; `crop_control.py` cuts a labelled segment to its
labelled area. The runs are in `runs/` (outputs on the box under `~/scroll-prizes/runs/<same name>/`).

**Numbers so far** (a tile counts when at least five of the six models agree):

- PHerc. 343, 8.64 µm: 78 % of its 18 letters, 10 % of its bare papyrus, 25 % of the PHerc0813 w079 false alarm.
- Clean 9.36 µm papyrus on PHerc0813 and PHerc0191 (six crops, depths 0 to +2): 2 of about 129 tile-depths (1.6 %).
- PHerc0841 segment w00, human-labelled text: 78 % of letter tiles (67 % with `--relative`).
- PHerc0841 segment ag2814, human-labelled text: **0 %**, with or without `--relative`. Its blind face is brighter
  everywhere, and its letters are not one-sided in most models.
- PHerc0139 w047 (139 letter tiles from the 2.4 µm reference; five models, d9v4C trained on this segment and is left
  out): at least four of five agree on **78 %** of letter tiles (all five on 58 %), on 21 % of the other papyrus (which
  may hold faint text the reference misses).

**Where it stands (2026-10-13, 10:20 am CT).** Three of the four known-text sets pass at the same rate (78 %: PHerc. 343,
PHerc0841 w00, PHerc0139 w047), against 0–2 % on clean papyrus and 25 % on our best-looking false alarm. One fails
(PHerc0841 ag2814, 0 %). So the rule catches most text and rarely fires on bare papyrus, but it can miss a whole segment.
As a filter it can set the order of deep looks; it must not veto one.

**Next.** Nine more labelled segments from the official ink labels (eight PHerc0139 windings, a third PHerc0841 segment;
`runs/2026-10-13_agreement-official/`, cut to their labelled areas by `crop_control.py`) say how often a segment fails
like ag2814 does. Then, if it still holds: agreement over the top-ranked windows of our searched bands (about 5–6 hours on
two home GPUs) to order the deep looks.

**Caveat.** Hecate may have been trained on PHerc0841, so the 0841 numbers are also given without it.

Site: https://skuzbucket1.github.io/scroll-prize/#run-model-agreement
