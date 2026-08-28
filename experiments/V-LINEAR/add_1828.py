"""Insert facts 1828-1833 into SYNTHESIS.md after row 1827.

Guarded, per ORCH: exits non-zero if any target number already exists or if
the anchor row is not found exactly once.  Run it twice -- the second run MUST
exit non-zero, which is the negative control on the guard itself.

ANCHOR NOTE.  ORCH said the tail was 1825 at 6c36106c.  It is 1827: two more
rows landed from other lanes while this block was being written.  The anchor
below was read from the file immediately before writing, not taken from the
instruction.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1827

ROWS = [
    (
        1828,
        "MEASURED",
        "V-LINEAR",
        "**THE ZERENE STACKER COMPARATOR IS BLOCKED BY AN EXPIRED TRIAL, NOT BY A HARNESS DEFECT, AND "
        "THE VENDOR'S OWN EXPIRED PATH WAS TAKEN TO ESTABLISH THAT THE FAILURE IS LITERAL RATHER THAN "
        "A WATERMARK.** Zerene Stacker 1.04 Build T2026-05-04-0750 at `C:\\Program Files\\ZereneStacker` "
        "runs as `License category = EXPIREDLICENSE` (bundled default key, expired 2026-06-06). It "
        "loads the frames, aligns and stacks to completion, and only then refuses to write: *\"Trial "
        "expired: cannot save output image: Aborting batch run.\"* Output folder afterwards **EMPTY, "
        "zero files** -- so it is not watermarking and not degrading, it simply produces nothing. The "
        "dialog offers `[Visit Website] [Install License Key] [Continue as Expired] [Exit "
        "Immediately]` and **Continue as Expired**, a path the vendor offers the user, was taken to "
        "establish which failure mode this is. **NO CIRCUMVENTION OF ANY KIND WAS ATTEMPTED:** the "
        "owner's `%APPDATA%\\ZereneStacker\\zerenstk.cfg` was backed up before first launch and "
        "verified **byte-identical** afterwards (sha256 `22293EC5CEBB...` both times). **THE WORKING "
        "INVOCATION, RECORDED SO THE NEXT ATTEMPT DOES NOT RE-DERIVE IT:** the batch option is "
        "`-batchScript <path.xml>` and **`-runBatchScript` DOES NOT EXIST**; the rest of the command "
        "line must be taken from `%APPDATA%\\ZereneStacker\\zerenstk.launchcmd` with `javaw.exe` "
        "replaced by `java.exe` to obtain console output "
        "(`-noSplashScreen -exitOnBatchScriptCompletion -runMinimized -batchScript <path.xml>`).",
    ),
    (
        1829,
        "MEASURED",
        "V-LINEAR",
        "**THIS CORPUS IS NOISE-LIMITED FROM 0.25 TO 0.48 CYC/PX ON LINEAR DEVELOPS, WHICH IS THE BAND "
        "EVERY STREHL-VERSUS-ANYTHING FINE-SCALE CLAIM HAD BEEN MADE IN -- BUT IT CARRIES REAL DETAIL "
        "BELOW 0.25, AND THE TWO MUST NOT BE CONFLATED.** Test (`experiments\\V-LINEAR\\noisefloor.py`, "
        "stack `113`): defocus is a low-pass filter, so in a badly defocused tile whatever fine-band "
        "power remains **is** the sensor/pipeline noise floor. Compare the same position in an "
        "in-focus frame and one 20 steps away; a ratio near 1.0 means the band is noise. Whole-frame, "
        "four bands spanning 0.20-0.48: strehl linear **1.015, 1.043, 1.004, 1.138**, against **2.1-"
        "3.0 per band** for the Lightroom development of **the same RAW frames** -- so the answer is a "
        "property of the *development*, not only of the scene. **AMENDED BY `bandsignal.py` (V-LINEAR2 "
        "sec.1/Q2) AND THE AMENDMENT IS LOAD-BEARING:** those four ratios are whole-frame, and at this "
        "magnification only a fraction of any frame is in focus, so a whole-frame ratio averages the "
        "sharp part against the soft part of the same raster. Choosing each tile's **own** best- and "
        "worst-focus frame over 29 tiles recovers **0.17-0.20 = 4.874** and **0.20-0.25 = 2.419 "
        "[1.961, 3.063] PASS**, with 0.25-0.30 **MARGINAL at 1.387** and everything above it flat. "
        "**The registered claim is therefore \"0.25-0.48 is noise\", NOT \"0.17-0.5 is noise\"** -- a "
        "lane told the wider version would discard real signal between 0.17 and 0.25. Note also that "
        "`noisefloor.py`'s printed verdict uses **`r < 1.3`** as its noise/detail discrimination "
        "threshold; it contains no `>= 2` constant, and a stricter acceptance bar for a *new capture* "
        "is a separate choice from the instrument's own cut.",
    ),
    (
        1830,
        "DISCIPLINE",
        "V-LINEAR",
        "**A COMPARISON AGAINST A COMPETITOR IS MEANINGLESS UNLESS THE BAND IT IS SCORED IN CARRIES "
        "SIGNAL FOR BOTH ARMS, AND THIS PROJECT CAME WITHIN ONE VALID LICENCE OF PUBLISHING A THIRD "
        "RETRACTION IN OUR OWN FAVOUR.** Had the Zerene trial been live (fact 1828), the head-to-head "
        "would have run in a band measured at **1.015-1.138** in-focus/defocused on linear develops "
        "(fact 1829) -- i.e. noise. Zerene PMax selects for local contrast, so on a noise-dominated "
        "band it would have selected **on the noise floor**, come out worse, and *\"strehl beats "
        "Zerene on tone-matched linear inputs\"* would have read as a clean headline win. It would "
        "have been wrong, it would have been in our favour, and it would have been the third retracted "
        "claim in this project. **THE TRAP IS THAT THE BLOCKED RUN LOOKS LIKE THE FAILURE AND THE "
        "SUCCESSFUL RUN WOULD HAVE BEEN THE REAL ONE.** GENERALISES, AND IS NOW A STANDING "
        "PRECONDITION: **before any sharpness, acuity or resolution claim, qualify the band on the "
        "actual development being measured** -- run the defocus ratio, per tile rather than whole "
        "frame, and state the band, the ratio and the instrument alongside the verdict. A band that "
        "is noise for both arms cannot rank them; a band that is noise for one is worse, because it "
        "will rank them confidently and backwards.",
    ),
    (
        1831,
        "DISCIPLINE",
        "V-LINEAR",
        "**A THRESHOLD THAT SITS ON AN ARTIFACT OF THE DATA LAYOUT IS NOT A THRESHOLD: AN ALPHA "
        "CHANNEL READ AS IMAGE DATA ALMOST RETRACTED TWO SOUND SECTIONS.** Answering ORCH's "
        "exposure-regression sweep, v1 of `experiments\\V-NOISE2\\clipaudit.py` counted "
        "`(a == 65535).mean()` over the whole array and returned **EXACTLY 25.0000%** clipped on all "
        "**18** enfuse arms -- different subjects, different frame counts, four identical decimals. "
        "That is not a measurement, it is **1/4**: `enfuse` writes RGBA `(4688, 7032, 4)` with a "
        "100%-opaque alpha channel while `strehl` writes RGB `(4688, 7032, 3)`, so **the two arms "
        "were not being measured on the same quantity at all**. Per channel on `119/coh-enfuse-A`: "
        "**0.0 / 0.0 / 0.0 / 100.0**. Against ORCH's `>25%` corpus threshold this declared the lane's "
        "own comparators BLOWN and would have retracted sections 9 and 10 over nothing. **THE TELL "
        "WAS THAT IDENTICAL PRINTED VALUES LANDED ON DIFFERENT VERDICTS** -- `> 0.25` is a knife edge "
        "that a single genuinely clipped RGB pixel tips, so `bee-L1` read `ok` and `bee-L2` read "
        "`BLOWN` at the same displayed 25.0000%. Fixed by excluding alpha and reporting per channel; "
        "true answer **0.0000% on all 34 arms**. **GENERALISES TWICE:** check the channel count "
        "before any whole-array statistic, and treat a suspiciously round constant repeated across "
        "independent inputs as an instrument reading rather than a result.",
    ),
    (
        1832,
        "MEASURED",
        "V-LINEAR",
        "**THERE IS NO LENS-DISTORTION WARP BETWEEN STREHL'S LINEAR DEVELOP AND LIGHTROOM'S EXPORT OF "
        "THE SAME RAW -- AND THE CONFIDENT FINDING THAT THERE WAS ONE WAS AN ARTIFACT OF COMPARING "
        "TWO FITS ON DIFFERENT ROWS.** The two developments differ by an **affine** transform (scale "
        "y **1.00189**, x **1.00166**) to **1.97 px rms**. Adding a two-parameter radial term buys "
        "**12%** of the residual, with coefficients **k1 = -0.0023 px** and **k2 = -0.0009 px** -- "
        "i.e. thousandths of a pixel across the frame, which is no warp. This **retracts this lane's "
        "own earlier \"NON-LINEAR RADIAL WARP\" conclusion**, which arose from fitting the rich model "
        "robustly and the simple model non-robustly, thereby crediting the two extra parameters with "
        "the outlier rejection. **METHOD RULE THIS ESTABLISHES:** when comparing two models to decide "
        "whether the richer one is needed, fit both on the **same rows**, and choose the "
        "outlier-rejection set using the **simpler** model's residual.",
    ),
    (
        1833,
        "MEASURED",
        "V-LINEAR",
        "**V-HEADTOHEAD2'S TONE ESTIMATOR IS CLEARED OF THE ONLY OBJECTION THAT WOULD HAVE VOIDED IT: "
        "IT CANNOT MANUFACTURE A RESOLUTION DIFFERENCE OUT OF TONE.** V-HEADTOHEAD2 reported that a "
        "4x4-block tone fit explained **89-212%** of a fine-scale gap, which invites the reply that "
        "the estimator is simply faking resolution from tone. Falsifier, 20 tiles from 9 frames, "
        "tiles admitted only where the frame is a local maximum of fine-band power against frames +/-4 "
        "away: fit `gradetest.fit_map` + `apply_map` on an image against a **pure 0.6 px Gaussian "
        "blur** of itself, where a 4x4 block-mean fit holds literally zero information above 0.125 "
        "cyc/px and so must fail. It explains **3.3% / 1.7% / 0.9%** of the blur at 0.20-0.25 / "
        "0.25-0.30 / 0.30-0.40 cyc/px. **AND MOST OF EVEN THAT IS AN IDENTITY BIAS THAT WAS ALSO "
        "MEASURED RATHER THAN ASSUMED:** fitting the map from an image to *itself* and applying it "
        "returns mapped/original = **0.9861 / 0.9898 / 0.9932**, a loss of **1.39% / 1.02% / 0.68%**, "
        "because `fit_map` is a 256-knot quantile interpolation and interpolation between knots is "
        "mildly smoothing. (Both this lane's prose and ORCH's summary rounded that range to "
        "\"1.0-1.4%\"; the measured low end is **0.68%**.) The bias is small but **signed**, in the "
        "direction of *understating* tone. **A positive result for the prior lane, produced by an arm "
        "that lane did not run.**",
    ),
]


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    for num, _, _, _ in ROWS:
        if re.search(r"^\| %d \|" % num, text, re.M):
            print("REFUSED: fact %d already exists" % num)
            return 2

    anchor_hits = re.findall(r"^\| %d \|.*$" % ANCHOR, text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row %d found %d times, expected 1"
              % (ANCHOR, len(anchor_hits)))
        return 3
    anchor = anchor_hits[0]

    block = anchor
    for num, kind, lane, body in ROWS:
        block += "\n| %d | %s | %s | %s |" % (num, kind, lane, body)

    out = text.replace(anchor, block, 1)
    if out == text:
        print("REFUSED: replacement did not land")
        return 4

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    after = io.open(PATH, encoding="utf-8").read()
    for num, _, _, _ in ROWS:
        if not re.search(r"^\| %d \|" % num, after, re.M):
            print("FAILED: fact %d not present after write" % num)
            return 5
    print("OK: inserted facts %s"
          % ", ".join(str(n) for n, _, _, _ in ROWS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
