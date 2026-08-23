import rawpy, numpy as np, glob, os
BLACK, CWL, CONT = 512, 15360, 16383

d = r"D:\personal\macro\coffee-bubbles"
fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
print(f"coffee-bubbles: {len(fs)} frames, ISO 1000, 2.5 s")

# green plane (raw_pattern [[0,1],[3,2]] -> G at (0,1) and (1,0)); take the (0,1) sublattice
ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)
cube = []
for f in fs:
    with rawpy.imread(f) as r:
        cube.append(r.raw_image_visible[ys, xs].astype(np.float32))
cube = np.stack(cube)                      # (n, H, W)
print("cube:", cube.shape, cube.dtype, f"{cube.nbytes/1e9:.2f} GB")

mean = cube.mean(0)
std  = cube.std(0, ddof=1)

# NOTE: frames are NOT aligned. Breathing inflates std for textured pixels.
# That biases AGAINST the hypothesis (it inflates the comparison group less than
# it inflates saturated blobs' neighbours), so a near-zero result is conservative.
g = 1000/436.8
def sigma_model(S):                        # S = signal above black, in DN
    return np.sqrt(np.maximum(g*S, 0) + (1.47*g)**2)

print()
print("cross-frame std vs modelled sigma, binned by mean level")
print(f"{'bin (mean DN)':>22}{'n':>12}{'obs std':>10}{'model sig':>11}{'obs/model':>11}")
bins = [(512,1000),(1000,2000),(2000,4000),(4000,8000),(8000,12000),
        (12000,15000),(15000,15360),(15360,16300),(16300,16384)]
rows=[]
for lo,hi in bins:
    m = (mean>=lo)&(mean<hi)
    n = int(m.sum())
    if n < 50: 
        print(f"{f'[{lo},{hi})':>22}{n:>12,}{'--':>10}{'--':>11}{'--':>11}")
        continue
    o = float(np.median(std[m]))
    s = float(np.median(sigma_model(mean[m]-BLACK)))
    rows.append((lo,hi,n,o,s))
    print(f"{f'[{lo},{hi})':>22}{n:>12,}{o:>10.1f}{s:>11.1f}{o/s:>11.3f}")

print()
# the sharp test: pixels saturated in EVERY frame
allsat = (cube >= CONT).all(0)
anysat = (cube >= CONT).any(0)
print(f"pixels at container max in ALL {len(fs)} frames : {int(allsat.sum()):,}")
print(f"pixels at container max in ANY frame           : {int(anysat.sum()):,}")
if allsat.sum() > 0:
    print(f"  their cross-frame std                       : {float(std[allsat].max()):.4f} (max), {float(std[allsat].mean()):.4f} (mean)")
    print(f"  modelled sigma at that level                : {float(sigma_model(CONT-BLACK)):.1f} DN")
    print(f"  => a spread-based confidence would rank them {float(sigma_model(CONT-BLACK))/max(float(std[allsat].mean()),1e-6):.0f}x MORE reliable than truth")
# compare against a moderate-signal control matched for count
ctrl = (mean>=4000)&(mean<8000)
print(f"control [4000,8000): n={int(ctrl.sum()):,}  median std={float(np.median(std[ctrl])):.1f}")
