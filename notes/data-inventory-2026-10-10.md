# Data inventory, 2026-10-10

Raw listing behind `docs/DATA_DICTIONARY.md`. Taken read-only on 2026-10-10 between 00:40 and 01:30 UTC with
`du -h --max-depth=N` (sizes in GiB/MiB as `du` prints them) and `ls`. Zarr stores were not opened beyond
`.zarray`/`.zattrs`/`.zgroup`, so their file counts are given only where a job log reported them.
Repeated items are collapsed into patterns: `wNNN` = 3-digit winding index, `TS14` = 14-digit timestamp,
`d+NN` = signed depth, `sNN` = first layer of a 17-layer ink window.

Jobs running at the time: new-fitter spiral fit `exp30k-z11200` (GPU 3, started 00:30 UTC) and old-fitter fit
`old-phase-30k` (GPU 0, running for 8 h 15 min). No ink, render or flatten process was running at 00:50 UTC.

Flags used below: `[DUP]` duplicate of another item, `[ORPHAN]` left over from a finished or killed job,
`[PARTIAL]` incomplete by design or by failure, `[TEMP]` temporary/working copy, `[NAME]` naming or placement
problem, `[RUNNING]` written by a job that is still running.

## 1. GPU box `llm`, NVMe `/mnt/nvme` (938 G, 840 G used, 89 G free)

