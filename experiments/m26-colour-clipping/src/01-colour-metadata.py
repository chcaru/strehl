import rawpy, numpy as np, glob, os, sys

STACKS = [
    ("109MSDCF",     r"C:\dev\macro\test\109MSDCF"),
    ("119MSDCF",     r"C:\dev\macro\test\119MSDCF"),
    ("coffee-bean",  r"C:\dev\macro\test\coffee-bean"),
    ("112MSDCF",     r"D:\personal\macro\112MSDCF"),
    ("113MSDCF",     r"D:\personal\macro\113MSDCF"),
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles"),
]

def find(d):
    for pat in ("*.ARW","*.arw"):
        f = sorted(glob.glob(os.path.join(d,pat)))
        if f: return f
    # maybe nested
    f = sorted(glob.glob(os.path.join(d,"**","*.ARW"), recursive=True))
    return f

print("=== per-stack colour metadata ===")
for name, d in STACKS:
    fs = find(d)
    if not fs:
        print(f"{name}: NO ARW FOUND at {d}")
        continue
    with rawpy.imread(fs[0]) as r:
        cw = np.array(r.camera_whitebalance, dtype=float)
        dw = np.array(r.daylight_whitebalance, dtype=float)
        blk = np.array(r.black_level_per_channel, dtype=float)
        print(f"\n--- {name}  (n={len(fs)})  {os.path.basename(fs[0])}")
        print(f"  camera_whitebalance   : {cw}")
        print(f"  daylight_whitebalance : {dw}")
        print(f"  black_level_per_channel: {blk}")
        print(f"  white_level: {r.white_level}   raw_pattern:\n{r.raw_pattern}")
        print(f"  color_desc: {r.color_desc}")
        print(f"  rgb_xyz_matrix:\n{np.array(r.rgb_xyz_matrix)}")
