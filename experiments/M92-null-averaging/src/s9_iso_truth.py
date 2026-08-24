"""M92b S9 -- ground-truth EXIF sensor metadata for every capture stack.

The M57 defect (M92 facts 1241-1243) was a hard-coded `ISO = 500` applied to an
ISO-160 stack.  That is a CLASS of defect, not an instance, so the audit needs a
ground truth to check every other hard-coded constant against.

This script builds it: for each stack under the capture roots, it reads EXIF ISO
and exposure from every frame (not just the first -- a stack with mixed ISO is a
different and worse problem than a stack with one wrong ISO) and records the
distinct values with their counts.

Read-only against the owner's captures.  Writes only to this experiment's out/.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402

sys.path.insert(0, os.path.join(M92.ROOT, "experiments", "m41-r3-kill", "src"))
import m41lib as M41  # noqa: E402

ROOTS = [r"D:\personal\macro", r"D:\macro-dark-frames"]
EXTS = (".arw", ".ARW")

# The canonical model, read from m57lib (which reads it from M41/M48).
sys.path.insert(0, os.path.join(M92.ROOT, "experiments", "m57-shape-metric",
                                "src"))
import m57lib as M57  # noqa: E402


def frames(d):
    try:
        return sorted(os.path.join(d, f) for f in os.listdir(d)
                      if f.endswith(EXTS))
    except OSError:
        return []


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log("M92b S9 -- ground-truth EXIF ISO per capture stack.")
    log(f"  canonical model: gain_dn_per_e(iso) = max(iso, {M57.BASE_ISO})"
        f" / {M57.GAIN_DIVISOR}")
    log(f"                   read_noise_e(iso)  = {M57.RN_E_HIGH} if iso >="
        f" {M57.SECOND_BASE_ISO} else {M57.RN_E_LOW}")
    log("=" * 78)

    out = {}
    for root in ROOTS:
        if not os.path.isdir(root):
            log(f"  (missing root {root})")
            continue
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name)
            fs = frames(d)
            if not fs:
                continue
            isos = {}
            for f in fs:
                v = M41.iso_of(f)
                isos[v] = isos.get(v, 0) + 1
            iso = max(isos, key=isos.get)
            g = M57.gain_dn_per_e(iso)
            rn = M57.read_noise_e(iso)
            # Key by root AND name: `119MSDCF` exists under both roots with
            # different ISO, so a bare name does not identify a stack. Keying
            # by name alone silently loses one of them -- which is the very
            # defect class this audit exists to find.
            key = f"{'capture' if 'personal' in root else 'dark'}|{name}"
            out[key] = dict(root=root, name=name, n_frames=len(fs), iso=iso,
                            iso_counts={str(k): v for k, v in isos.items()},
                            mixed=len(isos) > 1,
                            gain_dn_per_e=g, read_noise_e=rn)
            flag = "  MIXED ISO" if len(isos) > 1 else ""
            log(f"  {name:>36} {len(fs):>4} frames   ISO {iso:>5}"
                f"   g {g:.5f} DN/e-   rn {rn:.4f} e-{flag}")
            if len(isos) > 1:
                log(f"      {isos}")

    with open(os.path.join(M92.OUT, "s9_iso_truth.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    with open(os.path.join(M92.OUT, "s9_iso_truth.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote out/s9_iso_truth.{{json,log}}  ({len(out)} stacks)")


if __name__ == "__main__":
    main()
