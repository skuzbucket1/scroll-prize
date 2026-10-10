# Which scroll next? First Letters target choice (2026-10-10)

Question: is it worth continuing on PHerc. 0191, and which eligible scroll should we work on next?
Evidence: prizes page, villa eligibility file, open-data catalog, S3 and dl.ash2txt.org listings (fetched 2026-10-09/10),
Scan-Quality-Map (SQM), community repositories and our own results. Sources are listed at the end.

## Short answer

1. **Finish the PHerc. 0191 clear band (z 11200–12200), then stop working on 0191 unless it shows strokes.** The fit and snap are
   done and every input is local, so finishing costs about a day of free GPU time. It is the scroll's best band
   (SQM 0.54 against 0.37–0.40 for the band we already searched), and the fit is our best so far (0.519 satisfied track points).
   0191 is still a weak bet compared with other scrolls, though: it is mid-table on SQM (0.41, 4th of 11 at 9.362 µm),
   9th of 11 on a second clarity measure (sheet modulation 0.232), and all 99 windings of z 9000–10000 came back null under
   the method that passes the PHerc. 343 control.
2. **Next scroll: PHerc. 0813. Second: PHerc. 0358. Third: PHerc. 0175A** (more risk, more upside). 0826 is the fallback
   if we skip 0175A.
3. The pick of 0813 over 0358 is close. A cheap way to choose: mirror one band of each (about 50–80 GB each, 1.5–2.5 h at
   our ~10 MB/s), fit both, and keep the one whose snapped windings show cleaner papyrus weave.

## 1. The 22 eligible scrolls

