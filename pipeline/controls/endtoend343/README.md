# End to end on PHerc. 343: our whole pipeline on known letters

Status: works (2026-10-14). Site: https://skuzbucket1.github.io/scroll-prize/#run-control343-endtoend

Our recipe from scratch on z 9,300–11,300 of PHerc. 343 (8.64 µm): centre (VC3D vc_gen_umbilicus + smooth_umbilicus.py),
sheet tracks with the organisers' PHerc0813 parameters, the exp-30k spiral fit, Nieuwlaar's snap, Lasagna flatten. Then
Erwin Nieuwlaar's 18 First Letters letters, placed in 3D from his published segment (`letters3d.npz`, from
`experiments/ink-first`'s letters_to_3d.py), are matched to our windings (`letters_on_windings.py`: within 4 voxels along the
normal and 15 in-plane), the windings that carry them are read with Reader v2 + d9v4C at d 0 and +1, and the letter areas are
scored against the rest of each winding on both faces (`letters_eval.py`).

- `launch_aws.sh`: one AWS GPU worker (infra/aws), pushes the scripts, runs `control_job.sh`, fetches, terminates.
- `control_job.sh`: on the worker, inputs from S3 → centre → tracks → fit → snap → flatten → letters on our windings → read →
  eval. Marker CONTROL-EXIT.

Result (one NVIDIA L4, about 3.6 h): all 18 letters on our windings w047–w050 (median 0.7 voxel from our surface); AUC 0.78
(Reader v2) and 0.74 (d9v4C) on w047, 0.73 and 0.71 on w048, lower on the other face.
