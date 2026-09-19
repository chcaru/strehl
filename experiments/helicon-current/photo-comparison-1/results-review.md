# Independent fixed-region review

MEASURED preparation command:
`python -X faulthandler experiments/helicon-current/compare.py`.
It completed successfully in4.83s wall time reported by the command tool.
This reads completed workspace images only: no RAW, development or merge.
The coordinate receipt binds all five inputs, helper, frozen regions and crops.

The same scene is established by distributed structural correspondences, not
equal output coordinates. A similarity fitted on alternate384-native cells
was checked on the other cells without filtering their reported residuals:

| Output | Scale versus Strehl | Held-out median / p95 native pixels | Held-out within8 pixels |
| --- | --- | --- | --- |
| Helicon B | 1.01072485 | 0.720 / 3.964 | 98.773% |
| Helicon C | 1.01069721 | 0.900 / 3.978 | 98.759% |
| Fork | 0.99974735 | 0.814 / 4.356 | 98.488% |

Large mismatches remain explicitly recorded, including repeated-feature
outliers over2000 pixels. They are not correspondence truth. Each fixed region
has15–96 held-out matches within700 native pixels; local medians are0.54–2.16
pixels. Bright-facet has the sparsest/least precise local check. The receipt
and landmark files retain all point pairs and the train/test assignment.
I also inspected the B held-out landmark overview for matching scene structure.

All crops contain384x384 unresampled native samples, centred using the fitted
mapping. Helicon's approximately1.07% scale difference is retained: opposite
crop edges can differ by about4 native pixels of field width. These views can
judge the conspicuous rays and regional appearance; they do not support a
subpixel-resolution claim. The complete images have not been locally warped
to manufacture a match.

VERIFIED: baseline, green-match and both Helicon outputs contain byte-identical
2716-byte sRGB profiles (SHA256238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b).
The fork is untagged; its retained invocation requests sRGB. Individual fork
crops remain untagged. Boards display its unchanged code values with the common
sRGB profile and explicitly label that assumption. TIFF samples are reduced to
RGB8 by rounded division by257; source PNG samples are unchanged. No separate
tone normalization, sharpening or spatial interpolation was applied.

## Visual findings

These are qualitative observations of the five frozen boards, inspected
individually and beginning with the background, not calibrated quality scores.

- **Pale background:** green-match is visibly smoother than the baseline and
  Helicon B/C. Helicon B does not win this region; it retains fine grain. The
  fork shows more prominent grain. Broad shading and the visible small marks
  remain across the arms, so the green-match advantage here is not evidence
  about fine crystal resolution.
- **Facet edges:** Helicon B markedly contracts the left glint and removes much
  of its long coloured lateral/downward fan relative to both Strehl arms.
  The neighbouring faceted outline and internal structural boundaries remain
  visible. B is a useful positive comparator for this specific defect. It is
  not artifact-free: residual coloured flare and bright speckled core remain.
  Helicon C gives the glint more expansive bright rays and makes the lower
  border rays conspicuous. The fork replaces much of the clean ray pattern
  with a noisy, enlarged bright patch; that is not an unqualified repair.
- **Fine crystals:** B retains the major diagonal edges, pits and small dark
  inclusion, with a more compact upper central glint. C makes several glints
  and boundaries more contrasty. I cannot establish greater genuine resolved
  detail from that contrast alone. Neither Helicon arm shows a decisive general
  detail advantage over Strehl in this crop. The fork adds visible fine grain.
- **Bright facet:** this frozen crop is mostly smooth field below a dark facet.
  Green-match again has the cleaner field. B does not offer a comparable clear
  advantage here; C and the fork show more texture in the smooth areas. The
  broad facet edge persists in all arms. No claim about an otherwise missing
  bright-highlight region is inferred from this crop's name.
- **Dark inclusion:** B strongly reduces the bottom-left white/coloured rays
  while retaining the nearby crossing crystal boundaries. A diffuse coloured
  residue remains near the bottom border, so the defect is reduced rather than
  eliminated. The two Strehl arms retain the conspicuous long rays; C makes
  several smaller glints stronger too. The fork retains a large noisy bright
  patch and coloured contamination.

The concrete opportunity is to reach B's compact glint behaviour in the two
affected crops while preserving green-match's cleaner smooth fields and the
existing structural detail. The B result demonstrates a better outcome is
available on these prepared sources; it does not identify which part of B's
alignment, focus selection or blending causes it. A new Strehl proposal must
target that observed difference and retain the background/detail controls.

Scope remains one70-frame stack, these two fixed Helicon settings and complete
workflows. TIFF development occurred before external stacking, unlike Strehl's
CFA merge. No universal product ordering, speed, RAW-processing, causal or SOTA
claim follows. Both B and C results are retained, including their disadvantages.