The First Letters list is the same on scrollprize.org/prizes and in villa `scrollprize.org/src/data/prizeEligibility.json`
(last changed 2026-09-24, villa #1887). PHerc. 0343 is still listed but was won on 2026-10-08. PHerc. 1447 was taken off the
list on 2026-09-24 after the team found letters with a new 9 µm recipe; it is still on the Grand Prize list.

Scan protocols come from the catalog (`data/catalog/metadata.json`): 9.362 µm / 113 keV (Aug 2025 volumes) or 8.64 µm / 116 keV
(May/Nov 2025 volumes); the detector distance is 1.2 m for all.
- SQM = Scan-Quality-Map median layer-separation quality.
- Mod = claudepro1515 sheet modulation.
- Aspect = cross-section elongation from TAUIL-Abd-Elilah/eligible-volume-morphology (1.0 = round, above 2 = crushed flat).
- Inputs: T = spiral tracks on dl.ash2txt.org, L = Lasagna normals on S3, U = umbilicus (o = official on S3, m = Drobkov
  manual, community). Every scroll has the m7 surface prediction and normal grids on S3.

Compare SQM and Mod only between scrolls with the same scan protocol.

| scroll | µm / keV | slices | SQM | Mod | aspect | inputs | status / reported signal |
|---|---|---|---|---|---|---|---|
| PHerc0358 | 9.362 / 113 | 14744 | **0.57** | 0.277 | 1.11 | T L Um | nulls only (see section 3) |
| PHerc0813 | 9.362 / 113 | 16993 | **0.53** | 0.276 | 1.08 | T L Um | one published "candidate location" (z 12496, w060), no letterforms |
| PHerc0826 | 9.362 / 113 | 16920 | 0.44 | **0.316** | 2.20 | T L Uo | most-searched eligible scroll; all null |
| PHerc0191 | 9.362 / 113 | 18977 | 0.41 | 0.232 | 1.11 | T L Um | our 99 + 10 windings null; community fit null |
| PHerc0211 | 9.362 / 113 | 19416 | 0.38 | 0.238 | 1.63 | T L Uo | nulls; reverse-face clusters at z ≈ 9100 read as structure |
| PHerc1203 | 9.362 / 113 | 18977 | 0.35 | 0.243 | 1.31 | L Um (no T) | nulls on 4 public meshes; a 2.4 µm rescan exists |
| PHerc1545 | 9.362 / 113 | 20961 | 0.31 | 0.260 | 1.56 | L Um (no T) | nothing published |
| PHerc0846B | 9.362 / 113 | 13926 | 0.25 | 0.222 | 2.39 | none (no T, L, U) | nothing published |
| PHerc0846A | 9.362 / 113 | 14019 | 0.18 | 0.233 | 1.81 | T (no L, U) | Hecate null on 41 meshes; 2.4 µm patches null |
| PHerc0257 | 9.362 / 113 | 18872 | 0.14 | 0.217 | 1.34 | T L Um | nothing positive |
| PHerc0125 | 9.362 / 113 | 20840 | 0.12 | 0.223 | 1.87 | T L Uo | nulls (62 minimal-route meshes; fits satisfy 12–16 % of tracks) |
| PHerc0175A | 8.64 / 116 | 12748 | **0.50** | 0.264 | 1.19 | T (no L, U) | nulls only |
| PHerc0343 | 8.64 / 116 | 17998 | 0.34 | 0.246 | 1.28 | T L | **WON 2026-10-08** (Nieuwlaar); two more submissions found text |
| PHerc0483B | 8.64 / 116 | 11880 | 0.30 | 0.238 | 1.18 | T | nulls (TAUIL sites) |
| PHerc0306B | 8.64 / 116 | 15898 | 0.30 | 0.258 | 1.19 | T | nothing published beyond survey patches |
| PHerc0800 | 8.64 / 116 | 24298 | 0.28 | 0.235 | 1.27 | T L Um | nulls (6 team segments incl. ours, 92–95 community meshes) |
| PHerc0175B | 8.64 / 116 | 15897 | 0.27 | 0.222 | 1.08 | T | ~1 mm ring on both faces (Bullo27), nothing else |
| PHerc0483A | 8.64 / 116 | 15898 | 0.18 | 0.214 | 1.59 | T | nothing positive |
| PHerc1218 | 8.64 / 116 | 23247 | 0.17 | 0.211 | 2.19 | L Um (no T) | nothing positive |
| PHerc0490A | 8.64 / 116 | 11698 | 0.16 | 0.222 | 1.31 | T | nothing positive |
| PHerc0490B | 8.64 / 116 | 10648 | 0.11 | 0.207 | 1.09 | T | nothing positive |
| PHerc0268 | 8.64 / 116 | 14833 | 0.08 | 0.166 | 1.17 | T L Um | haziest scan of all 22 |

Points that matter for the choice:
- Of the eligible scrolls, ink has been found only in 0343 and 1447, and both are 8.64 µm / 116 keV scans. No 9.362 µm
  eligible scroll has shown letters yet, even though the 9 µm models were trained on 9.362 µm / 113 keV scans (0139, 0814).
- At 9.362 µm the scrolls where ink was found score higher on sheet modulation than 10 of the 11 eligible scans (AUC 0.95,
  p = 0.006, claudepro1515). That is an association across scrolls; it does not say where ink sits inside a scroll
  (ρ = 0.06). SQM gives a matching example after the fact: the 343 letter patches score 0.69 against 0.64 for the rest
  of the segment.
- 0358, 0813 and 0826 are the top three 9.362 µm scans on **both** clarity measures. 0191 is 4th on SQM and 8th–9th on
  modulation. 0175A is first among the 8.64 µm scans on both measures, ahead of the won 0343.
- Community nulls count for less than they look. TAUIL's 140-site survey of PHerc0343 (m7-tracked single sheets,
  Reader v2 + d9v4C) reported no lead, yet two of those sites contained the letters that later won. The tracked sheet was
  one to three windings away from the inked one. Our pipeline (spiral fit, snap, Lasagna flatten, 66-layer render,
  multi-model ensemble) is the one that passes the 343 control, and no one has run it on 0358, 0813 or 0175A.

## 2. Published inputs for the main candidates (S3 and dl.ash2txt.org listings, 2026-10-10)

CT sizes are estimates. They come from the level-2 chunk bytes in today's S3 listing (chunks are uncompressed 128³ uint8),
scaled by 0191's measured ratio (410 GiB on disk for all levels, against 7.82 GB at level 2).

| scroll | CT volume (all levels) | m7 + normal grids | Lasagna nx/ny/grad_mag/cos | tracks (dbm + crossings + .vctracks dir) | umbilicus | orientation flags |
|---|---|---|---|---|---|---|
| 0191 | local, 410 GiB | yes (bands local) | yes (local, levels 2–4) | local, 21 G | ours (vc_gen_umbilicus) | lh False, z top→bottom False (CW) |
| 0813 | ~300 GiB | yes | yes | 7.6 GiB + 2.0 GiB + dir | Drobkov manual (not returned in review, 1.4 % kinked) | lh False, z top→bottom False (CW): **same as 0191** |
| 0358 | ~275 GiB (smallest) | yes | yes | 5.6 GiB + 1.4 GiB + dir | Drobkov manual (0 % kinked; used by Lat70) | lh False, z top→bottom **True** (ACW) |
| 0826 | ~270 GiB | yes | yes | 5.0 GiB + 1.4 GiB + dir | **official** on S3 | lh False, z top→bottom True (ACW) |
| 0211 | ~305 GiB | yes | yes | 7.0 GiB + 1.9 GiB + dir | **official** on S3 | lh False, z top→bottom True (ACW) |
| 0175A | ~345 GiB | yes | **missing** | 8.2 GiB + 2.4 GiB + dir | **missing** | lh False, z top→bottom True (ACW) |

