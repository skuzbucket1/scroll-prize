# Is our "reading side" the same face of the sheet as on the PHerc. 0343 control? (2026-10-10)

Why: our ink maps come in two sides per depth, "reading" (`_reverse`) and "blind", named after the PHerc. 0343 control,
where the letters are on the reading side at depth +1. The air-gap depth profile showed our renders sit on the sheet the
same way as the control (gap at d −5, sheet core at +3), but that profile cannot tell the inner face of a turn from the
outer face. If our fits had the faces swapped, text would land in the blind maps, which the flag rule does not look at.

Test (`box/bin/side_check.py`): at random interior nodes of a flattened winding, compute the grid normal, sample the CT
along +n and −n and correlate each with the render column (which sign the renderer's +layer direction follows), then
check whether that direction points toward or away from the scroll centre (umbilicus, or a circle fit to the mesh).

| mesh | nodes | render +layer = +n (CT correlation) | centre from | +layer points away from the centre |
|---|---|---|---|---|
| PHerc. 0343 control (Nieuwlaar's winning segment, w047–w048) | 16 | r 0.96 vs −0.09 | circle fit | 16 / 16 |
| PHerc. 0191 exp30k-z11200 w073 | 60 | r 0.94 vs −0.01 | umbilicus (circle fit agrees) | 60 / 60 |
| PHerc. 0813 exp30k-z12000 w088 | 60 | r 0.95 vs −0.03 | umbilicus | 60 / 60 |

Result: in all three the render's +layer direction points outward, and the air gap sits on the inner side (d −5), so the
mesh lies on the inner face of the sheet in every case: the face that carried the letters on PHerc. 0343 (and the face
written on in a rolled scroll). Our reading/blind assignment matches the control. The nulls are not a swapped-side artefact.
