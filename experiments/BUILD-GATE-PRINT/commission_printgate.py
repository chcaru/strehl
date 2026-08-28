"""Commission `experiments/ORCH-drift-check/orch_printready.py`'s CORRECTED clip
gate, and prove that its crush statistic cannot issue a verdict.

WHAT THIS ADDS TO `commission_clip.py`

`commission_clip.py` (ORCH, commit 04074ab8) already runs the two arms that
matter most and it is not repeated here -- run it too. Its arms are:

    CLEAN / NEUTRAL (all-3 blow, must FAIL) / ONECHAN (one-channel pin, must
    PASS) / TINY (sub-threshold blow, must PASS)

Four things it does NOT do, and all four are load-bearing:

  1. A NULL ARM. It never scores the unmodified corpus, so it cannot say what
     the gate's verdict distribution on real data actually is. A gate whose
     plants behave and whose corpus is uniformly green may be a working gate --
     or it may be a gate with no discriminating power left on the only inputs
     anyone will ever run it on. Those look identical from the plant arms alone,
     and the difference is the whole question. This arm states the distribution.

  2. A REGRESSION ARM ON REAL PIXELS. The defect that motivated the correction
     was a specific master being failed and specific others being passed. The
     plant arms cannot re-test that; only the masters can.

  3. A DOSE-RESPONSE LADDER. A single over-threshold plant shows the gate fires
     somewhere. It does not show the gate fires AT ITS THRESHOLD. A statistic
     that fired at a thousandth of CLIP_MAX would pass the NEUTRAL arm and be a
     presence check wearing a threshold's clothes.

  4. A CRUSH ARM. `crush` is computed, printed, and deliberately not gated.
     "Deliberately not gated" is a claim about code that nobody has tested. It
     is one `if` away from being re-gated by a well-meaning reader, and the
     symptom would be masters failing for having open shadows. So: plant a
     genuinely crushed region far above anything in the corpus and require the
     verdict NOT to move, while requiring the printed number TO move. Both
     halves are needed -- a gate that ignores crush because it never computes it
     has lost the measurement, which is the other failure.

EVERY ARM'S VERDICT IS PREDICTED IN THE ARM TABLE BEFORE IT RUNS, and the arm
is checked on the FAILURE REASON as well as on the verdict. A plant large enough
to change `flattest()`'s chosen window could make an arm FAIL for banding while
the clip gate sat silent, and a bare PASS/FAIL comparison would have scored that
as a success.

Usage:
    python commission_printgate.py <corpus-dir> <arm-suffix>

e.g.
    python commission_printgate.py C:\\dev\\strehl-out\\acceptance\\SHIP-V3 SHIP-V3
"""

import pathlib
import re
import subprocess
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE.parents[1] / "experiments" / "ORCH-drift-check" / "orch_printready.py"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\BUILD-GATE-PRINT")

# Must track orch_printready.CLIP_MAX. Asserted against the source below rather
# than trusted, because a commissioning constant that silently drifts from the
# gate's own constant commissions a gate that does not exist.
CLIP_MAX = 0.001
CRUSH_DN = 35
CLIP_DN = 65500

