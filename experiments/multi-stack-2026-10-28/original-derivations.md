# Derivations

Every DERIVED number in the proposal comes from this script and its output below. It reads no RAW and runs with plain Python 3: `python3 -I derive.py`.

Inputs are corpus constants: λ = 0.55 µm, 5.12 µm pitch, m = 2.7198 (M84b), pupil factor 1.31–1.94 (M88), 7032 px width. Two are assumptions, not measurements: a 30% tile overlap, and D = 120, 200 or 260 mm.

## Script

```python
"""Derivations for the multi-bracket proposal. Inputs are corpus constants
quoted from the strehl repo docs (cited in the proposal); nothing here reads RAW."""
import math

lam_mm = 0.55e-3            # green, mm
pitch_mm = 5.12e-3          # A7C II pixel pitch (AGENTS reference rig)
m = 2.7198                  # M84b magnification
p_lo, p_hi = 1.31, 1.94     # M88 pupil factor bracket
width_px = 7032             # active area width

def mtf(nu, n_eff):
    nc = 1.0 / (lam_mm * n_eff)
    x = nu / nc
    if x >= 1: return 0.0
    phi = math.acos(x)
    return (2 / math.pi) * (phi - math.cos(phi) * math.sin(phi))

nyq = 1 / (2 * pitch_mm)
freqs = {"R/B plane Nyquist": nyq / 2, "green diagonal Nyquist": nyq / math.sqrt(2),
         "sensor Nyquist": nyq, "1.5x lattice Nyquist": 1.5 * nyq, "2x lattice Nyquist": 2 * nyq}
print(f"sensor Nyquist {nyq:.2f} cy/mm")
for N in (5.6, 11.0):
    ne = (N * (1 + m / p_hi), N * (1 + m / p_lo))
    print(f"\nf/{N}: N_eff {ne[0]:.2f}-{ne[1]:.2f}; cutoff {1/(lam_mm*ne[1]):.1f}-{1/(lam_mm*ne[0]):.1f} cy/mm")
    for name, nu in freqs.items():
        lo, hi = mtf(nu, ne[1]), mtf(nu, ne[0])
        print(f"  {name:24s} {nu:7.2f} cy/mm  MTF {lo*100:5.1f}% .. {hi*100:5.1f}%  mid {(lo+hi)*50:5.1f}%")

# Plane-plus-parallax: image shift difference = s_px * dz / D
step_px = 0.7 * width_px    # 30% overlap tile step
print(f"\ntile step (30% overlap) {step_px:.0f} px = {step_px*pitch_mm/m:.2f} mm at the subject")
Ds = (120.0, 200.0, 260.0)
def par(s, dz, D): return s * dz / D
print("stack-then-stitch residual (subject depth 1/2/5 mm):")
for D in Ds:
    print(f"  D={D:.0f} mm: " + ", ".join(f"{par(step_px, dz, D):6.1f} px" for dz in (1, 2, 5)))
print("per-slice translation: adjacent-slice disagreement for focus step 20/40/60 um:")
for D in Ds:
    print(f"  D={D:.0f} mm: " + ", ".join(f"{par(step_px, dz/1000, D):5.2f} px" for dz in (20, 40, 60)))
print("repeat-pass nudge of 10 / 50 px, sharp content within +-0.1 mm of the focal plane:")
for D in Ds:
    print(f"  D={D:.0f} mm: " + ", ".join(f"{par(s, 0.1, D):6.4f} px" for s in (10, 50)))
print("repeat-pass nudge of 10 / 50 px, defocused content 5 mm off the plane:")
for D in Ds:
    print(f"  D={D:.0f} mm: " + ", ".join(f"{par(s, 5, D):6.3f} px" for s in (10, 50)))

# Rotation about a point d mm from the entrance pupil, one tile step of view change
print("rotation panorama: parallax per mm of pupil offset, 5 mm deep subject:")
step_subject_mm = step_px * pitch_mm / m
for D in Ds:
    theta = step_subject_mm / D
    per_mm = theta * m * (5 / D) / pitch_mm
    print(f"  D={D:.0f} mm: theta {math.degrees(theta):.2f} deg, {per_mm:.2f} px per mm of offset; "
          f"offset for 0.5 px: {0.5/per_mm:.2f} mm")

# Depth of field at f/5.6 for a 2 px blur circle: total DOF = 2 N_eff c / m^2
c_mm = 2 * pitch_mm
for ne in (5.6 * (1 + m / p_hi), 5.6 * (1 + m / p_lo)):
    print(f"f/5.6, N_eff {ne:.2f}: DOF = +-{ne * c_mm / m**2 * 1000:.1f} um")

# Canvas memory, per-worker accumulators scale with canvas area
per_worker_mb = 1328
for name, (nx, ny) in {"2x1": (2, 1), "3x3": (3, 3)}.items():
    area = (1 + 0.7 * (nx - 1)) * (1 + 0.7 * (ny - 1))
    print(f"canvas {name}: {area:.2f}x frame area -> {per_worker_mb*area/1024:.2f} GiB per worker vs 6 GiB budget")

# Noise-model propagation for a K-frame average: sigma^2 = g S + (RN g)^2 -> /K
g, RN, S, K = 0.2289, 4.20, 3000.0, 3
lhs = (g * S + (RN * g) ** 2) / K
g2, RN2 = g / K, RN * math.sqrt(K)
rhs = g2 * S + (RN2 * g2) ** 2
print(f"\nK-average noise model check: (g/K, RN*sqrt(K)) reproduces sigma^2/K: {lhs:.6f} vs {rhs:.6f}")
```

