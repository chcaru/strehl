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


REGISTRY: dict[str, Declared] = {
    # ---------------- quality ----------------
    "STREHL_FIX_CA": Declared(
        kind="quality",
        default="off",
        evidence="optics.rs:470 (CA_ENV); main.rs:183-185,619 (--fix-ca)",
        note=(
            "Lateral-CA correction. Removes 61-67% of corner colour fringing "
            "(b914f31, R^2=0.9969) and 0.363px -> 0.059px of blue displacement "
            "(283ccf4). THE ORIGINAL DARK FEATURE. Being made default-on behind "
            "the EXIF gear guard by BUILD-RENDER."
        ),
    ),
    "STREHL_PHOTOMETRIC": Declared(
        kind="quality",
        default="off",
        verified="code",
        evidence="merge_cmd.rs:1965 (`_ => Ok(PhotometricMode::Off)`); "
        "main.rs:325-354,648-650 (--photometric)",
        note=(
            "Per-frame affine photometric normalisation. Three-valued "
            "off|on|auto; the flag wins over the env var and 'neither can mean "
            "ON by accident'. THE DEFAULT IS OFF, not 'auto' as this entry "
            "first claimed. "
            "Off is DEFENDED, not neglected: M122 ran a pre-registered "
            "14-stack promotion test and returned KEEP-OFF on its no-harm "
            "criterion K2, whose worst harm subject was flower-bud-alone-cpl "
            "(hf1-on-hf0 slope 0.9444). M125 then built `auto` and honestly "
            "declined to promote it -- 104% of its margin is one stack, and "
            "AUTO_FRAMES_DOMAIN=33..=100 makes it ABSTAIN (U1) on our 205- and "
            "299-frame stacks, so `auto` cannot help this corpus at all. "
            "OPEN AND CONTESTED: a verifier measured `on` recovering +1415 DN "
            "of aura on flower-bud-alone-cpl -- M122's own worst-harm subject. "
            "Both cannot be right about the same pixels. V-TONE is testing "
            "H-SEAM: that M122's 'lost fine structure' is election-seam step "
            "edges, i.e. the artifact, which an energy statistic with no "
            "spatial argument cannot distinguish from signal. Revisit this "
            "default when that lands."
        ),
    ),
    "STREHL_EDGE_AWARE": Declared(
        kind="quality",
        default="on",
        evidence="merge_cmd.rs:1241; GUIDE_RADIUS at merge_cmd.rs:1256",
        note=(
            "Adaptive-radius edge handling. Reported default-ON at pin-859edac. "
            "The shipped merge's winner field has its depth step displaced "
            "outward by exactly one window radius, and that displacement IS the "
            "halo."
        ),
    ),
    "STREHL_EDGE_TAU": Declared(
        kind="quality",
        default="built-in",
        evidence="merge_cmd.rs:1243",
        note="Depth-step tolerance override, in frames. Unset uses edge_tau().",
    ),
    "STREHL_EDGE_CONF": Declared(
        kind="quality",
        default="2.0",
        evidence="merge_cmd.rs:1246",
        note="Confidence veto, in multiples of the plane's low-percentile guide response.",
    ),
    "STREHL_EDGE_FEATHER": Declared(
        kind="quality",
        default="built-in",
        evidence="edgeaware.rs:779",
        note="Feather width for the edge-aware support.",
    ),
    "STREHL_FIX_HALO": Declared(
        kind="quality",
        default="off",
        evidence="merge_cmd/halo.rs:69 (FIX_ENV), :71 (DELTA_ENV)",
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
        evidence="focus.rs:101 (WINDOW_RADIUS_ENV)",
        note="Focus-measure window radius. Unset uses the shipped WINDOW_RADIUS=13.",
    ),
    "STREHL_MERGE": Declared(
        kind="quality",
        default="estimator",
        verified="measured",
        evidence="merge_cmd.rs (MERGE_BACKEND_ENV, resolve_merge_backend, "
        "DEFAULT_MERGE_BACKEND = MergeBackend::Estimator); "
        "main.rs (--merge, and the wrong-backend refusal table)",
        note=(
            "WHICH MERGE PRODUCES THE PIXELS. `estimator` or `pyramid`, and an "
            "unrecognised value is a hard error in BOTH the flag and the env "
            "channel -- neither can mean a backend by accident. The default is "
            "the estimator, unchanged, and `--merge estimator` is byte-"
            "identical to the pre-switch binary on all three write branches; "
            "the byte-freeze registry reproduces both of its recorded hashes "
            "twice each through this switch. "
            "THIS IS NOT A DARK QUALITY SWITCH, and the distinction matters "
            "for this script's purpose. `pyramid` is 1898 lines that no "
            "shipped binary could reach at all until it was wired -- every "
            "good render in the corpus came from it through an EXAMPLE. It is "
            "now reachable, and it is unselected on a measurement rather than "
            "by neglect: it wins micro-contrast on every subject tested (+35% "
            "to +192%) and wins acuity on this binary, but it hard-clips "
            "1.6777% and 2.9920% of pixels on dry-erase-marker-head-cpl and "
            "flower-bud-alone-cpl where the estimator clips 0.0009% and "
            "0.0006%, and ORCH measured p1 collapsing 8431 -> 110 on the fern "
            "subject. It fails the acceptance gate, so it does not get the "
            "default. BUILD-BLEND's clamp fix in pyramid.rs targets exactly "
            "that clipping; when its gate table passes, DEFAULT_MERGE_BACKEND "
            "is the one line that moves. MEASURED: unset, `strehl stack "
            "--srgb` on flower-bud-alone-cpl reproduces the pre-switch bytes; "
            "`--merge pyramid` emits sha256 F8A49C0A..., a different image on "
            "99.9895% of pixels at a mean of 1820 DN."
        ),
    ),
    # ---------------- control ----------------
    "STREHL_SOFT_GATE": Declared(
        kind="control",
        default="off",
        evidence="merge.rs:457-465 (SOFT_GATE_ENV)",
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
        default="off",
        evidence="merge.rs:633 (ROBUST_ENV); arm_from_setting at :635",
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
        default="off",
        evidence="align_cmd.rs:928 (ALIGN_ENV)",
        note="Selects the alignment arm.",
    ),
    "STREHL_SMOOTH": Declared(
        kind="control",
        default="built-in",
        evidence="align_cmd.rs:585",
        note="Warp-field smoothness lambda override.",
    ),
    "STREHL_SMOOTH_HUBER": Declared(
        kind="control",
        default="built-in",
        evidence="align_cmd.rs:603",
        note="Huber threshold, in pixels, for the smoothness term.",
    ),
    "STREHL_CACHE_DIR": Declared(
        kind="control",
        default="platform default",
        evidence="align_cmd.rs:1058",
        note="Alignment sidecar cache location. Infrastructure, not quality.",
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
        evidence="tests/byte-freeze.rs:656",
        note="Points the byte-freeze net at the corpus. Test infrastructure.",
    ),
    "STREHL_FREEZE_REQUIRE": Declared(
        kind="control",
        default="unset",
        evidence="tests/byte-freeze.rs:717",
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
        evidence="merge_cmd.rs:1258 (ONLY_FRAME_ENV)",
        note=(
            "Renders one frame with no election. TRAP: it changes the digest, so "
            "the alignment sidecar is rejected and alignment re-solves."
        ),
    ),
    "STREHL_DUMP_ELECTION": Declared(
        kind="diagnostic",
        default="off",
        evidence="merge_cmd.rs:1839 (ELECTION_ENV)",
        note=(
            "Dumps the pass-one winner field. The elected frame index IS a depth "
            "ordering, which is what BUILD-HALO's depth-coherence silhouette is "
            "built on (017e7c6). Also available as --election-map."
        ),
    ),
    "STREHL_DUMP_NEFF": Declared(
        kind="diagnostic",
        default="off",
        evidence="merge_cmd.rs:1919 (NEFF_ENV)",
        note="Dumps the n_eff map. Env twin of a flag.",
    ),
    "STREHL_DUMP_MERGE_STATE": Declared(
        kind="diagnostic",
        default="off",
        evidence="merge_cmd/dump.rs:42 (DUMP_ENV)",
        note="Dumps merge internals.",
    ),
    "STREHL_BIMODAL_DUMP": Declared(
        kind="diagnostic",
        default="off",
        evidence="merge_cmd.rs:1443 (BIMODAL_DUMP_ENV)",
        note="Dumps the through-focus bimodality statistic.",
    ),
    "STREHL_WARPMAP": Declared(
        kind="diagnostic",
        default="off",
        evidence="merge_cmd.rs:1773 (WARPMAP_ENV)",
        note="Dumps the per-frame warp field.",
    ),
    "STREHL_FIX_HALO_DELTA": Declared(
        kind="diagnostic",
        default="off",
        evidence="merge_cmd/halo.rs:71 (DELTA_ENV)",
        note="Writes the halo correction's delta image, for inspection.",
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


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    crates = root / "crates"
    if not crates.is_dir():
        print(f"FAIL: no crates/ under {root}", file=sys.stderr)
        return 1

    found = find_switches(crates)

    undeclared = sorted(set(found) - set(REGISTRY))
    stale = sorted(set(REGISTRY) - set(found))
    known = sorted(set(found) & set(REGISTRY))

    quality_dark = [
        n for n in known if REGISTRY[n].kind == "quality" and REGISTRY[n].default == "off"
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
    partition = len(quality_dark) + len(quality_on) + len(control) + len(diagnostic) + len(undeclared)

    print("\n" + "=" * 74)
    print(f"  quality, dark (DEFECT)     {len(quality_dark):3d}")
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
        print("\nPASS: every switch accounted for, no quality switch dark.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
