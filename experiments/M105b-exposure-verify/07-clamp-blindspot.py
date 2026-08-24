"""
07-clamp-blindspot.py -- why the positive control failed, derived then checked.

06-reconcile-targets.py's positive control FAILED: my post-file
reimplementation of the shipped rule gave +1.53 against M100's published +1.54
on `bee-3-cpl` (1 quantum) but -0.14 against -0.18 on `coffee-bean`
(4 quanta). Pre-registration said that voids the decomposition. Before
discarding it I want to know WHY, because the pattern is not random: it is
tiny on the stack that needs BRIGHTENING and large on the stack that needs
DARKENING.

MECHANISM, read at source (`merge_cmd.rs`, the `choose` closure ~2804-2818,
and the pipeline order in `image_out.rs`):

    linear camera RGB --> display_luminance(rgb, matrix) --> p99.9 --> gain
                                                                       |
    ... then, in image_out:  x gain  ->  matrix  ->  CLAMP [0,1]  ->  sRGB curve

  The chooser reads luminance BEFORE the clamp. The emitted TIF is written
  AFTER it. So any luminance above 1.0 is visible to the chooser and is
  destroyed in the file.

PREDICTION, derived before measuring, purely from the shipped rule's own
definition (gain = 0.90 / p99.9, so p99.9 = 0.90 * 2^stops):

    stack        published stops   implied chooser p99.9   above 1.0?
    bee-3-cpl        +1.54              0.90*2^-1.54          NO
    coffee-bean      -0.18              0.90*2^+0.18          YES

  If the implied p99.9 exceeds 1.0, the clamp has removed the very samples the
  chooser used, and NO post-file recomputation can recover the published
  number. The error should then be one-sided: my post-file estimate must read
  BRIGHTER (less negative) than the truth, never darker.

  FALSIFIED IF: coffee-bean's implied p99.9 is below 1.0 (then the clamp is
  not the mechanism and my reimplementation is simply wrong), or if my
  measured error on it is in the darker direction.

  CONTROL: `bee-3-cpl`'s implied p99.9 must be well below 1.0, and its error
  must be within one quantum. A mechanism that also "explains" the stack it
  should not touch explains nothing.
"""

import json
import os

import numpy as np

OUT = r"C:\dev\strehl-out\M105"

# The shipped rule's definition. gain = TARGET / p99.9 (color.rs), and
# gain = 2^stops, so the percentile the chooser saw is TARGET / 2^stops.
#
# I FIRST WROTE THIS AS `TARGET * 2**stops` AND MY OWN CONTROL CAUGHT IT: the
# run reported `CONTROL_bee3_below_clamp: FAIL` with an implied percentile of
# 2.617 for a stack that is 1.54 stops too DARK. A dark image cannot have a
# percentile of 2.6. The control was registered as "a mechanism that also
# explains the stack it should not touch explains nothing", and it fired
# against the arithmetic rather than the mechanism. Both runs are kept:
# 07-clamp-blindspot-SIGNERROR.json is the wrong one.
TARGET = 0.90

# From M100-exposure.md SS3.4, read from the report.
PUBLISHED = {"bee-3-cpl": 1.54, "coffee-bean": -0.18, "foam": -0.32,
             "lead-1-cpl": 3.74, "flat-on-ruler": 1.96,
             "highly-angled-ruler": 1.19, "bee-2-cpl": 1.54}

# What my post-file reimplementation measured in 06-reconcile-targets.py.
MINE = {"bee-3-cpl": 1.53, "coffee-bean": -0.14}


def main():
    rows = []
    for stack, stops in sorted(PUBLISHED.items(), key=lambda kv: -kv[1]):
        implied = TARGET / (2.0 ** stops)
        row = {
            "stack": stack,
            "published_stops": stops,
            "implied_chooser_p99_9": round(implied, 6),
            "above_clamp": bool(implied > 1.0),
        }
        if stack in MINE:
            err = MINE[stack] - stops
            row["my_post_file_stops"] = MINE[stack]
            row["error_stops"] = round(err, 4)
            row["error_direction"] = ("BRIGHTER than truth" if err > 0
                                      else "darker than truth" if err < 0 else "exact")
        rows.append(row)

    cb = next(r for r in rows if r["stack"] == "coffee-bean")
    bee = next(r for r in rows if r["stack"] == "bee-3-cpl")

    readings = {
        "PREDICTION_coffee_bean_above_clamp": (
            "CONFIRMED" if cb["above_clamp"] else "FALSIFIED"
        ),
        "PREDICTION_error_is_one_sided_brighter": (
            "CONFIRMED" if cb["error_stops"] > 0 else "FALSIFIED"
        ),
        "CONTROL_bee3_below_clamp": (
            "PASS" if not bee["above_clamp"] else "FAIL"
        ),
        "CONTROL_bee3_within_one_quantum": (
            "PASS" if abs(bee["error_stops"]) <= 0.01 else "FAIL"
        ),
        "n_published_stacks_above_clamp": sum(1 for r in rows if r["above_clamp"]),
        "n_published_stacks": len(rows),
    }

    # Which stacks can a post-file instrument measure at all?
    readings["post_file_instrument_is_valid_for"] = [
        r["stack"] for r in rows if not r["above_clamp"]
    ]
    readings["post_file_instrument_is_BLIND_for"] = [
        r["stack"] for r in rows if r["above_clamp"]
    ]

    result = {"rows": rows, "readings": readings}
    dst = os.path.join(OUT, "07-clamp-blindspot.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("%-22s %8s %12s %8s %10s" %
          ("stack", "stops", "implied p999", ">1.0?", "my error"))
    for r in rows:
        print("%-22s %+8.2f %12.6f %8s %10s" %
              (r["stack"], r["published_stops"], r["implied_chooser_p99_9"],
               "YES" if r["above_clamp"] else "no",
               ("%+.2f" % r["error_stops"]) if "error_stops" in r else "--"))
    print("")
    print(json.dumps(readings, indent=2))
    print("wrote " + dst)


if __name__ == "__main__":
    main()
