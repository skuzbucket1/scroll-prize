#!/bin/bash
# Six-model agreement on the official human ink labels (Ted 2026-10-13 ~10:10 am CT: "yes - do that next", home box, free).
# Nine labelled segments from the open-data bucket (announced 2026-09-22): eight PHerc0139 windings (w030-w045; w047, our
# earlier 0139 control, has no labels) and PHerc0841's third labelled segment (auto_grown ...144552896). Each is cut to its
# labelled area (crop_control.py), its CT chunks fetched (fetch_mesh_chunks.py), rendered in 66 layers (render66.sh), inked
# at d +1 (GPU 2, after the PHerc1447 block), tiled from the labels (label_boxes.py: 300 px tiles
# with >= 15 % labelled ink = letter, tiles inside the mask with none = bare) and scored (model_agreement.py). Which models
# trained on which segment comes from the public model cards and training lists (scratch/credits/report.md, 2026-10-13):
# controls.tsv gives the models to run (Hecate is skipped where it trained) and the clean ones; clean ones decide, the rest
# give a seen-text upper bound. Six of the eight 0139 windings were seen by every model: upper bound only.
# 2026-10-13 11:10 CT: trimmed to the three held-out segments (controls.tsv; all nine in controls_all9.tsv) because the
# box CPU was overloaded and the six seen-by-every-model windings only give an upper bound.
# GPU stage on GPU 2 after the PHerc1447 ink-first block (INKFIRST1447-EXIT); GPU 0 is the other session's top30 run.
# Markers in run.log: CPU-DONE (all renders), AGREE-OFFICIAL-EXIT.
S=/home/tbienapfl/scroll-prizes; R=$S/runs/2026-10-13_agreement-official; PY=$S/villa/vesuvius/.venv/bin/python
K=/mnt/nvme/scroll-prizes/data/controls9um/official; C=/mnt/nvme2/scroll-prizes/controls/official; CTD=/mnt/nvme2/scroll-prizes/data/controls-ct
U=https://vesuvius-challenge-open-data.s3.amazonaws.com
mkdir -p $K $C $CTD; cd $R
log(){ echo "[$(date -Is)] $*"; }
tail -n +2 controls.tsv | while IFS=$'\t' read -r id vol mesh lab um models clean; do
  n=c${id/-/_}_66
  [ -f $K/$id/crop.json ] || nice -n 10 $PY -I $S/bin/crop_control.py $mesh $lab $K/$id --um $um > $R/crop_$id.log 2>&1
  log "$id crop: $(tail -1 $R/crop_$id.log)"
  grep -q FETCHMESH-EXIT $R/ct_$id.log 2>/dev/null || nice -n 10 $PY -I $S/bin/fetch_mesh_chunks.py $U/$vol $K/$id/mesh.tifxyz $CTD/$id.zarr 48 16 > $R/ct_$id.log 2>&1
  log "$id CT: $(tail -2 $R/ct_$id.log | head -1)"
  [ -d $C/$n.zarr/0 ] || CT=$CTD/$id.zarr nice -n 10 bash $S/bin/render66.sh $K/$id/mesh.tifxyz $C/$n.zarr 6 12 > $R/render_$id.log 2>&1
  log "$id render: $(tail -1 $R/render_$id.log)"
done
log CPU-DONE
until grep -q INKFIRST1447-EXIT $S/runs/2026-10-13_inkfirst-1447/results/progress.log 2>/dev/null; do sleep 120; done
log "GPU stage starts on GPU 2"
tail -n +2 controls.tsv | while IFS=$'\t' read -r id vol mesh lab um models clean; do
  n=c${id/-/_}_66; M=$R/maps_$n; mkdir -p $M
  [ -d $C/$n.zarr/0 ] || { log "$id: no render, skipped"; continue; }
  (cd $S/villa/vesuvius && CUDA_VISIBLE_DEVICES=GPU-7937f33e-73c8-2a4f-d7c6-9c4c3c20c74f TORCHDYNAMO_DISABLE=1 \
     CKPT_DIR=$S/checkpoints/ckpt343 PY=$PY HECATE_PY=$S/checkpoints/ckpt343/hecate.py PREP_PY=$S/bin/ink343/hecate_prep.py \
     N_LAYERS=66 NATIVE_UM=$um VILLA_BATCH=16 HEC_BATCH=8 HEC_DEVICE=cuda TMPDIR=/mnt/nvme/scroll-prizes/tmp \
     MODELS="${models//,/ }" \
     bash $S/bin/ink343/run_depth_sweep.sh $C/$n.zarr $M 1 1 < /dev/null > $R/sweep_$n.log 2>&1)
  $PY -I $S/bin/label_boxes.py $K/$id/labels.zarr $K/$id/supervision.zarr $C/$n.zarr $um $R/boxes_$n.json >> $R/boxes.log 2>&1
  nice -n 5 $PY -I $S/bin/model_agreement.py $C/$n.zarr $M $n 1 $R/agree_${n}_d1.tsv --boxes $R/boxes_$n.json \
    --bare $R/boxes_$n.bare.json --models $models --label $n >> $R/agreement.log 2>&1
  log "$id agreement: $(grep -c . $R/agree_${n}_d1.tsv 2>/dev/null) tiles"
done
log AGREE-OFFICIAL-EXIT
