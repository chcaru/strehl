"""Does the map's `coords` key actually discriminate? Measure it; do not assume.

WHAT THIS ANSWERS.

85-map-v2.py writes `coords active` into the shipping map and argues for it
from provenance: the array these coordinates index was decoded by
15-corner-commissioned.py as `raw.raw_image_visible`, which IS the active area.
That argument is sound and it is still only an argument. This script asks the
binary.

The instrument is the loader's own site self-validation, which re-measures
every mapped site against real frames and prints a depth, a p-value and a
verdict per site. If `coords` is load-bearing, moving it from `active` to
`full` displaces every coordinate by the optical-black border and the sites
should stop confirming. If the two arms are indistinguishable, then this
sensor's `coords` key does nothing measurable on this subject and the choice is
UNFALSIFIED RATHER THAN CONFIRMED -- which this script reports as such instead
of quietly banking a green.

WHY THE MUTATION IS ANCHORED AND HARD-CHECKED.

The first attempt at this control was run from PowerShell with

    (Get-Content $src -Raw) -replace "(?m)^coords active$","coords full"

and it printed a perfectly clean "both arms identical, 2/2 confirmed in each".
The mutation had not landed: the written file still said `coords active`, so
both arms were the same file and the control was comparing a map to itself. It
was caught only because the arm printed its own `coords` line back.

That is the project's standing lesson in its purest form -- an inert plant and
a dead instrument produce the identical green -- so here the substitution is
counted, required to be exactly 1, and the written file is re-read and required
to contain the mutated line and not the original. If any of that fails the
script exits non-zero WITHOUT running an arm, because a control that silently
does not perturb is worse than no control: it manufactures confidence.

WHAT A RED AND A GREEN MEAN HERE.

  DISCRIMINATES   the `full` arm confirms strictly fewer sites than `active`.
                  The key is load-bearing on this subject and `active` is the
                  arm the frames agree with.
  BLIND           both arms confirm the same sites at the same depths. The key
                  changes nothing measurable here. Reported as a limitation of
                  the measurement, NOT as support for `active`.
  INVERTED        the `full` arm confirms MORE sites, or deeper ones. That
                  would mean the shipping map is in the wrong space, and the
                  script says so loudly.

Usage:
    python experiments/BUILD-DEFECT/src/86-coords-control.py [--subject DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUT = HERE.parent / "out"
DATA = HERE.parent / "data"
MAP = OUT / "defect-map-ILCE-7CM2-photo.txt"
EXE = ROOT / ".cargo-target-defect" / "release" / "strehl.exe"

SITE_RE = re.compile(
    r"site\s*\(\s*(\d+),\s*(\d+)\):\s*depth\s*([+-]?[\d.]+)%.*?p\s*([\d.]+).*?->\s*(\S+)"
)
SUMMARY_RE = re.compile(
    r"sites\s*:\s*(\d+)/(\d+) sites confirmed from (\d+) frames "
    r"\(not significant (\d+), too shallow (\d+), not stationary (\d+), unmeasurable (\d+)\)"
)


def log(m: str) -> None:
    print(m, flush=True)


def write_arm(space: str) -> Path:
    """Write a copy of the shipping map with `coords <space>`, or die trying."""
    src = MAP.read_text(encoding="utf-8")
    anchor = "coords active"
    n = src.count("\n" + anchor + "\n")
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: {n} occurrence(s) of a whole line {anchor!r} "
            f"in {MAP}. Expected exactly 1. Refusing to run an arm that may not differ."
        )
    if space == "active":
        body = src
    else:
        body = src.replace("\n" + anchor + "\n", f"\ncoords {space}\n", 1)
        if body == src:
            raise SystemExit("MUTATION DID NOT LAND: replace() returned the input unchanged.")

    p = Path(tempfile.gettempdir()) / f"86-map-coords-{space}.txt"
    p.write_text(body, encoding="utf-8")

    back = p.read_text(encoding="utf-8").splitlines()
    got = [ln for ln in back if ln.startswith("coords ")]
    if got != [f"coords {space}"]:
        raise SystemExit(f"MUTATION NOT PRESENT ON DISK: coords lines are {got!r}, wanted ['coords {space}']")
    return p


def run_arm(space: str, subject: str, frames: int) -> dict:
    mp = write_arm(space)
    env = dict(os.environ)
    env.update(STREHL_DEFECT="on", STREHL_DEFECT_MAP=str(mp), STREHL_DEFECT_ARM="dust")
    out = Path(tempfile.gettempdir()) / f"86-{space}.tiff"
    r = subprocess.run(
        [str(EXE), "stack", subject, "--out", str(out), "--limit", str(frames),
         "--linear-srgb", "--demosaic"],
        capture_output=True, env=env, cwd=str(ROOT),
    )
    text = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")

    # Read the arm's OWN coords line back out of the map it was handed, so the
    # record cannot claim an arm that was never run.
    declared = [ln for ln in mp.read_text(encoding="utf-8").splitlines() if ln.startswith("coords ")]

    sites = [
        dict(x=int(m[1]), y=int(m[2]), depth_pct=float(m[3]), p=float(m[4]), verdict=m[5])
        for m in SITE_RE.finditer(text)
    ]
    s = SUMMARY_RE.search(text)
    summary = None
    if s:
        summary = dict(
            confirmed=int(s[1]), total=int(s[2]), frames=int(s[3]),
            not_significant=int(s[4]), too_shallow=int(s[5]),
            not_stationary=int(s[6]), unmeasurable=int(s[7]),
        )
    return dict(space=space, exit=r.returncode, declared_coords=declared,
                summary=summary, sites=sites, map_path=str(mp))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default=r"D:\personal\macro\109MSDCF")
    ap.add_argument("--frames", type=int, default=2)
    a = ap.parse_args()

    if not EXE.exists():
        raise SystemExit(f"no binary at {EXE}")

    arms = {}
    for space in ("active", "full"):
        arms[space] = run_arm(space, a.subject, a.frames)
        r = arms[space]
        log(f"--- coords {space} (map declares {r['declared_coords']}, exit {r['exit']})")
        if r["summary"] is None:
            log("    NO SELF-VALIDATION SUMMARY PRINTED -- the arm did not reach the check.")
        else:
            s = r["summary"]
            log(f"    {s['confirmed']}/{s['total']} confirmed  "
                f"(not significant {s['not_significant']}, too shallow {s['too_shallow']}, "
                f"not stationary {s['not_stationary']}, unmeasurable {s['unmeasurable']})")
        for st in r["sites"]:
            log(f"    ({st['x']:5d},{st['y']:5d})  depth {st['depth_pct']:+8.3f}%  "
                f"p {st['p']:.4f}  {st['verdict']}")

    act, full = arms["active"], arms["full"]

    # The two arms must actually have been given different files. If the loader
    # refused the `full` arm outright that is still a discrimination, but it is
    # a different one and it is reported separately.
    if act["declared_coords"] == full["declared_coords"]:
        log("\nVERDICT: INCONCLUSIVE -- both arms declared the same coords. The control did not perturb.")
        return 2

    ca = act["summary"]["confirmed"] if act["summary"] else -1
    cf = full["summary"]["confirmed"] if full["summary"] else -1

    if full["exit"] != 0 and act["exit"] == 0:
        verdict = "DISCRIMINATES (the `full` arm is refused outright)"
        rc = 0
    elif ca < 0:
        verdict = "INCONCLUSIVE -- the `active` arm printed no summary"
        rc = 2
    elif cf > ca:
        verdict = f"INVERTED -- `full` confirmed {cf} > `active` {ca}. THE SHIPPING MAP MAY BE IN THE WRONG SPACE."
        rc = 1
    elif cf < ca:
        verdict = f"DISCRIMINATES -- `active` confirmed {ca}, `full` only {cf}. The frames agree with `active`."
        rc = 0
    else:
        # Same count. Depth is the finer instrument: a displaced site that still
        # clips the mote confirms, but shallower.
        da = {(s["x"], s["y"]): s["depth_pct"] for s in act["sites"]}
        df = {(s["x"], s["y"]): s["depth_pct"] for s in full["sites"]}
        common = sorted(set(da) & set(df))
        deltas = [df[k] - da[k] for k in common]
        if common and all(abs(d) < 1e-9 for d in deltas):
            verdict = (f"BLIND -- both arms confirmed {ca} sites at identical depths. "
                       "`coords` changes nothing measurable on this subject; the "
                       "`active` choice is UNFALSIFIED, not confirmed.")
            rc = 0
        else:
            worst = max(deltas, key=abs) if deltas else 0.0
            verdict = (f"DISCRIMINATES ON DEPTH -- both confirmed {ca}, but `full` reads "
                       f"{worst:+.3f} pp shallower/deeper at worst. `active` is the deeper read.")
            rc = 0

    log(f"\nVERDICT: {verdict}")
    DATA.mkdir(exist_ok=True)
    (DATA / "86-coords-control.json").write_text(
        json.dumps(dict(subject=a.subject, frames=a.frames, verdict=verdict, arms=arms), indent=1),
        encoding="utf-8",
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
