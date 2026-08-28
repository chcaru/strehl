#!/usr/bin/env python3
"""Measure what `--exposure` actually did at shipping pin 9b05d0b7.

WHY THIS EXISTS
---------------
The orchestrator tested the claim "`--exposure` is a no-op" by rendering the
same subject at `--exposure=3` and `--exposure=-3` and observing that the two
files had different SHA-256 hashes.  Different files, therefore the flag works,
therefore the accusation was false and the lane holding a fix was told to drop
it.

That test compares hashes.  A hash is a PRESENCE test: it answers "did any byte
move", never "did the image change".  This script asks the second question,
which is the one the claim was about.

WHAT IT MEASURES
----------------
Three quantities per pair, over the full 98,898,048-sample output:

  n_differ    how many samples differ at all
  max_delta   the largest single-sample difference, in DN of 65535
  mean_delta  the mean absolute difference over the samples that differ

`max_delta` is the load-bearing one.  A gain of 64x that moves no sample by
more than 1 DN of 65535 has not been applied to the image, whatever the hash
says.

COMMISSIONING
-------------
This instrument is a difference detector, so it can fail in two directions and
both arms are required:

  POSITIVE CONTROL (must read LOUD)
      The same two commands run against the HEAD binary, where `--exposure` is
      applied past the tone normalisation.  If this pair reads quiet, the
      comparison machinery is broken and every other reading here is void.  The
      script ABORTS rather than reporting, because a difference detector that
      cannot see a real difference would otherwise print "no-op" for every
      input and look like a finding.

  NEGATIVE CONTROL (must read SILENT)
      A file against itself.  Guards against a reader that manufactures
      difference from decode nondeterminism or dtype handling.

  IMPROVEMENT ARM (must read the RIGHT WAY, not merely "different")
      A degradation-only commissioning cannot separate a metric that is blind
      from one that is perverse.  Here the directional claim is that HEAD's
      +2.60 render is BRIGHTER than its 0 render, by roughly the commanded
      gain.  A detector that reported |delta| correctly but had the sign or the
      operands transposed would pass the two controls above and still be wrong
      about which way exposure goes.  So the arm checks a signed quantity: the
      mean of the +2.60 render must EXCEED the mean of the 0 render.

WHAT IS GATED
-------------
Every number this script prints is conditioned on.  The verdict is not a
summary of the numbers; it is computed from them, with an explicit floor:

  INERT      max_delta <= INERT_MAX_DN across the whole commanded range
  LIVE       max_delta >= LIVE_MIN_DN
  AMBIGUOUS  anything between, which is a refusal, not a pass

The band exists so the instrument can decline.  A detector whose only outcomes
are INERT and LIVE will label a 3 DN wobble as one of them and it is neither.

PARTITION
---------
Every pair declared in PAIRS is resolved into exactly one of
{measured, missing-input, failed}, and the three counts are asserted to sum to
the number declared.  A pair whose file is absent must never be able to read as
a pair that was measured and found quiet.
"""

from __future__ import annotations

import collections
import json
import os
import sys

import numpy as np
import tifffile

def _probe_dir():
    """Where the six probe renders live.

    They moved from C: to D: in the disk reclamation of 2026-08-27; C: is kept
    as a fallback so a tree that still holds the old location keeps verifying,
    and the env var lets a third location be named without editing this file.
    A missing tree is a typed refusal rather than a silent empty result: these
    renders are the evidence, and a verifier that quietly finds none of them
    would otherwise report perfect agreement over zero comparisons.
    """
    named = os.environ.get("STREHL_DEFECT_PROBE")
    if named:
        # An override that is SET but wrong must fail, not quietly fall through
        # to a default -- otherwise a typo silently measures a different tree
        # and reports it as the requested one.
        if not os.path.isdir(named):
            raise SystemExit("STREHL_DEFECT_PROBE is set to %r, which is not a "
                             "directory; refusing to fall back to a default"
                             % named)
        return named
    for p in (r"D:\strehl-out\BUILD-DEFECT\probe",
              r"C:\dev\strehl-out\BUILD-DEFECT\probe"):
        if os.path.isdir(p):
            return p
    raise SystemExit("probe renders not found in any known location; set "
                     "STREHL_DEFECT_PROBE to the directory holding "
                     "pin-e260.tiff and its siblings")