```
/mnt/nvme/
├── scroll-prizes/                        ~812 G   (= ~/scroll-prizes)
│   ├── data/                              738 G   see 1.1
│   ├── cache-root/                         30 G
│   │   ├── uv/                             24 G   uv package cache (archive-v0 24 G, builds/sdists/simple/wheels <100 M)
│   │   │                                          ~/.cache/uv on the root disk is a symlink to here. The project .venv
│   │   │                                          files are copies (link count 1), not hardlinks into this cache.
│   │   └── torchinductor/                 6.2 G   PyTorch compile cache: fxgraph 3.1 G, triton 2.9 G, aotautograd 81 M,
│   │                                              plus ~1,000 two-character hash dirs
│   ├── villa/                              29 G   clone of ScrollPrize/villa, branch fix/install-volcomp @ 12f21236a,
│   │   │                                          3 modified tracked files + 1 untracked dir
│   │   ├── .git/                          1.0 G   (shared by the 4 worktrees in wt/)
│   │   ├── spiral-fitting/.venv/          8.0 G
│   │   ├── vesuvius/.venv/                6.9 G
│   │   ├── lasagna/.venv/                 6.4 G
│   │   ├── volume-cartographer/build/     4.9 G   VC3D build tree (binaries installed to ~/.local/bin on the root disk)
│   │   ├── scrollprize.org/               617 M   (static 614 M)
│   │   ├── lasagna/torchinductor_tbienapfl/ 129 M  [TEMP][NAME] compile cache written inside the repo (untracked)
│   │   └── deprecated, foundation, segmentation, ink-detection, dinovol, scripts   ~215 M
│   ├── wt/                                9.5 G   git worktrees of villa
│   │   ├── spiral-0fb38c45/               6.9 G   pre-simplification fitter; volume-cartographer/.venv 6.1 G;
│   │   │                                          1 modified file (scripts/spiral/fit_spiral.py)  [RUNNING: old-phase-30k]
│   │   ├── fiber-lasagna-import/          890 M   detached @ 6222bbb8b, clean (staged PR)
│   │   ├── shell-confidence/              891 M   detached @ eec8eda20, clean (staged PR)
│   │   └── track-cache-signature/         889 M   detached @ 9c41cb9f5, clean (staged PR)
│   ├── checkpoints/                       2.8 G   70 files
│   │   ├── hecate/                       1001 M   hecate_9.6um.pth, hecate_2.4um.pth (522 M each), hecate.py, assets/, README, LICENSE
│   │   ├── lasagna-fiber/                 539 M   s1a_128_2_single_8x8_..._best_25_9k.pt (344 M) + 5scroll_..._ema_20260915_212757/ (211 M)
│   │   ├── dense_native/                  527 M   weights/{dense_native_016000,soup42_last4}.safetensors (273 M each), eval/training files
│   │   ├── ink_9um/                       396 M   hybrid_3d2d-seed42/{step-040000,step-075000}.pth, hybrid_3d2d-seed43/step-075000.pth (138 M each)
│   │   ├── ckpt343/                       261 M   dense_native-016000.pth (273 M, rebuilt from safetensors) + 4 symlinks into hecate/ and ink_9um/
│   │   └── winding_model_9um/             140 M   ckpt_final.pth, config.json, metrics.jsonl
│   ├── tmp/                               1.8 G   TMPDIR of all ink jobs                                      [TEMP]
│   │   ├── run_ink.XXXXXX/  × 6           932 M   leftovers of killed run_ink.sh calls (prep.zarr, hecate-*, torchinductor) [ORPHAN]
│   │   ├── appimg/                        486 M   vc3d.AppImage + squashfs-root/ (366 M), test of the AWS render path   [ORPHAN]
│   │   ├── torchinductor_tbienapfl/       216 M   compile cache (still written by jobs)
│   │   ├── flag/                          141 M   43 files: 21 ensemble/ct PNGs of w083/w090/w100–w102 (copies of Mac run2
│   │   │                                          results) + 22 review JPGs v_*/m_* (also on the Mac in data/strokes)  [DUP]
│   │   ├── t343/, w072/, win/             0.4 M   superseded stroke-score test outputs (old format)                [ORPHAN]
│   │   ├── patch6.py patch7.py patch8.py airprof.py profile.py permodel.sh win.sh threem-list.txt
│   │   │                                          ad hoc scripts; permodel.sh produced the data/strokes/*_pm_* files   [NAME]
│   │   └── w073_ens_d+0{0,1}_{0,1}.jpg × 4  0.5 M  review crops                                               [TEMP]
│   ├── runs/                              1.1 G   day-1 smoke tests (83 files + 2 zarr)
│   │   ├── 20231016151002-2.4um-g2-28-crop1/    414 M   render.zarr, vc_render.log
│   │   ├── 20231016151002-2.4um-g2-28-crop1b/   495 M   render.zarr 473 M, pred_s42-075k[_reverse][_preview-ds2].tif, render_z14_preview-ds2.tif
│   │   ├── 20231016151002-7.91um-ink9um-s42-075k/ 129 M pred[_reverse][_preview-ds8].tif
│   │   └── PHerc0800-ink9um/               88 M   72 files: 6 segments × {seed42-40000, seed42-75000, seed43-75000} × {fwd, _reverse} × {full, _preview-ds2}
│   ├── cache/                              20 K
│   │   ├── spiral/                        8 K     patches-<hash>_lines_v3_full_res_v1_slices-<hash>.pkl (fitter cache)
│   │   ├── spiral-old/                    empty   (old-fitter cache dir)
│   │   └── PHerc0343-l0/                  empty   passed to vc_render_tifxyz as --volume cache, never filled          [NAME]
│   ├── bin/                               528 K   ~60 scripts + ink343/ (third-party, 11 files) + __pycache__/; snap_newband.sh was
│   │                                              added during the listing; the Mac copy box/bin was in sync at the end
│   ├── build-vc3d.sh                              build script at the top level instead of bin/                     [NAME]
│   └── *.log  × 105                       2.0 M   job logs, one per job (see 1.2)
├── vc3d-remote-cache/                      29 G   VC3D remote-chunk cache, outside the project tree                  [TEMP]
│   ├── 20250821151635-9.362um-1.2m-113keV-masked.zarr-91d4e1ea37591385/   23 G  PHerc0191 CT (level_0 21 G); same chunks as the local mirror [DUP]
│   ├── 20250521140437-8.640um-1.2m-116keV-masked.zarr-597ee6d5b5abcada/  4.2 G  PHerc0343 CT chunks (control render)
│   ├── 20260411134726-2.400um-0.2m-78keV-masked.zarr-34348b309d65399c/   2.4 G  PHercParis4 2.4 µm level 2 (day-1 crop renders)
│   ├── 20250821151635-surface-...-m7-L0-th0.2.zarr-ac3e0d1c84f9dcc6/      42 M  m7 surface prediction (tracer runs)
│   └── .<store>.vc_cache.lock × 3
└── lost+found/
```

Root disk (107 G, 64 % used), for reference only: `~/.local` 1.5 G (VC3D binaries, uv-managed Python), `~/.triton` 34 M,
`~/.cache/uv` → symlink to `cache-root/uv`. Old helper scripts in `~` (`migrate_nvme.sh`, `sweep_pherc0800.sh`, logs) are outside the project.

