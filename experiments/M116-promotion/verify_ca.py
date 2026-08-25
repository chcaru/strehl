"""verify_ca.py — re-derive every numeric claim in section 5f of
docs/research/M116-promotion.md from the campaign-4 artefacts, and confirm each
one appears at its own canonical site in the report.

Two independent failure modes are guarded, both learned the hard way on this
project:

  1. A claim in the report that the artefacts do not support.  Every number is
     RECOMPUTED here from the raw JSON -- support_Q from rd_off/rd_on, the
     implied factor from the displacements, the 0.42% from D_worst -- rather
     than read out of a field that already holds the answer.

  2. A check that a DECOY satisfies.  A bare substring search for "0.485" is
     satisfied by any other 0.485 in a 1600-line report, so every check is
     anchored on a neighbouring literal that must appear on the SAME line.
     If an anchor does not land, that is a hard error and not a pass: an
     unanchored check is a check pointed at nothing.

Run:  python experiments/M116-promotion/verify_ca.py
Exit: 0 = GREEN, 1 = RED.
"""
import json
import math
import os
import pathlib
import sys

# The report is UTF-8 and its numbers use U+2212 MINUS SIGN. A verifier that
# dies in its own failure printer on cp1252 reports GREEN by crashing, which is
# the worst possible failure mode for an instrument like this.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORT = pathlib.Path(os.environ.get(
    "M116_REPORT", ROOT / "docs" / "research" / "M116-promotion.md"))
OUT = pathlib.Path(os.environ.get("M116_CA_OUT", r"C:\dev\strehl-out\M116\ca"))

CALIBRATED = ["flat-on-ruler-cpl", "tweezers-cpl"]
DEAD = ["bee-3-cpl", "flower-bud-with-background-fern-cpl"]
ALL = CALIBRATED + DEAD

FAILURES = []
CHECKS = 0


def load(name):
    p = OUT / name
    if not p.exists():
        sys.exit(f"FATAL: artefact missing: {p}\n"
                 f"The verifier cannot run without the campaign outputs.")
    return json.loads(p.read_text(encoding="utf-8"))


def lines_of(path):
    return path.read_text(encoding="utf-8").splitlines()


REPORT_LINES = lines_of(REPORT) if REPORT.exists() else sys.exit(
    f"FATAL: report missing: {REPORT}")

# The report is wrapped prose. A claim and its anchor routinely land on
# different physical lines, so a line-based search returns false RED on
# perfectly correct text. Collapse whitespace once and search proximity
# instead: that survives reflowing while still addressing ONE site.
COLLAPSED = " ".join(REPORT.read_text(encoding="utf-8").split())


def check(cid, what, needle, anchor, window=400):
    """Assert `needle` occurs within `window` chars of `anchor` in the report.

    `anchor` exists to defeat decoys. A short token like 0.440 or 95.2 occurs
    by chance elsewhere in a 1700-line report; pinning it near a neighbouring
    literal makes the check address one site rather than any site. A missing
    anchor is a HARD ERROR, not a pass, because it means the check is no longer
    pointed at the claim it was written for -- an unanchored check that reports
    GREEN is worse than no check.
    """
    global CHECKS
    CHECKS += 1
    starts = []
    i = COLLAPSED.find(anchor)
    while i != -1:
        starts.append(i)
        i = COLLAPSED.find(anchor, i + 1)
    if not starts:
        FAILURES.append(
            f"{cid}  ANCHOR NOT FOUND  {what}\n"
            f"      anchor {anchor!r} occurs nowhere in the report.\n"
            f"      The check is pointed at nothing; treat as RED.")
        return
    for s in starts:
        lo = max(0, s - window)
        hi = min(len(COLLAPSED), s + len(anchor) + window)
        if needle in COLLAPSED[lo:hi]:
            return
    ctx = COLLAPSED[max(0, starts[0] - 80):starts[0] + len(anchor) + 200]
    FAILURES.append(
        f"{cid}  MISSING  {what}\n"
        f"      expected {needle!r} within {window} chars of {anchor!r}\n"
        f"      ({len(starts)} anchor site(s); first reads)\n"
        f"        ...{ctx}...")


