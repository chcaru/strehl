#!/usr/bin/env python3
"""Audit every runtime switch in the crates, and refuse to let a new one hide.

# Why this exists

On 2026-08-25 three separate lanes discovered, within two hours of each other,
that a measured and tested subsystem was not reachable in the product's default
path:

  * lateral-CA correction (`STREHL_FIX_CA`) was unset in `gallery.ps1`, in
    `render_all.ps1`, and in **every render the owner had ever seen**. Commit
    b914f31: "The algorithm was finished months ago; nothing turned it on."
  * the gear-aware optical profile (`profile_for_capture_env`, 283ccf4) was
    written, tested, and called by nothing.
  * the multi-band merge (d4b8644) removed the cut-out rim on both polarities
    and was "not wired into the CLI".

The owner's verdict on the resulting gallery was "horrible" and "entirely
unusable". He was looking at a binary running with its best measured machinery
switched off. None of those three defects was an algorithm defect, none was
visible in any test, and all three were invisible in the source unless you went
looking for the absence of a caller.

A prose note saying "remember to wire things up" would have rotted within a
week. This is a ratchet instead: every switch must be declared here with its
intended default, and an undeclared switch is a hard failure. A new feature
cannot be added behind a dark switch without this script noticing.

# What it does NOT do

It does not prove a switch is honoured. Static analysis cannot tell you that,
and this script does not pretend to: `STATUS_WIRED` below is a *declaration of
intent by a human*, cross-checked by hand against the call sites named in
`evidence`. The only instrument that can prove a switch reaches output pixels is
rendering the same stack two ways and diffing the result, and that belongs in a
verifier, not here.

So this script answers exactly one question — "is there a switch nobody has
thought about?" — and it answers it exhaustively.

# The summary contract

Every switch found is counted into exactly one outcome, and the outcomes sum to
the total found. A switch that was skipped must never be able to read as a
switch that passed. See the note in `main` for why that rule is written down.

Usage:  python scripts/check-defaults.py          (from the repo root)
Exit:   0 = every switch accounted for, no quality switch dark
        1 = an undeclared switch, or a quality switch defaulting off
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# The declared registry.
#
# KIND:
#   "diagnostic" - writes a debug artifact or restricts the run for diagnosis.
#                  Default-off is CORRECT; these must never be on in a product
#                  render.
#   "quality"    - changes output pixels in a way that was measured to be
#                  better. Default-off is a DEFECT: it is the exact class of
#                  bug this script exists to catch.
#   "control"    - selects between arms for a controlled comparison, or is
#                  infrastructure (cache location, test gating). Default-off is
#                  correct, but the reason must be stated.
#
# BACKEND: which merge backend the switch actually reaches. This field exists
#          because the script reported two switches as dark defaults of the
#          shipping product when the shipping backend does not implement the
#          stages they control at all. `STREHL_PHOTOMETRIC` and
#          `STREHL_FIX_HALO` are ESTIMATOR-path stages; the default backend is
#          the PYRAMID, whose own run banner lists "photometric gain, clip
#          census, outlier rejection, halo correction, through-focus
#          statistics" under `not applied`. A switch that cannot run on the
#          default path is INAPPLICABLE there. That is a different fact from
#          "off", it has a different remedy, and conflating the two sent two
#          agents after a promotion that would have changed nothing.
#
#   "any"        - reaches pixels on whichever backend runs.
#   "pyramid"    - only on the default backend.
#   "estimator"  - only on `--merge estimator`. NOT dark when it is off on the
#                  default path; it is simply not there. Report it, count it,
#                  and do not call it a defect.
#
# DEFAULT: what the product does when the variable is unset, as a human read it
#          from the code cited in `evidence`. Not inferred by this script.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Declared:
    kind: str
    default: str
    evidence: str
    note: str
    # How the value in `default` was established. This field exists because
    # this script failed exactly the way it was written to prevent.
    #
    # `STREHL_PHOTOMETRIC` was declared here with `default="auto"`. The code
    # resolves it to `Off` (`merge_cmd.rs:1965`, `_ => Ok(PhotometricMode::Off)`).
    # The declaration was a guess, and its own `note` said so -- it read
    # "Verify the resolved default is genuinely 'auto' and not None-means-off."
    # Nobody verified it, and because the script TRUSTS the declaration, the
    # switch was classified "quality, reachable" and never counted as dark. It
    # was in fact off, and an independent verifier later priced it at +1415 DN
    # of recovered background on the owner's worst artifact.
    #
    # A registry of human-entered values is a checklist, not a ratchet. So the
    # provenance is now first-class and unverified is the default:
    #
    #   "measured" - the binary was run with the switch unset and with each
    #                value, and the outputs compared. This is the only level
    #                that actually proves a default.
    #   "code"     - a human read the resolving expression at the cited line.
    #                Good, but it is still a reading.
    #   "assumed"  - nobody has checked. For a `quality` switch this is a
    #                hard failure: you may not claim a quality default you
    #                have not looked at.
    verified: str = "assumed"
    # Which backend the switch reaches. See the BACKEND note above. Defaults to
    # "any" so an unclassified switch is still audited on the default path --
    # the permissive value has to be the one that gets CHECKED, or forgetting
    # the field would silently excuse a switch.
    backend: str = "any"


REGISTRY: dict[str, Declared] = {
    # ---------------- control / infrastructure ----------------
    "STREHL_BUILD_ID": Declared(
        kind="control",
        default="unset (build.rs derives the stamp from git)",
        verified="measured",
        backend="any",
        evidence=(
            "RESOLVING EXPRESSION READ, AND MEASURED. build.rs:101, `if let "
            "Ok(forced) = std::env::var(\"STREHL_BUILD_ID\")` -- a non-empty "
            "explicit stamp is emitted verbatim and build.rs returns early "
            "(:103-104). UNSET falls through to build.rs:108, `git rev-parse "
            "--short=12 HEAD` plus a `-dirty` suffix, and to the literal "
            "\"unknown\" (:110) when git is unavailable, so the variable can "
            "never resolve to nothing. Consumed at main.rs:34 and main.rs:55 "
            "by `env!(\"STREHL_BUILD_ID\")`, which is a COMPILE-TIME read and "
            "fails the build outright if the value is absent. MEASURED: the "
            "stamp moved 6e8c3898b2da-dirty -> fd02b6e063e8-dirty across two "
            "builds of this tree, and `--version` and TIFF tag 305 both "
            "carried the new value."
        ),
        note=(
            "BUILD-TIME, NOT RUNTIME -- the one entry in this registry that is "
            "not a switch on a render. MEASURED BOTH WAYS, because the first "
            "version of this note asserted both directions from the mechanism "
            "(`env!` bakes at compile time, build.rs returns early) under a "
            "verified='measured' label, which is the exact posture the fleet "
            "flagged: a mechanism that explains why a measurement must hold is "
            "when people stop measuring. RUNTIME: the pinned binary "
            "16EB215F6264DB69 printed `strehl 0.0.0 (c082a9860c66-dirty)` both "
            "unset and with STREHL_BUILD_ID=BOGUS-RUNTIME-VALUE -- identical, "
            "so runtime really is inert. BUILD TIME, which is the POTENCY "
            "CONTROL that null needs: a clean clone of HEAD b36260640de4 built "
            "with STREHL_BUILD_ID=OVERRIDE-PROBE-42 printed `strehl 0.0.0 "
            "(OVERRIDE-PROBE-42)`, and rebuilt with it unset printed `strehl "
            "0.0.0 (b36260640de4)`. The same variable moves the value through "
            "the build channel and not through the run channel, so the null "
            "above is a real null and not a dead probe. (The clean clone also "
            "carried no `-dirty` suffix while the working tree does, which "
            "exercises dirty_suffix() in both directions for free.) It "
            "is declared here anyway because this script scans for STREHL_* "
            "literals and finding one undeclared is a FAIL by design, and "
            "because leaving it undeclared would have made the count of "
            "undeclared switches read 1 forever -- a permanently red check is "
            "one nobody reads. The override exists so a build outside a git "
            "checkout (release tarball, container) can still name its source; "
            "unset is correct for every ordinary build because the derived "
            "value is the trustworthy one. DECLARED BY THE LANE THAT SHIPPED "
            "IT, LATE: this variable landed in 02564395 nineteen minutes after "
            "this registry was committed, and the author did not re-run this "
            "script before committing. The check was red from 15:51 and said "
            "so; nobody was looking."
        ),
    ),
    # ---------------- quality ----------------
    "STREHL_FIX_CA": Declared(
        kind="quality",
        default="on (gear-matched)",
        verified="measured",
        evidence=(
            "MEASURED, not read: ran the shipping binary "
            "(target/release/strehl.exe, built 2026-08-26 09:34) as "
            "`stack D:\\personal\\macro\\bee-3-cpl --srgb --auto-exposure "
            "--limit 6`, i.e. the shipping flags with NO --fix-ca. rc=0 and "
            "its own banner printed: `camera: ILCE-7CM2` / `lateral CA: "
            "CORRECTING, profile \"a7c2-fe100gm-2xtc-x4cpl\" (gear matched; "
            "default on)`. `stack --help` agrees in prose: \"This is "
            "DEFAULTED ON when the gear matches.\" "
            "Also optics.rs:470 (CA_ENV); main.rs:183-185,619 (--fix-ca)"
        ),
        note=(
            "Lateral-CA correction. Removes 61-67% of corner colour fringing "
            "(b914f31, R^2=0.9969) and 0.363px -> 0.059px of blue displacement "
            "(283ccf4). "
            "THIS ENTRY USED TO READ `default=off` AND CALL THIS 'THE ORIGINAL "
            "DARK FEATURE'. THAT WAS WRONG, and it is the most consequential "
            "wrong value this file has carried. The orchestrator inferred it "
            "from a provenance argv that contained no --fix-ca and concluded "
            "the shipping masters were rendered without the correction. An "
            "argv records what the CALLER said; only the run's own banner "
            "records what the PROGRAM did. Running the binary took one command "
            "and printed the answer in one line. "
            "INDEPENDENTLY CORROBORATED ON THE PROVENANCE SUBJECT ITSELF: "
            "re-ran the full argv the orchestrator quoted -- `stack "
            "D:/personal/macro/pencil-steep-angle-cpl --merge pyramid "
            "--pyramid-gate 4.5 --srgb --auto-exposure`, no --fix-ca, plus "
            "--limit 4 -- on target/release/strehl.exe built 2026-08-26 13:52. "
            "rc=0 and the banner printed `camera: ILCE-7CM2` / `lateral CA: "
            "CORRECTING, profile \"a7c2-fe100gm-2xtc-x4cpl\" (gear matched; "
            "default on)`. So the correction was active on the very render the "
            "'every image the owner has looked at was rendered without it' "
            "claim was built from. "
            "It is default-ON behind the EXIF gear guard, which reads body and "
            "composed lens id out of the file and declines on a mismatch -- "
            "because applying this profile to a different optical path would "
            "ADD an aberration. `--fix-ca off` is the supported escape hatch."
        ),
    ),
    "STREHL_PHOTOMETRIC": Declared(
        kind="quality",
        default="on (correction applied)",
        verified="measured",
        backend="estimator",
        evidence="merge_cmd.rs, `pub const DEFAULT_PHOTOMETRIC_MODE: "
        "PhotometricMode = PhotometricMode::On` -- cited by CONST NAME, not by "
        "line number, for the reason in the note. Pinned from the other side by "
        "merge_cmd.rs::the_merge_environment_channels_behave, which asserts "
        "DEFAULT_PHOTOMETRIC_MODE == On and says out loud that moving it must "
        "move this file too. MEASURED, two arms, one pinned binary, "
        "109MSDCF, `--merge estimator --srgb`: with NOTHING set the banner "
        "prints `mode : on`; against `--photometric off` the outputs differ by "
        "SHA-256 (05BCF2FB84298B0F vs E8B97B559CD7C13B). BACKEND CONFIRMED BY "
        "RUN: the default-path banner (pyramid) says nothing about photometric "
        "and the pyramid arm's own report lists `photometric gain` under "
        "`not applied` -- the stage is INAPPLICABLE there, not off.",
        note=(
            "Per-frame affine photometric normalisation. Three-valued "
            "off|on|auto; the flag wins over the env var and 'neither can mean "
            "ON by accident'. "
            "THE DEFAULT IS ON. It was declared `auto` here once and `off` "
            "here later; both were wrong, and this is the THIRD time this one "
            "entry has misreported its own default. "
            "WHAT MOVED IT: V-TONE resolved the contest the previous note left "
            "open. M122 returned KEEP-OFF on a 14-stack promotion test while a "
            "verifier measured `on` recovering +1415 DN of aura on M122's own "
            "worst-harm subject, flower-bud-alone-cpl. Both could not be right "
            "about the same pixels, and V-TONE found M122's 'lost fine "
            "structure' was election-seam step edges -- the artifact -- which "
            "a whole-frame energy statistic with no spatial argument cannot "
            "tell from signal. The default then moved to On. "
            "HOW THE DECLARATION ROTTED, which is the transferable part: this "
            "entry was marked verified='code' and cited `merge_cmd.rs:1965 "
            "(_ => Ok(PhotometricMode::Off))`. That expression NO LONGER "
            "EXISTS anywhere in the file, and line 1965 is now unrelated doc "
            "prose. A citation to a bare line number rots silently when the "
            "file moves, and 'code' then certifies a reading nobody can "
            "reproduce -- which is indistinguishable from an unexamined guess "
            "while looking stronger than one. Cite a const or a function name, "
            "which grep can still find after the line number is wrong."
        ),
    ),
    "STREHL_EDGE_AWARE": Declared(
        kind="quality",
        default="on (EdgeArm::Acuity)",
        verified="code",
        evidence=(
            "edge_aware_arm() in merge_cmd.rs (:1848 at time of reading; cite "
            "the symbol, the line drifts). The resolving match is "
            "`None | Some('') | Some('1') | Some('on') | Some('true') | "
            "Some('acuity') => EdgeArm::Acuity` -- unset falls in the FIRST "
            "arm, so the default is ON in the Acuity arm, not merely 'not "
            "off'. An unknown value panics rather than falling back."
        ),
        note=(
            "Adaptive-radius edge handling. The shipped merge's winner field "
            "has its depth step displaced outward by exactly one window "
            "radius, and that displacement IS the halo. Three arms exist "
            "(Off/Acuity/Layer) and only Acuity ships."
        ),
    ),
    "STREHL_EDGE_TAU": Declared(
        kind="quality",
        default="derived per image from the guide field (no constant)",
        verified="code",
        evidence=(
            "edge_tau(guide) in merge_cmd.rs (:1901 at time of reading). When "
            "the variable is absent it does NOT return a constant: it filters "
            "the guide field for k != u16::MAX and derives tau from that "
            "image's own distribution. A set value must parse and be > 0 or "
            "it panics."
        ),
        note=(
            "Depth-step tolerance, in frames. The previous declaration here "
            "said 'built-in', which read as a fixed constant; it is not one. "
            "This is data-derived per image, so it cannot drift with a "
            "constant but it also cannot be quoted as a single number in any "
            "report."
        ),
    ),
    "STREHL_EDGE_CONF": Declared(
        kind="quality",
        default="2.0",
        verified="code",
        evidence=(
            "edge_conf() in merge_cmd.rs (:1737 at time of reading) is "
            "`env_num(EDGE_CONF_ENV, 2.0)`, and env_num returns its `default` "
            "argument on Err(_). A set value that does not parse panics."
        ),
        note="Confidence veto, in multiples of the plane's low-percentile guide response.",
    ),
    "STREHL_EDGE_FEATHER": Declared(
        kind="quality",
        default="the built-in FEATHER constant",
        verified="code",
        evidence=(
            "feather() in edgeaware.rs, a OnceLock whose initialiser matches "
            "env::var(FEATHER_ENV) and returns `Err(_) => FEATHER`."
        ),
        note="Feather width for the edge-aware support.",
    ),
    "STREHL_FIX_HALO": Declared(
        kind="quality",
        default="off",
        verified="code",
        backend="estimator",
        evidence="merge_cmd/halo.rs:69 (FIX_ENV), :71 (DELTA_ENV). "
        "RESOLVING EXPRESSION READ (halo.rs:113): the match returns "
        "`Err(_) => false`, so unset is off; a set value is on unless it "
        "trims to ''/0/off/false/no. "
        "BACKEND CONFIRMED BY RUN: the default-path banner (pyramid, "
        "bee-3-cpl, --limit 3) says nothing about halo correction, and the "
        "pyramid arm's own report lists `halo correction` under `not "
        "applied`. It is an ESTIMATOR stage. The shipping product does not "
        "run it and cannot be fixed by turning it on.",
        note=(
            "Veiling-glare subtraction. DARK. Two instrument defects reported "
            "and unresolved: report()/report_statistics() at merge_cmd.rs:2083-2085 "
            "run BEFORE the halo pass at :2088, which would make every A/B on "
            "printed statistics null by construction; and '=1' without --out is "
            "a silent no-op that still prints an ON banner. BUILD-HALO owns both."
        ),
    ),
    "STREHL_WINDOW_RADIUS": Declared(
        kind="quality",
        default="13",
        verified="code",
        evidence=(
            "window_radius() in focus.rs (WINDOW_RADIUS_ENV at :101), a "
            "OnceLock whose initialiser returns `Err(_) => WINDOW_RADIUS`. "
            "The doc comment states the default is bit-identical when unset, "
            "and that a malformed value PANICS rather than falling back to "
            "13 -- deliberately, because a dose-response that silently "
            "rendered every rung at the default would look like a flat curve "
            "and refute the mechanism it was built to test."
        ),
        note="Focus-measure window radius. Unset uses the shipped WINDOW_RADIUS=13.",
    ),
    "STREHL_MERGE": Declared(
        kind="quality",
        default="pyramid",
        verified="measured",
        evidence="merge_cmd.rs (MERGE_BACKEND_ENV, resolve_merge_backend, "
        "DEFAULT_MERGE_BACKEND = MergeBackend::Pyramid); "
        "main.rs (--merge, and the wrong-backend refusal table)",
        note=(
            "WHICH MERGE PRODUCES THE PIXELS. `pyramid` or `estimator`, and an "
            "unrecognised value is a hard error in BOTH the flag and the env "
            "channel -- neither can mean a backend by accident. THE DEFAULT "
            "MOVED to `pyramid`; `--merge estimator` still reproduces the "
            "pre-switch bytes exactly, which is why every row in the "
            "byte-freeze registry names it explicitly and why ZERO freeze rows "
            "moved when the default flipped. "
            "THIS IS NOT A DARK QUALITY SWITCH, and the distinction matters "
            "for this script's purpose. `pyramid` was 1898 lines that no "
            "shipped binary could reach at all until it was wired -- every "
            "good render in the corpus came from it through an EXAMPLE. It is "
            "now the default, on a measurement rather than by taste. Measured "
            "through ONE binary with both arms camera-linear (--demosaic) and "
            "CA and photometric explicitly unset, at the STOCK band gate 2.00 "
            "with no --pyramid-gate anywhere, so the arms differ in the merge "
            "and nothing else. On flower-bud-alone-cpl: clip 0.0001 -> 0.0000, "
            "acuity 126.9 -> 223.4, microC 54.21 -> 117.55, p1 1028 -> 1042. "
            "On couch-fibers-cpl, the do-no-harm guard with no silhouette at "
            "all: clip 0.0000 both ways, acuity 290.3 -> 324.4, microC "
            "274.76 -> 322.1. "
            "The clip that blocked the flip was 1.4043% and is now 0.0000%; "
            "Hull::InputRange in pyramid.rs fixed it at the source. The halo "
            "the owner has complained about since the project started is the "
            "estimator's: scored through ONE mask taken from the estimator arm "
            "so both columns read identical pixels, its backdrop sits 4739 DN "
            "below its own far field across the 80-200 px aura zone, against "
            "the pyramid's 166 DN. Levels, not ratios, because an "
            "upper-envelope estimator on this project was measured to carry a "
            "+0.845 sigma upward bias that can null a veiling ERROR metric "
            "without improving the picture; the discriminator is that the "
            "pyramid's FAR FIELD moves -113 DN, opposite in sign to the "
            "+4452 DN it moves near the silhouette. The 109MSDCF placebo, "
            "which has no depth separation, moves +0 DN median and +5 DN mean. "
            "NOT CLEAN: accept.py still fails coffee-bean on microC at 67.2%, "
            "and the pyramid doubles white-rail clipping there, 1.17% -> "
            "2.86%. Both are recorded against DEFAULT_MERGE_BACKEND and are "
            "BUILD-BLEND's to fix in pyramid.rs."
        ),
    ),
    "STREHL_ACUITY": Declared(
        kind="quality",
        default="on",
        verified="code",
        evidence=(
            "merge_cmd.rs:1882 (ACUITY_ENV) and acuity_shrink() at :1884, "
            "which returns true unless the value trims to one of "
            "'0'/'off'/'no'/'false' -- so unset is ON. The doc comment above "
            "it states 'Default ON.' in terms."
        ),
        note=(
            "Exists only so both arms are renderable from ONE binary: 57e4554 "
            "deleted the acuity term after measuring a single subject's "
            "background noise, and a 26-subject gallery delta then charged "
            "the deletion -6.6% gradient RMS. Keeping the switch is what "
            "prevents that comparison re-acquiring the build-drift confound "
            "that made the original deletion look free."
        ),
    ),
    "STREHL_DEMOSAIC": Declared(
        kind="quality",
        default="malvar (non-directional)",
        verified="code",
        evidence=(
            "demosaic.rs:321 (DEMOSAIC_ENV); use_directional() at :323 is a "
            "OnceLock initialised to "
            "env::var(..).map(|v| v.eq_ignore_ascii_case('directional'))"
            ".unwrap_or(false) -- unset resolves to false, i.e. Malvar."
        ),
        note=(
            "The directional arm is Hamilton-Adams. It was landed as the "
            "default (d67fe13b) and REVERTED (0c236d85) after being rendered "
            "on the owner's real stacks: it raised HF power 1.50x in the "
            "FLATTEST 5% of tiles while returning 0.99x mean gradient at the "
            "SHARPEST 5%, and the added energy was a correlated maze pattern "
            "rather than noise. Correlated false texture reads as detail and "
            "survives print, which is the same defect class as a halo. The "
            "1.297x that motivated it was measured on a full-contrast grating "
            "at f_out=0.35, a stimulus this rig cannot deliver. Keep this "
            "switch: both arms must stay in one binary so the comparison "
            "never needs two builds."
        ),
    ),
    "STREHL_RESTORE": Declared(
        kind="quality",
        default="off",
        verified="measured",
        evidence=(
            "restore.rs:1233 gain_cap_from_env() returns Option and yields "
            "None when the variable is unset, empty, '0', 'off', or not "
            "above 1.0. Both call sites guard the stage on it: "
            "merge_cmd.rs:4006 inside fn run_estimator (defined :2680) and "
            "merge_cmd.rs:4641 inside fn run_pyramid (defined :4341). "
            "MEASURED, not only read: the shipping default banner from "
            "`strehl stack D:/personal/macro/109MSDCF --srgb --auto-exposure` "
            "on the pinned binary prints 'merge backend : pyramid (default)' "
            "and lists 'not applied : photometric gain, clip census, outlier "
            "rejection, halo correction, through-focus statistics' -- "
            "restoration is not in that list because it is not mentioned at "
            "all."
        ),
        note=(
            "DARK, and on the DEFAULT backend -- run_pyramid calls it, so "
            "this is not an absent stage that needs building. It is a "
            "finished stage nobody switched on. That is the exact shape of "
            "the three defects in this file's header, one of which produced "
            "the gallery the owner called unusable. Its own doc comment says "
            "the flag 'is meant to be temporary -- it exists to carry a "
            "measured trade curve to whoever sets the default', and nobody "
            "has set the default. THE MOTIVATING NUMBER IN THIS NOTE HAS "
            "SINCE BEEN RETRACTED, and the retraction is recorded here rather "
            "than deleted, because a gate that quietly changes the reason it "
            "is closed is a gate nobody can audit. This row used to say 'an "
            "independent head-to-head found strehl 17-27% behind two external "
            "stackers at 3-5 px features, which is the band restoration "
            "targets'. V-HEADTOHEAD2 s0 retracts that twice over: once on "
            "instrument grounds, and again on VARIABLE grounds -- a tone curve "
            "fitted to strehl's own pixels from 4x4 BLOCK AVERAGES ALONE, "
            "carrying no information above 0.125 cyc/px and therefore none "
            "about resolution at all, reproduces Zerene's 0.25-0.30 cyc/px "
            "band power to 0.02% (0.037147 vs 0.037138), accounting for 100.0% "
            "of the apparent gap there, 89.1% at 0.20-0.25 and 212% at "
            "0.30-0.40; a bare gamma of 1.25 moves the same statistic +8.5%. "
            "The comparators were fed Lightroom TIFFs at Contrast2012=+100. "
            "The honest current statement is 'undecidable on this corpus, in "
            "either direction' -- explicitly NOT 'behind'. So restoration has "
            "lost its motivating deficit. It has also lost confidence in its "
            "TARGET: V-LINEAR measured that a tile in focus carries the same "
            "0.20-0.48 cyc/px power as the same tile 20 frames OUT of focus "
            "(1.015, 1.043, 1.004, 1.138 across four frame pairs), so on this "
            "corpus that band may hold no focus-dependent scene signal for a "
            "restoration to restore. What survives unchanged is the second "
            "condition: the stage has been measured INERT at the calibrated "
            "sigma^2 it is given -- gain caps of 1.4, 1.7 and 2.5 produce "
            "BYTE-IDENTICAL output, so the cap is never the limiter -- and "
            "flipping it on today may change nothing. Do not flip it to clear "
            "this check. Measure it, then set it."
        ),
    ),
    "STREHL_GATE_FLOOR": Declared(
        kind="quality",
        default="on (the merge gate's per-band noise floor is MEASURED per frame)",
        verified="measured",
        backend="pyramid",
        evidence=(
            "RESOLVING EXPRESSION READ AND BOTH ARMS MEASURED. GATE_FLOOR_ENV "
            "at merge_cmd/gatefloor.rs:89; enabled() returns false only for "
            "the literal `white`, so UNSET is ON by falling through the same "
            "arm as any other value. MEASURED on wrapped-text-1 --limit 10: "
            "the banner's new `measured floor` line reads 1.0215-1.0224 at "
            "band 0 against the compile-time 0.88980, i.e. 1.149x, and "
            "STREHL_GATE_FLOOR=white restores 0.88980 exactly. The two render "
            "differently, so unset is demonstrably not `white`. IDENTITY NULL "
            "as the positive control for the probe itself: run on a REAL frame "
            "with its real white balance and real CA profile but an identity "
            "transform, the probe returns 1.0000x/0.9995x/0.9998x white at "
            "band 0 and at worst +0.583% across bands 0-3 -- so the correction "
            "is measuring the warp and not the instrument."
        ),
        note=(
            "WHAT IT CONTROLS: the constant 0.88980 in BandGain is E[L_0^2]/"
            "sigma_0^2 for a frame of INDEPENDENT per-photosite noise. A warped "
            "frame does not have that: resampling correlates neighbours and "
            "moves power between bands, so the constant is exact only for an "
            "unwarped frame. The error is not small and it is not one-signed -- "
            "on the shipping fullres-gather arm the true floor measures 1.149x "
            "white (gate too LOW, noise clears it and selects) and on the plane "
            "arm 0.620x (gate too HIGH, real detail is averaged away). It is "
            "also NOT correctable by a closed-form kernel ratio: the transfer "
            "is a function of per-frame warp PHASE, with period 1 plane-px on "
            "the plane arm against 1/2 plane-px on fullres, and the two curves "
            "CROSS -- so any single analytic factor is fitted to one phase and "
            "wrong at the others. Hence a probe: real noise pushed through the "
            "real warp with the frame's own transform. SCOPE OF THE "
            "CORRECTION: bands 0-3 only (CERTIFIED_BANDS), because the identity "
            "null's own error at bands 4-5 is the same size as the effect there "
            "and band 6 on this sensor is reconstructed across a level-size "
            "truncation seam (49 -> 24) that reads 12.6x. Beyond band 3 the "
            "white constant is kept, deliberately and visibly."
        ),
    ),
    "STREHL_FULLRES_GATHER": Declared(
        kind="quality",
        default="on (frames are gathered on the full output lattice)",
        verified="measured",
        evidence=(
            "RESOLVING EXPRESSION READ AND THREE ARMS MEASURED ON ONE PINNED "
            "BINARY. FULLRES_ENV at align_cmd.rs:956; fullres_gather_enabled() "
            "is `fullres_from_raw(&std::env::var(FULLRES_ENV)"
            ".unwrap_or_default())`, and unwrap_or_default() turns the unset "
            "case into the EMPTY STRING, which fullres_from_raw matches in its "
            "FIRST arm `\"\" | \"1\" | \"on\" | \"true\" | \"yes\" => true`. "
            "Unset is therefore ON by falling through the same arm as an "
            "explicit `on`, not by a fallback. MEASURED by "
            "experiments/ORCH-drift-check/fullres_default.py against pin "
            "9b05d0b7 (sha256 44C2F2CD2E5B2894), bee-3-cpl --limit 3, "
            "identical flags, variable the only difference: unset rendered "
            "A04795AD895B1452 and `off` rendered 3C267DDC46F60AD5, so unset is "
            "demonstrably not off. POSITIVE CONTROL FOR THE READ ITSELF: "
            "STREHL_FULLRES_GATHER=maybe exits 101 with 'Refusing to guess: "
            "this switch selects which resolution every pixel is gathered at', "
            "which is what makes the first pair interpretable -- without it, "
            "two identical renders could mean 'the default is off' or 'the "
            "variable is never read', and those are different facts."
        ),
        note=(
            "The largest measured quality behaviour in the product, and it was "
            "UNDECLARED here until 2026-08-27 while this file enumerated eight "
            "of its neighbours. That omission is not cosmetic: it is precisely "
            "the completeness of the rest of this registry that licenses a "
            "reader to treat an absence as evidence, and a reader did -- the "
            "26 shipped provenance sidecars list STREHL_ALIGN, STREHL_COVER, "
            "STREHL_SMOOTH and five others as unset while never naming this "
            "switch at all, and it took a byte search of five pinned binaries "
            "to establish that the shipping masters had it ON. WHAT IT "
            "CONTROLS: gathering on the CFA plane lattice rather than the "
            "output lattice band-limits every frame to the PLANE Nyquist, "
            "0.25 cyc/output px, before any election runs, so no later stage "
            "can recover it. V-NYQUIST measured the loss common-mode as 51% of "
            "band correlation at 0.20-0.30 cyc/output px, 88% at 0.30-0.40, "
            "and ANTI-CORRELATED (-0.0022) at 0.40-0.48. The flip also made "
            "the product FASTER -- 27.7->20.1 s at 79 frames, 110.3->97.1 s at "
            "299 -- against a prior analysis predicting +549 ms/frame slower; "
            "free-and-better is the shape of an artifact, so it was checked "
            "rather than banked. HONEST LIMIT ON THE CLAIM, from the lane's "
            "own follow-up: the gain is established as coherent power in the "
            "band it was aimed at (2.10x/3.58x/3.46x, 95% CIs excluding 1), "
            "NOT as recovered scene resolution, because V-LINEAR then measured "
            "that focus itself barely moves those bands on this corpus. Two "
            "overshoot statistics also disagree about ringing and that "
            "disagreement is recorded as OPEN, not resolved. The old path "
            "stays reachable deliberately: a quality change that cannot be "
            "declined is a tax rather than a default."
        ),
    ),
    "STREHL_VEIL": Declared(
        kind="quality",
        default="off",
        verified="code",
        backend="estimator",
        evidence=(
            "merge_cmd.rs:2513 `const DEFAULT_VEIL_ON: bool = false;`, "
            "returned by veil_enabled() at :2525 when the variable is unset. "
            "BACKEND: the only caller is merge_cmd.rs:3580, inside fn "
            "run_estimator (defined :2680). run_pyramid (:4341) never calls "
            "it, and the default-path banner does not mention a veil stage."
        ),
        note=(
            "Absent on the shipping backend rather than dark on it, so the "
            "remedy is to BUILD it on the pyramid, not to flip a flag. Worth "
            "prioritising on evidence rather than taste: a corpus-wide "
            "bimodality census found the veiling signature concentrated in a "
            "subject class rather than spread thin -- multi-peak fraction "
            "0.324 on bee-1-cpl and 0.199 on bee-3-cpl against a corpus "
            "median of 0.007 -- and those are subjects the project holds up "
            "as print-worthy. A correction that is absent on the default "
            "backend is absent hardest exactly where it is most needed."
        ),
    ),
    "STREHL_VEIL_MARGIN": Declared(
        kind="quality",
        default="3.0",
        verified="code",
        backend="estimator",
        evidence=(
            "merge_cmd.rs:2554 `const DEFAULT_VEIL_MARGIN: f32 = 3.0;`, "
            "returned by veil_margin() at :2558 on Err(_). A non-numeric or "
            "negative value warns on stderr and falls back rather than "
            "failing."
        ),
        note=(
            "How far above the gated mean the veil envelope must sit before "
            "it is believed, in single-frame sigmas. Inert while STREHL_VEIL "
            "is off and while the stage is absent from the default backend."
        ),
    ),
    "STREHL_VEIL_FLOOR": Declared(
        kind="quality",
        default="0.5",
        verified="code",
        backend="estimator",
        evidence=(
            "merge_cmd.rs:2575 `const DEFAULT_VEIL_LUMA_FLOOR: f32 = 0.5;`, "
            "returned by veil_luma_floor() at :2579 on Err(_). Values outside "
            "[0,1] warn and fall back."
        ),
        note=(
            "Fraction of the estimated backdrop level below which no pixel "
            "may be raised. Inert while STREHL_VEIL is off and while the "
            "stage is absent from the default backend."
        ),
    ),
    # ---------------- control ----------------
    "STREHL_RESTORE_SIGMA": Declared(
        kind="control",
        default="1.0 (the calibrated sigma^2, unscaled)",
        verified="code",
        evidence=(
            "restore.rs:1266 sigma_scale_from_env() returns 1.0 when the "
            "variable is unset or empty; applied at :1313 as "
            "`self.noise.variance(..) * scale * scale * sigma_scale_from_env()`."
        ),
        note=(
            "Classified control rather than quality on the authority of its "
            "own doc comment: 'This is not a quality knob and must not become "
            "one.' It exists because RESTORE_ENV's gain cap is measured never "
            "to bind, so sigma^2 is the only variable that actually changes "
            "the filter's strength and a trade curve has to be swept along "
            "it. Note the deliberate design: it PANICS on a non-finite or "
            "non-positive value rather than silently substituting 1.0, "
            "because an instrument that quietly repairs its own "
            "misconfiguration produces a curve that is wrong in a way nobody "
            "can see. If this switch ever acquires a shipped non-1.0 default "
            "it has become a quality knob and must be reclassified here."
        ),
    ),
    "STREHL_SOFT_GATE": Declared(
        kind="control",
        default="off (None -- the shipped top-hat Gate)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: SOFT_GATE_ENV at merge.rs:476 is read "
            "at :628 via `kernel_from_setting(std::env::var(SOFT_GATE_ENV).ok()"
            ".as_deref())`, and `kernel_from_setting` at :596 opens `let raw = "
            "match value { None => return Ok(None), .. }` -- unset is None is "
            "the top-hat. An empty value, `0`, `off` or `false` also return "
            "Ok(None) (:603-609); an unrecognised key is Err(UnknownSoftKernel), "
            "not a silent default."
        ),
        note=(
            "DELIBERATE. merge.rs states it: 'None is the shipped top-hat Gate "
            "and must remain the default. Every byte-freeze in the corpus is "
            "taken against it; making a soft kernel default would break the "
            "entire regression net in one commit.' Selects kernel SHAPE over an "
            "unchanged calibrated z-axis, which is what makes M111 15.7 a "
            "controlled comparison."
        ),
    ),
    "STREHL_ROBUST_ELECTION": Declared(
        kind="control",
        default="off (no robust arm)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: ROBUST_ENV at merge.rs:652 is read at "
            ":669 by `active_arm()` as `arm_from_setting(std::env::var("
            "ROBUST_ENV).ok().as_deref())`, and `arm_from_setting` at :654 "
            "opens `let Some(raw) = raw else { return Ok(None) }` -- unset is "
            "None is off. '' | '0' | 'off' | 'false' also map to Ok(None) "
            "(:657); an unknown key returns Err(UnknownArm) (:661-663), which "
            "is the rigour the note below describes, present in the code."
        ),
        note=(
            "Four-valued: off | soft | hard | ungated, and an unknown key is a "
            "hard error, not off - 'a typo that disables a gate you believe is "
            "running looks exactly like the gate doing nothing.' 'ungated' runs "
            "the whole ring and declines only to let weight reach the argmax, "
            "which is the control separating 'the gate changed the picture' from "
            "'the new plumbing changed the picture'."
        ),
    ),
    "STREHL_ALIGN": Declared(
        kind="control",
        default="on (registration runs)",
        verified="measured",
        evidence=(
            "MEASURED, AND IT CORRECTED THIS ENTRY. `align_enabled()` at "
            "align_cmd.rs:941-949 is `match std::env::var(ALIGN_ENV) { Ok(v) => "
            "!matches!(v.trim().to_ascii_lowercase().as_str(), \"0\"|\"off\"|"
            "\"false\"|\"no\"), Err(_) => true }` -- unset falls in the "
            "`Err(_) => true` arm, so registration is ON. Confirmed by running "
            "ONE binary (target/release/strehl.exe, built 2026-08-26 13:52) "
            "twice over bee-3-cpl --limit 3 with identical flags, differing "
            "only in the variable. Unset printed `alignment : ON (sidecar), "
            "reference frame 1, 3 placed / 0 refused`; STREHL_ALIGN=off printed "
            "`alignment : OFF -- frames are combined unregistered. M86 measured "
            "232.7 px of drift on bee-3-cpl.` The two renders differ (SHA-256 "
            "D9BE3CEC..3BBA564F unset against 00E70E4B..C2ABAC14 off), so unset "
            "is demonstrably not off. Same binary both arms, so no cross-build "
            "hazard applies. A second read at align_cmd.rs:1338 gives the value "
            "`zoom` a third meaning (fit the cover scale but apply nothing "
            "else), which is why the default is stated as an arm and not a bool."
        ),
        note=(
            "Selects the alignment arm. THIS ENTRY WAS DECLARED `off` AND WAS "
            "WRONG -- the same shape as the STREHL_PHOTOMETRIC defect this "
            "file's header was written about: a plausible-sounding default that "
            "nobody read the resolving expression for, trusted by a script that "
            "trusts declarations. It mattered more than PHOTOMETRIC's did, "
            "because it described the product's REGISTRATION -- the stage that "
            "makes a focus stack a focus stack rather than an average of "
            "misaligned frames -- as off by default, on a subject where turning "
            "it off genuinely costs 232.7 px of drift. Nothing in the SHIPPED "
            "PRODUCT was broken by it: alignment was running the whole time. "
            "The DECLARATION was broken, which is bad in one specific way -- "
            "this file is what the project reads to find out what it ships, so "
            "a wrong row here is a wrong answer to the only question the file "
            "exists to answer, and it is wrong with the script's blessing."
        ),
    ),
    "STREHL_SMOOTH": Declared(
        kind="control",
        default="built-in (DEFAULT_SMOOTH_LAMBDA)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: `apply_smooth_env()` at align_cmd.rs:584 "
            "opens `match std::env::var(\"STREHL_SMOOTH\")` at :585 whose FIRST "
            "arm is `Err(_) => DEFAULT_SMOOTH_LAMBDA` (:586) -- unset is the "
            "built-in lambda, not zero. `off` maps to 0.0 at :587, and the "
            "guard `if lambda <= 0.0 { return; }` at :599-601 then leaves "
            "`opts` untouched, so `off` also suppresses the huber read below it."
        ),
        note=(
            "Warp-field smoothness lambda override. Its own doc comment defends "
            "the prior as 'a strictly better registration at the span the merge "
            "selects across, at no cost' -- not as a sharpness fix."
        ),
    ),
    "STREHL_SMOOTH_HUBER": Declared(
        kind="control",
        default="built-in (DEFAULT_SMOOTH_HUBER_PX)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: align_cmd.rs:603 `match "
            "std::env::var(\"STREHL_SMOOTH_HUBER\")` closes on `Err(_) => "
            "Some(DEFAULT_SMOOTH_HUBER_PX)` at :610, so unset is the built-in "
            "threshold. NOT INDEPENDENT OF STREHL_SMOOTH: this read sits after "
            "the `if lambda <= 0.0 { return; }` guard at :599, so with "
            "STREHL_SMOOTH=off it is never reached at all. A set value that "
            "does not parse, or is non-finite or <= 0, silently becomes None "
            "via `.ok().filter(..)` at :608-609 rather than failing."
        ),
        note=(
            "Huber threshold, in pixels, for the smoothness term. Registered in "
            "SOLVE_ENV (align_cmd.rs:993) so it lands in the alignment cache "
            "key; that list's own comment warns that extending "
            "`apply_smooth_env` without adding the variable there reopens the "
            "defect `solve_config_key` exists to close."
        ),
    ),
    "STREHL_CACHE_DIR": Declared(
        kind="control",
        default="platform default",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: `cache_root()` at align_cmd.rs:1065 is "
            "`std::env::var_os(\"STREHL_CACHE_DIR\").map(PathBuf::from)"
            ".unwrap_or_else(..)`, so unset takes the fallback branch -- "
            "%LOCALAPPDATA%\\strehl\\warpmaps on Windows, "
            "$XDG_CACHE_HOME/strehl/warpmaps elsewhere, then the temp dir."
        ),
        note="Alignment sidecar cache location. Infrastructure, not quality.",
    ),
    "STREHL_PYRAMID_MEAN_COARSE": Declared(
        kind="control",
        default="0 (no Laplacian band averaged; base band is a mean regardless)",
        verified="measured",
        evidence="pyramid.rs (MEAN_COARSE_ENV, DEFAULT_MEAN_COARSE, "
        "mean_coarse_default); applied in the band loop, tested by "
        "averaging_the_coarse_bands_is_not_the_same_merge",
        note=(
            "How many of the COARSEST Laplacian bands the pyramid merge "
            "averages instead of selecting. Built to answer ORCH's registered "
            "criteria on the far-field bowl, measured on a 4-rung ladder over "
            "flower-bud-with-background-fern-cpl, and DELIBERATELY LEFT AT 0. "
            "Off is the right default and it was measured, not assumed: "
            "criterion (a), the bowl, ALREADY PASSES at 0 -- the residual bowl "
            "is +191 DN at d=550, which is +0.35 of 255 at ORCH's operating "
            "point against their 1.00 bar -- while every rung that closes the "
            "bowl further fails criterion (b), retaining only 44.3% (mc=2) and "
            "25.2% (mc=3) of the mid-field win against an 88.6% bar. ORCH "
            "pre-registered the response to exactly that outcome: report it as "
            "a failure and do not ship. mc=1 is a genuine trade rather than an "
            "improvement (better than mc=0 on every row from d=2 to d=90, "
            "worse by 142-194 DN across d=112-225) and is left available. "
            "ORCH's much larger measured bowl came from a toned+sRGB pair "
            "whose blend arm carried a collapsed black point; on untoned "
            "linear renders the control arm's rows transfer at 1.40x and the "
            "blend arm's at 4.79x, a 3.42x discriminating ratio. "
            "COMMISSIONED: rung 0 is byte-identical (SHA-256 84A4661D...D655C) "
            "to the render made before this knob existed, so the default "
            "cannot move a byte, and rungs 1-3 all differ from it, so the env "
            "var demonstrably reaches pixels. Full ladder and both instruments "
            "in docs/research/BUILD-BLEND.md and experiments/BUILD-BLEND/."
        ),
    ),
    "STREHL_PYRAMID_WORKERS": Declared(
        kind="control",
        default="solved from the memory budget alone",
        verified="measured",
        evidence="merge_cmd.rs (BAND_WORKERS_ENV, band_workers); "
        "MEMORY_BUDGET_BYTES at stack.rs:50",
        note=(
            "Worker count for the pyramid merge's fold. Unset it is "
            "min(MEMORY_BUDGET_BYTES / per-worker bytes, frames) -- 5 on the "
            "205-frame flower stack at 1070 MB per worker against the 6144 MB "
            "budget. Infrastructure, not quality: it chooses how the fold is "
            "partitioned and nothing else. IT NONETHELESS MOVES THE OUTPUT "
            "BYTES, which was measured rather than assumed and is the reason "
            "this entry exists in the shape it does: float addition is not "
            "associative and `BandMerge::absorb` sums the per-worker "
            "accumulators, so a different worker count is a different "
            "reduction order. On flower-bud-alone-cpl, 2 workers against 7 "
            "differ on 0.2573% of pixels at max |delta| = 1 DN with ZERO "
            "pixels above 1 DN -- last-bit rounding, against a control on the "
            "same pair of images (the two backends) of 99.9895% of pixels and "
            "a mean of 1820 DN. Because of this, the default deliberately does "
            "NOT consult available_parallelism(): every input to it is a "
            "property of the build and the stack, never of the host, so the "
            "shipped default merge is reproducible across machines. Setting "
            "this variable therefore leaves the byte-freeze net; that is what "
            "it is for."
        ),
    ),
    "STREHL_CAPTURES": Declared(
        kind="control",
        default="unset",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: byte-freeze.rs:739 is `if let Some(p) = "
            "std::env::var_os(\"STREHL_CAPTURES\")`, so unset takes no branch "
            "and the net has no corpus to check against."
        ),
        note="Points the byte-freeze net at the corpus. Test infrastructure.",
    ),
    "STREHL_FREEZE_REQUIRE": Declared(
        kind="control",
        default="unset (a missing corpus SKIPS)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: byte-freeze.rs:800-802 is "
            "`std::env::var(\"STREHL_FREEZE_REQUIRE\").map(..).unwrap_or(false)` "
            "-- unset is `false`, i.e. absent captures skip rather than fail."
        ),
        note=(
            "Forces the byte-freeze net to fail rather than skip when captures "
            "are absent. Unset means a missing corpus SKIPS - so a green "
            "byte-freeze run does not by itself mean the net ran."
        ),
    ),
    # ---------------- diagnostic ----------------
    "STREHL_ONLY_FRAME": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: ONLY_FRAME_ENV is declared at "
            "merge_cmd.rs:1709 and read at :1731 as `let Ok(raw) = "
            "std::env::var(ONLY_FRAME_ENV) else { .. }`, so unset takes the "
            "else branch and no single-frame render happens. A set value that "
            "is not a frame index PANICS at :1737 rather than falling back -- "
            "the rigour this file asks for, already present here."
        ),
        note=(
            "Renders one frame with no election. TRAP: it changes the digest, so "
            "the alignment sidecar is rejected and alignment re-solves."
        ),
    ),
    "STREHL_DUMP_ELECTION": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: ELECTION_ENV at merge_cmd.rs:2346, read "
            "at :2365 as `let raw = std::env::var(ELECTION_ENV).ok()?` -- the "
            "`?` returns None when unset, so nothing is dumped. (The cited line "
            "had drifted from :1839; the const is the durable anchor.)"
        ),
        note=(
            "Dumps the pass-one winner field. The elected frame index IS a depth "
            "ordering, which is what BUILD-HALO's depth-coherence silhouette is "
            "built on (017e7c6). Also available as --election-map."
        ),
    ),
    "STREHL_DUMP_NEFF": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: NEFF_ENV at merge_cmd.rs:2426, read at "
            ":2612 as `let raw = std::env::var(NEFF_ENV).ok()?` -- None when "
            "unset. (Cited line had drifted from :1919.)"
        ),
        note="Dumps the n_eff map. Env twin of a flag.",
    ),
    "STREHL_DUMP_MERGE_STATE": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: DUMP_ENV at merge_cmd/dump.rs:42, read "
            "at :50 as `let raw = std::env::var(DUMP_ENV).ok()?` -- None when "
            "unset."
        ),
        note="Dumps merge internals.",
    ),
    "STREHL_BIMODAL_DUMP": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: BIMODAL_DUMP_ENV at merge_cmd.rs:1950, "
            "read at :1953 as `std::env::var_os(BIMODAL_DUMP_ENV)"
            ".map(std::path::PathBuf::from)` -- None when unset, so no path and "
            "no dump. (Cited line had drifted from :1443.)"
        ),
        note="Dumps the through-focus bimodality statistic.",
    ),
    "STREHL_WARPMAP": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: WARPMAP_ENV at merge_cmd.rs:2280, read "
            "at :2297 as `let Some(explicit) = std::env::var_os(WARPMAP_ENV) "
            "else { .. }` -- unset takes the else branch. (Cited line had "
            "drifted from :1773.)"
        ),
        note="Dumps the per-frame warp field.",
    ),
    "STREHL_FIX_HALO_DELTA": Declared(
        kind="diagnostic",
        default="built-in DELTA (and the stage reading it is gated off)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ, AND THE DECLARED `off` WAS IMPRECISE: "
            "DELTA_ENV at merge_cmd/halo.rs:85 is read at :124-128 as "
            "`std::env::var(DELTA_ENV).ok().and_then(|v| v.trim()"
            ".parse::<u16>().ok()).unwrap_or(DELTA)` -- unset resolves to the "
            "built-in DELTA constant, NOT to nothing. The product-level "
            "behaviour is still 'no delta image written', but for a different "
            "reason than this row used to give: the whole stage is gated off by "
            "STREHL_FIX_HALO (halo.rs:113, `Err(_) => false`), which is itself "
            "estimator-only. DEFECT WORTH NAMING: `.unwrap_or(DELTA)` swallows "
            "a malformed value silently, so STREHL_FIX_HALO_DELTA=abc renders "
            "at the default delta while the operator believes they moved it. "
            "That is the pattern main.rs:649 bans for --photometric ('neither "
            "can mean ON by accident'). Low stakes because the switch is "
            "diagnostic and doubly gated, but it is the same shape."
        ),
        note="Writes the halo correction's delta image, for inspection.",
    ),
    # ---- previously UNDECLARED; declared 2026-08-26 after reading each
    # ---- resolving expression. An undeclared switch is one nobody has decided
    # ---- the default for, which is how this file's header says three measured
    # ---- fixes shipped turned off.
    "STREHL_COVER": Declared(
        kind="control",
        default="on (the coverage fit is applied)",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: COVER_ENV at align_cmd.rs:936, read at "
            ":1317-1324 as `let skip_fit = std::env::var(COVER_ENV).map(|v| "
            "matches!(.., \"0\"|\"off\"|\"false\"|\"no\")).unwrap_or(false)` -- "
            "unset gives `skip_fit = false`, so the fit RUNS. Note the "
            "inversion: the variable names the thing it can turn OFF, so "
            "`STREHL_COVER=0` skips the fit. Its own doc comment at :930 states "
            "'the coverage enlargement, which is **on** by default', and the "
            "banner from an unset run agrees -- the pencil-steep-angle-cpl "
            "render printed `coverage : field of view scaled to 0.9954 so that "
            "EVERY frame covers every pixel`."
        ),
        note=(
            "Skips only the cover fit, keeping the identical solve, per-frame "
            "warp and merge. Its own comment insists this is a MEASUREMENT "
            "CONTROL and not a shipping option, because a render made with it "
            "has edge pixels no frame covers; anything measured through it must "
            "stay well inside the frame. Distinct from STREHL_ALIGN=off, which "
            "removes registration entirely and lands ghosting in the band under "
            "test."
        ),
    ),
    "STREHL_HIGHLIGHT_KNEE": Declared(
        kind="quality",
        default="on (knee at 0.60 of the container ceiling)",
        verified="measured",
        evidence=(
            "RESOLVING EXPRESSION READ AND A/B MEASURED: KNEE_ENV at "
            "highlight.rs:113; `knee()` "
            "at :151 is a OnceLock whose initialiser opens `match "
            "std::env::var(KNEE_ENV)` at :152 with FIRST arm `Err(_) => "
            "Some(DEFAULT_KNEE)` at :153 -- unset is ON at the built-in knee, "
            "not off. DEFAULT_KNEE = 0.60 (highlight.rs:131). `off` or `0` "
            "yields None, which the doc records as 'the state the render was in "
            "before this module existed'. A set value outside (0,1) warns on "
            "stderr and falls back to 0.60 rather than failing."
        ),
        note=(
            "Chroma roll-off near the highlight container ceiling. ON BY "
            "DEFAULT BECAUSE IT IS A DEFECT FIX, per the module doc at "
            "highlight.rs:107. The 0.60 knee is anchored on the corpus's "
            "unsaturated stacks rather than tuned to the residual, so stacks "
            "that never approach saturation are bit identical with margin -- "
            "the module's own placebo arm. REACH ON THE DEFAULT BACKEND IS "
            "MEASURED, not argued: one binary (target/release/strehl.exe, built "
            "2026-08-26 13:52), dry-erase-marker-head-cpl (the corpus's worst "
            "clipper, chosen because the module's own null says an unsaturated "
            "stack MUST come back identical and so could not tell reach from "
            "no-op), --srgb --auto-exposure --limit 6, default pyramid backend, "
            "differing only in the variable: unset gave SHA-256 1CED2444.."
            "B8B36013 and STREHL_HIGHLIGHT_KNEE=off gave 7876A8DC..7C67D810. "
            "The stage therefore reaches pixels on the path that ships."
        ),
    ),
    "STREHL_VEIL_DISPERSION": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        backend="estimator",
        evidence=(
            "RESOLVING EXPRESSION READ: merge_cmd.rs:3600-3602, "
            "`std::env::var(\"STREHL_VEIL_DISPERSION\").map(|v| v != \"0\" && "
            "!v.is_empty()).unwrap_or(false)` -- unset is false. BACKEND: the "
            "read sits inside fn run_estimator (defined :2680), not run_pyramid "
            "(:4341), so the shipping default backend never reaches it."
        ),
        note=(
            "Diagnostic arm of the veil stage. Its own comment states why it is "
            "off and must stay off: debiasing by the OBSERVED spread is the "
            "right diagnosis of the far-field lift and the WRONG OPERATOR at a "
            "veiled pixel, because the observed spread there is mostly the veil "
            "signal itself. Off is a decision, not neglect."
        ),
    ),
    "STREHL_CONFIDENCE_MAP": Declared(
        kind="diagnostic",
        default="off",
        verified="measured",
        evidence=(
            "RESOLVING EXPRESSION READ AND MEASURED. CONFIDENCE_ENV at "
            "merge_cmd.rs:4273, read at :4280 as `let raw = "
            "std::env::var(CONFIDENCE_ENV).ok()?` -- None when unset. MEASURED "
            "on one binary over bee-3-cpl: with the flag the run wrote a "
            "3516x2344 u16 map and partitioned every pixel (graded 8241504 + "
            "saturated 0 + unreached 0 = 8241504); with and without the flag "
            "the RENDERED IMAGE was SHA-256 identical, which is the property "
            "that makes it safe as a diagnostic -- asking for the artifact "
            "cannot change the picture."
        ),
        note=(
            "Env twin of --confidence-map. Emits the per-pixel centrality rank "
            "on the DEFAULT pyramid backend: for each pixel, how far the merged "
            "value sits from the middle of the observation cloud that produced "
            "it, in milli-units. OFF IS THE RIGHT DEFAULT ON COST, NOT ON "
            "DOUBT: it costs a second full traversal of every frame (85.8 s "
            "against the fold's 148.2 s on bee-3-cpl), so it roughly halves "
            "throughput for an artifact most renders do not need. Not `quality` "
            "-- it writes a file and provably does not touch the image."
        ),
    ),
    "STREHL_CONFIDENCE_DEBUG": Declared(
        kind="diagnostic",
        default="off",
        verified="code",
        evidence=(
            "RESOLVING EXPRESSION READ: merge_cmd.rs:5091, `let debug_dir = "
            "std::env::var(\"STREHL_CONFIDENCE_DEBUG\").ok()` -- None when "
            "unset, and the debug branch is taken only for Some(dir)."
        ),
        note=(
            "MEASUREMENT SCAFFOLDING, deliberately retained. Set to a directory "
            "to have the confidence pass emit all five candidate statistics "
            "(dmin, dsharp, spread, centrality, withinfrac) from ONE traversal, "
            "which is how centrality was chosen over the other four rather than "
            "asserted: on the known veiled tarsus in bee-3-cpl at matched "
            "subject contrast, dmin 0.848 / dsharp 0.909 / spread 0.911 all "
            "read the KNOWN merge failure as MORE confident, and only "
            "centrality (1.453) read it as worse. Kept so a verifier can re-run "
            "the comparison instead of taking that on trust."
        ),
    ),
    "STREHL_DEFECT": Declared(
        kind="control",
        default="off",
        verified="measured",
        backend="pyramid",
        evidence=(
            "RESOLVING EXPRESSION READ AND THREE ARMS MEASURED ON ONE PINNED "
            "BINARY. stack.rs:884 `match std::env::var(\"STREHL_DEFECT\")` "
            "closes on `Err(_) => false` at :895, and that false falls through "
            "to `Ok(DefectRequest::Off)` at :906, so unset is OFF by an "
            "explicit branch rather than by a fallback. `\"off\"` returns early "
            "at :886 and beats everything else that may be set; `\"on\"` at "
            ":887; ANY OTHER VALUE bails at :888 rather than degrading to off. "
            "MEASURED by experiments/BUILD-DEFECT/src/44-default-arms.ps1 "
            "against pin f30ffdf8, coffee-bean --limit 10, pyramid backend, "
            "identical flags, the variable the only difference: unset rendered "
            "E15D9ED90A1C36B4 and `on` rendered 8E4D18ED4A4E9B7F -- same length "
            "(197801290 bytes), different bytes, so the switch moves pixels and "
            "unset is demonstrably not `on`. POSITIVE CONTROL FOR THE READ "
            "ITSELF: STREHL_DEFECT=bogus exits 1 with 'is not a setting; it is "
            "\"on\" or \"off\"', which is what makes the pair interpretable -- "
            "without it, two differing renders still could not separate 'unset "
            "is off' from 'unset is some third thing'. The unset arm's own "
            "banner reads `defect map      : off (STREHL_DEFECT=off)`; the `on` "
            "arm reads 2/2 sites confirmed from 8 frames (not significant 0, "
            "too shallow 0, not stationary 0, unmeasurable 0) and corrects "
            "(3434, 2305) at -14.945% depth, p 0.0025. BACKEND: the correction "
            "is applied by stack.rs's `load_frame`, the PYRAMID loader; the "
            "estimator loads through `field_for`/`Scratch` and "
            "`merge_cmd::preflight_defect_backend_support` refuses an estimator "
            "run with a map configured rather than silently dropping it."
        ),
        note=(
            "DECLARED `control` UNDER PROTEST, AND THE PROTEST IS THE POINT. "
            "This is a measured quality correction -- it is not `control` "
            "because off is intrinsically right, it is `control` because ORCH "
            "has ruled it must not default on while its COORDINATE IS "
            "DISPUTED, and this file's own contract is that a switch held off "
            "must say out loud why. WHY OFF IS RIGHT TODAY: a second lane "
            "hunting the same mote read -0.78% at 1:1 where this lane reads "
            "-13.28% to -14.945%, a 17x disagreement, and THREE coordinates "
            "for one mote are in circulation ((3434,2305) quad, (7008,4450) "
            "master, 6776_4322). If the coordinate is wrong, default-on does "
            "not merely fail to correct -- this lane's own MANUFACTURE "
            "commissioning arm injects +8.64% to +16.44% at a clean site, i.e. "
            "it would stamp a defect into every frame on the default path, in "
            "a product whose owner has already rejected one round of output. "
            "WHAT MAKES IT SAFE ENOUGH TO SHIP AT ALL: the map only NOMINATES "
            "a site; the amplitude is fitted from the stack's own frames and "
            "the site must be confirmed there first, so a stale map cannot "
            "manufacture a defect it is required to observe. That guard has a "
            "measured zero -- 26 masters examined = 17 corrected + 9 skipped + "
            "0 failed, every skip 'not significant', never 'too shallow'. "
            "SUPPORTING MEASUREMENT ON DATA THAT NEEDS NO STATISTIC: on 256 "
            "usable flat fields the site reads -3.483% over its core (odd "
            "-3.470% / even -3.590% split-half) as a resolved ~30-quad disc "
            "against a +0.5% background, and the shipping SiteValidator reads "
            "-3.235% of that, ratio 0.93, so the instrument does not "
            "over-read. RETRACTION KEPT DELIBERATELY: this lane earlier "
            "asserted the sensor coordinate indexes a specific master pixel; "
            "it withdrew that, because the master domain is underpowered "
            "(local residual sd 2.2-4.7% against the effect sought). WHAT "
            "WOULD MOVE THIS TO `quality`: V-REVIEW confirming the coordinate "
            "against the flats, plus a powered master-domain measurement. Do "
            "not flip it to clear this check; the reason it is off is written "
            "above and it is not a scheduling problem. CONSISTENCY WITH THE "
            "FREEZE HARNESS, CHECKED RATHER THAN ASSUMED: byte-freeze.rs "
            "hardcodes STREHL_DEFECT=off in `Freeze::env()`, but every "
            "registry row also hardcodes `--merge estimator` in `argv`, so no "
            "freeze row can reach this code path at all -- the hardcode spells "
            "out the value those rows already render under (the RENDER_ENV "
            "header requires unset be a spelled-out VALUE, never an empty "
            "field) rather than suppressing a feature to keep a hash still. "
            "Harness and product therefore agree that unset means off. The day "
            "a pyramid row is added, that hardcode must become a registry "
            "column and that row WILL differ from today's bytes."
        ),
    ),
    "STREHL_DEFECT_MAP": Declared(
        kind="control",
        default="unset (no sidecar; the embedded per-body map is used)",
        verified="code",
        backend="pyramid",
        evidence=(
            "RESOLVING EXPRESSION READ: stack.rs:897 "
            "`std::env::var_os(\"STREHL_DEFECT_MAP\")`, returning "
            "`DefectRequest::Sidecar(path)` at :900 for a non-empty path and "
            "otherwise falling through to `Embedded` (:904) or `Off` (:906). "
            "NOT GATED THE WAY ITS SIBLINGS ARE, AND THE ASYMMETRY IS "
            "DELIBERATE: this read sits inside `defect_request_from_env` "
            "BEFORE the `if requested` test, so naming a sidecar IMPLIES `on` "
            "-- setting only this variable turns the correction on. The one "
            "thing that suppresses the read is an explicit STREHL_DEFECT=off, "
            "which returns at :886 before line 897 is reached. So `off` beats "
            "a named map, but unset does not."
        ),
        note=(
            "Overrides the embedded per-body defect map with a sidecar file. "
            "Reason it implies `on`: requiring both STREHL_DEFECT=on AND a map "
            "path would make the single most likely invocation -- naming a map "
            "-- a SILENT NO-OP, which is the failure mode this project keeps "
            "shipping. A path that does not exist or does not parse is a hard "
            "error, not a fall back to the embedded map, on the same reasoning "
            "as `a_typod_override_errors_rather_than_falling_back_to_the_"
            "default`: falling back would leave the caller believing a "
            "different map was applied. FORMAT VERSION IS ENFORCED: the reader "
            "REJECTS a map that does not record which raw array its "
            "coordinates index, rather than guessing -- a guess already cost "
            "this lane a +54.8% misreading from an optical-black offset, and a "
            "loud failure on an old map is cheaper than a silent 54.8% error. "
            "Unset is the right default because the embedded map is the one "
            "that was commissioned; a sidecar is by construction unreviewed."
        ),
    ),
    "STREHL_DEFECT_ARM": Declared(
        kind="control",
        default="dust",
        verified="code",
        backend="pyramid",
        evidence=(
            "RESOLVING EXPRESSION READ: stack.rs:911 `let arm = "
            "std::env::var(\"STREHL_DEFECT_ARM\").unwrap_or_else(|_| "
            "\"dust\".into())`, so unset is the string \"dust\", parsed at :912 "
            "by `Correction::parse`. An unrecognised arm is an error at :913 "
            "naming the four legal values, not a fall back to dust. NOT "
            "INDEPENDENT OF STREHL_DEFECT: the only call to "
            "`defect_arms_from_env` is stack.rs:959, which sits AFTER the "
            "`if !req.wants_correction()` early return at :955-957, so with "
            "STREHL_DEFECT unset or off THIS VARIABLE IS NEVER READ AT ALL. "
            "Same shape as STREHL_SMOOTH_HUBER behind STREHL_SMOOTH."
        ),
        note=(
            "Selects which defect classes are corrected: \"none\", \"hot\", "
            "\"dust\", \"both\". Default `dust` and not `both` because the hot "
            "arm is the weaker evidence -- the dust site is confirmed on flat "
            "fields where it needs no statistic to be seen, while the hot-pixel "
            "population is inferred from darks and has never been shown to "
            "change a delivered master. READ THE GATING ABOVE BEFORE SETTING "
            "THIS: because the master switch defaults OFF, setting only "
            "STREHL_DEFECT_ARM changes NOTHING and produces no diagnostic, so "
            "a caller who sets it alone will believe they moved something. "
            "`none` is honoured rather than treated as a mistake -- it returns "
            "at stack.rs:961-962 with `no arms selected`, which is a counted, "
            "named outcome and not a silent skip."
        ),
    ),
    "STREHL_DEFECT_HOT_FLOOR": Declared(
        kind="control",
        default="8 e- (HotFloor::default())",
        verified="code",
        backend="pyramid",
        evidence=(
            "RESOLVING EXPRESSION READ: stack.rs:915 `match "
            "std::env::var(\"STREHL_DEFECT_HOT_FLOOR\")` closes on `Err(_) => "
            "HotFloor::default()` at :919, which is 8 electrons -- CONFIRMED "
            "BY BANNER, the measured `on` arm of 44-default-arms.ps1 printed "
            "`arms dust (floor 8.0 e-, gain 0.22894 DN/e-)`. A set value that "
            "does not parse as f32 is an error at :917, not a fall back. "
            "DOUBLY GATED, so unset is doubly unreachable by default: (1) it "
            "is read inside `defect_arms_from_env`, called only at stack.rs:959 "
            "AFTER the early return at :955-957, so STREHL_DEFECT unset means "
            "it is never read; and (2) even when read, it parameterises the "
            "HOT arm only, which the default STREHL_DEFECT_ARM=dust does not "
            "select."
        ),
        note=(
            "Electron floor above which a dark-frame pixel counts as hot. 8 e- "
            "is the reproducibility floor -- the level at which a candidate "
            "recurs across dark frames rather than appearing once -- so it is a "
            "statement about what the darks can support, not a taste setting. "
            "READ THE DOUBLE GATING ABOVE BEFORE SETTING THIS: on the shipped "
            "default path this variable is inert twice over, and lowering it "
            "alone will change no output and print no diagnostic saying so. To "
            "make it do anything a caller needs STREHL_DEFECT=on AND "
            "STREHL_DEFECT_ARM=hot or =both. Lowering it is not free: the hot "
            "arm's population grows fast below the reproducibility floor, and "
            "correcting a pixel that is not reliably hot spends the same "
            "interpolation on a good pixel as on a bad one."
        ),
    ),
}

# Matches a STREHL_* literal anywhere in the crates. Deliberately broad: the
# point is to find switches nobody declared, so a narrow pattern that only
# matched the tidy `pub const X_ENV` form would miss exactly the ad-hoc
# `std::env::var("STREHL_SMOOTH")` cases that are most likely to be forgotten.
SWITCH_RE = re.compile(r'"(STREHL_[A-Z0-9_]+)"')


def find_switches(crates: Path) -> dict[str, list[str]]:
    """Every STREHL_* literal in the crates, mapped to where it appears."""
    found: dict[str, list[str]] = {}
    for rs in sorted(crates.rglob("*.rs")):
        try:
            text = rs.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"  ! could not decode {rs}, skipping", file=sys.stderr)
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name in SWITCH_RE.findall(line):
                found.setdefault(name, []).append(f"{rs.name}:{lineno}")
    return found


# The clap-derive flag surface, which SWITCH_RE cannot see by construction: no
# `--flag` is spelled `STREHL_*`, so every partition above sums over env
# switches ONLY and reads exactly the same whether the flag surface is fully
# declared or entirely unexamined.
#
# That blind spot is not hypothetical: `--photometric` shipped with its help
# text and its default disagreeing, which is the defect this script was written
# to catch and which was invisible to it, because the property that decides
# whether it can see a switch -- being spelled as a quoted STREHL_ literal --
# was never varied.
#
# THE HISTORY OF THIS COMMENT IS ITSELF THE LESSON, AND IT HAS TWO RETRACTIONS
# IN IT. Both are kept.
#
# ROUND 1. This comment claimed, unsourced, that "`--exposure` and
# `--auto-exposure` reach no pixel while the banner announces `+2.61 stops
# (gain 6.105x)`".
#
# ROUND 2 (commit 4f2633bb) WITHDREW THAT CLAIM. I rendered five arms, found
# four distinct SHA-256s, and wrote a long retraction here concluding "The path
# is LIVE". THAT WITHDRAWAL WAS WRONG AND IS ITSELF NOW WITHDRAWN. Round 1 was
# substantively correct.
#
# ROUND 3, MEASURED, and the one to believe. Same four renders, but regressed
# instead of hashed: LSQ through the origin, all pixels, estimator commissioned
# first on planted 2.0x / 0.5x / 1.0x and returning each to nine decimals -- the
# 0.5x arm present specifically so an estimator bounded below at 1.0 could not
# pass. (experiments/BUILD-DEFECT/src/48-delivered-gain.py, /49-*.py.)
#
#     pair                       commanded      DELIVERED   samples differing
#     -3 stops vs +3 stops          64.000      1.0000000   0 of 98,898,048
#     --auto-exposure vs none        6.105      1.0000000   326,612, max 1 count
#
# A commanded 64x span delivers 1.0000000 and leaves every one of 98,898,048
# samples BIT-IDENTICAL. The flags are not ignored -- they are CANCELLED, and
# the cancellation is localised to the tone stage by a third, independent
# channel: the tone anchors each file embeds in its own ImageDescription scale
# by exactly the commanded gain (8.0000, 0.1250, 6.1050) while the pixels do
# not move. The tone stage receives the exposure in full and then divides it
# straight back out.
#
# WHY, ALGEBRAICALLY, from image_out.rs Tone::from_luminance and Tone::gain
# (read-only, not this lane's file). Both tone percentiles are linear in the
# data, so an upstream gain g gives black -> g*black and white -> g*white, hence
# s -> s/g while the normalised y = (l-black)*s is INVARIANT. TONE_TOE is a
# constant in that same normalised space, so the toe is invariant too, and the
# min(., s) cap cancels because both branches carry 1/g. Output is
# (g*v)*(gain/g) = v*gain: the original pixel, exactly, term by term.
#
# WHY THE HASH TEST LIED, which is the part worth carrying elsewhere. The +3
# and -3 files differ in TEN bytes, every one of them BEFORE the pixel data
# begins at offset 3,404. The differing run is 21 bytes at offset 339 and it is
# the ImageDescription's own record of the tone rendering. The instrument
# reported the file's SELF-DESCRIPTION as evidence about the file's CONTENT.
# The bytes being hashed contained the banner.
#
#     argv -> banner -> bytes moved -> the commanded quantity was delivered
#
# "The bytes moved" proves NOT INERT. It does not prove IT DID WHAT IT SAID.
# An argv records the request, a banner records the claim, a hash records that
# something somewhere is different, and only a calibrated measurement against
# an unmodified arm records the behaviour. Round 1's error was asserting
# without measuring; round 2's error was measuring the wrong quantity and
# mistaking sensitivity for specificity. Round 2 was the more dangerous, because
# it came with numbers.
#
# STATUS FOR THE PRODUCT: `--exposure` and `--auto-exposure` are INOPERATIVE
# controls. They are refused without `--srgb` (measured: exit 1), and `--srgb`
# is precisely the path that installs the tone stage that cancels them, so no
# combination tested can make either flag change the delivered image. This is
# not "the masters are under-exposed" -- the tone stage exposes them. It is
# that the exposure knob does nothing and says otherwise. Do not clear this by
# flipping anything; the fix re-renders the deliverable and is ORCH-sequenced.
#
# Most flags are derived from the field name (`pub auto_exposure` gives
# `--auto-exposure`); a few name themselves with `long = "..."`. Both forms
# count, because the whole point is to find the ones nobody tidied.
#
# THE ATTRIBUTE BODY MUST TOLERATE ONE LEVEL OF NESTING. The first version of
# this pattern used `[^\]]*` and its comment said nested brackets were rare, so
# it dismissed them without checking. `align_cmd.rs:109` is
# `#[arg(long, value_delimiter = ',', default_values_t = [1usize, 2, 4, ...])]`
# -- the ARRAY LITERAL closes before the attribute does, the class stopped
# early, and `--spans` was invisible. It occurs exactly once in the crates, and
# once is enough to make a coverage number wrong by one in the direction that
# flatters it. Caught by asking the shipped binary how many flags it has and
# differencing the two sets, which is a magnitude; the commissioning harness
# that scored this scanner 5/5 could not catch it, because it only ever tested
# forms its author had already thought of.
_ATTR_BODY = r"(?:[^\[\]]|\[[^\[\]]*\])*?"
CLI_ARG_RE = re.compile(
    rf"#\[arg\((?P<attr>{_ATTR_BODY})\)\]"  # the clap attribute
    rf"(?:\s*#\[{_ATTR_BODY}\])*"  # further attributes between it and the field
    r"\s*(?:pub\s+)?(?P<field>[a-z0-9_]+)\s*:"
)
CLI_LONG_NAME_RE = re.compile(r'long\s*=\s*"([a-z0-9\-]+)"')


def find_cli_flags(crates: Path) -> dict[str, list[str]]:
    """Every derived or explicit `--flag`, mapped to where it is declared."""
    flags: dict[str, list[str]] = {}
    for rs in sorted(crates.rglob("*.rs")):
        try:
            text = rs.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in CLI_ARG_RE.finditer(text):
            attr = m.group("attr")
            if "long" not in attr:
                continue  # a positional or short-only argument is not a --flag
            explicit = CLI_LONG_NAME_RE.search(attr)
            name = explicit.group(1) if explicit else m.group("field").replace("_", "-")
            lineno = text.count("\n", 0, m.start()) + 1
            flags.setdefault(f"--{name}", []).append(f"{rs.name}:{lineno}")
    return flags


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    crates = root / "crates"
    if not crates.is_dir():
        print(f"FAIL: no crates/ under {root}", file=sys.stderr)
        return 1

    found = find_switches(crates)
    cli_flags = find_cli_flags(crates)

    undeclared = sorted(set(found) - set(REGISTRY))
    stale = sorted(set(REGISTRY) - set(found))
    known = sorted(set(found) & set(REGISTRY))

    # A quality switch that is off AND cannot run on the default backend is not
    # dark -- it is absent. Both facts are "the product does not apply this",
    # but they have different remedies: a dark switch is turned on, an absent
    # stage has to be BUILT. Conflating them sent two agents after a promotion
    # that would have changed no pixel, because the default backend is the
    # pyramid and the stages in question are the estimator's.
    DEFAULT_BACKEND = "pyramid"

    def reaches_default_path(n: str) -> bool:
        return REGISTRY[n].backend in ("any", DEFAULT_BACKEND)

    quality_dark = [
        n
        for n in known
        if REGISTRY[n].kind == "quality"
        and REGISTRY[n].default == "off"
        and reaches_default_path(n)
    ]
    quality_inapplicable = [
        n
        for n in known
        if REGISTRY[n].kind == "quality"
        and REGISTRY[n].default == "off"
        and not reaches_default_path(n)
    ]
    quality_on = [
        n for n in known if REGISTRY[n].kind == "quality" and REGISTRY[n].default != "off"
    ]
    control = [n for n in known if REGISTRY[n].kind == "control"]
    diagnostic = [n for n in known if REGISTRY[n].kind == "diagnostic"]

    # A quality switch whose default nobody has checked is not "fine", it is
    # UNEXAMINED -- and an unexamined default is indistinguishable from a
    # correct one until someone looks. That indistinguishability is what let
    # STREHL_PHOTOMETRIC sit here misdeclared while it was worth +1415 DN.
    quality_unverified = [
        n for n in known if REGISTRY[n].kind == "quality" and REGISTRY[n].verified == "assumed"
    ]

    # ---- evidence first, verdict last. -----------------------------------
    # A verdict line must never be a script's only output. An earlier detector
    # on this project returned a confident false negative that was caught ONLY
    # because it printed its rows above the verdict; a wrong conclusion has to
    # be visible without a re-run.
    print("=" * 74)
    print("RUNTIME SWITCH AUDIT")
    print("=" * 74)

    if quality_dark:
        print("\n--- QUALITY SWITCHES DEFAULTING OFF (the defect class) ---")
        for n in quality_dark:
            d = REGISTRY[n]
            print(f"  {n}")
            print(f"      default : {d.default}")
            print(f"      code    : {d.evidence}")
            print(f"      seen at : {', '.join(found[n])}")
            print(f"      {d.note}")

    if quality_inapplicable:
        print("\n--- QUALITY SWITCHES NOT ON THE DEFAULT BACKEND (absent, not dark) ---")
        print(f"    The default backend is `{DEFAULT_BACKEND}`. These control stages")
        print("    it does not implement, so turning them on changes nothing. The")
        print("    remedy is to BUILD the stage on this backend, not to flip a flag.")
        for n in quality_inapplicable:
            d = REGISTRY[n]
            print(f"  {n}")
            print(f"      default : {d.default}   backend: {d.backend}")
            print(f"      code    : {d.evidence}")

    if quality_on:
        print("\n--- QUALITY SWITCHES REACHABLE BY DEFAULT ---")
        for n in quality_on:
            print(f"  {n:28s} default={REGISTRY[n].default:16s} {REGISTRY[n].evidence}")

    if control:
        print("\n--- CONTROL / INFRASTRUCTURE (default-off is correct) ---")
        for n in control:
            print(f"  {n:28s} default={REGISTRY[n].default:16s} {REGISTRY[n].evidence}")

    if diagnostic:
        print("\n--- DIAGNOSTIC (default-off is required) ---")
        for n in diagnostic:
            print(f"  {n:28s} {REGISTRY[n].evidence}")

    if undeclared:
        print("\n--- UNDECLARED (nobody has thought about these) ---")
        for n in undeclared:
            print(f"  {n}")
            print(f"      seen at : {', '.join(found[n])}")

    if stale:
        print("\n--- DECLARED BUT NO LONGER IN THE CODE ---")
        for n in stale:
            print(f"  {n:28s} {REGISTRY[n].evidence}")

    # ---- the partition. --------------------------------------------------
    # Every switch found lands in exactly one bucket and the buckets sum to the
    # total. A count that does not move is the same glyph whether nothing was
    # wrong or nothing was examined, so a skipped switch must never be able to
    # read as a passed one.
    total = len(found)
    partition = (
        len(quality_dark)
        + len(quality_inapplicable)
        + len(quality_on)
        + len(control)
        + len(diagnostic)
        + len(undeclared)
    )

    print("\n" + "=" * 74)
    print(f"  quality, dark (DEFECT)     {len(quality_dark):3d}")
    print(f"  quality, not on default    {len(quality_inapplicable):3d}  (absent stage, not a dark flag)")
    print(f"  quality, reachable         {len(quality_on):3d}")
    print(f"  control / infrastructure   {len(control):3d}")
    print(f"  diagnostic                 {len(diagnostic):3d}")
    print(f"  undeclared (FAIL)          {len(undeclared):3d}")
    print(f"  {'-' * 40}")
    print(f"  partition sums to          {partition:3d}")
    print(f"  switches found in crates/  {total:3d}")
    print(f"  declared but absent        {len(stale):3d}  (not counted above)")

    # ---- the SECOND partition: how well do we know these defaults? --------
    # Orthogonal to kind, and it also sums to the total, so an unchecked
    # declaration cannot be read as a checked one.
    by_v = {v: [n for n in known if REGISTRY[n].verified == v] for v in ("measured", "code", "assumed")}
    print()
    print("  how the declared defaults were established")
    print(f"    measured (ran the binary)  {len(by_v['measured']):3d}")
    print(f"    code     (read the line)   {len(by_v['code']):3d}")
    print(f"    assumed  (UNEXAMINED)      {len(by_v['assumed']):3d}")
    print(f"    {'-' * 38}")
    print(f"    sums to                    {sum(len(v) for v in by_v.values()):3d}")

    # ---- the THIRD accounting: the DOMAIN. -------------------------------
    # The two partitions above are rigorous, and both sum over `found`, which
    # is every STREHL_* env literal and nothing else. Neither one states what
    # it excluded, so a clean run has always been able to mean "I examined the
    # whole switch surface" or "I examined half of it and the half I skipped
    # is the half your defects are in" -- printing the identical glyph.
    #
    # The governing question, which cost this fleet three separate findings
    # tonight before anyone asked it: WHAT PROPERTY OF THE INPUT DECIDES
    # WHETHER THIS CHECK CAN SEE ANYTHING, AND HAVE I VARIED IT? Here that
    # property is the spelling of the switch, and varying it -- from env
    # literal to clap flag -- takes coverage from complete to half.
    declared_flags = sorted(n for n in REGISTRY if n.startswith("--"))
    unaudited = sorted(set(cli_flags) - set(declared_flags))
    print()
    print("  DOMAIN -- what this script does NOT look at")
    print(f"    env switches audited       {len(found):3d}")
    print(f"    CLI --flags declared       {len(declared_flags):3d}")
    print(f"    CLI --flags in the source  {len(cli_flags):3d}")
    print(f"    CLI --flags UNAUDITED      {len(unaudited):3d}  <- outside every count above")
    if unaudited:
        for i in range(0, len(unaudited), 4):
            print("      " + "  ".join(f"{n:22s}" for n in unaudited[i : i + 4]).rstrip())
        print("    These are not passing. They are unexamined. A dead --flag")
        print("    cannot be reported by this script in its present form.")

    if partition != total:
        print("\nFAIL: the partition does not sum to the total found.")
        print("      This script's own bookkeeping is broken; fix it before")
        print("      believing any other line it printed.")
        return 1

    rc = 0
    if undeclared:
        print(f"\nFAIL: {len(undeclared)} switch(es) are not declared in REGISTRY.")
        print("      Add each one with its kind, its default and the code that")
        print("      proves the default, then re-run. A switch nobody has")
        print("      declared is a switch nobody has decided the default for,")
        print("      and that is how three measured fixes shipped turned off.")
        rc = 1
    if quality_dark:
        print(f"\nFAIL: {len(quality_dark)} quality switch(es) default to OFF.")
        print("      Each one is a measured improvement the product does not")
        print("      apply. Either wire it on, or change its kind to 'control'")
        print("      and state in `note` why off is the right default.")
        rc = 1
    if quality_unverified:
        print(
            f"\nFAIL: {len(quality_unverified)} quality switch(es) have an "
            f"UNEXAMINED default."
        )
        for n in quality_unverified:
            print(f"      {n}")
        print("      Nobody has confirmed what the product does when these are")
        print("      unset. Read the resolving expression and set verified=")
        print("      'code', or run the binary unset vs set and compare output")
        print("      and set verified='measured'. This check exists because")
        print("      STREHL_PHOTOMETRIC was declared default='auto' here while")
        print("      the code returned Off, so it was never counted as dark.")
        rc = 1
    if rc == 0:
        print("\nPASS: every ENV switch accounted for, no quality switch dark.")
        if unaudited:
            print(
                f"      Scope: this verdict covers {len(found)} env switches and "
                f"says NOTHING about {len(unaudited)} CLI --flags."
            )
    return rc


if __name__ == "__main__":
    sys.exit(main())