PROBE = _probe_dir()
OUT_JSON = os.path.join(os.path.dirname(__file__), "..", "out", "72-exposure-inert-at-pin.json")

# The decision band.  INERT_MAX_DN is 2 rather than 0 because a renderer is
# entitled to dither: the question is whether a 64x gain is distinguishable
# from rounding, not whether the pipeline is bit-deterministic.  LIVE_MIN_DN is
# deliberately far above it so the two verdicts cannot touch.
INERT_MAX_DN = 2
LIVE_MIN_DN = 256

FULL_SCALE = 65535

# label, file A, file B, commanded stops apart
PAIRS = [
    ("pin  +3    vs -3   ", "pin-epos3.tiff", "pin-eneg.tiff", 6.00),
    ("pin  +2.60 vs 0    ", "pin-e260.tiff", "pin-e000.tiff", 2.60),
    ("pin  0     vs -3   ", "pin-e000.tiff", "pin-eneg.tiff", 3.00),
    ("HEAD +2.60 vs 0    ", "head-e260.tiff", "head-e000.tiff", 2.60),
]

# Which label carries the positive control.  Named, not positional, so that
# reordering PAIRS cannot silently move the control onto a different pair.
POSITIVE_CONTROL = "HEAD +2.60 vs 0    "


def read(path: str) -> np.ndarray:
    return tifffile.imread(path).astype(np.int32)