### 1.1 `data/` (738 G)

```
data/
├── PHerc0191/                                                     732 G
│   ├── volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr/    410 G   OME-Zarr v2, levels 0–5 (353 G, 49 G, 7.3 G, 1.3 G, 269 M, 45 M),
│   │                                                                      209,814 objects (mirror log), uint8, 128³ chunks, uncompressed;
│   │                                                                      metadata.json (ESRF scan record), .zattrs, .zgroup
│   │   └── .dl_cache/0.level.lock                                    0    stray lock from a VC tool                          [ORPHAN]
│   ├── winding/band9000-10000/                                    108 G
│   │   ├── winding_native_phase_ws8_ss96.zarr/                    104 G   winding-model native-phase cache, 7,102 slabs, complete
│   │   ├── smoke.zarr/                                            3.7 G   smoke-test cache                                     [ORPHAN]
│   │   ├── smoke.tmp/ (1.3 M), winding_native_phase_ws8_ss96.tmp/ (468 K)                                                   [ORPHAN]
│   │   └── band_ws8_ss96.log, export_ws8_ss96.log, smoke_bs2.log, band_vram.txt, smoke_bs2_vram.txt
│   ├── render66/                                                   92 G   198 entries
│   │   ├── exp30k_snapped_wNNN_66.zarr/  × 99                    89.8 G   w020–w119 without w116; 0.27–1.60 G each; array "0" (66, H, W)
│   │   │                                                                  uint8 blosc-lz4, chunks (66,128,128), plus pyramid levels 1–5
│   │   ├── lasagna150_66.zarr/                                    3.5 G   render of the 150-generation tracer patch
│   │   └── render_wNNN.log  × 98                                          (w070 has none; its log is ~/scroll-prizes/render66-w070.log) [NAME]
│   ├── lasagna/20250821151635-lasagna-20260419180421/              35 G
│   │   ├── PHerc0191_{nx,ny,grad_mag}.ome.zarr/                  18.1 G   community Lasagna normals + gradient magnitude, levels 2–4 only,
│   │   │                                                                  .mirror-listing.json each (nx: 273,057 objects)          [PARTIAL]
│   │   ├── PHerc0191_nx.ome.zarr.respool_g2_pair/                  12 G   resident-pool sidecar (nx+ny), no CT mask, built by the pilot fit
│   │   ├── PHerc0191_grad_mag.ome.zarr.respool_g2/                5.6 G   same for grad_mag
│   │   ├── *.respool_g2*.lock × 2                                    0                                                       [ORPHAN]
│   │   └── PHerc0191.lasagna.json                                         Lasagna manifest (also lists a cos group that was not mirrored)
│   ├── spiral-dataset/                                             23 G   fitter dataset (spiral-scroll.json)
│   │   ├── lasagna_inputs/                                         17 G
│   │   │   ├── PHerc0191_{nx,ny,grad_mag}.ome.zarr -> ../../lasagna/<id>/…   symlinks
│   │   │   ├── PHerc0191_nx.ome.zarr.respool_g2_pair/              12 G   CT-masked sidecar from assemble_pherc0191.sh; the fitter resolves the
│   │   │   └── PHerc0191_grad_mag.ome.zarr.respool_g2/            5.6 G   symlinks and uses the copies under lasagna/ instead       [DUP]
│   │   ├── tracks -> ../spiral/20250821151635/tracks                      symlink
│   │   ├── outer_shell/                                           160 M   tifxyz-like (x/y/z.tif, meta.json, shell_stats.json); full-scroll dz=1
│   │   ├── outer_shell_dz1/                                       160 M   identical to outer_shell (x.tif and shell_stats.json match)  [DUP]
│   │   ├── outer_shell_band8500-10500/ (17 M), outer_shell_dz8/ (20 M), outer_shell.v0/ (20 M, superseded)                   [NAME]
│   │   ├── surf_sdt_band9000-10000.ome.zarr/                      1.4 G   surface SDT, levels 1–3, working-z range only            [PARTIAL]
│   │   ├── surf_sdt_band9000-10000.ome.zarr.respool_g1/           4.6 G   its sidecar (old fitter)                                [RUNNING]
│   │   ├── surf_sdt_band9000-10000.ome.zarr.done_tiles.json, .respool_g1.lock
│   │   ├── winding_inference/                                     1.1 M   manifest.json, shard_0/, shard_1/ (winding-model supervision)
│   │   └── umbilicus.json, umbilicus_raw.json, umbilicus_estimates.csv, spiral-scroll.json
│   ├── spiral/20250821151635/tracks/                               21 G   PHerc0191_20250821151635_surface_m7_L0_th0.2.{dbm (9.9 G),
│   │                                                                      dbm.crossings.npz (2.4 G), dbm.vctracks/ (~8.7 G), extract.json}
│   ├── spiral-output/                                              11 G   11 run dirs, 9,314 files
│   │   ├── 2026-10-08_PHerc0191_slice-9000-10000_0-patch_pilot-z9000-10000/  1008 M
│   │   ├── 2026-10-09_PHerc0191_slice-9000-10000_0-patch_<tag>/  × 9   986 M–1.1 G each; tag ∈ exp-30k, exp-dirlow, exp-dirlow2, exp-dr32,
│   │   │                                                                  exp-shell105, exp-shell105b, exp-track2x, exp-wm, exp-wm2
│   │   └── 2026-10-10_PHerc0191_slice-11200-12200_0-patch_exp30k-z11200/   933 M                                       [RUNNING]
│   │       per run: checkpoint_fitted.ckpt (~933 M), meshes/fitted_<tag>/{wNNN_<tag>, wNNN_spliced_<tag>} (tifxyz; 120 + 120 for exp-30k,
│   │       63 M), satisfaction_metrics_fitted.json, satisfied_fitted.json, mesh_in_mask.json, non_liftable_patches.txt,
│   │       spiral_on_{patches,tracks}_sNNNNN_fitted.png × 20 each (11 M)
│   ├── spiral-output-old/2026-10-09_..._0-patch_old-phase-30k/      empty   [RUNNING] output appears when the old-fitter run ends
│   ├── spiral-dataset-old/                                         44 K   symlink farm for the old fitter + its spiral-scroll.json (adds surf_sdt)
│   ├── fiber/                                                      11 G
│   │   ├── band8500-10500/                                        3.5 G   fiber_{nx,ny,presence}.ome.zarr (0.79–0.94 G), dirfield.zarr (965 M;
│   │   │                                                                  x,y symlinks + z), fiber.lasagna.json, inference.json, infer.log,
│   │   │                                                                  infer-attempt1.log
│   │   └── dirfield_lasagna.zarr/                                 6.8 G   x, y (symlinks to Lasagna nx/ny), z (6.8 G)
│   ├── normal-grids/                                              5.6 G   metadata.json + xy/ 18,977 × NNNNNN.grid (one per z slice)
│   ├── grow-test/                                                 5.2 G   tracer (vc_grow_seg_from_seed) tests, 200 files + 8 zarr
│   │   ├── out/, out2/, out3/, out_ct/                            ~4 M    1 × auto_grown_<TS17> tifxyz each (out_ct empty-ish)
│   │   ├── qa/ (866 M), qa2/ (698 M), qa_ct/ (8 K)                        render zarr + ink tifs + previews per patch
│   │   ├── dirfield/                                              28 K    first direction-field attempt (failed)                  [ORPHAN]
│   │   ├── dirfield2/                                             3.7 G   out_<v>/ + qa_<v>/ + params_<v>.json + grow_<v>.log for
│   │   │                                                                  v ∈ 70, 150, ct70, lasagna70, lasagna150, ng70, ng100w3
│   │   └── params.json, params70.json, seeds3.txt, grow.log, grow2.log, grow3.log, grow_ct.log, grow150.log
│   ├── surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr/  5.0 G   level 0 (4.4 G; z chunk rows 46–52 and 57–65),
│   │                                                                      level 1 (653 M; rows 22–27), .zattrs, .zgroup        [PARTIAL]
│   ├── ink-triage/                                                3.4 G   104 entries, 908 files
│   │   ├── maps/                                                  2.0 G   333 entries: exp30k_snapped_wNNN_66__<model>__L66s<s>[_reverse].tif
│   │   │                                                                  and __hecate__L66zc<zc>[_reverse].{png,json}; logs/ (9 files)
│   │   │     hybrid_3d2d-seed42: 29 windings (w033–w036, w060–w080, w103–w106); s25 × 29, s26 × 28, s27 × 21, s24 × 20
│   │   │     hybrid_3d2d-seed43, dnative: 12 windings (w033–w036, w068–w072, w103–w105), s25–s26
│   │   │     hecate: 5 windings (w068–w072), zc32.50 and zc33.50
│   │   ├── ensemble/wNNN/  × 5 (w068–w072)                        528 M   four-model ensemble images (22 PNG + stats.json + ensemble.log each)
│   │   ├── ensemble3/wNNN/ × 7 (w033–w036, w103–w105)             650 M   three-model ensemble images                          [NAME]
│   │   ├── previews/                                              224 M   20 × {wNNN_d{-1,+0,+1,+2}_{read,blind}.png (8), wNNN_done}
│   │   ├── claims/wNNN × 21, claims3/wNNN × 9                    244 K   work-claim marker dirs (file "gpu"); claims3/w032 and w106 are
│   │   │                                                                  stale (job stopped at 00:27), they make a rerun skip them [ORPHAN]
│   │   └── wNNN_dN.log × 84, three_wNNN.log × 9, ensemble_wNNN.log × 5
│   ├── flatten/                                                   1.9 G   110 entries, 1,983 files
│   │   ├── exp-30k-snapped-wNNN/  × 100 (w020–w119)              1.88 G   tifxyz/flatten.tifxyz/{x,y,z.tif, meta.json, model.pt}, model_final.pt
│   │   │                                                                  (1.6 M), model_snapshots/ (10 × model_stage0_NNNNNN.pt, 16 M),
│   │   │                                                                  flatten.log, flatten_input.json. All model_snapshots: 1.6 G.
│   │   │     exp-30k-snapped-w116: flatten failed (rc 1), no tifxyz, 2.7 M                                               [ORPHAN]
│   │   ├── community-snapped-wNNN/ × 10 (w000–w009)               ~10 M   same layout
│   │   └── lasagna150/                                             61 M   same layout
│   ├── winding-qa/{exp-30k,exp-wm}/                               865 M   2 windings each (w040, w070): wNNN.zarr, wNNN_render_z14_ds2.tif,
│   │                                                                      wNNN_ink_seed4{2,3}-75000[_reverse][_preview-ds2].tif, .err, .render.log
│   ├── pilot-qa/                                                  794 M   w040, w070, w100: .zarr (141–347 M), wNNN_seed4{2,3}-75000[...].tif,
│   │                                                                      .err, .render.log, wNNN_render_z14_ds2.tif
│   ├── sweeps/                                                    474 M   paused depth sweeps                                    [PARTIAL]
│   │   ├── exp30k_snapped_w070/                                   236 M   villa models s23–s27 (d −2..+2), hecate zc31.50/32.50; logs/
│   │   │                                                                  (timings.tsv), images_early/ (53 M)
│   │   └── lasagna150/                                            239 M   seed42 s24–s25, seed43 s25, dnative s24–s25; logs/
│   ├── snapped/                                                   437 M   472 files + 2 zarr
│   │   ├── exp-30k/                                                27 M   100 × wNNN_exp-30k/ (tifxyz) + windings.txt, snap_report.tsv, snap.log
│   │   ├── community/                                             324 K   10 × wNNN/ (tifxyz) + windings.txt, snap_report.tsv, snap.log
│   │   ├── qa_exp-30k_w040_exp-30k/ (151 M), qa_exp-30k_w070_exp-30k/ (259 M)   render.zarr, ink tifs, selfcross.json       [NAME]
│   ├── triage/previews/                                           202 M   99 × wNNN_ct_d0.png
│   ├── aws-maps/{w073,w074}/                                      188 M   20 maps each, copied from fleet run 1 for scoring     [DUP]
│   ├── aws-ens/{w073,w074}/                                       167 M   12 and 24 ensemble images, copied from fleet run 1     [DUP]
│   ├── bench1660/                                                 5.7 M   GTX 1660 SUPER benchmark: w040_seed42-75000{,_fp32,_ctrl3060}[_reverse].tif + 3 logs
│   ├── community-fit/                                             312 K   10 × wNNN/ (tifxyz, z 11600–12400; third-party fit)
│   └── mirror-*.log × 9, tracks-download.log                              download logs at the dataset root                       [NAME]
├── PHerc0343/control/                                             1.1 G   49 files + 1 zarr
│   ├── concat_w047-w048_R5B2_z9500-11000.tifxyz/                 528 K   Nieuwlaar's published winning mesh
│   ├── control343_66.zarr/                                        905 M   66-layer render
│   ├── maps/                                                       74 M   16 files: seed42 s24–s27, seed43 s26, dnative s26 (pairs), hecate zc33.50 (pair + json)
│   ├── images/                                                     47 M   ensemble images at d+01 + control343_66__stats.json + ensemble.log
│   ├── preview_d{-1,+0,+1,+2}_{read,blind}.png × 8
│   └── render.log, ink_d{-1,0,1,2}.log, ink_{dnative,hecate,hybrid_3d2d-seed43}_d1.log
├── PHerc0800/segments/                                            665 M   6 × <TS14>-auto_grown_<TS17>/surface-volumes/
│                                                                          8.64um-1.2m-116keV-volume-20250521135224.zarr (31 layers, levels 0–5; 31–163 M each)
├── PHercParis4/segments/20231016151002/                           4.6 G   mesh/ (3 tifxyz: -on-20260411134726-2.4um, -on-20230205180739-7.91um,
│                                                                          -on-20260310170716-45.532um), surface-volumes/7.91um-54keV-volume-20230205180739.zarr
└── strokes/                                                       355 M   638 files
    ├── wNNN/  × 23 (w036, w060–w080, w103)                        290 M   6–40 files each: exp30k_snapped_wNNN_66__strokes[_tag]_d+NN.{json,png},
    │                                                                      ..._d+NN__top0{1,2,3}.png, exp30k_snapped_wNNN_66__valid.png;
    │                                                                      tags: none (four models), _s42, _3m, _s4243, _pm                [NAME]
    ├── box3m/wNNN/ × 7 (w033–w036, w103–w105) + errors.log         45 M   11 files each, three models but no tag                  [NAME]
    ├── aws/{w073,w074}/                                            12 M   13 files each (four models, no tag; plus _pm)
    ├── c343/                                                      7.5 M   13 files: control343_66__strokes{,_s42,_3m,_s4243}_d+01...
    ├── ranking.tsv                                                        97 rows (control + PHerc0191; sets s42 and ens4)
    └── rank-errors.log, rank-force.log, rank-last.log
```

