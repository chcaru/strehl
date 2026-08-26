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
import codecs
import hashlib
import os
import pathlib
import re
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

# The audit's third structural flaw, and the one that took longest to find.
#
# M126 measured `STREHL_SMOOTH_HUBER=off` as DEAD at 22 frames (0 samples) and
# LIVE at 299 frames (99.35% of samples, peak 24331 DN = 37.13% of full scale).
# It also showed this is a DOSE-RESPONSE and not a cliff: `STREHL_SMOOTH=0`
# moves peak 1306 DN at 22 frames and 16974 DN at 299.
#
# A gate whose input is pooled across frames CANNOT be exercised by a shallow
# probe. This audit shipped with `--limit 8`. So its DEAD column was, for that
# whole class of gate, a measurement of its own shallowness.
#
# This is the same failure shape as the `=1` trap, one level deeper: an
# instrument whose failure mode resembles its intended output. A shallow probe
# manufactures DEAD verdicts, and DEAD is the finding the audit exists to
# produce, so breaking it reads as succeeding.
#
# Therefore a DEAD verdict below this depth is NOT a finding. It is reported
# separately as SHALLOW and must be re-run on a deep stack before anyone may
# call a flag dead.
DEEP_FRAMES = 100


# The audit's FOURTH structural flaw, and the one that should have been obvious
# first: a binary cannot be asked about a flag it does not contain.
#
# Measured 2026-08-26. `STREHL_HIGHLIGHT_KNEE` read byte-identical at `off`,
# `0.05` and `0.02` on pin 0B3B6F19 -- while an independent verifier had, hours
# earlier, measured knee 0.05 moving 67.56% of the SAME subject. That looked
# exactly like a regression. It was not. The pin was built from 96b7e119, and
# `git cat-file -e 96b7e119:crates/strehl-core/src/highlight.rs` fails: the
# feature did not exist in that tree. The binary had never heard of the
# variable, so byte-identical is the only output it could possibly have made.
#
# Note the shape, because it is now the fourth member of one family. All four of
# these emit the SAME GLYPH -- byte-identical output:
#
#   1. `=1` on a multiplicative gate      -> the identity element   (DEGEN)
#   2. 8 frames on a frame-pooled gate    -> the probe is shallow   (SHALLOW)
#   3. a value equal to the default        -> the arm never ran      (DEGEN)
#   4. a binary predating the flag         -> nothing was probed     (UNIMPLEMENTED)
#
# So: byte-identical output is the null result of every possible probe failure,
# and it is indistinguishable from a true negative from the pixels alone. Every
# guard in this file exists to subtract one member of that family from the DEAD
# column. DEAD must mean "present, reached, and inert" -- nothing else.
#
# The check is cheap and needs no render: Rust emits `std::env::var("NAME")` and
# clap's flag names as literals in .rdata, so a flag absent from the binary's
# own bytes cannot be under test. Verified discriminating: on pin 0B3B6F19,
# STREHL_HIGHLIGHT_KNEE is ABSENT while five other probed vars are PRESENT.
SCAN_MIN_ENV_LITERALS = 10
SCAN_NEGATIVE_CONTROL = "STREHL_THIS_FLAG_DOES_NOT_EXIST_XYZZY"


def binary_literals(exe: pathlib.Path) -> str:
    """The binary's own bytes as ASCII, for literal lookup."""
    return codecs.decode(exe.read_bytes(), "ascii", "replace")


