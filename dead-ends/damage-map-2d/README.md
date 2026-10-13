# Damage map (2D): didn't work

**Idea.** Most of our false alarms looked like they sat on cracks, holes and torn sheet edges. A per-tile damage map of
each winding would let us search the clean papyrus first and discount flags that fall on damage.

**What we tried** (2026-10-13, `damage_map.py`; runs in `runs/2026-10-13_damage-map/`, outputs on the box):
- v1 marks holes as dark in at least 7 of 9 sheet layers, opened by 0.1 mm and at least 0.05 mm². It marks cracks as
  black-hat lines at least 0.3 mm long, per 1.5 mm tile.
- v2 marks holes as a dark surface layer, opened.

We tested both on PHerc. 343 (letter boxes), on PHerc0841 ag2814 and w00 (human labels), and on 150 null windings from
PHerc0813 z12000 and PHerc0191 z11200.

**What it showed.**
- The hot tiles on null windings are not on damage: AUC 0.47–0.59 on every measure, about chance.
- The eight flags we had already judged false alarms sit at the 37th–55th percentile of their winding on every damage
  measure. They are ordinary papyrus by this map.
- Masking out the damage removes half the area and moves the hot rate only from 4.7 % to 4.6 %.
- v2 gives the same answer.

**Why it failed.** Our false alarms are not mostly on damage that a 2D map can see. Bright marks along cracks are there,
but the crack itself is not what makes a tile hot.

**What would change it.** Nothing obvious in 2D. The 3D version is in `../damage-map-3d` and also came out null.
