"""Classify each subject's POLARITY, so the A/B subject list is a rule not a memory.

The defect ORCH measured is polarity-specific: a dark subject on a bright ground
gets a bright rim and a grey aura; a bright subject on a dark ground does not.
So the subject list for the comparison has to be "every dark-on-bright stack in
the library", and picking that list from memory would quietly make the subject
choice part of the finding.

The statistic, fixed before looking: on the existing gallery JPEG, take the
median luminance of the OUTER 8% frame border as the background level, and the
median of the central 40% box as the subject level. A macro stack is framed on
its subject, so this is a reliable proxy without needing a segmentation.

  polarity = background - subject      (positive => dark subject on bright ground)

These JPEGs are read only to CLASSIFY, never to judge -- an 8-bit 2400 px JPEG
is exactly the wrong thing to judge a few-pixel rim on, which is the whole
reason the A/B renders full-resolution TIFFs.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image  # 8-bit JPEG only; never used for 16-bit TIFF

src = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\gallery")
rows = []
for p in sorted(src.glob("*.jpg")):
    a = np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0
    h, w = a.shape
    by, bx = int(h * 0.08), int(w * 0.08)
    border = np.concatenate([a[:by].ravel(), a[-by:].ravel(),
                             a[:, :bx].ravel(), a[:, -bx:].ravel()])
    cy0, cy1 = int(h * 0.3), int(h * 0.7)
    cx0, cx1 = int(w * 0.3), int(w * 0.7)
    bg, subj = float(np.median(border)), float(np.median(a[cy0:cy1, cx0:cx1]))
    rows.append((bg - subj, bg, subj, p.stem))

rows.sort(reverse=True)
print(f"{'polarity':>9} {'bg':>6} {'subj':>6}  subject")
print(f"{'-'*9} {'-'*6} {'-'*6}  {'-'*40}")
for pol, bg, subj, name in rows:
    mark = "  <-- DARK ON BRIGHT" if pol > 0.15 else ""
    print(f"{pol:9.3f} {bg:6.3f} {subj:6.3f}  {name}{mark}")

picks = [n for pol, _, _, n in rows if pol > 0.15]
print(f"\n{len(picks)} dark-on-bright subjects:")
print(",".join(picks))
