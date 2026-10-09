# scroll-prizes — a Vesuvius Challenge campaign on PHerc0191

Working notes, scripts and results for an attempt at the Vesuvius Challenge First Letters prize on
PHerc0191, plus the tooling problems found along the way in `ScrollPrize/villa`.

**Research log (static site):** open `docs/index.html` — every run, what it asked, what it showed,
what changed. Rebuild with `python3 scripts/build_site.py` after editing `research/registry.json`.

## Layout

| path | what |
|---|---|
| `research/registry.json` | the experiment/finding registry that drives the site |
| `docs/` | generated site (GitHub Pages serves this folder) |
| `notes/` | campaign plan, daily results, friction log (evidence-backed tooling issues), PR drafts |
| `box/bin/` | the scripts that run on the 4-GPU box (mirroring, spiral-fit experiments, outer shell, winding cache, tracer tests, QA) |
| `scripts/` | Mac-side helpers (site build, preview pulling) |
| `CLAUDE.md` | project brief and where state lives |

Large data (CT mirrors, caches, meshes, renders) lives on the GPU box under `~/scroll-prizes/data/` and
is not versioned; `docs/img/` holds downsampled previews only.

## Status (2026-10-09)

Calibrated the ink pipeline on known text; chose PHerc0191; found the minimal-route spiral fit sits on
the sheet only ~46–49% of the time and why; the patch-growing route needs the normal grids the docs call
required and then partly follows sheets. Winding-model supervision and anisotropic-fit experiments are
running. Eight tooling findings so far; #1 submitted as villa PR #2008.

## License

MIT for the code and notes here. Scroll data is the Vesuvius Challenge's, under its own terms.
