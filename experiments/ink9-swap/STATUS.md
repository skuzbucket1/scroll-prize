# Better ink_9um members: in test (prepared 2026-10-13, not run yet)

**Question.** Two of our six models are the challenge's ink_9um, seeds 42 and 43, each at its last step (75k). Would a
different checkpoint of the same training runs, or a soup of the last four (the uniform weight average Erwin Nieuwlaar
published for seed 42), make a better member: as good on held-out letters, fewer false alarms?

**Code.** `make_soup.py` averages checkpoints the way Nieuwlaar's MIT `make_soup.py` does (HF Nieuwlaar/ink9um-dense-native)
and records the inputs and distances in a sidecar json. `verify_ckpts.py` loads every candidate the way villa does, with a
strict load, and compares names, shapes, dtypes, configs and weights with the member we run now. Run scripts:
`runs/2026-10-13_ink9-swap/` (`fetch.sh`, `build.sh`; outputs on the box under `~/scroll-prizes/runs/2026-10-13_ink9-swap/`).

**Done so far.**
- The extra checkpoints (seeds 42 and 43 at 40k, 50k, 60k) come from the public HF repo scrollprize/ink_9um (revision
  7109667e), each checked against its listed sha256.
- Our seed-42 soup of 40k/50k/60k/75k is bit-identical to Nieuwlaar's published soup42_last4 (508 tensors). The seed-43
  soup is built the same way.
- All five candidates load strictly in villa's model and are finite. The seed-42 soup is 0.11 relative L2 from the 75k
  member; the seed-43 checkpoints are 1.19–1.23 from it (a different run).

**What decides it.** The candidates against the current members on the controls that ink_9um never saw (PHerc0841 and
PHerc0139 w030, w045): AUC on the labelled letters, and the share of one-sided tiles on text-free windings. A swap only if
held-out AUC stays and false alarms drop. The GPU comparison is not written yet.
