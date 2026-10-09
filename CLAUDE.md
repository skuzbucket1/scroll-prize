# Vesuvius Challenge — project brief

Working directory: `/Users/tbienapfl/dev/vscode/scroll-prizes`
Brief written 2026-10-08 from a claude.ai triage session. Pick up from here.

## Goal

Ted and Claude are evaluating the Vesuvius Challenge (https://scrollprize.org/prizes) as a side project.
Decision so far: vet the `ScrollPrize/villa` repo's "help wanted" issues. Done — see findings below.
Not yet decided: which lane to pursue. Claude's recommendation is at the bottom.

## Ted's resources

- 4-GPU on-site Linux/unknown-OS box currently running Ollama — usable for long-running jobs.
  Open questions: GPU model and VRAM per card, OS (VC3D build script wants Ubuntu 24.04+ / Debian 13+),
  free disk, network throughput.
- AWS Bedrock access.
- MacBook Pro, Zed, Claude Code, Claude Team plan.
- Note: Ollama and Bedrock host LLMs. The challenge's models are PyTorch vision models (3D UNets etc.)
  that run directly on the GPUs; spiral-fitting has a CUDA path. The GPUs are the asset, not Ollama.

## Prize structure (all deadline June 25 2027, 11:59pm Pacific, except Progress Prizes)

- **Grand Prize** $800k (+$100k/$50k/$50k for 2nd–4th). Fully unroll and read one of 13 eligible scrolls.
  Pipeline must integrate with VC3D; max 8 documented hours of human annotation; open source on GitHub;
  datasets CC-BY-NC 4.0; W&B runs public; fixed seeds.
- **First Letters** $50k per scroll (max 10 scrolls). 10 legible letters within a single 4 cm² area on any of
  22 eligible scrolls. Start guide: https://scrollprize.substack.com/p/from-ct-scan-to-ancient-text-a-first
- **PHerc. Paris 4 Title** $50k. Title region has shown no detectable ink so far.
- **Progress Prizes**: $20k guaranteed monthly to the best submission; others $250–$20k.
  Next deadline Oct 31 2026. Favors early open-source release, actual community use, evaluation on real
  data, good docs. Wishlist = villa issues labeled "help wanted" / "good first issue", plus VC3D improvements.
- Must be registered on the Discord at submission time: https://discord.gg/V4fJhvtaQn
- Do not publish discoveries before the official announcement.
- Tutorials: https://scrollprize.org/tutorial_VC3D, /tutorial_spiral, /tutorial5 (ink detection), /get_started

## villa repo state (https://github.com/ScrollPrize/villa) as of 2026-10-08

- "help wanted" label = 3 stale umbrella issues from Apr 2025: #191 surface/fiber predictions in
  compressed/curved areas, #192 accurate 3D ink labels, #193 label-generation methods. Research directions,
  not scoped tasks. "VC3D" label has 0 open issues.
- 107 open issues, ~100 filed Jul–Oct 2026, mostly audit-style data/metadata reports:
  OME-Zarr volumes missing scale units (#1957, #1951, #1962); S3 mirror missing 7 volumes (#1949);
  ~1 PB stored uncompressed (#1950); zero-chunk pyramid (#1963); stale bboxes (#1272, #1618);
  `:edge`/`:main` containers 285 commits stale (#1588); remote chunk fetch aborts runs (#1846, #1666);
  tools exit 0 after writing nothing (#1403, #1360, #1320).
  Comment threads are all community "independently verified" posts. No visible maintainer engagement.
- CONTRIBUTING.md rules: PRs must come from a human running tools on real scroll data; bugfix PRs need an
  error screenshot plus the fix working; before/after evidence on real data (no synthetic); concise
  human-written motivation; they close LLM "fishing expedition" PRs. CI has a large-PR review gate and PR
  time limits. A commenter referenced a three-PR cap per contributor.
- Community PRs that did get merged (the pattern to copy — use → friction → fix):
  #1905 `vc_render_tifxyz` chunk prefetch; #1886 `render_ink` fail on all-zero strips;
  #1873 `lasagna` native Windows; #1818 bicubic rendering; #1888 spiral-fitting on NVIDIA GPUs.
- Dev setup: `uv` + `pyproject.toml` in `ink-detection`, `volume-cartographer`, `vesuvius`, `spiral-fitting`
  (`uv sync`; `--all-extras` for `vesuvius`). VC3D via `build_from_src_debian.sh` (Ubuntu 24.04+ /
  Debian 13+, CMake ≥ 3.28) or `docker pull ghcr.io/scrollprize/villa/volume-cartographer:edge`
  (verify staleness per #1588). Windows installer on GitHub releases. macOS CI exists.
- Data: served from `data.aws.ash2txt.org` and S3 bucket `vesuvius-challenge-open-data`.
  Volumes are OME-Zarr, hundreds of GB each. Meshes are `tifxyz` with `meta.json`.

## Claude's recommendation (Ted has not decided yet)

Skip filing more audit issues — the tracker is saturated and maintainers aren't engaging there.
Instead, run the First Letters workflow end-to-end on one eligible scroll on the GPU box, with VC3D built
from `main`. Every bit of friction hit along the way (remote zarr/S3 fetch robustness, caching, silent
exit-0 failures) is a legitimate evidence-backed PR and Progress Prize material, and the rendered segment
plus ink prediction is the on-ramp to First Letters.

## Suggested first steps in this directory

1. `git clone https://github.com/ScrollPrize/villa` here.
2. Answer the hardware questions above; decide whether VC3D and the Python tooling build on the GPU box
   or the Mac. Prefer the GPU box — data and compute live there.
3. Register on the Discord.
4. Work through the First Letters Substack guide on one eligible scroll.

Tailscale ip of llm: 100.74.214.106

## Where the project state lives (added 2026-10-08 by the working agent)

- `memory/` — persistent agent memory (index: `memory/MEMORY.md`; format in `memory/README.md`). Canonical; the Claude harness symlinks to it.
- `notes/campaign-plan.md` — the full First Letters campaign plan (PHerc0191), prior art, calibration, phases, open asks.
- `notes/results-2026-10-08.md` — what was run and found on day 1. `notes/friction-log.md` — evidence-backed tooling problems/fixes.
- `notes/pr-*.md`, `notes/fix-*.patch` — staged contribution(s). `scripts/` — Mac-side helpers. `data/ref`, `data/results` — small reference/result images.
- GPU box `llm` (192.168.1.61 / llm.tailb8796.ts.net): work tree `~/scroll-prizes` → `/mnt/nvme/scroll-prizes` (NVMe); tools in `bin/`, job logs `*.log`;
  scroll data under `data/PHerc0191/`. Credentials: `.secrets` (labelled lines; never print).
- GPUs on `llm`: use only 0 (RTX 3060 12 GB), 2 (RTX 3060 Ti 8 GB), 3 (RTX 3060 12 GB). **GPU 1 (GTX 1660 SUPER) is not usable for any of this work** (fits at 0.04 it/s, ink inference writes all-zero maps, no bf16) — decided 2026-10-09; never schedule on it.
- Public repo: https://github.com/skuzbucket1/scroll-prize (MIT) with the research-log site at https://skuzbucket1.github.io/scroll-prize/ (GitHub Pages, `docs/`). Registry `research/registry.json` → `python3 scripts/build_site.py`. `memory/`, `data/`, `villa/`, `.secrets` are not versioned. Box scripts are synced into `box/bin/`.
