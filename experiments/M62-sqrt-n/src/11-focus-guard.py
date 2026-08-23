"""The guard my own battery cannot supply: is the merge still a focus merge?

**A static burst is degenerate for focus.** Every frame is in focus, so the
correct gate behaviour on my plant is to admit everything -- which means a merge
that admits everything *unconditionally* scores exactly sqrt(N) on the sqrt(N)
battery and is, on a real stack, not a focus stacker at all.

That failure mode is invisible to `10-acceptance.py` by construction. This is the
arm that sees it: run the binary over a **real through-focus stack** from the
corpus and read the `n_eff` the CLI reports for itself. On a real stack the
frames disagree about focus, so a merge that still selects will report `n_eff`
materially below `N`, and a merge that has stopped selecting will report `n_eff`
at or near `N`.

No truth is available on a real stack, so nothing here is scored against one.
The observable is the binary's own `mean n_eff`, plus the spread across the gate
ladder it chooses to print. That is a statement about the operator's behaviour,
not about its accuracy.

Corpus is READ-ONLY.

    python src/11-focus-guard.py [--exe path] [--src path] [--tag name]
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

STACK = pathlib.Path(r"D:\personal\macro\109MSDCF")
EXPECTED_FRAMES = 22  # AGENTS.md corpus table; discipline 388


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe")
    ap.add_argument("--src")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--stack", default=str(STACK))
    ap.add_argument("--frames", type=int, default=EXPECTED_FRAMES)
    a = ap.parse_args()
    if a.exe:
        os.environ["STREHL_BIN"] = a.exe
    if a.src:
        os.environ["STREHL_SRC"] = a.src

    stack = pathlib.Path(a.stack)
    got = len(list(stack.glob("*.ARW")))
    assert got == a.frames, f"{stack}: {got} frames, expected {a.frames}"

    txt = H.run_cli(["merge", str(stack)], H.EVID / f"11-focus-guard-{a.tag}.log", check=False)
    assert txt is not None, f"binary refused `merge {stack}` -- see out/11-focus-guard-{a.tag}.log"

    rows = re.findall(
        r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$",
        txt, re.M)
    ladder = [dict(gate=float(g), tolerance=float(t), mean_n_eff=float(ne),
                   n_eff_1_pct=float(p1), boundary_pct=float(bp),
                   pred_sigma_gain=float(sg), n_eff_over_N=float(ne) / a.frames)
              for g, t, ne, p1, bp, sg in rows]
    assert ladder, "no gate calibration rows found; the CLI's report format changed"

    rec = dict(
        stack=str(stack), frames=a.frames, tag=a.tag,
        provenance=H.provenance(),
        ladder=ladder,
        min_n_eff_over_N=min(r["n_eff_over_N"] for r in ladder),
        max_n_eff_over_N=max(r["n_eff_over_N"] for r in ladder),
        selects_somewhere=any(r["n_eff_over_N"] < 0.95 for r in ladder),
        note="observable only. A merge that reports n_eff/N >= 0.95 at EVERY gate "
             "it offers has stopped discriminating focus on a real stack, and the "
             "sqrt(N) battery cannot see that.",
    )
    H.dump(f"11-focus-guard-{a.tag}.json", rec)


if __name__ == "__main__":
    main()