# The real-data arms. Each is (subject, accepted-verdicts, why-it-is-here).
# These are read out of ONE run over the unmodified corpus, which is also the
# null arm -- the same numbers cannot be quoted for two purposes and disagree.
#
# WHY THE PREDICTION IS A SET AND NOT A SINGLE GLYPH. These arms are about the
# CLIP gate, and the gate emits five outcomes, only one of which clip can
# cause. Reading `verdict()`: `fails` is populated by banding and clip alone,
# and a non-empty `fails` returns FAIL immediately -- so REVIEW is reachable
# only when `fails` is empty, and ACQUIT is reachable only from REVIEW. An
# acquittal is therefore STRUCTURALLY incapable of masking a clip failure; it
# can only ever waive a blotch or chroma REVIEW. Demanding the literal glyph
# "PASS" from a clip arm would fail the arm whenever an unrelated statistic
# raised a REVIEW, which is a false alarm about the wrong instrument. So each
# arm names the outcomes that are consistent with its clip prediction, and the
# clip number is asserted separately against CLIP_MAX below.
REAL_ARMS = [
    ("dry-erase-marker-head-cpl", ("PASS",),
     "REGRESSION. The corpus's only master with ZERO blown highlights "
     "(clipALL3 = 0.0000%, the joint minimum over 26). The old channel-sample "
     "statistic FAILED it. If it does not pass now, the correction did nothing."),
    ("flowers-cpl", ("PASS",),
     "SPECIFICITY ON REAL PIXELS. Carries the corpus's heaviest single-channel "
     "gamut pin (clipONE 0.4004%, B==65535 at 0.4458%) and reads 0.1433% on the "
     "OLD statistic -- over the 0.1% threshold, so the old gate failed it -- "
     "against 0.0086% on the corrected one. This is the gamut wall, not a blow."),
    ("112MSDCF", ("PASS", "ACQUIT"),
     "The corpus MAXIMUM on the corrected statistic (clipALL3 0.0691%). It "
     "passed under the old gate too, at 0.0775% -- which is the scandal the "
     "correction fixes: it carried 5.3x more genuine clipping than flowers-cpl "
     "and was passed while flowers-cpl was failed. It must not be FAILED, and "
     "the margin to CLIP_MAX is the headroom this threshold actually has. It "
     "reads ACQUIT, not PASS: it carries a registered acquittal on an unrelated "
     "chroma/blotch REVIEW, which -- see above -- cannot be reached at all if "
     "clip had gated it. Its clip number is asserted against CLIP_MAX directly."),
]


def gate_source_constant(name):
    """Read a constant out of the gate's source. Do not duplicate it by hand."""
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r"^%s\s*=\s*([0-9.eE+-]+)" % re.escape(name), src, re.M)
    if not m:
        raise SystemExit("could not find `%s` in %s" % (name, GATE))
    return float(m.group(1))


def run_gate(directory, arm):
    r = subprocess.run([sys.executable, str(GATE), str(directory), arm],
                       capture_output=True, text=True)
    return r.stdout + r.stderr, r.returncode


ROW = re.compile(r"^(PASS|FAIL|REVIEW|ACQUIT|EXPIRED|SKIP)\s+(\S+)\s+(.*)$")


def rows_of(text):
    """subject -> (verdict, detail). Verdicts are the gate's own partition names."""
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            out[m.group(2)] = (m.group(1), m.group(3).strip())
    return out


def partition_of(text):
    m = re.search(r"^partition: (.*)$", text, re.M)
    return m.group(1) if m else "(no partition line)"


def clip_of(detail):
    m = re.search(r"clip ([0-9.]+)% \(gamut ([0-9.]+)%\)", detail)
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


def crush_of(detail):
    m = re.search(r"crush ([0-9.]+)%", detail)
    return float(m.group(1)) if m else None


def blotch_of(detail):
    m = re.search(r"blotch ([0-9.]+)", detail)
    return m.group(1) if m else "-"


