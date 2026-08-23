import rawpy, numpy as np, glob, os

STACKS = [
    ("109MSDCF",       r"C:\dev\macro\test\109MSDCF",        160),
    ("119MSDCF",       r"C:\dev\macro\test\119MSDCF",         50),
    ("coffee-bean",    r"C:\dev\macro\test\coffee-bean",      50),
    ("112MSDCF",       r"D:\personal\macro\112MSDCF",        500),
    ("113MSDCF",       r"D:\personal\macro\113MSDCF",        500),
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", 1000),
]
BLACK, CWL, CONTAINER = 512, 15360, 16383

print("=== 1. saturation census (3 frames per stack, spread across the bracket) ===")
print(f"{'stack':<16}{'max':>7}{'>=15360':>12}{'==16383':>12}{'frac>=CWL':>12}{'p99.99':>9}")
sat = {}
for name, d, iso in STACKS:
    fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
    idx = [0, len(fs)//2, len(fs)-1]
    mx=0; nc=0; nk=0; tot=0; p=0
    for i in idx:
        with rawpy.imread(fs[i]) as r:
            v = r.raw_image_visible
            mx = max(mx, int(v.max())); nc += int((v>=CWL).sum())
            nk += int((v>=CONTAINER).sum()); tot += v.size
            p = max(p, float(np.percentile(v, 99.99)))
    sat[name] = (mx, nc, nk, tot)
    print(f"{name:<16}{mx:>7}{nc:>12,}{nk:>12,}{nc/tot:>12.3e}{p:>9.0f}")

print()
print("=== 2. as-shot WB multipliers (auto WB -> per stack, not constant) ===")
print(f"{'stack':<16}{'R':>8}{'G':>8}{'B':>8}")
wb = {}
for name, d, iso in STACKS:
    fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
    with rawpy.imread(fs[0]) as r:
        c = np.array(r.camera_whitebalance, float)
        m = c[:3] / c[1]
    wb[name] = m
    print(f"{name:<16}{m[0]:>8.3f}{m[1]:>8.3f}{m[2]:>8.3f}")

print()
print("=== 3. if WB is applied BEFORE the noise-model gate, how wrong is sigma? ===")
print("model: sigma^2(S) = g*S + (RN_e*g)^2,  g = ISO/436.8 DN/e-")
print("after scaling a channel by m:  true sigma^2 = m^2*(g*S + (RN*g)^2)")
print("                          naive model gives  g*(m*S) + (RN*g)^2")
print("=> ratio sigma_true/sigma_naive -> m in the read-limited (shadow) limit,")
print("   and -> sqrt(m) in the shot-limited (highlight) limit.")
print()
print(f"{'stack':<16}{'chan':>5}{'m':>8}{'shadow':>9}{'highlt':>9}")
for name, d, iso in STACKS:
    for ci, cn in ((0,'R'),(2,'B')):
        m = wb[name][ci]
        print(f"{name:<16}{cn:>5}{m:>8.3f}{m:>9.2f}{np.sqrt(m):>9.2f}")
