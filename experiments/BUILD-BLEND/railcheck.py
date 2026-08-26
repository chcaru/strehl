"""Why does coffee-bean's microC fall 33% while its flat-region noise rises 11x?

Two instruments disagree in sign on the same pair, which on this project means
one of them is measuring something other than what its name says. The suspect is
saturation: coffee-bean's backdrop sits near the white rail, and a control whose
backdrop is CLIPPED is flat by arithmetic rather than by being clean. Every
"noise ratio" against a clipped reference is then a ratio against zero.

So this asks the only questions that separate those cases, on the raw pixels:

  1. what fraction of each arm is at or near the white rail
  2. what the backdrop's local std actually is, measured only where the CONTROL
     is not clipped, so the comparison is not a ratio against a rail
  3. the same split for the subject interior, which is where a real softening
     would have to show up

Never open a 16-bit TIFF with PIL. tifffile, and assert the dtype.
"""

import sys

import numpy as np
import tifffile

CTRL, TREAT = sys.argv[1], sys.argv[2]


def load(p):
    im = tifffile.imread(p)
    assert im.dtype == np.uint16, f"{p}: expected uint16, got {im.dtype}"
    return im


a, b = load(CTRL), load(TREAT)
assert a.shape == b.shape, (a.shape, b.shape)
ga, gb = a[:, :, 1].astype(np.float32), b[:, :, 1].astype(np.float32)

print(f"ctrl  {CTRL}")
print(f"treat {TREAT}")
print(f"shape {a.shape}\n")

RAIL = 65535
for name, im in (("ctrl", a), ("treat", b)):
    at = float((im == RAIL).mean() * 100)
    near = float((im >= RAIL * 0.99).mean() * 100)
    print(f"{name:6s} at white rail {at:7.4f}%   within 1% of rail {near:7.4f}%   "
          f"max {int(im.max())}")
print()


def local_std(g, k=8):
    h, w = g.shape
    th, tw = h // k * k, w // k * k
    t = g[:th, :tw].reshape(th // k, k, tw // k, k).swapaxes(1, 2).reshape(-1, k * k)
    return t.std(axis=1), t.mean(axis=1)


sa, ma = local_std(ga)
sb, mb = local_std(gb)

# Backdrop = bright tiles. Subject = dark tiles. Split on the CONTROL only, so
# both arms are scored on an identical pixel population.
thr = np.quantile(ma, 0.5)
back = ma > thr
subj = ~back

# The clipped-control guard: a tile whose control mean is within 1% of the rail
# cannot report noise, because it has none left to report.
unclipped = ma < RAIL * 0.99

print(f"tiles {len(sa):,}   backdrop {back.mean()*100:.1f}%   "
      f"control tiles clear of the rail {unclipped.mean()*100:.1f}%\n")

print(f"{'population':<34}{'ctrl std':>11}{'treat std':>11}{'ratio':>9}")
print("-" * 65)
for label, m in (
    ("backdrop (all)", back),
    ("backdrop, control clear of rail", back & unclipped),
    ("subject interior", subj),
    ("everything", np.ones_like(back)),
):
    if m.sum() == 0:
        print(f"{label:<34}{'--':>11}{'--':>11}{'--':>9}   (empty)")
        continue
    ca, cb = float(np.median(sa[m])), float(np.median(sb[m]))
    r = cb / ca if ca > 0 else float("inf")
    print(f"{label:<34}{ca:11.2f}{cb:11.2f}{r:9.4f}   n={m.sum():,}")

print()
print("READING")
print("  If the backdrop ratio collapses toward 1 once rail-clipped control")
print("  tiles are excluded, the 11x was a ratio against the white rail and not")
print("  a noise measurement. If the SUBJECT INTERIOR std falls materially,")
print("  that is a real softening and no amount of backdrop argument excuses it.")