def plant(a, frac, channels, value, mode="band"):
    """Set `frac` of the frame to `value` on `channels`.

    Two geometries, because one of them is not safe for every arm.

    mode="band" -- a contiguous full-width band from row 0. Good for CLIP arms:
    `flattest()` searches for a 900x900 window, so a band of fewer than 900
    rows cannot become the flattest window on its own, and a band planted at
    the WHITE end raises the window mean rather than collapsing it.

    mode="sparse" -- a deterministic scattered mask at the same areal fraction,
    spread over the whole frame. Required for the CRUSH arm. `blotch_ratio` is
    std(band)/MEAN, so a contiguous BLACK band drives the denominator toward
    zero and manufactures a blotch REVIEW that has nothing to do with crush --
    measured, not assumed: a 468-row black band moved blotch 0.00446 -> 0.02742
    and tripped BLOTCH_REVIEW = 0.02. That is a defect in the PLANT, not in the
    gate. A scattered mask moves `crush` -- a position-independent per-pixel
    mean -- by exactly the same amount while leaving the mid-scale `band` term
    alone, because both boxblurs remove single-pixel structure. It changes one
    variable, which is what a plant is for. Both are run; see the arms below.
    """
    out = a.copy()
    h, w = out.shape[0], out.shape[1]
    if mode == "band":
        rows = max(1, int(round(frac * h * w)) // w)
        for c in channels:
            out[:rows, :, c] = value
        return out, rows * w / float(h * w), "%d rows" % rows
    if mode == "sparse":
        # Deterministic, seeded, no reliance on stride aliasing against the
        # sensor pattern: draw a fixed permutation and take the first `frac`.
        rng = np.random.default_rng(20260828)
        mask = rng.random((h, w)) < frac
        for c in channels:
            out[:, :, c][mask] = value
        return out, float(mask.mean()), "%d scattered px" % int(mask.sum())
    raise SystemExit("unknown plant mode %r" % mode)


def plant_arm(base, name, frac, channels, value, expect, expect_reason, notes,
              mode="band", forbid_reason=None):
    d = SCRATCH / name
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.tif*"):
        old.unlink()
    planted, actual, geom = plant(base, frac, channels, value, mode)
    stem = "commission-" + name.lower()
    tifffile.imwrite(str(d / ("%s--%s.tiff" % (stem, name))), planted)
    text, _ = run_gate(d, name)
    got = rows_of(text)
    verdict, detail = got.get(stem, ("MISSING", "<no row emitted>"))
    part = partition_of(text)
    accept = (expect,) if isinstance(expect, str) else tuple(expect)
    ok = verdict in accept
    reason_ok = True
    if expect_reason is not None:
        reason_ok = expect_reason in detail
    # A negative assertion as well as a positive one. "The verdict did not
    # move" is satisfied by a gate that never ran; "the verdict moved, but for
    # a statistic that is NOT the one I planted" is the subtler failure, and it
    # is only catchable by naming the term that must be absent from the reason.
    #
    # Only the REASON segment counts, not the whole detail line. The detail
    # line always contains the word "crush" because the gate REPORTS crush as a
    # number -- which is the entire point of leaving it in. Searching the whole
    # line for "crush" therefore fires on every arm and proves nothing. The
    # verdict-bearing text is what follows "<==".
    forbid_ok = True
    reason_seg = detail.split("<==")[-1] if "<==" in detail else ""
    if forbid_reason is not None:
        forbid_ok = forbid_reason not in reason_seg
    # Every arm must also partition to exactly its one input. An arm the gate
    # declined to examine reads as a quiet pass otherwise.
    part_ok = "1 total (found 1)" in part
    return {
        "arm": name, "expect": "|".join(accept), "got": verdict,
        "ok": ok and reason_ok and part_ok and forbid_ok,
        "verdict_ok": ok, "reason_ok": reason_ok, "part_ok": part_ok,
        "forbid_ok": forbid_ok, "reason_seg": reason_seg,
        "planted_frac": actual, "geom": geom, "detail": detail, "partition": part,
        "notes": notes,
    }


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    corpus = pathlib.Path(argv[1])
    arm = argv[2]
    if not corpus.is_dir():
        raise SystemExit("no such corpus directory: %s" % corpus)
    if not GATE.is_file():
        raise SystemExit("cannot find the gate at %s" % GATE)

    src_clip_max = gate_source_constant("CLIP_MAX")
    print("=" * 100)
    print("COMMISSIONING THE CORRECTED PRINT GATE")
    print("=" * 100)
    print("gate      : %s" % GATE)
    print("corpus    : %s   (arm suffix `%s`)" % (corpus, arm))
    print("CLIP_MAX  : %.6f in the gate source, %.6f here -- %s"
          % (src_clip_max, CLIP_MAX,
             "AGREE" if src_clip_max == CLIP_MAX else "*** DISAGREE, ABORTING ***"))
    if src_clip_max != CLIP_MAX:
        return 2
    print()

    failures = []

    # ---------------------------------------------------------------- null arm
    print("-" * 100)
    print("ARM 1of4  NULL -- the unmodified corpus. This arm has no planted defect and")
    print("          exists to state the verdict distribution on real data. If every")
    print("          subject passes, the plant arms below are the ONLY evidence the")
    print("          gate discriminates, and this report must say so out loud.")
    print("-" * 100)
    text, rc = run_gate(corpus, arm)
    corpus_rows = rows_of(text)
    part = partition_of(text)
    print("partition : %s" % part)
    print("exit code : %d" % rc)
    m = re.search(r"(\d+) total \(found (\d+)\)", part)
    if not m or m.group(1) != m.group(2):
        print("*** PARTITION DOES NOT SUM -- every number below is void ***")
        failures.append("null arm partition does not sum")
    else:
        print("partition sums: %s counted == %s found" % (m.group(1), m.group(2)))
    n_fail = int(re.search(r"(\d+) FAIL", part).group(1))
    print()
    print("clip and crush per subject, as NUMBERS beside their subject -- never a bare")
    print("verdict. `clip` is the all-3-channel statistic that gates; `gamut` is the old")
    print("channel-sample statistic, retained for comparison and gating nothing; `crush`")
    print("is reported and gates nothing by design.")
    print("%-38s %-8s %10s %10s %10s" % ("subject", "verdict", "clipALL3", "gamut(old)", "crush"))
    print("-" * 82)
    worst = ("", -1.0)
    old_would_fail = []
    for name in sorted(corpus_rows):
        v, d = corpus_rows[name]
        c, g = clip_of(d)
        cr = crush_of(d)
        if c is None:
            print("%-38s %-8s %10s %10s %10s" % (name[:38], v, "-", "-", "-"))
            continue
        print("%-38s %-8s %9.4f%% %9.4f%% %9.3f%%" % (name[:38], v, c, g, cr))
        if c > worst[1]:
            worst = (name, c)
        if g > src_clip_max * 100:
            old_would_fail.append((name, g, c, v))
    print("-" * 82)
    print("corpus maximum on the GATING statistic : %s at %.4f%%  (CLIP_MAX = %.1f%%, "
          "headroom %.1fx)" % (worst[0], worst[1], src_clip_max * 100,
                               src_clip_max * 100 / worst[1] if worst[1] else float("inf")))
    if old_would_fail:
        print("subjects the OLD statistic would still fail, and the corrected one passes:")
        for name, g, c, v in old_would_fail:
            print("   %-36s old %.4f%% > %.1f%%   corrected %.4f%%   verdict now %s"
                  % (name, g, src_clip_max * 100, c, v))
    else:
        print("no subject exceeds the threshold on the OLD statistic either.")
    print()
    print("NULL ARM CONCLUSION: %d of %s masters FAIL. %s"
          % (n_fail, m.group(2) if m else "?",
             "The gate issues no FAIL on this corpus, so its discriminating power is "
             "demonstrated ONLY by the planted arms below -- state that in any report "
             "that quotes this table." if n_fail == 0 else
             "The gate fails at least one real master, so it is not vacuous on this corpus."))
    print()

    # ---------------------------------------------------------- regression arm
    print("-" * 100)
    print("ARM 2of4  REGRESSION -- named subjects, predicted verdict written above,")
    print("          read out of the SAME corpus run as the null arm.")
    print("-" * 100)
    for subject, accept, why in REAL_ARMS:
        v, d = corpus_rows.get(subject, ("MISSING", "<not in this corpus>"))
        c, g = clip_of(d)
        # Two independent assertions, because the verdict glyph alone is a
        # summary and the number is the evidence. (1) the subject is not
        # FAILED and lands in one of the outcomes its clip prediction admits;
        # (2) its clip statistic is genuinely under the threshold -- a subject
        # that passed for some reason OTHER than being under CLIP_MAX would
        # satisfy (1) and is exactly the silent-pass this whole exercise is about.
        verdict_ok = v in accept
        clip_ok = c is not None and (c / 100.0) <= CLIP_MAX
        ok = verdict_ok and clip_ok
        if not ok:
            failures.append("regression arm %s: expected one of %s got %s "
                            "(verdict_ok=%s clip_under_CLIP_MAX=%s)"
                            % (subject, "/".join(accept), v, verdict_ok, clip_ok))
        print("%-34s expect %-14s got %-8s %s"
              % (subject, "|".join(accept), v, "OK" if ok else "*** WRONG ***"))
        print("   clipALL3 %s   old-statistic %s   clipALL3 <= CLIP_MAX (%.1f%%): %s"
              % ("%.4f%%" % c if c is not None else "-",
                 "%.4f%%" % g if g is not None else "-",
                 CLIP_MAX * 100, "YES" if clip_ok else "*** NO ***"))
        print("   %s" % why)
    print()

    # ------------------------------------------------- sensitivity/specificity
    print("-" * 100)
    print("ARM 3of4  PLANTED -- sensitivity, specificity and the dose-response ladder.")
    print("          Planted onto %s, the zero-clipping master, so any clip the gate"
          % REAL_ARMS[0][0])
    print("          reads is the plant and nothing else.")
    print("-" * 100)
    base_path = None
    for p in corpus.glob("*%s*.tiff" % REAL_ARMS[0][0]):
        base_path = p
        break
    if base_path is None:
        raise SystemExit("cannot find a %s master in %s" % (REAL_ARMS[0][0], corpus))
    base = tifffile.imread(str(base_path))[..., :3]
    print("base      : %s  shape %s  dtype %s" % (base_path.name, base.shape, base.dtype))
    print("base clip : all-3 %.6f%%   any-channel %.6f%%"
          % (float(((base >= CLIP_DN).sum(axis=2) == 3).mean()) * 100,
             float((base >= CLIP_DN).any(axis=2).mean()) * 100))
    print()

    arms = [
        # name           frac              chans      value  expect              reason      mode      forbid
        ("SENS-4X",      CLIP_MAX * 4.0,   (0, 1, 2), 65535, "FAIL",             "clipped",  "band",   None),
        ("SPEC-40X",     CLIP_MAX * 40.0,  (1,),      65535, "PASS",             None,       "band",   "clipped"),
        ("DOSE-0P5X",    CLIP_MAX * 0.5,   (0, 1, 2), 65535, "PASS",             None,       "band",   "clipped"),
        ("DOSE-2X",      CLIP_MAX * 2.0,   (0, 1, 2), 65535, "FAIL",             "clipped",  "band",   None),
        # The crush ladder. Every rung asserts the claim being commissioned --
        # NOT FAIL, and `crush` absent from the verdict-bearing reason -- and
        # the rungs together locate the dose at which the CONFOUNDER (blotch)
        # starts to speak, which is the honest way to present a plant that
        # cannot be made single-variable. See the note on CRUSHBAND.
        ("CRUSH-1PC",    0.01,             (0, 1, 2), 0,     ("PASS", "REVIEW"), None,       "band",   "crush"),
        ("CRUSH-2P5PC",  0.025,            (0, 1, 2), 0,     ("PASS", "REVIEW"), None,       "band",   "crush"),
        ("CRUSH-5PC",    0.05,             (0, 1, 2), 0,     ("PASS", "REVIEW"), None,       "band",   "crush"),
        ("CRUSHBAND",    CLIP_MAX * 100.0, (0, 1, 2), 0,     ("PASS", "REVIEW"), "blotch",   "band",   "crush"),
        ("CRUSHSPARSE",  CLIP_MAX * 100.0, (0, 1, 2), 0,     ("PASS", "REVIEW"), None,       "sparse", "crush"),
    ]
    crush_ladder = ["CRUSH-1PC", "CRUSH-2P5PC", "CRUSH-5PC", "CRUSHBAND", "CRUSHSPARSE"]
    notes = {
        "SENS-4X": "SENSITIVITY. All three channels at the ceiling over 4x CLIP_MAX. "
                   "A neutral blow is a specular or a blown white and no renderer "
                   "recovers it. If this passes, the gate is decorative.",
        "SPEC-40X": "SPECIFICITY. ONE channel at the ceiling over FORTY times "
                    "CLIP_MAX -- ten times the area of the arm above, and no "
                    "all-channel clipping at all. This is the sRGB gamut wall that "
                    "gamut_map manufactures on every out-of-gamut colour pixel, and "
                    "it is exactly what the OLD statistic failed masters for. If "
                    "this fails, the correction did not take.",
        "DOSE-0P5X": "THRESHOLD, low side. Half of CLIP_MAX, same mechanism as "
                     "SENS-4X. Must pass, or the gate is a presence check.",
        "DOSE-2X": "THRESHOLD, high side. Twice CLIP_MAX. With DOSE-0P5X this "
                   "brackets the threshold within a factor of 4 on the same plant.",
        "CRUSH-1PC": "CRUSH LADDER, rung 1. 1% of the frame at zero on all three "
                     "channels. Must not FAIL and must not be named in a reason.",
        "CRUSH-2P5PC": "CRUSH LADDER, rung 2. 2.5% -- comparable to 109MSDCF's real "
                       "2.470%, which the corpus run above scores PASS.",
        "CRUSH-5PC": "CRUSH LADDER, rung 3. 5%, above the corpus maximum of 3.639% "
                     "(flower-inner-edge-cpl).",
        "CRUSHBAND": "CRUSH LADDER, rung 4, and the CONFOUNDER ARM. 10% of the frame "
                     "as a contiguous black band. `blotch_ratio` is std(band)/MEAN, so "
                     "a large black region collapses the denominator: blotch runs "
                     "0.00446 -> 0.02742 and trips BLOTCH_REVIEW = 0.02. The verdict "
                     "moves, and the reason names BLOTCH. That is the plant perturbing "
                     "a second statistic, not crush voting -- which is why every rung "
                     "asserts the absence of `crush` from the reason rather than mere "
                     "verdict stability.",
        "CRUSHSPARSE": "THE SAME DOSE SCATTERED, kept because it refutes this lane's "
                       "own first fix. Scattering was predicted to leave blotch alone "
                       "because both boxblurs remove single-pixel structure. It does "
                       "not: a difference of box filters at two radii does not cancel "
                       "an injection this large, and blotch goes to 0.25219 -- WORSE "
                       "than the band. So there is no geometry that moves crush by a "
                       "large factor and moves nothing else, and the claim has to be "
                       "carried by the reason string and by real data instead.",
    }
    results = []
    for name, frac, chans, value, expect, reason, mode, forbid in arms:
        r = plant_arm(base, name, frac, chans, value, expect, reason, notes[name],
                      mode=mode, forbid_reason=forbid)
        results.append(r)
        if not r["ok"]:
            failures.append("planted arm %s: expected %s got %s (verdict_ok=%s "
                            "reason_ok=%s partition_ok=%s forbidden_term_absent=%s)"
                            % (name, r["expect"], r["got"], r["verdict_ok"],
                               r["reason_ok"], r["part_ok"], r["forbid_ok"]))
    for r in results:
        print("%-11s expect %-8s got %-8s planted %.4f%% of frame (%s)   %s"
              % (r["arm"], r["expect"], r["got"], r["planted_frac"] * 100, r["geom"],
                 "OK" if r["ok"] else "*** WRONG ***"))
        print("   %s" % r["detail"])
        print("   partition: %s" % r["partition"])
        if not r["reason_ok"]:
            print("   *** the verdict is right but the REASON is not: this arm did not")
            print("   *** move the statistic it claims to, so it proves nothing.")
        if not r["forbid_ok"]:
            print("   *** the reason string names the statistic that must NOT be able")
            print("   *** to reach a verdict. That statistic is gated after all.")
        print("   %s" % r["notes"])
        print()

    # ------------------------------------------------------------- crush, both halves
    print("-" * 100)
    print("ARM 4of4  CRUSH IS REPORTED BUT CANNOT VOTE.")
    print("          Three independent lines, because NO PLANT GEOMETRY IS SINGLE-")
    print("          VARIABLE HERE: both a contiguous black band and a scattered black")
    print("          mask move `blotch` as well as `crush` (rung table above). So")
    print("          `the verdict did not move' cannot carry this claim on its own.")
    print("-" * 100)
    clean_crush = None
    cd = SCRATCH / "CLEAN"
    cd.mkdir(parents=True, exist_ok=True)
    for old in cd.glob("*.tif*"):
        old.unlink()
    tifffile.imwrite(str(cd / "commission-clean--CLEAN.tiff"), base)
    ctext, _ = run_gate(cd, "CLEAN")
    crows = rows_of(ctext)
    cv, cdet = crows.get("commission-clean", ("MISSING", ""))
    clean_crush = crush_of(cdet)
    ladder = [r for r in results if r["arm"] in crush_ladder]

    print("(1) THE MEASUREMENT SURVIVES. crush is still computed and printed:")
    print("    %-13s verdict %-7s crush %s   blotch %s"
          % ("CLEAN", cv, "%.3f%%" % clean_crush if clean_crush is not None else "-",
             blotch_of(cdet)))
    for r in ladder:
        print("    %-13s verdict %-7s crush %-9s blotch %-8s  reason: %s"
              % (r["arm"], r["got"], "%.3f%%" % (crush_of(r["detail"]) or 0.0),
                 blotch_of(r["detail"]), r["reason_seg"].strip() or "(none)"))
    top = max((crush_of(r["detail"]) or 0.0) for r in ladder)
    moved = clean_crush is not None and top > clean_crush + 1.0
    print("    crush number MOVED: %s   (%.3f%% -> %.3f%%, a factor this gate would have"
          % ("YES" if moved else "*** NO ***", clean_crush or 0.0, top))
    print("    lost entirely had the statistic been deleted rather than ungated)")

    print()
    print("(2) NO VERDICT IS EVER ATTRIBUTED TO CRUSH. The verdict-bearing text is what")
    print("    follows `<==`. Across CLEAN and all %d crush rungs, including the rungs"
          % len(ladder))
    print("    whose verdict DID move, the reason names blotch and chroma and never crush:")
    named = [r["arm"] for r in ladder if "crush" in r["reason_seg"]]
    print("    rungs naming crush in a reason: %s"
          % ("*** %s -- IT IS GATED ***" % ", ".join(named) if named else "NONE (0 of %d)" % len(ladder)))
    if named:
        failures.append("crush arm: crush is named in the verdict reason of %s, so it "
                        "is gated after all" % ", ".join(named))
    nofail = [r["arm"] for r in ladder if r["got"] == "FAIL"]
    print("    rungs FAILED: %s"
          % ("*** %s ***" % ", ".join(nofail) if nofail else "NONE (0 of %d) -- crush cannot reach FAIL" % len(ladder)))
    if nofail:
        failures.append("crush arm: %s FAILED, so crush can reach a FAIL verdict"
                        % ", ".join(nofail))
    if not moved:
        failures.append("crush arm: the printed crush number did not move, so the "
                        "measurement has been lost rather than merely ungated")

    print()
    print("(3) REAL DATA, WITH NO PLANT AND THEREFORE NO CONFOUNDER -- the strongest of")
    print("    the three. From the null-arm table above:")
    for subj in ("109MSDCF", "119MSDCF", "flower-inner-edge-cpl", "coffee-bean"):
        v, d = corpus_rows.get(subj, ("MISSING", ""))
        print("    %-24s verdict %-7s crush %s" % (subj, v, "%.3f%%" % (crush_of(d) or 0.0)))
    hi = crush_of(corpus_rows.get("109MSDCF", ("", ""))[1]) or 0.0
    hiv = corpus_rows.get("109MSDCF", ("MISSING", ""))[0]
    print("    109MSDCF carries %.3f%% crush -- the highest in the corpus that is not"  % hi)
    print("    also under an unrelated acquittal -- and its verdict is %s, unqualified." % hiv)
    print("    Any threshold below that would have to fail it; the corpus maximum is")
    print("    3.639%, so any threshold above it is inert. There is no threshold to set.")
    if hiv != "PASS":
        failures.append("crush arm: 109MSDCF reads %s, not PASS, so the real-data line "
                        "of evidence does not hold" % hiv)

    print()
    print("BUILD-OUTPUT measured this statistic ANTI-CORRELATED with the property it")
    print("names -- it reads 7-11% of the frame on subjects whose flagged pixels sit at")
    print("median luma 0.24-0.33 across 36k-54k distinct surviving levels, and 0.004% on")
    print("flowers-cpl, whose genuine black sits at luma 0.0011 across 135 levels.")
    print("Gating it fails the good masters and passes the bad one. DO NOT RE-GATE IT.")
    print()

    print("=" * 100)
    if failures:
        print("COMMISSION FAILED -- %d arm(s) did not behave as predicted:" % len(failures))
        for f in failures:
            print("  - %s" % f)
        print("Do not trust any table this gate prints.")
        return 1
    print("COMMISSION PASSED. The corrected gate:")
    print("  * bites on a neutral all-channel blow at 4x CLIP_MAX, and names clipping")
    print("    as the reason;")
    print("  * ignores a one-channel gamut pin TEN TIMES LARGER than the blow it fails;")
    print("  * brackets its own threshold (0.5x passes, 2x fails);")
    print("  * passes dry-erase-marker-head-cpl, the zero-clipping master the old")
    print("    statistic failed, and does not FAIL 112MSDCF, the corpus clipping")
    print("    maximum, whose clip number is under CLIP_MAX;")
    print("  * still computes and prints crush, and never attributes a verdict to it:")
    print("    no crush rung reaches FAIL and none is named in a reason.")
    print("AND: on the unmodified corpus it issues %d FAIL. Read the null arm above"
          % n_fail)
    print("before quoting any of this as print-readiness.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
