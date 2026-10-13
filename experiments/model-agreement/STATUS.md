# Six-model agreement: in test

**Question.** Real letters light up in every ink model, but our false alarms (cracks, holes, bright zones) light up in
only one or two. If at least five of the six models agree that a spot is one-sided, with the reading side brighter than
the blind side, is that a filter we can trust before spending hours on a deep look?

**Code.** `model_agreement.py` takes a render, its ink maps and tiles (letter boxes, bare-papyrus boxes or a window), and
counts how many models are one-sided in each tile. `--relative` takes out a render-wide offset between the two faces.
The runs are in `runs/` (outputs on the box under `~/scroll-prizes/runs/<same name>/`).

**Numbers so far** (a tile counts when at least five of the six models agree):

- PHerc. 343, 8.64 µm: 78 % of its 18 letters, 10 % of its bare papyrus, 25 % of the PHerc0813 w079 false alarm.
- Clean 9.36 µm papyrus on PHerc0813 and PHerc0191 (six crops, depths 0 to +2): 2 of about 129 tile-depths (1.6 %).
- PHerc0841 segment w00, human-labelled text: 78 % of letter tiles (67 % with `--relative`).
- PHerc0841 segment ag2814, human-labelled text: **0 %**, with or without `--relative`. Its blind face is brighter
  everywhere, and its letters are not one-sided in most models.
- PHerc0139 w047 (letter tiles from the 2.4 µm reference): running on 2026-10-13, result due late morning CT.

**What decides it.** If PHerc0139's letters pass at a rate like w00 and 343, agreement becomes a filter in triage: deep
looks only where at least five of six agree. Running it over the top-ranked windows would be about 5–6 hours on two home
GPUs. If 0139 fails too, the rule only works on some text, and it moves to `dead-ends/`.

**Caveat.** Hecate may have been trained on PHerc0841, so the 0841 numbers are also given without it.

Site: https://skuzbucket1.github.io/scroll-prize/#run-model-agreement