What our pipeline needs: the spiral fit needs tracks, Lasagna normals and an umbilicus, and the snap needs the m7 prediction.
- 0813, 0358, 0826 and 0211 have everything published. 0813 and 0358 need an umbilicus check (Drobkov's curve against
  `vc_gen_umbilicus` from the normal grids, then our ray-peak audit).
- 0175A lacks Lasagna normals. We would have to run `scrollprize/lasagna` (public on Hugging Face) ourselves, at least over
  the fit band, and make our own umbilicus from its normal grids (we already do this for 0191).
- No eligible scroll has published ink predictions or team segments on S3, except 0800 (6 segments) and 1203.
- A newer 9 µm surface model distilled from 2.4 µm predictions (Ben Kyles, August Progress Prize) is not on S3 for these scrolls.

Box limits: NVMe at about 655 / 938 G after the 2026-10-10 cleanup, so roughly 280 G free. A full CT mirror of any candidate
(270–345 GiB) does not fit unless we delete 0191 data or finish the planned data-layout cleanup. A band mirror does fit:
- CT level 0 for 1000 slices ±64 is about 17–20 GiB, plus the coarser levels.
- Tracks are about 10–17 GiB.
- Lasagna levels 2–4 are about 12–18 GB, or only the band's chunk rows (bnleft packed a band in 4.6 min).
- m7 for the band is about 5 GB.
- Total: about 50–80 GB, roughly 1.5–2.5 h at ~10 MB/s. A full scroll at that rate takes about 9 h in theory and up to ~18 h
  in practice (our 0191 estimate).

## 3. Prior attempts on the candidates

**PHerc0813.**
- pscamillo minimal-route spiral meshes: 75 meshes, screened with ink_9um and Hecate by rodriguescarson (5 of 340 meshes
  across 8 scrolls pass a screen; those maps were sent privately).
- TAUIL corpus survey (71 meshes, 341 cm²): its top candidate is `PHerc0813_z12496_w060`, forward face. Hecate 0.130 against
  0.069 on the known-ink control, but it is a compact band about 12 mm wide with no letterforms. TAUIL calls it "a candidate
  location, not a discovery".
- TAUIL 124 m7-tracked sites (126 cm²): no lead.
- Bullo27: 3 patches, speckle. gmDevi sweeps: 0–1 blobs.
- The candidate sits inside 0813's clearest band (SQM z 12288 = 0.66). SQM stays at 0.6 or above over most of z 8448–14592,
  which is the longest clear stretch of any 9.362 µm scroll.

**PHerc0358.**
- Lat70 fitted z 6000–6500 with tracks only on a 6 GB card. w080 did not stay on one sheet (48 % followed), and no ink model
  was run. That band is 0358's haziest (SQM 0.35–0.36 at z 6144–6912). Its clear bands (z 9216 = 0.73, z 3840 = 0.72,
  z 13056 = 0.67) have never been fitted.
- TAUIL 99 sites (100 cm²): no lead; TAUIL describes the papyrus as "crushed diagonally", "crumpled and folded".
- pscamillo: 3 meshes (9.2 cm²), no letters. Bullo27: 3 patches.

**PHerc0826.**
- Miller & Müller: z 10000–11000, ink_9um only, no ink. That window is SQM 0.63, so scan quality was probably not the limit.
- Scheirer (ShribyrLabs): 3 bands and 21 patches, no letters.
- TAUIL: 150 sites (162 cm²) with Reader v2 + d9v2, seven leads, all isolated marks.
- rodriguescarson: 3 spiral fits, which claudepro1515's audit scores as no closer to the sheets than chance.
- The scroll is crushed flat (aspect 2.20), which is hard for the spiral fitter. It has the most competition.

**PHerc0211.**
- armando-gaona: z 8000–9000, null, with 5× lower render contrast than a curated mesh.
- bnleft: z 10000–11000, CW and ACW fits, null.
- TAUIL: 110 sites, null. pscamillo: 90 meshes.
- claudepro1515: an ACW refit with a phase term is the first eligible fit above chance; still no ink.

