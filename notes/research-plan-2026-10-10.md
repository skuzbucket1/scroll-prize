# Research plan from 2026-10-10

Written after three nights of work and four null AWS runs. It replaces the "cover everything fast" approach with
fewer, deeper looks, each ending in a decision.

## Ground rules

- **Compute:** the home GPU box is the default (GPUs 0, 2, 3; GPU 1 is never used). AWS runs only with a fresh,
  explicit go-ahead from Ted, with the cost stated up front. Spend so far: about $23.
- **Pace:** depth over breadth. Every phase ends at a gate, a decision we take together, before the next one starts.
- **Evidence:** every candidate is checked against the blind side of the same sheet, the CT, and the PHerc. 343
  positive control. The stroke score decides where to look; a human decides what is real. Nothing about a possible
  find is published before the official announcement.
- **Credit:** every tool, model and dataset we use is credited on the site.

## Where we stand

- PHerc. 0191, band z 9,000–10,000: all 99 flattened windings checked at depths 0 and +1 (7 with four models,
  92 with three). No ink. The depth window was checked against the 343 control and is right.
- PHerc. 0191, band z 11,200–12,200 (the scroll's clearest band on Scan-Quality-Map, 0.54 against 0.37–0.40):
  fitted (best fit so far: 0.519 of track points within the sheet, 0.138 of whole tracks), snapped, 100 windings
  w020–w119 ready on the box. Not inked.
- Scroll choice (`notes/scroll-choice-2026-10-10.md`): 0191 as a whole is a weak bet (crushed; 4th of 11 on scan
  clarity at its scan type, 9th of 11 on a second clarity measure). Ranked next scrolls: PHerc. 0813, then 0358, then 0175A.

## Phase A: finish PHerc. 0191's clear band (home GPUs, about 2 days, free)

A1. **Geometry first.** Flatten, render (66 layers) and make a CT preview of all 100 windings, w070 outwards.
    Flattening runs on the GPUs (about 7 min each); rendering is CPU-bound on the box's 4-core i3, so two
    windings at a time at most. Estimate: 8–10 h.
A2. **Pick together.** A montage of the CT previews; Ted and I pick the 5 windings with the cleanest papyrus weave
    over the largest area.
A3. **Deep look at the best 5.** The full four-model ensemble (with Hecate) at depths −2 to +3, stroke score, and a
    row-scale look at every depth. Hecate takes about an hour per depth at home, so about 6 h per winding;
    5 windings over 3 GPUs is about 10 h.
A4. **The rest in the background.** Three models at depths 0 and +1 on the other 95, as GPUs free up (about 40 min
    each, about 21 h on 3 GPUs). Automatic stroke score; flags checked by eye.

**Gate A.** Strokes anywhere: a full depth sweep (−15 to +15) and close-ups of that winding, then we plan the claim.
Nothing: we stop work on PHerc. 0191.

## Phase B: next-scroll pilot (download runs while Phase A computes)

B1. **Data for one band of PHerc. 0813** (z 12,000–13,000; its clearest stretch): level-0 CT for the band, the m7
    surface prediction band, Lasagna normals (levels 2–4), the spiral tracks dataset, the normal grids for the
    umbilicus. About 50–80 GB, about 2 h. The box has about 274 GB free.
B2. **Assemble** the spiral dataset (umbilicus, packed inputs), as for 0191.
B3. **Fit** the band with our best recipe (exp-30k: tracks, grad_mag spacing, no shell, 30k steps), about 1.5 h on
    one GPU, then snap.
B4. **Judge the geometry by eye** against 0191's clear band (weave, layer separation in the CT), then the same
    A2–A4 sequence on its best windings.

**Gate B.** Clean geometry: we commit to 0813 and extend to its other clear bands. Poor geometry: we run the same
pilot on PHerc. 0358 (z 8,900–9,900; it needs its flipped z direction checked first).

## Phase C: the stroke score as a tool, tested on more known text (mostly CPU; some GPU for the positives)

C1. **Package** a standalone tool (`tools/stroke-score/`): inputs are a 66-layer render and any set of ink maps;
    outputs are the scores, a ranking with the flag, and review crops. No dependence on our folder layout.
C2. **Positives:** the other published text segments (the other PHerc. 0343 submissions, and any other
    known-text segment at 8–9.4 µm found by `notes/known-text-positives-2026-10-10.md`), rendered and inked the
    same way as our control, on the home GPUs.
C3. **Negatives:** our ~135 checked windings (PHerc. 0191 old band and community fit) give a measured
    false-alarm rate per threshold.
C4. **Thresholds and limits** set from C2 and C3, the false-alarm types documented with examples (CT voids and
    cracks, recurring bright zones, core geometry, tiny meshes).
C5. **Release** before the Oct 31 Progress Prize deadline: repo, site page, and a write-up in Ted's voice.

## Phase D: housekeeping (in gaps)

- Site write-up for AWS runs 3 and 4, and the migration.
- Code-dictionary fix list, in order of risk: the GPU 1 guard (it should refuse the index, not only the UUID); exit
  markers that report 0 after failures; scripts pointed at the new data paths and at `runs/<date>_<run-id>/` logs;
  one ranker for every score file.
- Reader v2 (another public ink model) is reported to beat Hecate on 8.64 µm scans. Test it on the 343 control first;
  add it to the ensemble only if it shows the letters there.

## GPU schedule (home box, first pass)

| Time | GPU 0 (12 GB) | GPU 2 (8 GB) | GPU 3 (12 GB) |
|---|---|---|---|
| Day 1 | A1 flatten/render | A1 flatten/render | C2 positives (render + four models) |
| Day 1–2 | A3 deep look | A3 deep look | A3 deep look, then B3 fit once B1–B2 are done |
| Day 2–3 | A4 three-model rest | A4 three-model rest | B4 on 0813's best windings |

Downloads (B1) and CPU work (C1, C3, C4, Phase D) run alongside. Each gate is a conversation with Ted.