## Output

```text
sensor Nyquist 97.66 cy/mm

f/5.6: N_eff 13.45-17.23; cutoff 105.5-135.2 cy/mm
  R/B plane Nyquist          48.83 cy/mm  MTF  43.3% ..  55.0%  mid  49.1%
  green diagonal Nyquist     69.05 cy/mm  MTF  23.1% ..  37.9%  mid  30.5%
  sensor Nyquist             97.66 cy/mm  MTF   2.4% ..  16.8%  mid   9.6%
  1.5x lattice Nyquist      146.48 cy/mm  MTF   0.0% ..   0.0%  mid   0.0%
  2x lattice Nyquist        195.31 cy/mm  MTF   0.0% ..   0.0%  mid   0.0%

f/11.0: N_eff 26.42-33.84; cutoff 53.7-68.8 cy/mm
  R/B plane Nyquist          48.83 cy/mm  MTF   3.3% ..  17.9%  mid  10.6%
  green diagonal Nyquist     69.05 cy/mm  MTF   0.0% ..   0.0%  mid   0.0%
  sensor Nyquist             97.66 cy/mm  MTF   0.0% ..   0.0%  mid   0.0%
  1.5x lattice Nyquist      146.48 cy/mm  MTF   0.0% ..   0.0%  mid   0.0%
  2x lattice Nyquist        195.31 cy/mm  MTF   0.0% ..   0.0%  mid   0.0%

tile step (30% overlap) 4922 px = 9.27 mm at the subject
stack-then-stitch residual (subject depth 1/2/5 mm):
  D=120 mm:   41.0 px,   82.0 px,  205.1 px
  D=200 mm:   24.6 px,   49.2 px,  123.1 px
  D=260 mm:   18.9 px,   37.9 px,   94.7 px
per-slice translation: adjacent-slice disagreement for focus step 20/40/60 um:
  D=120 mm:  0.82 px,  1.64 px,  2.46 px
  D=200 mm:  0.49 px,  0.98 px,  1.48 px
  D=260 mm:  0.38 px,  0.76 px,  1.14 px
repeat-pass nudge of 10 / 50 px, sharp content within +-0.1 mm of the focal plane:
  D=120 mm: 0.0083 px, 0.0417 px
  D=200 mm: 0.0050 px, 0.0250 px
  D=260 mm: 0.0038 px, 0.0192 px
repeat-pass nudge of 10 / 50 px, defocused content 5 mm off the plane:
  D=120 mm:  0.417 px,  2.083 px
  D=200 mm:  0.250 px,  1.250 px
  D=260 mm:  0.192 px,  0.962 px
rotation panorama: parallax per mm of pupil offset, 5 mm deep subject:
  D=120 mm: theta 4.42 deg, 1.71 px per mm of offset; offset for 0.5 px: 0.29 mm
  D=200 mm: theta 2.65 deg, 0.62 px per mm of offset; offset for 0.5 px: 0.81 mm
  D=260 mm: theta 2.04 deg, 0.36 px per mm of offset; offset for 0.5 px: 1.37 mm
f/5.6, N_eff 13.45: DOF = +-18.6 um
f/5.6, N_eff 17.23: DOF = +-23.8 um
canvas 2x1: 1.70x frame area -> 2.20 GiB per worker vs 6 GiB budget
canvas 3x3: 5.76x frame area -> 7.47 GiB per worker vs 6 GiB budget

K-average noise model check: (g/K, RN*sqrt(K)) reproduces sigma^2/K: 229.208084 vs 229.208084
```
