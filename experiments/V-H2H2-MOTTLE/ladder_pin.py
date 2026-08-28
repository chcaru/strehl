# What exponent does the shipped merge actually use at each band?
#
# Three answers are in circulation and they disagree:
#   ORCH's arithmetic  -- "band 0 = 2.0*1.4^5 = 10.8 -> 8.0, mid band 2 ~ 5.5"
#   the source comment -- "runs 2, 3, 4, 5, 8, 8, 8 from coarsest to finest"
#   the source CODE    -- exponent_at(), which is what actually executes
#
# Only the third one runs. This computes it from constants PARSED out of the
# pinned file rather than typed in here, in f32, reproducing `powi` as repeated
# multiplication the way LLVM lowers it.
#
# The comparison is commissioned: a planted comment and a planted constant must
# both be detected, and two analytic cases must be reproduced exactly. A
# comparison that has only ever agreed is not evidence that it can disagree.

import re
import subprocess
import sys

import numpy as np

PIN = "9b05d0b7"
PATH = "crates/strehl-core/src/pyramid.rs"
F32 = np.float32


def pin_source():
    # bytes, decoded here -- a `>` redirect on Windows re-encodes the stream
    r = subprocess.run(["git", "show", "%s:%s" % (PIN, PATH)], capture_output=True)
    if r.returncode != 0:
        sys.exit("git show failed: %s" % r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout.decode("utf-8")


def parse_consts(src):
    """Every constant comes out of the file. Missing one is fatal, not defaulted."""
    pats = {
        "bands": r"pub const DEFAULT_BANDS: usize = (\d+);",
        "max_exponent": r"pub const MAX_EXPONENT: f32 = ([\d.]+);",
        "gate": r"\n            gate: ([\d.]+),",
        "exponent": r"\n            exponent: ([\d.]+),",
        "sharpen": r"\n            sharpen_per_octave: ([\d.]+),",
    }
    out = {}
    for k, p in pats.items():
        m = re.search(p, src)
        if m is None:
            sys.exit("CONSTANT NOT FOUND: %s (%r) -- the parse is void" % (k, p))
        out[k] = float(m.group(1))
    out["bands"] = int(out["bands"])
    return out


def powi_f32(base, n):
    """LLVM lowers powi to exponentiation by squaring in the value's own type."""
    result, b, n = F32(1.0), F32(base), int(n)
    while n > 0:
        if n & 1:
            result = F32(result * b)
        b = F32(b * b)
        n >>= 1
    return result


def exponent_at(k, bands, exponent, sharpen, max_exponent):
    """A transcription of pyramid.rs:1051-1057 at the pin, in f32."""
    if sharpen == 1.0 or bands == 0:
        return F32(exponent)
    steps = (bands - 1) - min(k, bands - 1)
    return F32(min(F32(F32(exponent) * powi_f32(sharpen, steps)), F32(max_exponent)))


def ladder(c, bands=None):
    b = c["bands"] if bands is None else bands
    return [float(exponent_at(k, b, c["exponent"], c["sharpen"], c["max_exponent"]))
            for k in range(b)]


def comment_ladder(src):
    """The ladder the comment claims, read out of the comment itself."""
    m = re.search(r"Over a (\d+)-band pyramid this runs ([\d, ]+?)\s*//\s*([\d, ]+?) "
                  r"from coarsest to finest", re.sub(r"\n\s*//", "\n            //", src))
    if m is None:
        m = re.search(r"Over a (\d+)-band pyramid this runs (.*?) from coarsest to "
                      r"finest", src, re.S)
        if m is None:
            return None, None
        nums = [int(x) for x in re.findall(r"\b(\d+)\b", m.group(2).replace("//", " "))]
        return int(m.group(1)), nums
    nums = [int(x) for x in re.findall(r"\d+", m.group(2) + " " + m.group(3))]
    return int(m.group(1)), nums


def commission():
    """Four arms. Two analytic, one planted defect, one planted improvement."""
    fails = []

    def arm(name, ok, detail):
        print("  %-4s %-44s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            fails.append(name)

    # 1. analytic: sharpen == 1.0 must give a flat ladder at `exponent`
    flat = [float(exponent_at(k, 7, 2.0, 1.0, 8.0)) for k in range(7)]
    arm("flat ramp is flat", flat == [2.0] * 7, "%s" % flat)

    # 2. analytic: with the cap lifted the ladder is exactly geometric
    unc = [float(exponent_at(k, 7, 2.0, 2.0, 1e9)) for k in range(7)]
    want = [2.0 * 2.0 ** (6 - k) for k in range(7)]
    arm("uncapped ramp is geometric", unc == want, "%s" % unc)

    # 3. planted DEFECT: a wrong comment must be detected
    src = pin_source()
    bad = src.replace("this runs 2, 3, 4, 5, 8,", "this runs 2, 3, 4, 6, 8,", 1)
    if bad == src:
        sys.exit("PLANT TARGET NOT FOUND -- control is void")
    nb, cl = comment_ladder(bad)
    c = parse_consts(src)
    rounded = [int(round(v)) for v in ladder(c)][::-1]
    arm("a wrong comment is detected", cl is not None and cl != rounded,
        "planted %s vs code %s" % (cl, rounded))

    # 4. planted IMPROVEMENT: a comment corrected to the code must be accepted.
    #    Without this arm the comparison could be one that rejects everything.
    good = src.replace("this runs 2, 3, 4, 5, 8,",
                       "this runs %d, %d, %d, %d, 8," % tuple(rounded[:4]), 1)
    nb2, cl2 = comment_ladder(good)
    arm("a corrected comment is accepted", cl2 == rounded,
        "corrected %s vs code %s" % (cl2, rounded))
    return fails


def main():
    print("commissioning")
    fails = commission()
    if fails:
        print("\nRED -- %s" % ", ".join(fails))
        return 1
    print("  GREEN\n")

    src = pin_source()
    c = parse_consts(src)
    print("constants parsed from %s:%s" % (PIN, PATH))
    for k in ("bands", "gate", "exponent", "sharpen", "max_exponent"):
        print("  %-14s %s" % (k, c[k]))

    lad = ladder(c)
    print("\nthe ladder the CODE computes, bands = %d" % c["bands"])
    print("  %-6s %-10s %-12s %s" % ("k", "steps", "exponent", "note"))
    for k, v in enumerate(lad):
        steps = (c["bands"] - 1) - min(k, c["bands"] - 1)
        raw = float(F32(F32(c["exponent"]) * powi_f32(c["sharpen"], steps)))
        note = "CAPPED from %.4f" % raw if raw > c["max_exponent"] else ""
        print("  k=%-4d %-10d %-12.4f %s" % (k, steps, v, note))

    nb, cl = comment_ladder(src)
    rounded = [int(round(v)) for v in lad][::-1]
    print("\nthe ladder the COMMENT claims, coarsest to finest: %s (%s bands)"
          % (cl, nb))
    print("the code's ladder, coarsest to finest, rounded      : %s" % rounded)
    print("the code's ladder, coarsest to finest, exact        : %s"
          % ["%.4f" % v for v in lad[::-1]])
    agree = (cl == rounded)
    print("\ncomment matches code to the nearest integer: %s" % agree)
    if agree:
        exact = [v for v in lad if abs(v - round(v)) > 1e-4]
        print("but %d of %d entries are not integers: %s"
              % (len(exact), len(lad), ["%.4f" % v for v in exact]))

    print("\nORCH's arithmetic assumed bands = 6:")
    print("  ladder at bands=6, finest first: %s"
          % ["%.4f" % v for v in ladder(c, 6)])
    print("  ladder at bands=7, finest first: %s"
          % ["%.4f" % v for v in lad])
    return 0


if __name__ == "__main__":
    sys.exit(main())
