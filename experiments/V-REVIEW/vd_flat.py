"""Build a dust map from flat fields.  No inference required: a mote on a
defocused evenly-lit field is a depression, full stop.

Two INDEPENDENT halves (the two exposure ramps, one with CPL one without) are
accumulated separately so each can check the other.  Anything appearing in only
one half is not a mote on the sensor.
"""
import rawpy, numpy as np, os, glob, json
D = r"C:\dev\strehl-out\V-REVIEW\dust"
os.makedirs(D, exist_ok=True)
SRC = r"D:\personal\macro\flat-fields\flat-fields"
names = json.load(open(r"C:\dev\strehl-out\V-REVIEW\good_flats.json"))
BLACK = 512.0

def bin2(a):
    h, w = a.shape[0]//2*2, a.shape[1]//2*2
    return a[:h:2,:w:2] + a[1:h:2,:w:2] + a[:h:2,1:w:2] + a[1:h:2,1:w:2]

groups = {"rampA": [n for n in names if int(n[3:8]) < 300],
          "rampB": [n for n in names if int(n[3:8]) >= 300]}
for g, ns in groups.items():
    acc = None; k = 0
    for n in ns:
        with rawpy.imread(os.path.join(SRC, n)) as r:
            a = r.raw_image_visible.astype(np.float32) - BLACK
        b = bin2(a)
        b /= np.median(b)                      # normalise exposure, keep shape
        acc = b if acc is None else acc + b
        k += 1
    acc /= k
    np.save(os.path.join(D, "flat_%s.npy" % g), acc.astype(np.float32))
    print("%s: %d frames -> %s  median %.4f  min %.4f  max %.4f"
          % (g, k, acc.shape, np.median(acc), acc.min(), acc.max()))
print("\nbinned flat is sensor/2; sensor coords = 2 x binned coords")
