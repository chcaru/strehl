"""Does this flag reach a pixel?

Three features of this tool have now been found to be documented, banner-reported,
tested, and inert: `--exposure` / `--auto-exposure` (an 8x darkening changed zero
of 98,898,048 samples while the banner said it was applied), `STREHL_ROBUST_ELECTION`
(the constants were quoted correctly in a report; the code never executes), and
`outlier.rs` (reachable only from `examples/`). All three were found by accident,
by three parties who were looking for something else.

Finding them by accident does not scale. This is the accident made systematic.

The method is one rule:

    A flag is not wired until an ABSURD value has visibly changed the output.

A *small* measured difference is indistinguishable from a small correctly-chosen
one, and that ambiguity is exactly where dead code lives. So every probe here
uses a value no sane person would pass -- eight stops, a gate of zero, one
pyramid band -- because the only reading that cannot be explained away is a
difference of nothing at all.

The audit carries its own commissioning, because an audit that reports "all dead"
because the renderer crashed looks identical to a real finding:

  NULL      baseline against itself must be byte-identical, or the renderer is
            non-deterministic and every verdict below is noise.
  POSITIVE  a probe known to work must read LIVE, or the comparator is broken.
  NEGATIVE  a probe known to be dead must read DEAD, or the audit cannot detect
            deadness and its greens are vacuous.

Usage:  python scripts/check-potency.py [--exe PATH] [--subject NAME] [--limit N]
Exit:   0 if commissioning passed, 2 if the instrument failed its own controls.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import time

import numpy as np
import tifffile

# name, extra argv, extra env, prior
#   prior "live" -> we expect this to change the image (positive control)
#   prior "dead" -> independently established as inert (negative control)
#   prior None   -> unknown; this is what the audit is for
#
# ON CHOOSING THE VALUE, which is the whole difficulty. `=1` is NOT an absurd
# value. It is the multiplicative identity, and for any numeric parameter -- a
# cap, a gain, a lambda, a strength -- it is the single most likely value to be
# either the default or the documented no-op. Probing every gate with `1` tests
# whether the program responds to being told to do what it already does. This
# audit's first run did exactly that and produced two false "dead flag"
# findings:
#   STREHL_RESTORE is a gain CAP whose guard is `cap > 1.0`, so `=1` returns the
#     identical state to unset. For a cap, absurd means LARGE.
#   STREHL_SMOOTH defaults to lambda = 1.0 and is ON, so `=1` set it to its own
#     default. For a parameter with a live default, absurd means BOTH
#     directions -- off, and far past sane.
# Both errors are now caught structurally by the banner check below rather than
# relying on whoever writes this table to know each flag's type.
PROBES: list[tuple[str, list[str], dict[str, str], str | None]] = [
    # --- commissioning ------------------------------------------------------
    ("NULL baseline vs baseline", [], {}, "null"),
    ("--pyramid-gate 0.0", ["--pyramid-gate", "0.0"], {}, "live"),
    ("--exposure=-6.0", ["--exposure=-6.0"], {}, "dead"),

    # --- pyramid merge controls --------------------------------------------
    ("--pyramid-bands 1", ["--pyramid-bands", "1"], {}, None),
    ("--pyramid-gate 40", ["--pyramid-gate", "40"], {}, None),
    ("--pyramid-exponent 0.01", ["--pyramid-exponent", "0.01"], {}, None),
    ("--pyramid-sharpen 4.0", ["--pyramid-sharpen", "4.0"], {}, None),

    # --- render / colour ----------------------------------------------------
    ("--auto-exposure", ["--auto-exposure"], {}, None),
    ("--resampler nearest", ["--resampler", "nearest"], {}, None),

    # --- environment gates --------------------------------------------------
    ("STREHL_ALIGN=0", [], {"STREHL_ALIGN": "0"}, None),
    ("STREHL_HIGHLIGHT_KNEE=0.02", [], {"STREHL_HIGHLIGHT_KNEE": "0.02"}, None),
    # =1 maps to Arm::Soft, a real non-default setting -- not a degenerate arm.
    ("STREHL_ROBUST_ELECTION=1", [], {"STREHL_ROBUST_ELECTION": "1"}, None),
    # lambda defaults to 1.0 and is ON, so probe BOTH directions away from it.
    ("STREHL_SMOOTH=off", [], {"STREHL_SMOOTH": "off"}, None),
    ("STREHL_SMOOTH=400", [], {"STREHL_SMOOTH": "400"}, None),
    # a gain cap: `1` is the documented no-op, so absurd means large.
    ("STREHL_RESTORE=8.0", [], {"STREHL_RESTORE": "8.0"}, None),
]


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def render(exe, subj, out, extra, env_extra, base):
    env = dict(os.environ)
    env.update(env_extra)
    argv = [str(exe), "stack", str(subj), "-o", str(out), *base, *extra]
    t0 = time.time()
    r = subprocess.run(argv, capture_output=True, env=env)
    banner = (r.stderr or b"").decode("utf-8", "replace")
    return r.returncode, banner, time.time() - t0


def backend_of(banner: str) -> str:
    for line in banner.splitlines():
        if "merge backend" in line:
            return line.split(":", 1)[1].strip()
    return "?"


def normalise_banner(banner: str, out: pathlib.Path) -> str:
    """Strip the parts of a banner that must differ between any two runs."""
    keep = []
    for line in banner.splitlines():
        s = line.strip()
        if out.name in s or out.stem in s:
            continue
        # elapsed times, throughput and memory figures move run to run
        if any(k in s for k in ("elapsed", "wall ", " MB/s", "throughput", "s)")):
            continue
        keep.append(s)
    return "\n".join(keep)


def compare(a: pathlib.Path, b: pathlib.Path):
    """Return (identical, n_differing, max_abs_diff, frac)."""
    if sha256(a) == sha256(b):
        return True, 0, 0, 0.0
    x = tifffile.imread(str(a)).astype(np.int64)
    y = tifffile.imread(str(b)).astype(np.int64)
    if x.shape != y.shape:
        return False, -1, -1, 1.0  # shape change is a very live flag
    d = np.abs(x - y)
    n = int((d > 0).sum())
    return False, n, int(d.max()), n / d.size


# Peak change, in 16-bit DN, at or below which an ABSURD value has not produced
# the effect its flag names. This is not a perceptual threshold -- it is far
# below one. It exists because `--auto-exposure` was measured moving 325,061
# samples by a peak of exactly 1 DN while its own banner announced "+2.61 stops
# (gain 6.105x)". A binary differs/does-not-differ test scores that as working.
# It is not working; it is rounding. A flag that survives an absurd value with a
# 1 DN peak is inert with a receipt, which is worse than inert.
TOKEN_DN = 2


def classify(ident: bool, n: int, mx: int, frac: float) -> str:
    if ident:
        return "DEAD"
    if 0 <= mx <= TOKEN_DN:
        return "TOKEN"
    return "LIVE"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=r"C:\dev\strehl-out\ORCH-GATE\pin-cur\strehl.exe")
    ap.add_argument("--subject", default="109MSDCF")
    ap.add_argument("--corpus", default=r"D:\personal\macro")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--work", default=r"C:\dev\strehl-out\ORCH-POTENCY")
    a = ap.parse_args()

    exe = pathlib.Path(a.exe)
    if not exe.exists():
        print(f"no binary at {exe}", file=sys.stderr)
        return 2
    subj = pathlib.Path(a.corpus) / a.subject
    frames = sorted(str(p) for p in subj.glob("*.ARW"))[: a.limit]
    if len(frames) < 3:
        print(f"only {len(frames)} frames under {subj}", file=sys.stderr)
        return 2

    work = pathlib.Path(a.work)
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    # --merge is named explicitly: with it absent the backend is INFERRED FROM
    # FLAGS, and several probes below add flags. An audit that silently swapped
    # backends between arms would attribute the backend's difference to the flag.
    base = ["--merge", "pyramid", "--srgb", "--limit", str(a.limit)]

    print(f"  binary   {exe}")
    print(f"  sha256   {sha256(exe)}")
    print(f"  subject  {a.subject}, {len(frames)} of "
          f"{len(list(subj.glob('*.ARW')))} frames")
    print(f"  base     {' '.join(base)}\n")

    ref = work / "_base.tif"
    rc, banner, dt = render(exe, subj, ref, [], {}, base)
    if rc != 0:
        print(f"  baseline render FAILED rc={rc}\n{banner[-1500:]}", file=sys.stderr)
        return 2
    ref_backend = backend_of(banner)
    ref_banner = normalise_banner(banner, ref)
    print(f"  baseline rendered in {dt:.1f}s, banner backend = {ref_backend!r}\n")

    hdr = f"  {'probe':<32}{'verdict':<9}{'differing':>12} {'max|d|':>8}  {'%':>7}  note"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    rows, failures = [], []
    for name, extra, env_extra, prior in PROBES:
        out = work / (name.replace(" ", "_").replace("=", "-")
                      .replace("--", "").replace("/", "_") + ".tif")
        rc, banner, dt = render(exe, subj, out, extra, env_extra, base)
        if rc != 0:
            print(f"  {name:<32}{'ERROR':<9}{'':>12} {'':>8}  {'':>7}  rc={rc}")
            rows.append((name, "ERROR", prior))
            continue
        bk = backend_of(banner)
        note = "" if bk == ref_backend else f"BACKEND CHANGED -> {bk!r}"
        ident, n, mx, frac = compare(ref, out)
        verdict = classify(ident, n, mx, frac)
        # The structural guard against a degenerate arm. If the program's own
        # banner is unchanged, the setting was not merely ineffective -- it was
        # never registered, because a value equal to the default or to the
        # documented no-op leaves the program with nothing new to report. That
        # is an untested arm, not a dead flag, and the two are indistinguishable
        # from the pixels alone. Both false findings this audit's first run
        # produced would have been caught here.
        if verdict == "DEAD" and normalise_banner(banner, out) == ref_banner:
            verdict = "DEGEN"
            note = (note + "  banner unchanged: the value was the default "
                    "or the no-op").strip()
        shown = "byte-identical" if ident else f"{n:,}"
        print(f"  {name:<32}{verdict:<9}{shown:>12} {mx:>8}  "
              f"{frac*100:>6.3f}%  {note}")
        rows.append((name, verdict, prior))

    # ---- commissioning: the audit judges itself ---------------------------
    print()
    for name, verdict, prior in rows:
        if prior == "null" and verdict != "DEAD":
            failures.append(f"NULL FAILED: {name} read {verdict}; the renderer is "
                            f"not deterministic and no verdict above is meaningful")
        if prior == "live" and verdict != "LIVE":
            failures.append(f"POSITIVE CONTROL FAILED: {name} read {verdict}; the "
                            f"comparator cannot see a change it was shown")
        if prior == "dead" and verdict == "LIVE":
            failures.append(f"NEGATIVE CONTROL CHANGED: {name} read {verdict}. This "
                            f"is GOOD NEWS if the flag was repaired -- confirm, then "
                            f"retire it as a control")

    unknown = [(n, v) for n, v, p in rows if p is None]
    dead = [n for n, v in unknown if v == "DEAD"]
    degen = [n for n, v in unknown if v == "DEGEN"]
    token = [n for n, v in unknown if v == "TOKEN"]
    live = [n for n, v in unknown if v == "LIVE"]
    err = [n for n, v, p in rows if v == "ERROR"]

    print(f"  probes {len(PROBES)}  =  commissioning {len(PROBES)-len(unknown)}"
          f"  +  live {len(live)}  +  token {len(token)}  +  inert {len(dead)}"
          f"  +  untested {len(degen)}  +  errored {len(err)}")
    if degen:
        print("\n  ARM NEVER TESTED -- the banner did not change, so the value was\n"
              "  the default or the documented no-op:")
        for n in degen:
            print(f"    - {n}")
        print("  These are NOT findings. Re-probe with a value appropriate to the\n"
              "  parameter's type: for a cap or a gain, large; for a live default,\n"
              "  both off and far past sane. `=1` is the identity, not an absurdity.")
    if dead:
        print("\n  REACHED NO PIXEL under an absurd value:")
        for n in dead:
            print(f"    - {n}")
        print("  Each is either dead code, or nested behind another gate that is "
              "off.\n  Both look identical here; separate them by READING THE CODE, "
              "not by\n  inferring it from this null.")
    if token:
        print(f"\n  MOVED PIXELS BY <= {TOKEN_DN} DN under an absurd value "
              f"-- inert with a receipt:")
        for n in token:
            print(f"    - {n}")
        print("  These are worse than the ones above: they produce a difference, so\n"
              "  a differs/does-not-differ test scores them as working, and they\n"
              "  announce an effect in the banner that no pixel carries.")

    if failures:
        print("\n  INSTRUMENT NOT COMMISSIONED:")
        for f in failures:
            print(f"    ! {f}")
        return 2
    print("\n  commissioning passed: null byte-identical, positive live, "
          "negative inert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