### 1.2 Top-level job logs (105 files, 2.0 M)

| pattern | count | what |
|---|---|---|
| `fit-<tag>.log`, `fit-<tag>-full.log` | 12 tags × 2 | spiral fits: summary (overrides, metrics, FIT-EXIT) and full stdout |
| `fit-*-attemptN[-oom][-full].log` | 7 | failed attempts of old-phase-30k |
| `pilot-fit[-full].log`, `pilot-qa.log` | 3 | pilot fit and QA |
| `hf-*.log` | 6 | checkpoint downloads from Hugging Face |
| `dl-*.log`, `mirror-surf-*.log`, `villa-clone.log` | 6 | downloads (`tracks-download.log` and the CT/Lasagna/normal-grid mirror logs are in `data/PHerc0191/`) |
| `render*.log`, `infer-*.log`, `flatten-*.log`, `sweep-*.log` | 12 | renders, inference, flattening, sweeps (`sweep-lasagna150-gpu0.log` is empty) |
| `winding-*.log`, `queue-*.log`, `export-help.log` | 7 | winding model |
| `tracer-*.log`, `grow-qa.log`, `patch-qa*.log`, `mesh-audit*.log`, `dirfield-*.log`, `fiber-*.log` | 14 | tracer and fiber tests |
| `ink-triage*.log`, `ensemble-windings.log`, `three-model.log`, `stroke-watch.log`, `triage-windings.log`, `control343*.log` | 8 | ink passes and scoring |
| `assemble-pherc0191.log`, `outer-shell.log`, `shell-dense.log`, `surf-sdt[-attempt1].log`, `snap-exp30k.log`, `prep-community.log` | 7 | dataset preparation |
| `apt-vc3d-deps.log`, `build-vc3d.log`, `uv-sync-*.log`, `lasagna-env.log`, `bench-1660.log`, `candidates-survey.log`, `ray-peaks-9500.log`, `resume-volume*.log` | 11 | environment and one-off checks |

