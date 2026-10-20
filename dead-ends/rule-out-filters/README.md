# Rule-out filters for false marks: didn't work

**Idea.** The ink models also mark blank papyrus. Medicine's computer-aided detection has the same problem and handles it with
a stack of cheap, weak rules, each of which throws out some false candidates while keeping nearly all the real ones. We tried the
same: measure each strong mark a model makes, and drop the ones that fail a rule.

**What we tried.**
- Marks: Reader v2's strong marks at depth +1 (contrast against a 3 mm local mean).
- Known letters: marks centred on the official labels of three held-out PHerc0841 sheets (27 letter marks), and on Erwin
  Nieuwlaar's PHerc. 343 letters. Blank hits: 847 marks on windings of PHerc0813 and PHerc0191 where no writing was found.
- The rules (`venn.py`): one-sidedness (the other face's contrast), agreement with a second model (d9v4C), fibre direction under the
  mark, whether the mark runs along the fibres, CT density, distance to the surface's edge, a line-grid layout around the mark,
  and the fine "crackle" texture of the ink layer. Then the neighbouring turn (`venn_setoff.py`: does the mark repeat at the same
  place one turn in or out?) and the depth profile (`venn_depth.py`: does the mark peak at the surface and fall off away from it?).
- One pass line for every rule, fixed before each run: keep 90 % of the 0841 letter marks, and remove at least 30 % of the blank hits.

**What it showed.**
- Every rule fails. They remove 0 to 23 % of the blank hits at the threshold that keeps 90 % of real letters.
- Two early passes, measured on only 12 letter marks, did not hold up with 27.
- Agreement with a second model looked like a pass (66 % removed), but every mark on the 0841 renders scores high, letter or not.
  It tells the scrolls apart, not ink from no ink.
- On the neighbouring turn the test ran the other way: letter marks repeat there more often than blank marks, because the
  model's 17-layer window reaches the next sheet.
- The depth profile does not separate them either: letter marks and blank hits peak equally (medians 44.3 and 43.9); keeping
  89 % of the letters removes 9 % of the blank hits.
- Marks are not concentrated at the surface's edges or on stretched mesh.

**Why it failed.** At 9 µm a model's strong marks on known text and on blank papyrus look alike on everything we can measure at
the mark itself. Whatever makes a mark real is not in these local numbers.

**What would change it.** A measure from outside the ink models that judges shape over a wider area (several letters at once)
rather than one mark at a time.

Site: https://skuzbucket1.github.io/scroll-prize/#run-ruleout-filters
