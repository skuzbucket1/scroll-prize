# Damage map (3D): didn't work

**Idea.** Maybe the damage behind a false alarm is invisible on the flattened sheet but plain in 3D: a crack running
across several sheets, or crushed papyrus where the layers lose their order.

**What we tried** (2026-10-13; `damage3d.py`, `damage3d_project.py`; runs in `runs/2026-10-13_damage3d/`):
- A structure tensor of the CT at level 2 of the PHerc0813 z12000 band gives sheet planarity, radial alignment, darkness
  and a cross-sheet crack measure.
- Each field is sampled along the line through every mesh node (±1.5 mm), per 1.5 mm tile.
- v0 took the sheet normal as radial. In a crushed scroll that is often wrong (median alignment 0.74).
- v1 projects along each mesh's own normal.

We compared the hot tiles with the rest of each winding, and the eight known false alarms with their windings.

**What it showed** (v1, scores for hot tiles against the others):
- crack column 0.52, dark column 0.55, crack run 0.55, disorder 0.38, planarity 0.63, alignment 0.64.
- So the hot tiles sit on *flatter, better aligned, less cracked* papyrus than the rest.
- The eight false alarms sit at the 0th–31st percentile for cracks, and the 55th–70th for planarity.
- Sections through w110 show stacked, ordered sheets, so the geometry under the flags is fine.

**Why it failed.** The false alarms are not on 3D damage either. If anything they are on the cleanest papyrus. There is
no known text in this band, so this tests only the false alarms, not what damage does to real letters.

**What would change it.** Nothing we know of. Damage does not explain our false alarms.