Every job ends its log with a marker `<NAME>-EXIT: <rc>`; waiter scripts poll for it.

## 2. Mac, `/Users/tbienapfl/dev/vscode/scroll-prizes`

```
scroll-prizes/                         (data/, villa/, memory/, aws/state/, aws/spot.env, *.tif are git-ignored)
├── data/                              3.5 G   8,866 files
│   ├── aws-results/                   2.9 G
│   │   ├── run2/                      2.5 G   fleet run 2 (2026-10-09, 10 workers, 59 windings, three models)
│   │   │   ├── wNN/  × 10 (w01–w10)  210–270 M each: 6 × exp30k_snapped_wNNN/ + 6 × exp30k_snapped_wNNN.run.log,
│   │   │   │                                  batch.log, progress.txt. Per segment: ensemble/ (ct, ensemble, ensemble_blind
│   │   │   │                                  PNG at d+00/d+01, stats.json, ensemble.log), strokes/ (11 files), render.log,
│   │   │   │                                  ink_<model>_d{0,1}.log × 6, timings.tsv, gpu.txt, DONE   (1,855 files)
│   │   │   └── ranking.tsv                    118 rows; "crops" column points to data/aws-results/fleet/…, which no longer exists [NAME]
│   │   ├── run1/                      463 M   fleet run 1 (2 workers, w073 and w074, four models); w01/, w02/ (233 M, 230 M):
│   │   │                                      maps/ (98 M), ensemble/ (114 M), previews/ (21 M), 8 ink logs, render.log, timings.tsv,
│   │   │                                      gpu.txt, DONE  (146 files)
│   │   └── i-07316924655570581/        14 M   proof of concept: control343/ (maps: seed42 s26 pair; previews; logs), instance-info.txt [NAME]
│   ├── prior-art/                     256 M   5,864 files: substack-<slug>.{html,txt} × 12, api-<slug>.json × 12, substack-archive.json,
│   │                                          pherc343-first-letters/ (24 M, Nieuwlaar repo), scrollfiesta_public/ (229 M, third-party repo), sqm/ (92 K)
│   ├── aws-stage/                     204 M   466 files: segments/exp30k_snapped_wNNN/flatten.tifxyz × 92 (copies from the box),
│   │                                          manifest.tsv (absolute Mac paths), flattest/w005/ (an unflattened community winding) [TEMP][NAME]
│   ├── results/                        82 M   94 files: images used by the site (JPG/PNG, plus git-ignored TIF originals);
│   │                                          names: PHerc0191-<topic>.jpg, control343-*.jpg, w070-*.{jpg,png}, sample-*.jpg, PHerc0800-*.jpg
│   ├── strokes/                        19 M   45 files: review crops v_wNNN_ensemble[_blind]_d+NN_K.jpg, m_wNNN_d+NN.jpg, z_w083_*.jpg,
│   │                                          wNNN_ens_d+NN_K.jpg, copies of __topNN.png crops, w070_d+00.{json,png}, c343_d+01.png,
│   │                                          triage-candidates.jpg                                                     [NAME]
│   ├── catalog/metadata.json           17 M   open-data metadata catalog (schema from vesuvius-challenge-open-data)
│   └── ref/                            12 M   5 entries: reference images (Discord screenshot, early renders/predictions), atlas/{manifest.csv,
│                                              spiral-fits-README.md}
├── villa/                             1.9 G   clone, branch fix/install-volcomp @ 382d6d0d8 (fork remote)
├── docs/                               25 M   GitHub Pages site: index.html (156 K), img/ (32 files, 25 M; copied from data/results by build_site.py), .nojekyll
├── research/registry.json              48 K   project, 5 phases, 33 experiments, 15 findings, 4 next items, 13 credits
├── notes/                             140 K   12 files (plans, results notes, friction log, PR drafts, one patch)
├── memory/                            120 K   session memory files (not documented here)
├── aws/                               504 K   fleet/spot scripts, remote/ (4 scripts), spot.env, state/ (376 K)
│   └── state/                                 poc-*.log × 6, fleet-run-*.log × 5, bootstrap-<instance>.log × 2, userdata.sh, known_hosts,
│                                              last_*_log, run-instances.err (empty), one SSH key file (*.pem, not opened),
│                                              fleet/{plan.tsv, wNN/ × 10 (instance_id, instance_ip, instance_type, launched_at, batch.tsv,
│                                              userdata.sh, run-instances.err), wNN.up.log × 10, wNN.maps.done × 2}
├── box/bin/                           488 K   copy of the box scripts (in sync at the end of the listing)
└── scripts/                            32 K   build_site.py, pull_preview.sh
```

