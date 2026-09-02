"""M-PHASE0-ZFIELD -- verify the research note.

Independence is the point. This file does NOT import zflib. Every DERIVED check
re-implements the estimator from the preregistration's description and recomputes
from the primary NPY cubes or from pure kernel arithmetic. A checker that imported
the lane's own library would be a transcription test wearing a verifier's clothes
(house rule 35).

Three provenance classes, counted separately:
  DERIVED  recomputed here from primary data or first principles
  PINNED   the note's number equals the run's stored JSON, to 1e-9 or a stated tol
  CLAIM    a stated sentence is present

Env overrides: NOTE_PATH, CENSUS_PATH, VERDICT_PATH, CONTROLS_PATH.
"""

import json
import os
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
LANE = pathlib.Path(__file__).resolve().parents[1]
M66 = ROOT / "experiments" / "M66-gate-n-dependence" / "data"

NOTE = pathlib.Path(os.environ.get("NOTE_PATH", ROOT / "docs" / "research" / "M-PHASE0-ZFIELD.md"))
CENSUS = pathlib.Path(os.environ.get("CENSUS_PATH", LANE / "out" / "z1-census.json"))
VERDICT = pathlib.Path(os.environ.get("VERDICT_PATH", LANE / "out" / "z5-verdict.json"))
CONTROLS = pathlib.Path(os.environ.get("CONTROLS_PATH", LANE / "out" / "z2-controls.json"))

TEXT = NOTE.read_text(encoding="utf-8").replace("\r\n", "\n")
FLAT = re.sub(r"\s+", " ", TEXT)
CEN = json.loads(CENSUS.read_text(encoding="utf-8"))
VER = json.loads(VERDICT.read_text(encoding="utf-8"))
CTL = json.loads(CONTROLS.read_text(encoding="utf-8"))
CTL_BY = {r["control"]: r for r in CTL["results"]}

PASSED, FAILED, SKIPPED = [], [], []


def chk(kind, name, ok, detail=""):
    (PASSED if ok else FAILED).append((kind, name, detail))


def near(a, b, tol=1e-9):
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def row(label):
    """A markdown table row from the note, as a list of trimmed cells."""
    m = re.search(r"^\|\s*" + re.escape(label) + r"\s*\|(.+)$", TEXT, re.M)
    if not m:
        return None
    return [c.strip() for c in m.group(1).split("|") if c.strip() != ""]


def pct(cell):
    m = re.search(r"(-?[\d.]+)\s*%", cell)
    return float(m.group(1)) if m else None


def num(cell):
    m = re.search(r"(-?[\d.]+(?:[eE]-?\d+)?)", cell.replace("**", ""))
    return float(m.group(1)) if m else None


def says(phrase, name):
    pat = re.compile(r"\s+".join(re.escape(t) for t in phrase.split()))
    chk("CLAIM", name, bool(pat.search(TEXT)), phrase[:70])


# --------------------------------------------------------------- DERIVED: kernels
def d_kernels():
    """F is pure arithmetic; re-derive it with no reference to the lane's code."""
    def sq(k):
        k = np.asarray(k, float)
        k = k / k.sum()
        return float((k * k).sum())
    s27, s17, s5 = sq(np.ones(27)), sq(np.ones(17)), sq(np.ones(5))
    casc = sq(np.convolve(np.ones(27) / 27, np.ones(17) / 17))
    f = np.sqrt(s5 ** 2 / casc ** 2)
    f_lo = np.sqrt(s5 ** 2 / s27 ** 2)
    for label, got in (("`box27` 0.037037", s27), ("`box17` 0.058824", s17),
                       ("their cascade 0.029291", casc), ("`box5` 0.2", s5)):
        want = float(re.search(r"([\d.]+)$", label).group(1))
        chk("DERIVED", f"kernel {label}", abs(got - want) <= 5e-6,
            f"recomputed {got:.6f} vs note {want}")
    chk("DERIVED", "2D cascade 8.579e-4", abs(casc ** 2 - 8.579e-4) <= 5e-7,
        f"recomputed {casc ** 2:.6e}")
    chk("DERIVED", "F = 6.83", abs(f - 6.83) <= 0.005, f"recomputed {f:.4f}")
    chk("DERIVED", "F lower bound 5.40", abs(f_lo - 5.40) <= 0.005,
        f"recomputed {f_lo:.4f}")
    chk("DERIVED", "note states F=6.83", "6.83" in TEXT)
    chk("DERIVED", "note states F lower bound 5.40", "5.40" in TEXT)


