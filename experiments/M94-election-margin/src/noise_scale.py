"""TABLE 7 -- the constant-free noise scale vs the shipped constant.

M89's [1,-4,6,-4,1]/6 estimator has an analytic null (E[z^2]=1) and needs no
fitted constant. Applied along the FRAME axis of the focus response it gives a
per-stack response-noise scale `sigma_R_hat` that owes nothing to
FOCUS_NOISE_SD, the constant M69 and M81 both failed to calibrate.

The permuted arm is the estimator's own power control: destroying the frame
ordering should make a 4th difference along that axis explode. If it did not,
the estimator would be measuring something other than frame-axis smoothness.
"""

import json
import pathlib
import re

OUT = pathlib.Path("experiments/M94-election-margin/out")
FOCUS_NOISE_SD = 0.015214

STACKS = [
    ("109MSDCF", 22),
    ("119MSDCF", 33),
    ("112MSDCF", 79),
    ("foam", 100),
    ("coffee-bean", 105),
    ("wrapped-text-1", 130),
    ("bee-3-cpl", 299),
]

RE_RATIO = re.compile(r"median sigma_R_hat / FOCUS_NOISE_SD = ([\d.]+)\s+\(n windows = (\d+)\)")
RE_Q = re.compile(r"sigma_R_hat\s+q0\.01=([\d.]+)\s+q0\.10=([\d.]+)\s+q0\.25=([\d.]+)\s+"
                  r"q0\.50=([\d.]+)\s+q0\.75=([\d.]+)\s+q0\.90=([\d.]+)\s+q0\.99=([\d.]+)")

print("TABLE 7 -- sigma_R_hat (M89 4th-difference, analytic null, NO fitted constant)")
print(f"FOCUS_NOISE_SD (shipped) = {FOCUS_NOISE_SD}")
print()
print(f"{'stack':<16}{'N':>5}{'q50 real':>11}{'/const':>9}{'q50 perm':>11}{'/const':>10}"
      f"{'perm/real':>11}{'win':>6}")

reals, perms = [], []
for name, n in STACKS:
    p = OUT / f"r4-{name}.txt"
    txt = p.read_text(encoding="utf-8", errors="replace")
    ratios = RE_RATIO.findall(txt)
    qs = RE_Q.findall(txt)
    if len(ratios) < 2 or len(qs) < 2:
        print(f"{name:<16} INCOMPLETE ratios={len(ratios)} qs={len(qs)}")
        continue
    r_real, nw = float(ratios[0][0]), int(ratios[0][1])
    r_perm = float(ratios[1][0])
    q_real = float(qs[0][3])
    q_perm = float(qs[1][3])
    reals.append(r_real)
    perms.append(r_perm)
    print(f"{name:<16}{n:>5}{q_real:>11.6f}{r_real:>9.4f}{q_perm:>11.6f}{r_perm:>10.4f}"
          f"{q_perm / q_real:>11.2f}{nw:>6}")

print()
print(f"REAL  ratio to shipped constant: min {min(reals):.4f}  max {max(reals):.4f}")
print(f"PERM  ratio to shipped constant: min {min(perms):.4f}  max {max(perms):.4f}")
print(f"Every real stack lies within [{min(reals):.2f}x, {max(reals):.2f}x] of the "
      f"shipped constant.")
print("The permuted arm is the power control: the same estimator on the same pixels "
      "with the frame axis destroyed.")

# Cross-check the constant is what the instrument says it is.
js = OUT.parent
found = None
for cand in pathlib.Path("C:/dev/strehl-out/M94-election-margin").glob("*/summary.json"):
    d = json.loads(cand.read_text(encoding="utf-8"))
    if "focus_noise_sd" in d:
        found = (cand.name, d["focus_noise_sd"])
        break
print(f"summary.json cross-check: {found}")