## 3. Flags, collected

Duplicates
- `spiral-dataset/lasagna_inputs/*.respool*` (17.6 G, CT-masked) vs `lasagna/<id>/*.respool*` (17.6 G, unmasked). The pilot fit log shows the
  fitter did not find the first copy and built the second next to the resolved symlink target; later fits load the second.
- `spiral-dataset/outer_shell_dz1/` = `spiral-dataset/outer_shell/` (160 M).
- `/mnt/nvme/vc3d-remote-cache/…9.362um…` (23 G) holds PHerc0191 CT chunks that are also in the local mirror.
- `data/PHerc0191/aws-maps/`, `aws-ens/` (355 M) are copies of Mac `data/aws-results/run1/*/maps` and `ensemble`.
- `tmp/flag/` (141 M) = copies of Mac run2 ensemble PNGs plus review JPGs that are also in Mac `data/strokes/`.
- `checkpoints/ckpt343/dense_native-016000.pth` is a rebuilt copy of `dense_native/weights/dense_native_016000.safetensors` (needed by run_ink.sh).

Orphaned or temporary
- `tmp/run_ink.*` × 6 (932 M), `tmp/appimg/` (486 M), `tmp/t343`, `tmp/w072`, `tmp/win`, loose scripts and JPGs in `tmp/`.
- `winding/band9000-10000/smoke.zarr` (3.7 G), `smoke.tmp`, `winding_native_phase_ws8_ss96.tmp`.
- `flatten/exp-30k-snapped-w116/` (failed flatten), `grow-test/dirfield/` (failed attempt).
- Stale claim dirs `ink-triage/claims3/w032`, `w106` (the three-model job stopped at 00:27 with these unfinished).
- Zero-byte `*.lock` files next to respool sidecars and in `volumes/…/.dl_cache/`.
- `cache/PHerc0343-l0/`, `cache/spiral-old/` (empty).
- `villa/lasagna/torchinductor_tbienapfl/` (129 M, inside the repo).
- Mac `data/aws-stage/` (204 M) once a fleet run is over.