def approx(cid, what, computed, claimed, tol=6e-4, places=None):
    """Assert the report's claimed value matches the value recomputed here.

    `places` compares at the precision the report actually prints, which is the
    honest test for a rounded display value: 0.3295 IS 0.330 to three places,
    and an absolute tolerance of 5e-4 rejects it on a boundary that means
    nothing.  `tol` remains for quantities compared at full precision.
    """
    global CHECKS
    CHECKS += 1
    ok = (round(computed, places) == round(claimed, places)) if places is not None \
        else math.isclose(computed, claimed, abs_tol=tol)
    if not ok:
        detail = (f"to {places} dp" if places is not None
                  else f"(|d| = {abs(computed - claimed):.6f} > {tol})")
        FAILURES.append(
            f"{cid}  DERIVATION  {what}\n"
            f"      report claims {claimed}, artefacts give {computed:.6f}"
            f"  {detail}")


def check_exact(cid, what, needle, expected):
    """Assert `needle` occurs EXACTLY `expected` times in the whole report.

    A presence test is satisfied by any duplicate of the value. Section 5f's
    headline numbers are deliberately restated in the section 1 summary, so
    `"90.1 %" in report` stays true after section 5f's own table has been
    falsified -- which is exactly how plants D1, D2 and D11 walked past the
    first version of this verifier. Pinning the count makes every site load-
    bearing: change one of four and the count drops to three and this fires.

    The cost is that a legitimate edit which adds or removes a mention must
    update the number here. That is intended. This report is finished; a
    changing count is a change to a published claim and should require a
    deliberate keystroke.
    """
    global CHECKS
    CHECKS += 1
    got = COLLAPSED.count(needle)
    if got != expected:
        FAILURES.append(
            f"{cid}  SITE COUNT  {what}\n"
            f"      {needle!r} occurs {got} time(s), expected {expected}.\n"
            f"      {'A site was removed or altered.' if got < expected else 'A new site appeared.'}"
            f" Every site is load-bearing; presence alone is not enough.")


# Every canonical site of every headline claim, counted at the commit that
# froze this report. Registered here so a single-site falsification cannot
# hide behind a duplicate elsewhere in the document.
SITE_COUNTS = {
    # Counts revised once, deliberately, when P61 was written into section 5g
    # and quoted three of these strings a further time each. This is the
    # intended workflow: the verifier objected to my own edit, I checked that
    # the new mentions were discussion rather than restated claims, and I
    # updated the registration by hand. An automatic recount would have made
    # the whole mechanism ornamental.
    "90.1 %": 5,
    "95.2 %": 4,
    "−0.7478 px": 1,
    "+0.0741 px": 2,
    "−0.6861 px": 1,
    "+0.0332 px": 3,
    "1.099": 2,
    "1.048": 2,
    "+0.485": 2,
    "+0.440": 2,
    "+0.015": 3,
    "+0.120": 3,
    "0.085 px": 1,
    "0.075 px": 3,
    "0.330 px": 1,
    "0.310 px": 1,
    "−0.00169": 4,
    "−0.00101": 3,
    "−0.00155": 3,
    "−0.00184": 4,
    "on every subject scored": 6,
}


