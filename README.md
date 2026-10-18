# scroll-prize

Our attempt at the Vesuvius Challenge First Letters prize: find ten letters inside an unopened Herculaneum scroll, using
only its CT scan. So far we have searched parts of PHerc0191, PHerc0813 and PHerc0175A and found no writing.

**Research log:** https://skuzbucket1.github.io/scroll-prize/ has every run: what it asked, what it showed, and what
changed because of it.

The repo is sorted by what we know about each piece of code. What works sits in one place. What we are still testing
sits in another. What we tried and dropped sits in a third, with the reason written down.

## What works: `pipeline/`

Every step here has been checked on a scroll where the text is known, and every search uses it.

- **Geometry** (`pipeline/geometry/`): a spiral fit of one band of the scroll (villa's spiral fitter with our 30k-step
  recipe), snapped onto the predicted papyrus surface (Erwin Nieuwlaar's snap), then flattened (Lasagna). On PHerc0191
  and PHerc0813 this gives windings that show clean papyrus weave. One known limit: in places the fit lays two or three
  windings on the same sheet (being measured in `experiments/geometry-coverage`).
- **Render** (`pipeline/render/`): a 66-layer stack around each flattened winding, from a local copy of the CT.
- **Ink** (`pipeline/ink/`): six public ink models, run through Nieuwlaar's scripts on both faces of the sheet at any
  depth. The models are ink_9um 42/43, dense_native, Hecate, Reader v2 and d9v4C. The step reproduces three lines of
  Greek on PHerc. Paris 4 and the winning letters on PHerc. 343, and matches the published scores on PHerc0139 and
  PHerc0841.
- **Rank** (`pipeline/rank/` and the released tool `tools/stroke-score/`): stroke, row and shape scores pick out the spots
  worth a closer look. On text it never saw (PHerc0841) it flags 14 of 15 one-centimetre strips; on bare windings, 8 of 294 winding-depths (each one checked by eye). It ranks;
  it does not prove anything.
- **Review** (`pipeline/review/`): the pictures we judge by eye. A candidate window, the same place on the neighbouring
  turns, and a deep look (six models at every depth from −15 to +15).
- **Controls** (`pipeline/controls/`): the known-text checks above, plus the check that our "reading side" is the written face.

## Still being tested: `experiments/`

Each folder has a `STATUS.md` that gives the question, the numbers so far, and what will decide it.

- **model-agreement**: real letters light up in at least five of the six models; false alarms light up in only some.
  Holds on PHerc. 343, PHerc0841 w00 and PHerc0139 w047, fails on PHerc0841 ag2814. Next: the official ink labels on
  the segments the models never saw (running).
- **ink-ablation**: what in the CT do the models respond to on real 9.36 µm letters? Fine texture, about 75 µm, in the
  layers just above the surface, not brightness.
- **synthetic-letters**: train on letters painted into real text-free renders, with that texture. (just started)
- **ink9-swap**: would another checkpoint, or a soup, of ink_9um make a better member? Candidates built and checked;
  comparison not run yet.
- **geometry-coverage**: how much of a fitted band is really new papyrus? First pass: about a fifth of the area repeats
  a sheet that another winding already covers.
- **ink-first**: find ink without building a mesh first. It sees real letters where it lands. A whole-scroll sweep is
  still a coarse net.

## Didn't work: `dead-ends/`

Kept so that nobody, us included, repeats them. Each README gives what we tried, the numbers, and why it failed.

- **damage-map-2d** and **damage-map-3d**: our false alarms do not sit on cracked or damaged papyrus, so a damage mask
  would not remove them.
- **model-free-ink**: at 8–9 µm you cannot see the ink in the raw CT, even after taking out the papyrus weave.
- **model-8um-v1**: a model fine-tuned on PHerc. 343 using our own ensemble's guesses as labels memorised its training
  letters and did worse on letters it hadn't seen.
- **spiral-fit-tuning**, **winding-model-supervision**, **old-fitter**: fit settings, an outer shell, local spacing
  supervision and the older fitter. None of them moved the fit onto the sheet. What helped (more steps, then the snap)
  is in the pipeline.
- **patch-growing**: growing a surface from a seed point stays on one sheet for only part of a patch.
- **rerun-public-segments**: re-inking already-published segments found nothing new.

## Also here

- `archive/`: one-off setup steps that are done, and scripts that newer ones replaced (the README says which replaced which).
- `infra/`: plumbing. This is data mirroring, the cloud runs, backup and the artifact catalog, and the site and viewer
  builders. It also holds `infra/box/sync_bin.py`, which maps these folders to the GPU machine, where every script lives flat
  in `~/scroll-prizes/bin/`.
- `research/registry.json` drives the site in `docs/` (`python3 infra/site/build_site.py`). `docs/` also holds the code
  dictionary, the data layout and the data dictionary.

The large data (CT copies, meshes, renders, ink maps) lives on the GPU machine and is not versioned. `docs/img/` holds
downsampled previews only. `infra/moved-2026-10-13.tsv` lists where every file went when the repo was sorted this way.

## License

MIT for the code and notes here. Copied code keeps its own licence notice (`pipeline/ink/ink343/`,
`pipeline/geometry/LICENSE-snap_meshes_nieuwlaar`). Scan data belongs to the Vesuvius Challenge and is under its own terms.