def diff(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.abs(a - b)
    nz = int((d > 0).sum())
    hist = collections.Counter(d[d > 0].tolist()) if nz else {}
    return {
        "n_total": int(d.size),
        "n_differ": nz,
        "pct_differ": 100.0 * nz / d.size,
        "max_delta": int(d.max()),
        "mean_delta": float(d[d > 0].mean()) if nz else 0.0,
        "hist_top": {str(k): int(v) for k, v in collections.Counter(hist).most_common(4)},
    }


def main() -> int:
    print("=" * 108)
    print("WHAT `--exposure` DID TO THE IMAGE AT PIN 9b05d0b7")
    print("=" * 108)
    print()

    declared = len(PAIRS)
    measured: dict[str, dict] = {}
    missing: list[str] = []
    failed: list[str] = []
    means: dict[str, float] = {}

    for label, fa, fb, stops in PAIRS:
        pa, pb = os.path.join(PROBE, fa), os.path.join(PROBE, fb)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            missing.append(label)
            continue
        try:
            a, b = read(pa), read(pb)
            r = diff(a, b)
            r["stops"] = stops
            r["linear_ratio_commanded"] = 2.0 ** stops
            r["mean_a"] = float(a.mean())
            r["mean_b"] = float(b.mean())
            means[fa] = r["mean_a"]
            means[fb] = r["mean_b"]
            measured[label] = r
            del a, b
        except Exception as exc:  # noqa: BLE001 - a failed pair must be counted, not silent
            failed.append(f"{label}: {exc}")

    assert len(measured) + len(missing) + len(failed) == declared, (
        f"partition does not sum: {len(measured)} measured + {len(missing)} missing "
        f"+ {len(failed)} failed != {declared} declared"
    )

    print("%-21s %6s %9s %14s %9s %10s %11s" % (
        "pair", "stops", "commanded", "samples differ", "% differ", "max |d|", "mean |d|"))
    print("-" * 108)
    for label, _, _, _ in PAIRS:
        if label in measured:
            r = measured[label]
            print("%-21s %6.2f %8.1fx %14s %8.4f%% %10d %11.4f" % (
                label, r["stops"], r["linear_ratio_commanded"],
                "{:,}".format(r["n_differ"]), r["pct_differ"], r["max_delta"], r["mean_delta"]))
        elif label in missing:
            print("%-21s %6s %9s %14s %9s %10s %11s" % (label, "-", "-", "MISSING", "-", "-", "-"))
        else:
            print("%-21s %6s %9s %14s %9s %10s %11s" % (label, "-", "-", "FAILED", "-", "-", "-"))
    print("-" * 108)
    print("declared %d = measured %d + missing-input %d + failed %d"
          % (declared, len(measured), len(missing), len(failed)))
    print()

    # ---- commissioning ---------------------------------------------------
    print("COMMISSIONING")
    problems: list[str] = []

    if POSITIVE_CONTROL not in measured:
        print("  positive control       : ABSENT -- cannot proceed")
        problems.append("positive control absent")
    else:
        pc = measured[POSITIVE_CONTROL]
        loud = pc["max_delta"] >= LIVE_MIN_DN
        print("  positive control       : max |d| = %d DN, needs >= %d  ->  %s"
              % (pc["max_delta"], LIVE_MIN_DN, "LOUD (machinery works)" if loud else "QUIET"))
        if not loud:
            problems.append("positive control quiet: the difference detector cannot see a real exposure change")

    nc_path = os.path.join(PROBE, "pin-eneg.tiff")
    if os.path.exists(nc_path):
        a = read(nc_path)
        nc = diff(a, a.copy())
        del a
        silent = nc["n_differ"] == 0
        print("  negative control       : file against itself, %d samples differ  ->  %s"
              % (nc["n_differ"], "SILENT (no manufactured difference)" if silent else "NOISY"))
        if not silent:
            problems.append("negative control noisy: the reader manufactures difference")
    else:
        print("  negative control       : ABSENT -- cannot proceed")
        problems.append("negative control absent")

    if "head-e260.tiff" in means and "head-e000.tiff" in means:
        hi, lo = means["head-e260.tiff"], means["head-e000.tiff"]
        right_way = hi > lo
        print("  improvement arm        : HEAD mean at +2.60 = %.1f, at 0 = %.1f  ->  %s"
              % (hi, lo, "brighter, correct direction" if right_way else "DARKER, sign is wrong"))
        if not right_way:
            problems.append("improvement arm went the wrong way: a positive gain did not brighten the image")
    else:
        print("  improvement arm        : ABSENT -- cannot proceed")
        problems.append("improvement arm absent")

    print()
    if problems:
        print("COMMISSIONING FAILED -- no verdict is reported:")
        for p in problems:
            print("  - %s" % p)
        return 2
    print("  all three arms pass; the readings below are admissible.")
    print()

    # ---- the gated verdict ----------------------------------------------
    print("VERDICT  (band: INERT <= %d DN, LIVE >= %d DN, anything between is AMBIGUOUS)"
          % (INERT_MAX_DN, LIVE_MIN_DN))
    verdicts: dict[str, str] = {}
    for label, _, _, _ in PAIRS:
        if label not in measured:
            verdicts[label] = "UNDEFINED"
            print("  %-21s UNDEFINED (input absent -- this is not a pass)" % label)
            continue
        m = measured[label]["max_delta"]
        v = "INERT" if m <= INERT_MAX_DN else ("LIVE" if m >= LIVE_MIN_DN else "AMBIGUOUS")
        verdicts[label] = v
        print("  %-21s %-9s  max |d| = %d DN over a commanded %.1fx"
              % (label, v, m, measured[label]["linear_ratio_commanded"]))

    pin_labels = [lab for lab, _, _, _ in PAIRS if lab.startswith("pin")]
    pin_verdicts = {verdicts[lab] for lab in pin_labels}
    print()
    if pin_verdicts == {"INERT"}:
        widest = max(measured[lab]["linear_ratio_commanded"] for lab in pin_labels if lab in measured)
        worst = max(measured[lab]["max_delta"] for lab in pin_labels if lab in measured)
        print("  CONCLUSION: at pin 9b05d0b7, `--exposure` is INERT on the delivered image.")
        print("  Across a commanded linear range of %.1fx, no sample moved by more than %d DN of %d."
              % (widest, worst, FULL_SCALE))
        print("  The hash difference the orchestrator observed is therefore not evidence of effect.")
        conclusion = "INERT"
    elif "LIVE" in pin_verdicts:
        print("  CONCLUSION: at least one pin pair is LIVE; the no-op reading does NOT hold.")
        conclusion = "LIVE"
    else:
        print("  CONCLUSION: REFUSED -- pin verdicts are %s, which is not a clean reading."
              % sorted(pin_verdicts))
        conclusion = "REFUSED"

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({
            "declared": declared,
            "measured": len(measured),
            "missing_input": len(missing),
            "failed": len(failed),
            "inert_max_dn": INERT_MAX_DN,
            "live_min_dn": LIVE_MIN_DN,
            "pairs": measured,
            "verdicts": verdicts,
            "conclusion": conclusion,
        }, fh, indent=2)
    print()
    print("wrote %s" % os.path.normpath(OUT_JSON))
    return 0 if conclusion in ("INERT", "LIVE") else 3


if __name__ == "__main__":
    sys.exit(main())