**PHerc0175A.**
- TAUIL: 126 sites (111 cm²), no lead, with more strong sites on the reverse face. Bullo27: 3 patches, speckle.
- gmDevi `p0175A` batch: nothing.
- No spiral fit has been published, because there are no Lasagna normals and no umbilicus.

**PHerc0191.**
- Ours: all 99 flattened windings of z 9000–10000 null at d 0/+1 (7 with four models, 92 with three), plus the 10 community
  windings. The z 11200–12200 fit and snap are done.
- Community: rodriguescarson's fit of z 11600–12400 (no ink result; scored at chance by the audit) and gmDevi's `p0191` batch.
- Drobkov's 0191 umbilicus failed review; we do not use it.

Model notes:
- Ritwik-Gaur (2026-09-18) found ink_9um weak at 116 keV. The 343 win since then shows the four-model ensemble works on an
  8.64 µm / 116 keV scan.
- Reader v2 (DomRusso2, MIT) reports AUC 0.834 at 116 keV against 0.725 for Hecate, with false alarms on blank papyrus of
  10.4 % (Nieuwlaar's dense_native: 10.5 %). It is not in our ensemble yet.
- TAUIL's d9v2/d9v3 and Nader's v8-in are also public.

The 2.4 µm rescans of 0846A and 1203: the Grand Prize rules forbid "data derived from higher resolution scans of the submitted
scroll volume". The First Letters list names the 9.362 µm volume ids. Treat the 2.4 µm data as off-limits for a First Letters
claim unless the team confirms otherwise on Discord.

## 4. Recommendation

**(a) PHerc0191: finish the clear band, with a stop rule.**
- Ink all ~100 snapped windings of z 11200–12200 with the three-model ensemble at d 0/+1, then four models (or add Reader v2)
  at d −1..+2 on the windings with the cleanest weave. Stroke score, then eye check at row scale.
- If nothing passes, stop 0191 work and keep the meshes for later models. This uses free GPU time while the next scroll's
  data downloads, and the two jobs do not compete (one is GPU-bound, the other network-bound).
- Further 0191 bands make sense only if the clear band shows row-aligned strokes, or if a better model appears. Its scan
  clarity is below 0358/0813/0826 on both measures.

**(b) Ranked candidates.**

1. **PHerc0813.**
   - Top three at 9.362 µm on both clarity measures, the roundest cross-section of the original set (1.08), and the
     longest clear z stretch.
   - All inputs published. Orientation flags are the same as 0191, so our scripts and render settings carry over unchanged.
   - One published candidate location (z 12496) inside its clearest band, which one band fit can confirm or rule out.
   - Same protocol as the models' training scrolls. Spiral fits have only been run in the minimal-route configuration;
     nobody has applied snap plus ensemble.
   - Switching cost: ~60–80 GB for a band pilot, or ~330 GB for the full set.
2. **PHerc0358.**
   - The clearest 9.362 µm scan on SQM (0.57 median, 47 % clear, best band 0.73) and essentially tied with 0813 on modulation.
   - All inputs published, and the smallest volume (~275 GiB CT).
   - The only spiral fit so far was in its haziest band. The risks are the "crushed diagonally / folded" description and
     the flipped z direction (z_top_to_bottom True, sense ACW), which needs our orientation and air-gap check repeated.
   - Switching cost: ~50–70 GB for a band, or ~300 GB full.
3. **PHerc0175A.**
   - The clearest 8.64 µm scan on both measures (SQM 0.50 against 0.34 for the won 0343), and the same protocol as both
     eligible scrolls where ink was found.
   - Less competition, because the published workflow cannot run without Lasagna normals.
   - Costs about a day of setup: Lasagna normal inference over the band with `scrollprize/lasagna`, and an umbilicus from
     normal grids.
   - Download: ~345 GiB CT full, or ~70–90 GB band plus tracks.
   - If we do not want to build Lasagna normals, take **PHerc0826** as third instead. It has the best modulation and official
     inputs, but it is flat (aspect 2.20) and the most searched.

**Rough plan for 0813.** Days 0–1 overlap the 0191 clear-band inking.

1. Mirror tracks (dbm, crossings, .vctracks), Lasagna nx/ny/grad_mag levels 2–4 (or band rows), m7 and normal grids for
   z 11900–13100, and CT levels 0–5 for z 11900–13100. Use `bin/mirror_s3*.py` and `bin/mirror_surf_band*.sh` with the new
   volume id `20250821151723`.
2. Write `spiral-scroll.json` (same flags as 0191). Compare Drobkov's umbilicus with `vc_gen_umbilicus`, then run the
   12-ray peak audit at two heights.
3. Fit z 12000–13000 with the exp-30k recipe (tracks, no shell, 30k steps; ~6–8 h on a 3060). Snap to m7, flatten and
   triage the geometry. Then render and ensemble the windings that pass through TAUIL's candidate (z 12496) first, at
   d −2..+2, before the rest of the band.
4. If the geometry is clean but there is no ink, move along the clear stretch: z 8448–9984, then 13056–14592.
5. Add Reader v2 to the ensemble after it reproduces the 343 control. Use paid AWS runs only with Ted's go-ahead per run.
6. Pilot a 0358 band in parallel. Mirror z 8900–9900 (SQM 0.73), fit it on the third GPU, and compare snapped weave with
   0813 before committing the full mirror to either.

## Sources

- Prize terms and eligible lists: https://scrollprize.org/prizes ; https://github.com/ScrollPrize/villa/blob/main/scrollprize.org/src/data/prizeEligibility.json (commits #1593, #1751, #1887)
- Substack (local text): `data/prior-art/substack-50k-first-letters-prize-awarded-for.txt` (343 award, three submissions),
  `substack-multiple-scrolls-now-show-greek-letters.txt`, `substack-finallyletters-in-scroll-4.txt`,
  `substack-the-hard-parts-are-getting-clearer.txt`, `substack-a-new-1m-grand-prize-for-2027.txt`,
  `substack-335k-awarded-in-july.txt`, `substack-from-ct-scan-to-ancient-text-a-first.txt`, `substack-70-of-pherc-172-is-now-digitally.txt`
- Prize winners (August 2026 Progress Prizes): https://scrollprize.org/winners
- Catalog: `data/catalog/metadata.json` (scan protocol, shapes, flags, representations per volume)
- S3 listings: `https://vesuvius-challenge-open-data.s3.amazonaws.com/?list-type=2&prefix=<SCROLL>/...` (volumes, representations/predictions/{surfaces,lasagna}, representations/umbilicus)
- Tracks: https://dl.ash2txt.org/datasets/spiral_datasets/ (no folder for 0846B, 1203, 1218, 1545)
- SQM: https://github.com/jcooperkai-sys/Scan-Quality-Map ; local `data/prior-art/sqm/atlas.json`, `targets.json`
- Sheet modulation and readiness: https://github.com/claudepro1515/first-letters-scan-atlas ; fit audit: https://github.com/claudepro1515/first-letters-fit-audit
- Morphology: https://github.com/TAUIL-Abd-Elilah/eligible-volume-morphology
- 0826: https://github.com/millerandmuller/first-light-pherc0826 ; https://github.com/ShribyrLabs/vesuvius-reports ; https://github.com/TAUIL-Abd-Elilah/pherc0826-first-letters-search (also 0358/0813/0175A/0343/0211/0483B sites and the 343 correction)
- 0358: https://github.com/Lat70/first-light-pherc0358
- 0211: https://github.com/bnleft/first-light-pherc0211 ; https://github.com/armando-gaona/pherc0211-first-letters-free-compute
- 0813 candidate: https://github.com/TAUIL-Abd-Elilah/corpus-ink-survey
- Community meshes and screens: https://github.com/rodriguescarson/eligible-scroll-atlas ; pscamillo/vesuvius-eligible-meshes; gmDevi/vesuvius-ink-sweeps (see `notes/campaign-plan.md`)
- Survey patches: https://github.com/Bullo27/first-letters-survey ; 1203: https://github.com/robertlangdonn/pherc1203-readability-atlas ; 0846A: https://github.com/alexxxmur/vesuvius-pherc0846a-2p4um ; https://github.com/ArcheyChen/vesuvius-eligible-scouting
- 1447 removal and recipe: https://github.com/nerln/vesuvius-first-letters-pherc0800 ; https://github.com/TAUIL-Abd-Elilah/pherc1447-ink-survey
- Umbilici: https://github.com/AlexeyDrobkovStrikesBack/herculaneum-umbilici
- Models: https://github.com/DomRusso2/reader-v2 ; https://github.com/Ritwik-Gaur/vesuvius-energy-transfer ; https://huggingface.co/scrollprize (ink_9um, hecate, lasagna)
- Our work: `notes/results-2026-10-09.md`, `notes/prior-art-digest.md`, `notes/campaign-plan.md`, `notes/data-inventory-2026-10-10.md`, `memory/handoff-runbook.md`

Caveats: the clarity measures are associations, not predictors of where ink lies. The CT sizes are estimates. Prize-page
status is as of 2026-10-09 (0343 not yet removed from the page). Community claims are as stated in their READMEs and were
not re-run here.