# --------------------------------------------------------- DERIVED: from the cubes
def sr_indep(cube):
    """sigma_r, re-implemented from the preregistration's description."""
    c = cube.astype(np.float64)
    d = c[4:] - 4 * c[3:-1] + 6 * c[2:-2] - 4 * c[1:-3] + c[:-4]
    mad = np.median(np.abs(d - np.median(d, axis=0)), axis=0)
    return mad / 0.674489750196082 / np.sqrt(70.0)


def d_cubes():
    expect = {"109MSDCF": 22, "112MSDCF": 79, "113MSDCF": 63, "119MSDCF": 33,
              "bee-1": 299, "coffee-bean": 105, "coffee-bubbles": 19, "foam": 100}
    for s, n in expect.items():
        p = M66 / f"{s}-d4.npy"
        if not p.exists():
            SKIPPED.append(("DERIVED", f"cube {s}", "npy absent"))
            continue
        a = np.load(p, mmap_mode="r")
        r = row(s)
        chk("DERIVED", f"{s} n_frames from npy", a.shape[0] == n and r is not None
            and int(num(r[0])) == n, f"npy {a.shape[0]}, note {r[0] if r else '-'}")
        chk("DERIVED", f"{s} shape 586x879", a.shape[1:] == (586, 879), str(a.shape))
        chk("PINNED", f"{s} n_frames vs census", a.shape[0] == CEN["stacks"][s]["1"]["n_frames"])


def d_sigma_r():
    """Independent sigma_r must match the lane's stored value on the same cube."""
    a = np.asarray(np.load(M66 / "113MSDCF-d4.npy", mmap_mode="r")[:, 200:328, 300:428],
                   dtype=np.float32)
    mine = float(np.median(sr_indep(a)))
    note = None
    m = re.search(r"this lane reads ([\d.]+) where M69", FLAT)
    if m:
        note = float(m.group(1))
    chk("DERIVED", "sigma_r on 113MSDCF crop", note is not None and abs(mine - note) <= 5e-4,
        f"recomputed {mine:.4f} vs note {note}")
    det = CTL_BY.get("C3' sigma_r truth test", {}).get("detail", "")
    chk("PINNED", "C3' recorded GREEN", CTL_BY.get("C3' sigma_r truth test", {}).get("pass") is True)
    m2 = re.search(r"worst error ([\d.]+)%", det)
    chk("PINNED", "C3' worst error 0.74%", m2 is not None and abs(float(m2.group(1)) - 0.74) <= 0.005,
        det[:60])


def d_autocorr():
    """Noise correlation lags, re-implemented, must reproduce the note's 8 and 12."""
    a = np.asarray(np.load(M66 / "113MSDCF-d4.npy", mmap_mode="r"), dtype=np.float32)
    c = a.astype(np.float64)
    d = c[4:] - 4 * c[3:-1] + 6 * c[2:-2] - 4 * c[1:-3] + c[:-4]
    idx = np.sort(np.random.default_rng(0).choice(d.shape[0], 8, replace=False))
    f = d[idx]
    f = f - f.mean(axis=(1, 2), keepdims=True)
    den = float((f * f).mean())
    lags = {}
    for ax, nm in ((2, "x"), (1, "y")):
        L = 0
        for lag in range(1, 25):
            r = float((np.take(f, range(0, f.shape[ax] - lag), axis=ax) *
                       np.take(f, range(lag, f.shape[ax]), axis=ax)).mean()) / den
            if r < 1 / np.e:
                L = lag
                break
        lags[nm] = L
    m = re.search(r"1/e at \*\*(\d+) px in x and (\d+) px in y", TEXT)
    chk("DERIVED", "noise 1/e lag x", m is not None and lags["x"] == int(m.group(1)),
        f"recomputed {lags['x']}, note {m.group(1) if m else '-'}")
    chk("DERIVED", "noise 1/e lag y", m is not None and lags["y"] == int(m.group(2)),
        f"recomputed {lags['y']}, note {m.group(2) if m else '-'}")