def probe_tokens(extra: list[str], env_extra: dict) -> list[str]:
    """The literals a binary must contain for this probe to be answerable.

    Env vars are matched exactly. CLI flags are matched on the BARE name: clap
    stores `fix-ca` without leading dashes, so requiring `--fix-ca` would report
    a live flag as missing and manufacture the very false verdict this guards.
    """
    toks = list(env_extra.keys())
    for x in extra:
        if x.startswith("--"):
            toks.append(x[2:].split("=", 1)[0])
    return toks


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

    # ---- commission the literal scanner before trusting any absence --------
    # A scan that finds nothing looks identical to a binary that contains
    # nothing. Both halves are checked: enough real literals to prove the scan
    # reaches .rdata, and a token that must NOT be found to prove it can say no.
    blob = binary_literals(exe)
    found_env = sorted(set(re.findall(r"STREHL_[A-Z0-9_]{3,}", blob)))
    if len(found_env) < SCAN_MIN_ENV_LITERALS:
        print(f"  SCANNER FAILED: only {len(found_env)} STREHL_ literals in the "
              f"binary; the scan is not reaching .rdata and every ABSENT "
              f"verdict below would be an artifact", file=sys.stderr)
        return 2
    if SCAN_NEGATIVE_CONTROL in blob:
        print(f"  SCANNER FAILED: the negative control matched; the scan cannot "
              f"report absence", file=sys.stderr)
        return 2
    print(f"  scanner   {len(found_env)} STREHL_ literals found, "
          f"negative control absent -- absence is measurable\n")

    # The source-tree half of the presence guard. A literal missing from the
    # binary means something entirely different depending on whether the
    # CURRENT source still declares it, so read the source too.
    source_literals = ""
    src_root = pathlib.Path(__file__).resolve().parent.parent / "crates"
    if src_root.is_dir():
        parts = []
        for p in src_root.rglob("*.rs"):
            try:
                parts.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
        source_literals = "\n".join(parts)
    if not source_literals:
        print(f"  NOTE: no sources under {src_root}; a missing literal cannot "
              f"be attributed to an old pin vs dead-stripping\n")

    hdr = f"  {'probe':<32}{'verdict':<9}{'differing':>12} {'max|d|':>8}  {'%':>7}  note"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    rows, failures = [], []
    for name, extra, env_extra, prior in PROBES:
        # The presence guard, before the render: a flag absent from the
        # binary's own bytes is not dead, it is not there. Costs no render.
        #
        # But ABSENT has two causes with OPPOSITE meanings, and they must not
        # share a verdict:
        #
        #   the literal is also absent from crates/  -> the binary predates the
        #       feature (or it was deleted). A probe error. Not a finding.
        #   the literal IS in crates/ but not in the binary -> either an old
        #       pin, or the LINKER DEAD-STRIPPED IT because no reachable path
        #       calls it. The second is the strongest finding this audit can
        #       produce: unreachability certified by the toolchain, not
        #       inferred from a null.
        #
        # Measured: STREHL_ROBUST_ELECTION is declared at merge.rs:652 and read
        # at merge.rs:669 via std::env::var, its wiring commit e0281139 IS an
        # ancestor of the pin's source 96b7e119 -- and the literal is absent
        # from the binary. It was stripped. That is exactly the "quoted in a
        # report, never executes" defect this file's docstring opens with.
        #
        # Left un-disambiguated by the tool on purpose: the binary cannot name
        # its own source commit (`strehl --version` says only "strehl 0.0.0"),
        # so the ancestry test cannot be automated from the artifact. The tool
        # reports which half applies and hands the reader the exact command.
        missing = [t for t in probe_tokens(extra, env_extra) if t not in blob]
        if missing and prior is None:
            in_src = [t for t in missing if t in source_literals]
            tag = "STRIPPED?" if in_src else "ABSENT"
            why = (f"in crates/ but not in .rdata: {', '.join(in_src)}"
                   if in_src else
                   f"absent from crates/ too: {', '.join(missing)}")
            print(f"  {name:<32}{tag:<10}{'not in binary':>11} {'':>8}  "
                  f"{'':>7}  {why}")
            rows.append((name, tag, prior))
            continue
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
        # The depth guard. A gate whose input is pooled across frames cannot be
        # exercised by a shallow stack, so below DEEP_FRAMES a byte-identical
        # result is a statement about the probe, not about the flag. Controls
        # are exempt: their expected verdict is a property of the renderer's
        # determinism, which does not depend on stack depth.
        if verdict == "DEAD" and prior is None and len(frames) < DEEP_FRAMES:
            verdict = "SHALLOW"
            note = (note + f"  only {len(frames)} frames: too few to exercise "
                    "a frame-pooled gate").strip()
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
    shallow = [n for n, v in unknown if v == "SHALLOW"]
    degen = [n for n, v in unknown if v == "DEGEN"]
    token = [n for n, v in unknown if v == "TOKEN"]
    live = [n for n, v in unknown if v == "LIVE"]
    unimpl = [n for n, v in unknown if v == "ABSENT"]
    stripped = [n for n, v in unknown if v == "STRIPPED?"]
    err = [n for n, v, p in rows if v == "ERROR"]

    print(f"  probes {len(PROBES)}  =  commissioning {len(PROBES)-len(unknown)}"
          f"  +  live {len(live)}  +  token {len(token)}  +  inert {len(dead)}"
          f"  +  unconfirmed {len(shallow)}  +  absent {len(unimpl)}"
          f"  +  stripped? {len(stripped)}"
          f"  +  untested {len(degen)}  +  errored {len(err)}")
    if stripped:
        print("\n  DECLARED IN SOURCE, MISSING FROM THE BINARY -- and this is the\n"
              "  one category here that may be a REAL finding:")
        for n in stripped:
            print(f"    - {n}")
        print("  Two causes, opposite meanings. Either the pin predates the\n"
              "  wiring commit -- a probe error -- or the linker DEAD-STRIPPED the\n"
              "  literal because no reachable path calls it, which is\n"
              "  unreachability certified by the toolchain rather than inferred\n"
              "  from a null. Settle it, do not guess:\n"
              "      git log -S <LITERAL> --oneline -- crates     # wiring commit\n"
              "      git merge-base --is-ancestor <wiring> <pin-source>\n"
              "  Ancestor -> STRIPPED, and it is dead code. Not an ancestor ->\n"
              "  the pin is simply too old and nothing was measured.")
    if unimpl:
        print("\n  NOT IN THIS BINARY OR IN THE SOURCE -- nothing was probed:")
        for n in unimpl:
            print(f"    - {n}")
        print("  These are NOT findings, and they are the trap this guard exists\n"
              "  for: a binary predating a feature answers every question about it\n"
              "  with byte-identical output, which is exactly what a dead flag\n"
              "  looks like. Check the pin's provenance -- `git cat-file -e\n"
              "  <commit>:<path>` -- and re-probe on a binary that contains it.")
    if shallow:
        print(f"\n  NO VERDICT -- byte-identical, but measured on only "
              f"{len(frames)} frames:")
        for n in shallow:
            print(f"    - {n}")
        print(f"  These are NOT findings and must not be reported as dead flags.\n"
              f"  A gate whose input is pooled across frames cannot be exercised\n"
              f"  by a shallow stack: STREHL_SMOOTH_HUBER=off reads 0 samples at\n"
              f"  22 frames and 99.35% at 299. Re-run with --limit {DEEP_FRAMES}\n"
              f"  or more, on a deep subject, before calling any of these dead.")
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
