# The winner's older fitter: didn't help

**Idea.** The PHerc. 343 First Letters win used villa's spiral fitter from before its September 2026 simplification. A
fit with that fitter and the winner's recipe reported more satisfied track points than ours (56.3 % against 49.0 % on the
same band). Is it better geometry?

**What we tried** (2026-10-10). `fit_old_phase.sh` runs the old fitter, in a worktree at villa `0fb38c45` with
`old-fitter-0fb38c45-fit_spiral.diff` applied. We snapped both fits and compared them winding by winding on the CT.

**What it showed.** The snap statistics are level. The two fits sit on the same sheet pieces (median distance 3.2 voxels)
but chain them into turns differently. Each pair of previews shows the same papyrus, the same crack band and the same
clean stretch. Neither is cleaner.

**Why it didn't help.** The higher number comes from how the old fitter counts track crossings, not from better geometry.
We kept the current fitter with the 30k-step recipe.

Site: https://skuzbucket1.github.io/scroll-prize/#run-oldfit-check
