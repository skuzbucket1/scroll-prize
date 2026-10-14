# A machine letter reader on our 9 µm maps

**Idea.** Chase Hendrick's Greek letter reader (github.com/ChaseHendrick/Scrolls, `kit/letterread.py`, Apache-2.0; weights
letters-v2-real, CC BY-NC 4.0) names Greek capitals line by line on ink maps and reports controls with every read: scrambled
copies of the image, orientation, no language model. A first machine check of ink maps before human readers.

**What we did (2026-10-14).** Ran it locally on CPU on our maps of known text: PHerc. 343 w047 and w048 from our own
end-to-end control (14–15 of Erwin Nieuwlaar's letters each; Reader v2 + d9v4C, d 0 and +1) and PHerc0841 ag144 (official
labels; five models), in four orientations, with the letter height measured from the known letters and estimated by the
reader, and the other face of the sheet as a control.

**Why it did not work.** It kept 1–5 letters on windings with 14–15 known letters, about as many as on its own scrambled
copies and as many on the other face; 0–3 on PHerc0841. Its letter-height guess fell back to a default on our maps. Its author
shows it working on 2.4 µm maps; ours are 9 µm and softer. It would need fine-tuning on 9 µm maps of transcribed text, and we
do not have enough of that (PHerc. 343 has 18 letters).

Site: https://skuzbucket1.github.io/scroll-prize/#run-letter-reader-9um
