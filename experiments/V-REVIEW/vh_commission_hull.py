"""Commission vh_hull.py in BOTH directions before trusting a single number."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_hull as V

W, H = 7040, 700


def synth(fn):
    a = np.zeros((H, W), np.float64)
    fn(a)
    return np.clip(np.round(a), 0, 255).astype(np.uint8)


def run(name, a8):
    hi, lo = V.hull_bounds(a8)
    row = []
    for k in ("box", "bilinear", "bicubic", "lanczos"):
        out = V.reduce_f(a8, k)
        s = V.excess_stats(out, hi, lo)
        row.append((k, s["max_excess"], s["max_deficit"], s["frac_gt_1dn"]))
    print("%-34s %s" % (name, " | ".join(
        "%s exc %7.3f dfc %7.3f f>1 %.5f" % r for r in row)))
    return dict((r[0], r[1]) for r in row)


print("== ARM H1  must CATCH: hard step, negative-lobe kernels only ==")
def f_step(a):
    a[:, :W // 2] = 40.0
    a[:, W // 2:] = 200.0
r1 = run("hard step 40->200", synth(f_step))

print("")
print("== ARM H2  must NOT fire: no edge to ring ==")
r2 = run("constant 128", synth(lambda a: a.__setitem__(Ellipsis, 128.0)))
r3 = run("linear ramp 20->230", synth(
    lambda a: a.__setitem__(Ellipsis, np.linspace(20, 230, W)[None, :])))

print("")
print("== ARM H3  must NOT fire: rim is REAL, planted in the master ==")
def f_rim(a):
    a[:, :W // 2] = 40.0
    a[:, W // 2:] = 200.0
    a[:, W // 2:W // 2 + 60] = 240.0        # 60 px bright rim, IN the master
r4 = run("step + real 40 DN rim in master", synth(f_rim))

print("")
print("== ARM H4  must TRACK amplitude (kills amplitude-invariance) ==")
prev = None
for amp in (20, 40, 80, 160):
    def f_amp(a, amp=amp):
        a[:, :W // 2] = 20.0
        a[:, W // 2:] = 20.0 + amp
    r = run("step amplitude %3d DN" % amp, synth(f_amp))
    if prev is not None:
        print("      lanczos ratio vs previous: %.3f" % (r["lanczos"] / prev))
    prev = r["lanczos"]