Naming and placement
- One winding, three spellings: `wNNN_exp-30k` (fit and snapped meshes), `exp-30k-snapped-wNNN` (flatten dirs, hyphens),
  `exp30k_snapped_wNNN_66` (renders, maps, scores, underscores).
- `snapped/qa_exp-30k_w040_exp-30k` repeats the fit tag.
- Stroke-score files without a tag mean four models in `data/strokes/wNNN/` and `data/strokes/aws/`, but three models in
  `data/strokes/box3m/` and in AWS run 2. `_3m` and `_s4243` files are an older format without the window metric; `_pm` comes from
  `tmp/permodel.sh`, which is not in `bin/`.
- `ensemble/` vs `ensemble3/`, `claims/` vs `claims3/`, `box3m/`: model count encoded in directory names, inconsistently.
- AWS worker dirs `w01`–`w10` look like winding names.
- `data/aws-results/run1`, `run2` were renamed from `fleet/`; `run2/ranking.tsv` and `notes/results-2026-10-09.md`
  (`data/aws-results/fleet-run2-ranking.tsv`) still point to the old paths, and the fleet scripts still write to `data/aws-results/fleet/`.
  The proof-of-concept dir is named by instance id.
- Community fit windings `w000`–`w009` use a different numbering from our fit's `w020`–`w119`; the names collide in meaning.
- `-old` suffix (`spiral-dataset-old`, `spiral-output-old`, `cache/spiral-old`) means "old fitter", not "old data".
- `outer_shell.v0` vs `outer_shell_dz8` vs `outer_shell_dz1`: version and sampling mixed in suffixes.
- Download logs live inside `data/PHerc0191/`; `render_w070.log` lives at the top level as `render66-w070.log`; `build-vc3d.sh` sits outside `bin/`.
