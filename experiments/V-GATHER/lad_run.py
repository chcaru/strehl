r"""The exponent ladder: make the merge the independent variable.

THE EXPERIMENT. The claim under test is that the merge's SELECTION LAW is what
manufactures detail the input frames do not contain. That claim has so far been
supported two ways, neither of which is an experiment: `stack.rs:11` names the
mechanism, which is an argument about code, and 13 of 19 subjects exceed their
own focus ceiling, which is an observation about pixels. Neither varies the
merge. This does.

--pyramid-sharpen 1.0 disables the per-octave ramp, so --pyramid-exponent is a
single global exponent at every band and the arm is unambiguous. The pin prints
`per-band exp : 1 1 1 1 1 1 1` for exponent 1 and `16 16 16 16 16 16 16` for 16,
and that line is CAPTURED PER ARM as provenance rather than assumed.

THE PREDICTION, AND WHAT WOULD REFUTE IT. If the selection law is the mechanism,
ceiling excess should rise with the exponent and approach zero near exponent 1.
If excess is flat across a 16x range, or large at exponent 1, the selection law
is not the mechanism.

ONE CAVEAT ON THE PREDICTION'S STATED REASON, WHICH DOES NOT WEAKEN THE TEST.
The reason offered for expecting zero at exponent 1 is that the output is then a
convex combination of the inputs and so cannot leave their hull. The pin's own
run log says selection is `SOFT -- a convex combination` AT EVERY EXPONENT, not
only at 1, so convexity per se does not separate the arms. It also does not
imply the hull property for this measurand: the weights are per band
coefficient and therefore SPATIALLY VARYING, and a spatially varying convex
combination is not a convex combination of the images. A bandpass contrast can
exceed every input's under it. The empirical prediction -- monotone rise, small
at 1 -- is unaffected and is what is tested here.

FROZEN. Sites and ceilings come from sharp.json and never move; lad_probe.py
showed a source frame is byte-identical at exponent 1 and 16, so the ceiling is
not a function of the variable under test. Registration between arms is
MEASURED, not assumed.
"""
import io
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import lad_measure as lm                                           # noqa: E402

OUT = os.path.join(HERE, "ladder.json")
LAD = lm.LAD
ARMS = [("default", None, None), ("e1", 1, 1.0), ("e2", 2, 1.0),
        ("e4", 4, 1.0), ("e8", 8, 1.0), ("e16", 16, 1.0)]
# Cheapest first, so the ladder's shape is readable before the deep stacks land.
SUBJECTS = ["coffee-bubbles", "109MSDCF", "119MSDCF", "112MSDCF", "foam",
            "wrapped-text-1", "leaf-2-cpl", "flower-inner-edge-cpl",
            "pencil-steep-angle-cpl"]


def render(sub, out, exponent, sharpen):
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = os.path.join(LAD, "cache-" + sub)
    os.makedirs(env["STREHL_CACHE_DIR"], exist_ok=True)
    for v in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU",
              "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME"):
        env.pop(v, None)
    cmd = [cm.EXE, "stack", os.path.join(cm.RAW, sub), "--out", out,
           "--linear-srgb", "--demosaic"]
    if exponent is not None:
        cmd += ["--pyramid-exponent", str(exponent), "--pyramid-sharpen", str(sharpen)]
    t = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    dt = time.time() - t
    if p.returncode != 0 or not os.path.exists(out):
        # The tail of stderr is INFORMATIONAL on this tool -- it prints a
        # coverage and memory plan on every run -- so slicing the tail reports
        # the run log rather than the cause. Measured: a 112MSDCF e1 arm was
        # recorded as "RENDER FAILED d of view scaled to 0.9765...", which is a
        # progress line. Keep the exit code and the lines that actually name a
        # failure, and say when none was found.
        tail = (p.stderr or "").splitlines()
        hot = [l for l in tail if any(w in l.lower() for w in
                                      ("error", "panic", "failed", "refus",
                                       "cannot", "unable", "budget", "memory"))]
        why = ("exit=%d out_exists=%s | %s"
               % (p.returncode, os.path.exists(out),
                  " || ".join(hot[-4:]) if hot else "(no line named a failure)"))
        return None, why, dt
    both = (p.stdout or "") + "\n" + (p.stderr or "")
    line = ""
    for l in both.splitlines():
        if "per-band exp" in l:
            line = l.split(":", 1)[1].strip()
            break
    return line, "", dt


def do_subject(sub, doc):
    sites, rec = lm.frozen_sites(sub)
    if not sites:
        doc[sub] = {"refused": "no frozen sites in sharp.json"}
        return
    entry = {"n_sites": len(sites), "converged_ceiling": bool(sites[0]["converged"]),
             "arms": {}}
    ref_lum = None
    for tag, e, s in ARMS:
        p = os.path.join(LAD, "%s-%s.tiff" % (sub, tag))
        line, err, dt = render(sub, p, e, s)
        if line is None:
            entry["arms"][tag] = {"refused": "render failed: %s" % err.strip()[:400]}
            print("    %-8s RENDER FAILED :: %s" % (tag, err.strip()[:220]))
            continue
        ml, lat = lm.load_lum(p)
        rows = lm.measure_array(ml, sites)
        summ = lm.summarise(rows)
        a = {"per_band_exp": line, "seconds": round(dt, 1), "lattice": list(lat)}
        a.update(summ)
        if tag == "default":
            ref_lum = ml
            # SELF-CONSISTENCY: this measurement must reproduce the band value
            # sharp.json recorded for the shipping master at the same sites.
            got = [r.get("master") for r in rows if lm.finite(r.get("master"))]
            wantv = [s2["master_ref"] for s2 in sites]
            if got and len(got) == len(wantv):
                d = max(abs(g - w) / w for g, w in zip(got, wantv) if w > 0)
                a["reproduces_sharp_json_maxrel"] = float(d)
        else:
            a["shift_bad"] = lm.arm_shifts(ref_lum, ml, sites)
            del ml
        entry["arms"][tag] = a
        os.remove(p)
        m = summ["median"]
        print("    %-8s exp[%s] n=%2d  median excess %s  p90 %s  (%.0fs)"
              % (tag, line, summ["n"],
                 ("%+8.3f%%" % (100 * m)) if lm.finite(m) else "   REFUSED",
                 ("%+8.3f%%" % (100 * summ["p90"])) if lm.finite(summ["p90"]) else "  --",
                 dt))
        doc[sub] = entry
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    doc[sub] = entry


def main():
    cm.check_binary()
    os.makedirs(LAD, exist_ok=True)
    doc = {}
    if os.path.exists(OUT):
        doc = json.load(io.open(OUT, encoding="utf-8"))
    only = sys.argv[1:] or SUBJECTS
    for sub in SUBJECTS:
        if sub not in only:
            continue
        if sub in doc and len(doc[sub].get("arms", {})) == len(ARMS):
            print("  %-26s already complete" % sub)
            continue
        print("\n== %s" % sub)
        do_subject(sub, doc)
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()