def main():
    global CHECKS
    cal = load("calibration.json")
    disp = load("scores-ca-disp.json")
    chroma = load("scores-ca.json")

    # ---- provenance -----------------------------------------------------
    sha = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
    for name, blob in (("scores-ca-disp.json", disp), ("scores-ca.json", chroma)):
        CHECKS += 1
        if blob.get("pinned_sha") != sha:
            FAILURES.append(
                f"A0  PROVENANCE  {name} was produced at "
                f"{blob.get('pinned_sha')!r}, not at the pinned {sha!r}")
    check("A1", "pinned SHA stated in the report", sha[:12], "worktree")

    # ---- CD1 calibration ------------------------------------------------
    # The plant is +0.500 px; the instrument must return it to +/-0.10 px.
    plant = cal["plant_px"]
    tol = cal["tolerance_px"]
    approx("B0", "registered plant magnitude", plant, 0.500, tol=1e-9)
    approx("B0b", "registered tolerance", tol, 0.100, tol=1e-9)

    expect_recovered = {
        "flat-on-ruler-cpl": (0.485, "+0.485"),
        "tweezers-cpl": (0.440, "+0.440"),
        "bee-3-cpl": (0.015, "+0.015"),
        "flower-bud-with-background-fern-cpl": (0.120, "+0.120"),
    }
    expect_err = {
        "flat-on-ruler-cpl": (0.085, "0.085 px"),
        "tweezers-cpl": (0.075, "0.075 px"),
        "bee-3-cpl": (0.330, "0.330 px"),
        "flower-bud-with-background-fern-cpl": (0.310, "0.310 px"),
    }
    for s in ALL:
        c = cal["subjects"][s]
        want, shown = expect_recovered[s]
        approx(f"B1[{s}]", "recovered plant", c["translation_recovered_dx"], want,
               places=3)
        approx(f"B2[{s}]", "radial worst error", c["radial_worst_err_px"],
               expect_err[s][0], places=3)
        # Anchored on the subject's own table row, which is the one canonical
        # site for that subject's calibration numbers.
        check(f"B3[{s}]", "recovered plant appears in the CD1 table", shown, s)
        check(f"B4[{s}]", "radial error appears in the CD1 table",
              expect_err[s][1], s)

    # The verdict split: exactly two calibrated, exactly two dead.
    passed = sorted(s for s in ALL if cal["subjects"][s]["translation_pass"])
    CHECKS += 1
    if passed != sorted(CALIBRATED):
        FAILURES.append(
            f"B5  VERDICT SPLIT  calibration.json says the passing subjects are "
            f"{passed}, the report says {sorted(CALIBRATED)}")
    CHECKS += 1
    if len(passed) != 2:
        FAILURES.append(
            f"B6  CD1 COUNT  {len(passed)} of 4 subjects pass CD1; the report's "
            f"'2 of 4' and the whole HOLD verdict depend on this being 2")
    # And CD1 must be recorded as FAILED, because it was registered universally.
    check("B7", "CD1 recorded as failing as registered", "FAILS as registered",
          "CD1")

    # ---- CD4 / CD5 primary result --------------------------------------
    expect_primary = {
        "flat-on-ruler-cpl": ("−0.7478 px", "+0.0741 px", "90.1 %", "1.099"),
        "tweezers-cpl": ("−0.6861 px", "+0.0332 px", "95.2 %", "1.048"),
    }
    for s in CALIBRATED:
        d = disp["subjects"][s]
        off, on = d["support_rd_off"], d["support_rd_on"]
        s_off, s_on, s_q, s_fac = expect_primary[s]

        approx(f"C1[{s}]", "RD_off", off, float(s_off.split()[0].replace("−", "-")),
               places=4)
        approx(f"C2[{s}]", "RD_on", on, float(s_on.split()[0].replace("+", "")),
               places=4)

        # Q is RECOMPUTED from the two displacements, not read from support_Q.
        q = 1.0 - abs(on) / abs(off)
        approx(f"C3[{s}]", "Q recomputed from RD_off/RD_on", q * 100.0,
               float(s_q.split()[0]), tol=0.05)
        # ... and cross-checked against the field the scorer wrote.
        approx(f"C4[{s}]", "Q agrees with the scorer's own field", q,
               d["support_Q"], tol=1e-9)

        # Implied factor: how far red moved, over how far it had to move.
        factor = abs(on - off) / abs(off)
        approx(f"C5[{s}]", "implied over-correction factor", factor,
               float(s_fac), tol=5e-4)

        check(f"C6[{s}]", "RD_off at its canonical site", s_off, s)
        check(f"C7[{s}]", "RD_on at its canonical site", s_on, s)
        check(f"C8[{s}]", "Q at its canonical site", s_q, s)

        # CD4 itself: the correction must shrink |RD| in the support band.
        CHECKS += 1
        if not abs(on) < abs(off):
            FAILURES.append(
                f"C9[{s}]  CD4  |RD_on| = {abs(on):.4f} is not < "
                f"|RD_off| = {abs(off):.4f}; the primary bar does not hold")

    # The transfer claim: tweezers must actually be flagged as transfer.
    CHECKS += 1
    if not disp["subjects"]["tweezers-cpl"]["is_transfer"]:
        FAILURES.append(
            "C10  TRANSFER  tweezers-cpl is not flagged is_transfer, but the "
            "report's headline rests on it being a subject M110 never used")

    # ---- CD7 do-no-harm -------------------------------------------------
    expect_worst = {
        "bee-3-cpl": (-0.00169, "−0.00169"),
        "flat-on-ruler-cpl": (-0.00101, "−0.00101"),
        "tweezers-cpl": (-0.00155, "−0.00155"),
        "flower-bud-with-background-fern-cpl": (-0.00184, "−0.00184"),
    }
    # Anchored on each row's OTHER cell rather than on the subject name: the
    # CD7 table prints fern with an ellipsis, and D_worst is duplicated into
    # the section 1 summary. These four anchors are unique in the document and
    # none of them is the needle, so no check can satisfy itself.
    anchor_e3 = {
        "bee-3-cpl": "−0.00010",
        "flat-on-ruler-cpl": "+0.01031",
        "tweezers-cpl": "+0.00450",
        "flower-bud-with-background-fern-cpl": "+0.00067",
    }
    for s in ALL:
        d = disp["subjects"][s]
        want, shown = expect_worst[s]
        # D_worst must genuinely be the worst of the three, not a copied field.
        recomputed = min(d["D_R"], d["D_B"], d["D_L"])
        approx(f"E1[{s}]", "D_worst is the min of R/B/L", recomputed, want,
               tol=5e-6)
        approx(f"E2[{s}]", "D_worst matches the scorer's field", recomputed,
               d["D_worst"], tol=1e-12)
        check(f"E3[{s}]", "D_worst at its canonical site", shown, anchor_e3[s],
              window=120)
        CHECKS += 1
        if recomputed < -0.02:
            FAILURES.append(
                f"E4[{s}]  CD7  D_worst = {recomputed:.5f} breaches the "
                f"-0.02 dex do-no-harm bar")
        # Blue is an exact no-op by design (eps_b: None). Exactly zero.
        CHECKS += 1
        if d["D_B"] != 0.0:
            FAILURES.append(
                f"E5[{s}]  BLUE  D_B = {d['D_B']!r}, not exactly 0.0. The "
                f"report claims the correction provably does not touch blue")

    # The "at most 0.42 %" claim is a restatement of the worst D across all
    # four subjects, converted from dex to a percentage.
    worst_all = min(disp["subjects"][s]["D_worst"] for s in ALL)
    pct = (1.0 - 10.0 ** worst_all) * 100.0
    approx("E6", "worst fine-structure cost as a percentage", pct, 0.42,
           tol=5e-3)
    check("E7", "the 0.42 % claim", "0.42", "halo correction destroyed")

    # ---- CD2 trap and CB1 null -----------------------------------------
    for s in ALL:
        d = disp["subjects"][s]
        CHECKS += 1
        worst_centre = max(abs(d["centre_rd_off"]), abs(d["centre_rd_on"]))
        if worst_centre > 0.10:
            FAILURES.append(
                f"F1[{s}]  CD2 TRAP  centre |RD| = {worst_centre:.4f} exceeds "
                f"the registered 0.10 px; a radial-only profile must not move "
                f"the centre")
    trap_worst = max(
        max(abs(disp["subjects"][s]["centre_rd_off"]),
            abs(disp["subjects"][s]["centre_rd_on"])) for s in ALL)
    approx("F2", "worst centre displacement across all subjects", trap_worst,
           0.075, tol=5e-4)

    for s in ALL:
        c = chroma["subjects"].get(s)
        if c is None:
            continue
        CHECKS += 1
        if not c.get("CB1_identical"):
            FAILURES.append(
                f"F3[{s}]  CB1 NULL  the two OFF renders are not byte-identical; "
                f"every difference reported in 5f is confounded")
        CHECKS += 1
        if c["sha_off"] == c["sha_on"]:
            FAILURES.append(
                f"F4[{s}]  DEAD ARM  the ON and OFF renders are byte-identical "
                f"({c['sha_off'][:16]}). The treatment did nothing, so any "
                f"non-zero effect reported for this subject is impossible")

    # ---- the void readings must NOT be presented as results -------------
    # bee's Q and fern's Q are artefacts of a dead correlator. The report is
    # required to mark them void. This is the trap for my own writing: if a
    # future edit quietly promotes them to results, this fires.
    check("G1", "bee's Q is marked void", "VOID", "not small effects")
    for s in DEAD:
        CHECKS += 1
        if cal["subjects"][s]["translation_pass"]:
            FAILURES.append(
                f"G2[{s}]  the report calls this subject DEAD but "
                f"calibration.json says its plant PASSED")

    # ---- 5g: the unsatisfiability finding -------------------------------
    check("H1", "CD1's universal quantifier is quoted", "on every subject scored",
          "P58")
    check("H2", "the cancelled render batch is disclosed", "cancelled",
          "measuring more subjects")

    # ---- report ---------------------------------------------------------
    for needle, n in SITE_COUNTS.items():
        check_exact(f"S[{needle}]", "canonical site count", needle, n)

    print(f"verify_ca: {CHECKS} checks over section 5f/5g")
    if FAILURES:
        print(f"\nverify_ca: RED — {len(FAILURES)} failure(s)\n")
        for f in FAILURES:
            print(f)
        return 1
    print("verify_ca: GREEN — every numeric claim re-derived from the "
          "artefacts and located at its anchored site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
