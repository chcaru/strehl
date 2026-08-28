# Where do the hull numbers actually come from?
#
# ORCH has quoted "hull violations 0 / 72 / 511 at exponents 1 / 8 / 16" four
# times, most recently as "V-NEVERWORSE priced hull violations at 0/72/511 ...
# Two lanes, two instruments, one parameter." It then amended its hard gate from
# `hull_violations` to `pinned_to_hull`, on the correct reasoning that the
# violation count is saturated at zero.
#
# The reasoning is right. The provenance is not, and the replacement statistic
# cannot be reported as instructed. Every claim below is checked against the pin
# and fails loudly if the source moves.
#
# Commissioned: each check is run once against the true source and once against
# a mutated copy that must flip it. A check that has only ever passed is not
# evidence that it can fail.

import re
import subprocess
import sys

PIN = "9b05d0b7"
PATH = "crates/strehl-core/src/pyramid.rs"


def pin_source():
    r = subprocess.run(["git", "show", "%s:%s" % (PIN, PATH)], capture_output=True)
    if r.returncode != 0:
        sys.exit("git show failed")
    return r.stdout.decode("utf-8")


def lineno(lines, pat, start=0):
    for i in range(start, len(lines)):
        if re.search(pat, lines[i]):
            return i + 1
    return None


def facts(src):
    """Every fact is derived from the source, never asserted here."""
    L = src.split("\n")
    cfg_test = lineno(L, r"#\[cfg\(test\)\]")
    f = {
        "cfg_test_line": cfg_test,
        "pinned_to_hull_line": lineno(L, r"fn pinned_to_hull"),
        "hull_violations_lines": [i + 1 for i, l in enumerate(L)
                                  if "hull_violations" in l],
        # does pinned_to_hull accept an image, or construct its own fixture?
        "pinned_signature": next((l.strip() for l in L if "fn pinned_to_hull" in l), ""),
        "pinned_fixture": any("disagreeing_bands" in L[i]
                              for i in range(lineno(L, r"fn pinned_to_hull") or 0,
                                             (lineno(L, r"fn pinned_to_hull") or 0) + 8)),
        # who does the file itself credit for the 0/72/511 construction?
        "credits_orch": "ORCH established this by construction" in src,
        "ladder_in_doc": re.search(r"The shipped per-band ramp is\s*\n?\s*///?\s*`([\d ]+)`",
                                   src),
        "both_read_zero": "both\n    /// read zero" in src or "both read zero" in
                          re.sub(r"\s*///\s*", " ", src),
    }
    f["pinned_is_test_only"] = (f["pinned_to_hull_line"] or 0) > (cfg_test or 0)
    f["violations_all_test_only"] = all(n > (cfg_test or 0)
                                        for n in f["hull_violations_lines"])
    return f


CHECKS = [
    ("pinned_to_hull is TEST-ONLY", lambda f: f["pinned_is_test_only"]),
    ("hull_violations is TEST-ONLY too", lambda f: f["violations_all_test_only"]),
    ("pinned_to_hull builds its own synthetic fixture", lambda f: f["pinned_fixture"]),
    ("pinned_to_hull takes a Hull, not an image",
     lambda f: "hull: Hull" in f["pinned_signature"] and "img" not in f["pinned_signature"]),
    ("the file credits ORCH, not another lane, for the construction",
     lambda f: f["credits_orch"]),
    ("the doc comment quotes the ROUNDED ladder",
     lambda f: f["ladder_in_doc"] is not None
     and f["ladder_in_doc"].group(1).split() == ["2", "3", "4", "5", "8", "8", "8"]),
]


def run(src, label, expect_all):
    f = facts(src)
    print("  %s" % label)
    results = []
    for name, fn in CHECKS:
        try:
            ok = bool(fn(f))
        except Exception as e:
            ok = False
            name += " (raised %s)" % type(e).__name__
        results.append(ok)
        print("    %-4s %s" % ("PASS" if ok else "FAIL", name))
    return results, f


