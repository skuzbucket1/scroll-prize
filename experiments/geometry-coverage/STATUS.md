# How much of a band is really new sheet? In test

**Question.** Reviewing the tall band, we found PHerc0813 windings w082–w084 lying on one sheet, 0.06–0.08 mm apart with
identical CT. If the fit often stacks windings like that, part of what we counted as searched is the same papyrus two or
three times, and the sheets in between were never searched.

**Code.** `geometry_coverage.py` takes every node of every flattened winding of a fit and finds the nearest node of any
other winding. Under 0.03 mm along the normal (about three voxels) the two windings sit on the same sheet there. It
reports, per winding and per fit, the duplicated share and the area on sheets no earlier winding covers. `coverage_view.py`
draws the check on a CT slice: overlapping dots on one bright band mean two windings share a sheet.

**First numbers** (2026-10-13; outputs on the box in `~/scroll-prizes/runs/2026-10-13_coverage/`):

- PHerc0191 z11200: 100 windings, 852 cm², 78 % on sheets no other winding covers
- PHerc0813 z12000: 80 windings, 860 cm², 80 %
- PHerc0813 z10500: 76 windings, 2,108 cm², 77 %
- PHerc0813 z8000: 76 windings, 2,022 cm², 76 %

So roughly a fifth of the fitted area repeats a sheet that another winding already covers. These numbers have not yet
been checked by eye (the two `view_*.jpg` pictures).

**What decides it.** If the pictures confirm it, the search counts only unique area, triage stops reporting the same
sheet twice, and the sheets between stacked windings become a target for new geometry. If they don't, the threshold is
wrong and we adjust it.