def d_neff():
    """n_eff formula re-implemented, checked against the note's 1.54 and 2.19."""
    nc = CEN["stacks"]["113MSDCF"]["1"]["noise_corr"]
    rx, ry = nc["rho_x"], nc["rho_y"]

    def s_of(rho, w):
        t = float(w)
        for dd in range(1, w):
            t += 2.0 * (w - dd) * (rho[dd] if dd < len(rho) else 0.0)
        return t

    def ne(w):
        return max(1.0, min(w ** 4 / (s_of(rx, w) * s_of(ry, w)), float(w ** 2)))

    chk("DERIVED", "n_eff(9x9) = 1.54", abs(ne(9) - 1.54) <= 0.005, f"recomputed {ne(9):.3f}")
    chk("DERIVED", "deflation 53x", abs(81.0 / ne(9) - 53.0) <= 0.5,
        f"recomputed {81.0 / ne(9):.1f}")
    gains = [np.sqrt(ne(w)) for w in (3, 5, 9, 17, 33)]
    want = [1.03, 1.09, 1.24, 1.57, 2.19]
    chk("DERIVED", "pooling gains 1.03/1.09/1.24/1.57/2.19",
        all(abs(g - w) <= 0.005 for g, w in zip(gains, want)),
        ", ".join(f"{g:.2f}" for g in gains))


# ----------------------------------------------------------------- PINNED: tables
def p_census_table():
    for s, arm in ((k, v["1"]) for k, v in CEN["stacks"].items()):
        r = row(s)
        if r is None:
            FAILED.append(("PINNED", f"census row {s}", "row absent from note"))
            continue
        p = arm["partition"]["1.5"]
        w = str(p["best_window"])
        pairs = [
            ("sigma_z p50", num(r[1]), arm["sigma_z_q"]["50"], 5e-4),
            ("sigma_z p95", num(r[2]), arm["sigma_z_q"]["95"], 5e-3),
            ("has signal", pct(r[3]), 100 * arm["frac_with_signal"], 0.05),
            ("plane R2", num(r[4]), arm["zhat_coherence"]["plane_r2_median"], 5e-4),
            ("EASY", pct(r[5]), 100 * p["by_window"][w]["easy"], 0.05),
            ("WINNABLE", pct(r[6]), 100 * p["by_window"][w]["winnable"], 0.005),
            ("LOST", pct(r[7]), 100 * p["by_window"][w]["lost"], 0.05),
        ]
        for nm, got, want, tol in pairs:
            chk("PINNED", f"{s} {nm}", got is not None and abs(got - want) <= tol,
                f"note {got} vs run {want:.4f}")


def p_f_table():
    labels = {"1 (substrate as-is)": "1.0", "2": "2.0", "4": "4.0", "5.40": "5.4",
              "**6.83 (shipping operator)**": "6.83", "8": "8.0", "16": "16.0",
              "32": "32.0", "64": "64.0"}
    summ = VER["f_sensitivity"]["summary"]
    for label, key in labels.items():
        r = row(label)
        if r is None:
            FAILED.append(("PINNED", f"F row {label}", "row absent"))
            continue
        for i, half in ((0, "1.5"), (2, "3.0")):
            k = f"F{float(key)}_half{half}"
            if k not in summ:
                FAILED.append(("PINNED", f"F {key} half {half}", "absent from verdict json"))
                continue
            want = 100 * summ[k]["median_winnable"]
            chk("PINNED", f"F={key} WINNABLE @ {half}", abs(pct(r[i]) - want) <= 0.005,
                f"note {pct(r[i])} vs run {want:.3f}")
            chk("PINNED", f"F={key} verdict @ {half}", summ[k]["verdict"] in r[i + 1],
                f"note {r[i + 1]} vs run {summ[k]['verdict']}")


