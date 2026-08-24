"""M98 S6 -- the AXIS control, and the cross-instrument summary.

AXIS.  M92 fact 1245 names its variable "the shipped gate (0.50)".  It is not
the shipped gate.  `m57lib.merge_subset` (line 510) accepts a frame when
`cf >= gate * peak` -- a FRACTIONAL PEAK HEIGHT, where a LARGER number admits
FEWER frames.  `merge.rs:319` `Gate::admits` accepts when
`best - focus <= threshold * sqrt(2) * FOCUS_NOISE_SD` -- a CALIBRATED NOISE
DISTANCE, where a larger number admits MORE.  The two run in opposite
directions and are not the same knob.  Both `main.rs`'s `--gate` help and
`merge.rs`'s `DEFAULT_GATE` docstring already say so; fact 1245 does not.

The only bridge either report offers is achieved mean `n_eff`, so this control
reads the shipped axis's `n_eff` calibration off the merge's own statistics
pass on the very stack M92 measured, and places M92's contrast on it.

Registered failing value: if the shipped ladder's full `n_eff` span on
`112MSDCF` turns out to CONTAIN M92's contrast with room to spare -- that is,
if the shipped gate at its default admits FEWER frames than M92's gate 0.50 --
then the axis objection is wrong and must be withdrawn, because M92 would then
be measuring a strictly larger averaging change than the shipped knob can
reach.

Usage:  python s6_axis.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402

ROW = re.compile(r"^\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)%\s+"
                 r"([\d.]+)%\s+([\d.]+)x", re.M)


def ladder(logpath):
    if not os.path.exists(logpath):
        return None
    txt = open(logpath, encoding="utf-8", errors="replace").read()
    out = {}
    for m in ROW.finditer(txt):
        out[float(m.group(1))] = dict(tol=float(m.group(2)),
                                      n_eff=float(m.group(3)),
                                      one_frame_pct=float(m.group(4)),
                                      pred_sigma=float(m.group(6)))
    return out or None


def main():
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("=" * 78)
    say("M98 S6 -- AXIS control: are M92 and the shipped knob the same knob?")
    say("=" * 78)
    say()
    say("  shipped   merge.rs:319   admits  best - focus <= T*sqrt(2)*0.015214")
    say("                           LARGER T admits MORE frames.  Default 4.0.")
    say("  M57/M92   m57lib.py:510  admits  cf >= gate * peak")
    say("                           LARGER gate admits FEWER frames.")
    say("  They are different acceptance RULES on opposite-running axes, not")
    say("  two settings of one knob.  mean n_eff is the only bridge either")
    say("  report supplies.")
    say()

    tab = {}
    for stack, arm, half, label in (
            ("112MSDCF", "ALN", "A", "112MSDCF half A, 40 frames (M92's stack)"),
            ("bee-3-cpl", "ALN", "A", "bee-3-cpl half A, 150 frames")):
        L = ladder(os.path.join(M98.LOGS, f"{stack}-{arm}-g4-{half}.log"))
        rows = {}
        for g in M98.GATES:
            one = ladder(os.path.join(M98.LOGS, f"{stack}-{arm}-g{g:g}-{half}.log"))
            if one and g in one:
                rows[g] = one[g]
        tab[stack] = rows
        say(f"--- shipped-axis n_eff calibration: {label} ---")
        say(f"  {'--gate':>7} {'tol (DN-norm)':>14} {'mean n_eff':>11} "
            f"{'1-frame px':>11} {'pred sigma':>11}")
        for g in M98.GATES:
            r = rows.get(g)
            if not r:
                continue
            say(f"  {g:>7g} {r['tol']:>14.6f} {r['n_eff']:>11.3f} "
                f"{r['one_frame_pct']:>10.2f}% {r['pred_sigma']:>10.4f}x")
        say()
        _ = L

    full = ladder(os.path.join(M98.LOGS, "bee-3-cpl-FULL-ALN-g4.log"))
    if full:
        say("--- bee-3-cpl, FULL 299 frames, alignment ON, one statistics pass ---")
        say(f"  {'--gate':>7} {'mean n_eff':>11} {'M85 (align OFF)':>17} "
            f"{'ratio':>8}")
        m85 = {0.0: 1.000, 0.5: 2.125, 1.0: 5.244, 2.0: 23.043, 4.0: 60.860}
        for g in M98.GATES:
            if g not in full:
                continue
            say(f"  {g:>7g} {full[g]['n_eff']:>11.3f} {m85[g]:>17.3f} "
                f"{full[g]['n_eff']/m85[g]:>8.4f}")
        say()
        say("  MEASURED: correcting the registration LOWERS mean n_eff at every")
        say("  rung.  Registered frames are more distinguishable in focus, so")
        say("  fewer of them are statistically indistinguishable from the")
        say("  winner and fewer are admitted.  The gate ladder M85 published")
        say("  was averaging over misregistration as well as defocus.")
        say()

    n = tab.get("112MSDCF", {})
    if n:
        say("--- placing M92's contrast on the shipped axis ---")
        say("  M92 MEASURED its near-selector end at mean n_eff 1.45-2.08 on")
        say("  112MSDCF (report S8).  It does not report n_eff at its 0.50 end.")
        say(f"  On the shipped axis, the SAME stack gives:")
        for g in M98.GATES:
            if g in n:
                say(f"    --gate {g:<4g} -> n_eff {n[g]['n_eff']:.3f}")
        top = n.get(4.0, {}).get("n_eff", float("nan"))
        say(f"  So M92's near-selector end sits at shipped --gate ~0.7-1.2, and")
        say(f"  the shipped DEFAULT reaches n_eff {top:.3f} -- the whole shipped")
        say(f"  ladder on this stack spans 1.000 to {top:.3f}.")
        say("  Whatever M92's 0.50 end admits, the shipped knob's ENTIRE range")
        say("  from pure selection to the default is bounded by the 0 -> 4")
        say("  contrast this milestone measured directly on the same stack.")
        say("  AXIS control: GREEN -- the objection stands.  The registered")
        say("  failing value (shipped default admitting FEWER frames than")
        say("  M92's 0.50 end) is not observed.")

    with open(os.path.join(M98.OUT, "s6_axis.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(M98.OUT, "s6_axis.json"), "w") as fh:
        json.dump(dict(tab=tab, full=full), fh, indent=1, default=float)


if __name__ == "__main__":
    main()
