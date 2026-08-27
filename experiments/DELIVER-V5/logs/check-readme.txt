=== counts on disk vs what the README claims ===
  [PASS] crops-on-disk              78 crop PNGs on disk, README says 78
  [PASS] overviews-on-disk          26 overview PNGs on disk, README says 26
  [PASS] manifest-consistent        manifest lists 26 images and 78 crops
  [PASS] what-stacking-does         carried forward, 3 files
  [PASS] known-defects              the dust evidence file ships

=== every claimed number is in the log that produced it ===
  [PASS] rim-zero                   verify.txt reports max rim 0.000000000 DN and the README states it
  [PASS] neg-control                104 of 104 planted corruptions caught
  [PASS] byte-equality              verify.txt asserts byte equality, not closeness
  [PASS] commission-36              commissioning partition pass 36 + fail 0 = 36 of 36, README says 36 arms
  [PASS] nearest-arm                the nearest-neighbour arm -- the one that cannot ring -- is in the log
  [PASS] blind-declared             the blindness is declared in both
  [PASS] overview-limit             the 4x reduction's resolution limit AND the probe's non-triviality
  [PASS] crosscheck-17.1256         17.1256 appears in crosscheck.txt and in the README
  [PASS] crosscheck-36.9970         36.9970 appears in crosscheck.txt and in the README
  [PASS] crosscheck-13.4237         13.4237 appears in crosscheck.txt and in the README
  [PASS] min-resolved               the one disagreement is resolved to a definition in both
  [PASS] dust-underpowered          the whole-frame arms are called underpowered in both
  [PASS] dust-not-reproduced        the decisive arm's -0.78%% is in the log and the README
  [PASS] dust-14of14                14 of 26 flat+bright subjects, both places
  [PASS] dust-ratios                the null ratios are in the logs and the README

=== claims the README must NOT make ===
  [PASS] absent:halo[- ]free        1 occurrence(s), all negated -- this gallery does not measure the merge
  [PASS] absent:\bproves the (merg  0 occurrence(s), all negated -- the rim statistic cannot say that
  [PASS] absent:dust (is|was) (abs  0 occurrence(s), all negated -- not established; arms were underpowered

=== positive control: the relaxed filter must still convict ===
  [PASS] filter-can-convict         planted an unqualified 'halo-free' claim: filter fired 1 time(s)
  pass 24 + fail 0 = 24 of 24   OK

VERDICT: every load-bearing number in the shipped README is traceable to the log that produced it, and the counts match the files on disk