def p_controls():
    d = CTL_BY.get("C2 planted-zhat (bootstrap)", {}).get("detail", "")
    for want, name in ((0.2634, "empirical sd"), (0.3000, "bootstrap"),
                       (0.1454, "symmetric-point"), (0.1965, "general-offset")):
        chk("PINNED", f"C2 {name} {want}", f"{want:.4f}" in d, d[:60])
    for want in ("1.139", "0.552", "0.746"):
        chk("PINNED", f"C2 ratio {want}", want in d and want in TEXT)
    for n, easy, med in ((22, "90.2", "5.852"), (105, "97.9", "29.663")):
        dd = CTL_BY.get(f"C4 null n={n}", {}).get("detail", "")
        chk("PINNED", f"C4 n={n} analytic EASY {easy}%", easy in dd, dd[:70])
        chk("PINNED", f"C4 n={n} bootstrap median", med[:4] in dd, dd[:70])
    chk("PINNED", "all controls green", CTL["n_fail"] == 0, f"n_fail={CTL['n_fail']}")
    chk("PINNED", "note says 8/8 controls pass",
        bool(re.search(r"All eight controls pass", TEXT)))


def p_verdict():
    nc = VER["native_corpus"]
    for half, wcell in (("1.5", "1.91"), ("3.0", "1.13")):
        chk("PINNED", f"native WINNABLE @ {half}",
            abs(100 * nc[half]["median_winnable"] - float(wcell)) <= 0.005,
            f"run {100 * nc[half]['median_winnable']:.3f}, note {wcell}")
        chk("PINNED", f"native verdict @ {half} is KILL", nc[half]["verdict"] == "KILL")
        chk("PINNED", f"note carries native {wcell}%", f"{wcell}%" in TEXT)
    for half, e in (("1.5", "92.1"), ("3.0", "94.4")):
        chk("PINNED", f"native EASY @ {half}",
            abs(100 * nc[half]["median_easy"] - float(e)) <= 0.05,
            f"run {100 * nc[half]['median_easy']:.2f}, note {e}")


# -------------------------------------------------------------------- CLAIM checks
def claims():
    says("A5 survives its phase-0 kill gate, and it survives on a margin that the "
         "substrate itself was hiding", "headline is survive")
    says("SURVIVE, NOT ROBUST", "verdict is not robust")
    says("This does not license A5", "does not license A5")
    says("B1 as registered is incomplete, and the omitted half is the one that "
         "decides this lane", "B1 incomplete disclosed")
    says("without the F analysis this lane would have reported KILL", "near miss stated")
    says("A5 anticipated failure by", "A5's expectation named")
    says("the risk to A5 is not that depth cannot be estimated but that it is already "
         "estimated well enough per-pixel", "risk re-pointed at EASY")
    says("The verdict is an extrapolation", "extrapolation disclosed")
    says("The white-noise assumption is conservative in the survive direction",
         "F assumption direction stated")
    says("errs **conservative**, which is a bias against A5", "bootstrap bias direction")
    says("Agreement was the wrong test", "C3 replacement disclosed")
    says("That is my error, not a finding", "sigma_z derivation error owned")
    says("The kill would be by **EASY saturation**, not by LOST saturation",
         "kill mechanism named")
    says("a deliberate generosity to A5, so that a kill would be unimpeachable",
         "window generosity disclosed")
    says("Pooling gain must be quoted as measured `n_eff`, never window area",
         "n_eff proposal ask")
    says("is a units error", "units error disclosed")


def main():
    d_kernels()
    d_cubes()
    d_sigma_r()
    d_autocorr()
    d_neff()
    p_census_table()
    p_f_table()
    p_controls()
    p_verdict()
    claims()

    total = len(PASSED) + len(FAILED) + len(SKIPPED)
    for kind, name, det in FAILED:
        print(f"  FAIL [{kind}] {name}: {det}")
    for kind, name, det in SKIPPED:
        print(f"  SKIP [{kind}] {name}: {det}")
    by = {}
    for kind, _, _ in PASSED:
        by[kind] = by.get(kind, 0) + 1
    print(f"\n  passed {len(PASSED)}  failed {len(FAILED)}  skipped {len(SKIPPED)}"
          f"  = {total} checks")
    print("  passed by provenance: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    print("  GREEN" if not FAILED and not SKIPPED else "  RED")
    return 1 if (FAILED or SKIPPED) else 0


if __name__ == "__main__":
    raise SystemExit(main())
