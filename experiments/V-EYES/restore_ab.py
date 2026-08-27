#!/usr/bin/env python3
"""
V-EYES: the STREHL_RESTORE A/B on the frozen instrument.

WHAT THIS ANSWERS
-----------------
ORCH routed a second before/after for the pinned softness instrument. The
subject is `crates/strehl-core/src/restore.rs`, a single-image Wiener
restoration whose H is strehl's OWN resampling kernel -- built, wired into the
merge, and OFF by default. It was parked on a three-ROI edge-rise measurement
that found one ROI marginally above its floor and two nulls, and the routing
argument was that a three-edge instrument and a per-site band-energy ceiling
over a complete focus bracket are not the same class of instrument: a change
can be a null on three hand-placed edges and a real uniform gain everywhere.

That argument is correct in general. This script tests whether it applies here.

WHY THIS IS NOT AN INSTRUMENT RUN
---------------------------------
The pinned instrument (corpus_softness.py, envelope_null.py) is deliberately
untouched -- this script never imports or edits it. The reason is that the A/B
turned out to be decidable one level upstream, at the intervention rather than
the outcome:

    restore R  : cap 1.700, max gain 1.0000 (2-D 1.0000), at Nyquist 1.0000,
                 recovered 0.0000, mean 1016.7 DN, sigma2 233.7 DN^2

`cap 1.700` proves the binary read the switch. `max gain 1.0000` and
`recovered 0.0000` say the estimator then declined to amplify anything. The
restored and unrestored masters for 119MSDCF are SHA-256 identical. When the
two arms of an A/B are the same file, running a bootstrap over them is theatre;
the honest report is the byte comparison plus the mechanism.

So what this script does is establish HOW GENERAL that no-op is, which is the
only part still in question. It renders each subject twice -- STREHL_RESTORE
unset and STREHL_RESTORE=1.7 -- and reports, per subject:

    * the per-plane gain the estimator chose,
    * whether the two output files are byte-identical.

A subject where the gain exceeds 1 and the files differ is a subject where the
A/B has real content and the instrument must then be run. A subject where the
files are identical is settled without it.

METHOD NOTE -- WHY THE GAIN CAN BE EXACTLY 1
--------------------------------------------
restore.rs computes, per radial frequency,

    g(f) = clamp( h / (h^2 + sigma2/S(f)),  1,  cap )

with h the gather MTF and S(f) the image's own measured power at f. The lower
clamp is at 1, so the filter is structurally incapable of blurring -- and it
reaches 1 exactly whenever sigma2/S(f) >= h(1-h) at every frequency, i.e.
whenever the noise at f is comparable to the signal at f, or whenever h is
already close to 1 so there is nothing to invert. Both are self-calibrating
declines on the estimator's own evidence, not failures.

Usage:
    python restore_ab.py <subject> [<subject> ...]
"""
import os
import pathlib
import re
import subprocess
import sys
import hashlib

EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SRC = pathlib.Path(r"D:\personal\macro")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-EYES\restore-ab")
CAP = "1.7"

RE_RESTORE = re.compile(
    r"restore\s+(\S+)\s*:\s*cap\s+([\d.]+),\s*max gain\s+([\d.]+)\s*"
    r"\(2-D\s+([\d.]+)\),\s*at Nyquist\s+([\d.]+),\s*recovered\s+([\d.]+),"
    r"\s*mean\s+([\d.]+)\s*DN,\s*sigma2\s+([\d.]+)"
)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def render(subject, restore):
    """Render one master. `restore` is None (arm A) or the gain cap (arm B)."""
    tag = "restore" if restore else "plain"
    d = OUT / subject
    d.mkdir(parents=True, exist_ok=True)
    tif = d / f"MASTER-{tag}.tiff"
    log = d / f"MASTER-{tag}.log"
    if tif.exists() and log.exists():
        return tif, log.read_text(errors="replace")

    env = dict(os.environ)
    # Arm A must not inherit a stale switch from the shell; delete rather than
    # set to "0", so the two arms differ only in the variable's presence.
    env.pop("STREHL_RESTORE", None)
    if restore:
        env["STREHL_RESTORE"] = restore

    r = subprocess.run(
        [EXE, "stack", str(SRC / subject), "--out", str(tif),
         "--linear-srgb", "--demosaic"],
        capture_output=True, text=True, env=env)
    blob = (r.stdout or "") + (r.stderr or "") + f"\nrender exit={r.returncode}\n"
    log.write_text(blob, errors="replace")
    if r.returncode != 0 or not tif.exists():
        return None, blob
    return tif, blob


def main(argv):
    subjects = argv[1:]
    if not subjects:
        print(__doc__)
        return 1

    print(f"pin {EXE}")
    print(f"pin sha256 {sha256(EXE)}")
    print()
    hdr = f"{'subject':<22} {'plane':<4} {'cap':>6} {'gain':>7} {'2-D':>7} {'Nyq':>7} {'recov':>7} {'sigma2':>10}"
    for s in subjects:
        ta, la = render(s, None)
        tb, lb = render(s, CAP)
        print(f"--- {s} " + "-" * (60 - len(s)))
        if ta is None or tb is None:
            print("  RENDER FAILED")
            print((la or lb or "")[-800:])
            continue

        rows = RE_RESTORE.findall(lb)
        if not rows:
            print("  arm B logged no `restore` line -- the switch was not honoured")
        else:
            print(hdr)
            for (pl, cap, g, g2, nyq, rec, mean, s2) in rows:
                print(f"{'':<22} {pl:<4} {cap:>6} {g:>7} {g2:>7} {nyq:>7} {rec:>7} {s2:>10}")

        # Arm A must be silent: no switch, no filter, no log line.
        if RE_RESTORE.search(la):
            print("  !! arm A ALSO logged a restore line -- arms are not clean")

        ha, hb = sha256(ta), sha256(tb)
        same = ha == hb
        print(f"  plain    {ha}")
        print(f"  restored {hb}")
        print(f"  BYTE-IDENTICAL: {same}"
              + ("   -> the A/B has no content on this subject; ratio cannot move"
                 if same else "   -> arms DIFFER; the instrument must be run"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
