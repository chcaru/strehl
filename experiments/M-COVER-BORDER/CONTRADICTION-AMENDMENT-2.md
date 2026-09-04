# M-COVER-BORDER contradiction — amendment 2

Frozen after aggregate 109/113 profiles and before examining any central-window
profile.

The 113 Scale aggregate has a non-minimum nominal tail. The original protocol
would call that a specificity failure because Scale has complete warp
coverage, but the follow-up explicitly requires testing rather than inheriting
that assumption.

Add a negative-control profile on a centered `1024x1024` window whose boundary
is not an emitted-image boundary:

- use the same b7/b2 green ratio and `0.1%` threshold;
- measure distance from the artificial window boundary;
- use deep start 384 and edges
  `0,2,4,8,16,32,64,96,128,160,192,256,320,384`;
- report the same nominal safe-tail statistic and peak.

Interpretation:

- if the physical Scale profile is non-minimum and the central artificial
  boundary also fires, the statistic is demonstrably nonspecific to an output
  boundary on that scene;
- if the central control stays at 8 while the physical Scale boundary fails,
  a genuine Scale boundary-local band-depth effect is supported;
- either result remains distinct from conserved Crop error, which is governed
  by preregistered P3.

Commission the control with: an untouched null; a physical outer-64 defect
that must leave the centered window at 8; and a planted outer-64 ring on the
artificial window that must return 64.
