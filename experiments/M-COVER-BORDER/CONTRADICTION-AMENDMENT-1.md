# M-COVER-BORDER contradiction — amendment 1

Frozen after the first matched 109 score and before any 113 render or score.

The primary fixed-edge safe insets and P3 Scale/Crop mass ratios were computed
as registered. The P4 field named `positive_mass_concentration_ratio` was not:
it divided two independently normalized positive *fractions*. Because the
through-256 and full-plane denominators differ, that quotient is not the
fraction of positive residual mass located within 256 px and can exceed one.

Correction:

1. retain the raw positive residual level sum as well as its normalized
   fraction in each scope;
2. define concentration as
   `positive_level_sum(distance<256) / positive_level_sum(full plane)`;
3. commission an outer-64 defect whose concentration through 256 must be
   exactly one;
4. rerun the 109 score before interpreting P4.

No threshold, edge, deep normalization, safe-inset rule, P2 ladder predicate,
or P3 conserved-error predicate changes.
