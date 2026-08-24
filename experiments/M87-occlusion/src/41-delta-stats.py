import numpy as np
d = np.load("cache/ship-delta.npy").astype(np.int32)
nz = d[d>0]
print("changed px:", nz.size)
for q in (50,90,99,99.9,100):
    print(f"  p{q:<5}: {np.percentile(nz,q):.1f}")
print("count >  16:", int((d>16).sum()))
print("count >  64:", int((d>64).sum()))
print("count > 128:", int((d>128).sum()))
ys,xs = np.nonzero(d>128)
if ys.size: print("big-delta bbox y", ys.min(), ys.max(), " x", xs.min(), xs.max())
# where is the change concentrated?
h,w = d.shape
sub = d[::8,::8]
print("row profile of mean delta (16 bands):")
bands = np.array_split(sub, 16, axis=0)
print("  ", " ".join(f"{b.mean():.1f}" for b in bands))