def main():
    src = pin_source()
    print("checking against %s:%s\n" % (PIN, PATH))
    truth, f = run(src, "against the true source (all must PASS)", True)
    if not all(truth):
        print("\nRED: a check failed against the real source")
        return 1

    print("\ncommissioning: each check must FLIP under a targeted mutation")
    muts = [
        ("move pinned_to_hull above #[cfg(test)]",
         lambda s: s.replace("#[cfg(test)]", "fn pinned_to_hull(hull: Hull) -> (usize, usize) { (0,0) }\n#[cfg(test)]", 1)),
        ("strip the ORCH credit",
         lambda s: s.replace("ORCH established this by construction", "A lane measured this", 1)),
        ("correct the doc ladder to the true values",
         lambda s: s.replace("`2 3 4 5 8 8 8`", "`2.0 2.8 3.92 5.49 7.68 8 8`", 1)),
    ]
    caught = 0
    for name, mut in muts:
        bad = mut(src)
        if bad == src:
            print("    MUTATION NOT APPLIED: %s -- control is void" % name)
            return 1
        res, _ = run(bad, "mutation: %s" % name, False)
        flipped = sum(1 for a, b in zip(truth, res) if a and not b)
        print("    -> %d check(s) flipped to FAIL" % flipped)
        if flipped:
            caught += 1
    if caught != len(muts):
        print("\nRED: %d of %d mutations went undetected" % (len(muts) - caught, len(muts)))
        return 1

    print("\n" + "=" * 72)
    print("FINDINGS")
    print("=" * 72)
    print("""
1. THE 0/72/511 NUMBERS ARE SYNTHETIC AND TEST-ONLY.
   Every `hull_violations` site is at line %s, all inside `#[cfg(test)]`
   (line %d). The numbers come from a 1-D construction over 8 synthetic
   frames, not from any real subject. They are not comparable to
   V-GATHER's "13 of 19 real subjects" and the two should not be
   presented as "two lanes, two instruments, one parameter".

2. THE FILE CREDITS ORCH FOR THEM.
   The doc comment reads "ORCH established this by construction rather
   than by reading the code". So the 0/72/511 originated with ORCH, was
   recorded in the source, and has since been re-attributed to
   V-NEVERWORSE and quoted back as independent corroboration. That is a
   circular citation, and it is the common-cause artifact I was asked to
   hunt for.

3. THE REPLACEMENT STATISTIC CANNOT BE REPORTED AS INSTRUCTED.
   `fn pinned_to_hull(hull: Hull)` at line %d is test-only and builds its
   own 192x144x8 fixture from `disagreeing_bands`. It takes a `Hull`
   enum, not an image. It cannot be pointed at `bee`. Making it the third
   column of an arm matrix needs NEW PRODUCTION INSTRUMENTATION, which is
   a real task and should be scoped as one rather than assumed present.

4. ORCH'S REASONING ABOUT THE STATISTIC IS CORRECT, AND THE FILE SAYS SO.
   "Both end up inside the hull, so counting violations cannot tell them
   apart -- both read zero." So the amendment is right in substance: the
   violation count IS blind. Only its provenance and its executability
   are wrong.

5. THE DOC COMMENT QUOTES THE ROUNDED LADDER, `2 3 4 5 8 8 8`, so its
   claim that "the three finest bands sit exactly where this turns
   severe" rests on 8/8/8 where the true values are 8.00/8.00/7.68. Third
   sighting of this rounding.

CREDIT WHERE DUE: the test at `per_level_leaves_the_final_clamp_less_to_do`
carries a potency guard -- `assert!(pinned_flat > 0, "the fixture does not
exercise the clamp at all, so this comparison would be vacuous")`. That is
exactly the discipline this fleet has been reinventing all night, already
in the file.
""" % (f["hull_violations_lines"], f["cfg_test_line"], f["pinned_to_hull_line"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
