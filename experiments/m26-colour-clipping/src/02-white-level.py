import rawpy, numpy as np, glob, os

f = sorted(glob.glob(r"C:\dev\macro\test\109MSDCF\*.ARW"))[0]
with rawpy.imread(f) as r:
    print("white_level                :", r.white_level)
    try:
        print("camera_white_level_per_ch  :", r.camera_white_level_per_channel)
    except Exception as e:
        print("camera_white_level_per_ch  : ERR", e)
    v = r.raw_image_visible
    print("raw_image_visible dtype/shape:", v.dtype, v.shape)
    print("observed max               :", int(v.max()))
    print("observed min               :", int(v.min()))
    # histogram of the top end
    top = v[v > 15000]
    print("count > 15000              :", top.size)
    for thr in (15300, 15350, 15359, 15360, 15361, 16000, 16383):
        print(f"  count >= {thr:6d} : {int((v>=thr).sum()):>12d}")
    vals, cnts = np.unique(v[v>15000], return_counts=True)
    order = np.argsort(-cnts)[:8]
    print("  most common values above 15000:", [(int(vals[i]), int(cnts[i])) for i in order])

print()
print("=== check a bright stack too (coffee-bubbles, ISO 1000, 2.5 s) ===")
f2 = sorted(glob.glob(r"D:\personal\macro\coffee-bubbles\*.ARW"))[0]
with rawpy.imread(f2) as r:
    v = r.raw_image_visible
    print("observed max:", int(v.max()), " count>=15360:", int((v>=15360).sum()))
    vals, cnts = np.unique(v[v>15000], return_counts=True)
    order = np.argsort(-cnts)[:8]
    print("  most common above 15000:", [(int(vals[i]), int(cnts[i])) for i in order])
