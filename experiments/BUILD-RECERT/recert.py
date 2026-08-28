"""BUILD-RECERT: one entry point that certifies a candidate strehl.exe.

    python recert.py --candidate <path-to-strehl.exe> --arm RECERT-<name>

WHAT IT IS FOR
--------------
Promoting a new binary currently means re-rendering 26 masters, re-running the
print gate, re-running the head-to-heads and updating the README by hand. If
that takes hours the fix lane can afford one attempt. This makes it one command
and one verdict, so that promotion is a DECISION and not an interpretation.

THE PROPERTY THAT MATTERS MOST
------------------------------
Every noise number is paired with a structure number on the SAME PIXELS, in the
SAME BAND, and the two are never averaged. The fix now being built can win every
blotch number by blurring, and a shipping tool has already taken that trade:
`focus-stack` reads sigma_hp 0.077 and sigma_mid 0.260 on
`119MSDCF__worst-on-subject`, 10-25x below both other arms, and it is the arm
that resolves 1.326x LESS than we do. It wins the noise table by being blurred.
`recertlib.classify` therefore reports BLUR_TRADE, and a BLUR_TRADE is not a win.
The measurement is commissioned in `commission_bands.py` against a planted
degradation AND a planted improvement; that file must exit 0 before this one is
trusted, and this one refuses to run if it has not been run.

WHAT IT DOES NOT DO
-------------------
It does not re-adjudicate an expired acquittal. Nine of the 26 masters PASS the
print gate on an ACQUITTAL pinned to a measured number, which EXPIRES when the
render moves more than 5%. All six subjects convicted of mid-scale mottle are
inside those nine. So the gate cannot certify the very subjects the fix targets:
a candidate that changes them at all will expire their acquittals by
construction. That is reported explicitly rather than absorbed, because an
expired acquittal is not a pass and must not be read as one.

STAGES  (--stages to run a subset; each is timed and the total is the number
         that decides how many attempts the fix lane can afford)
  identity  hash the candidate, refuse the known-mislabelled binary
  render    26 masters via scripts/finalpass.ps1 -- reused, not reimplemented,
            so provenance and seals are written exactly as the shipped masters'
  gate      experiments/ORCH-drift-check/orch_printready.py, called through its
            own entry point so it may gain checks without this file changing
  pair      the band-separated noise+structure pairing, candidate vs baseline,
            on all 26 subjects
  h2h       the same pairing against `enfuse` and `focus-stack`
  verdict   one line, plus recert.json
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recertlib import BANDS, classify, display_crop, measure_crop  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FINALPASS = REPO / "scripts" / "finalpass.ps1"
GATE = REPO / "experiments" / "ORCH-drift-check" / "orch_printready.py"
BASELINE_DIR = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
OUT_ROOT = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT")
FLAGS = "--srgb --auto-exposure"

SHIPPING_SHA = "44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490"
# PIN-V3 is mislabelled: it is a DIFFERENT binary from the one its directory
# name claims. Four builds on this machine share size 9,568,768, so size proves
# nothing and only the hash identifies a build.
BANNED = {"B50EABC1": "C:\\dev\\strehl-out\\PIN-V3\\strehl.exe is mislabelled -- "
                      "it is not the pin its path claims. Identify builds by SHA-256 only."}

# Deterministic crop sites. Fixed, not random: the same pixels must be compared
# on every run or a difference between runs is not attributable to the binary.
CROPS = [(1200, 1200), (2400, 3600), (3600, 2000), (1600, 4800), (2800, 2400)]
STATE_RE = re.compile(r"^([A-Z]+)\s+(\S+)")
PARTITION_RE = re.compile(r"^partition:\s*(.+)$")

# The gate states that mean "this subject was examined and its standing is not
# an objection". Everything else -- FAIL, SKIP, EXPIRED, REVIEW, MISSING -- is a
# subject we cannot ship on the strength of. Leaving this set is a regression.
GOOD_STATES = ("PASS", "ACQUIT")

# Head-to-head: the comparator arms are FIXED artifacts and are never rebuilt.
H2H_SUBJECT = "119MSDCF"
H2H_ROOT = Path(r"C:\dev\strehl-out\V-NOISE2\119")
H2H_MANIFEST = Path(r"C:\dev\strehl-out\DELIVER-V5\vs-the-field\manifest-119MSDCF.json")
H2H_SRC = Path(r"D:\personal\macro\119MSDCF")
H2H_DIGEST = "5e1f4bf433effb2c"   # half-A frame digest, from logs/align-A.log
H2H_FLAGS = ["--merge", "pyramid", "--pyramid-gate", "4.5", "--linear-srgb", "--demosaic"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def stage_identity(cand):
    h = sha256(cand)
    for pre, why in BANNED.items():
        if h.startswith(pre):
            raise SystemExit(f"REFUSED: candidate sha256 {h[:16]} is banned.\n  {why}")
    info = {"path": str(cand), "sha256": h, "size": cand.stat().st_size,
            "is_shipping_pin": h == SHIPPING_SHA}
    print(f"candidate : {cand}")
    print(f"sha256    : {h}")
    print(f"identity  : {'THE SHIPPING PIN (this is a null re-certification)' if info['is_shipping_pin'] else 'a new binary'}")
    return info


def _ps_env():
    """Environment for the Windows PowerShell child that runs `finalpass.ps1`.

    THE FIRST FULL RUN OF THIS HARNESS RENDERED ZERO MASTERS because
    `finalpass.ps1` died on `Get-FileHash: The term ... is not recognized`. The
    cmdlet was not missing; the module path was wrong. This process is launched
    from `pwsh` (PowerShell 7), which exports a PSModulePath pointing at PS7's
    module directories. Python inherits it, `powershell.exe` (Windows PowerShell
    5.1) inherits it in turn, and 5.1 cannot autoload Microsoft.PowerShell.Utility
    from 7's directories -- so a core cmdlet disappears from a shell that is
    otherwise working, which is why the failure reads as a corrupt install rather
    than as an inherited variable. Measured, three arms, same one-line probe:

        powershell, env as-is             exit 1   Get-FileHash not recognized
        powershell, PSModulePath = 5.1's  exit 0   8DD1EBB0
        pwsh,       env as-is             exit 0   8DD1EBB0

    THE FIRST FIX WRITTEN HERE WAS INERT AND SAID SO ONLY WHEN MEASURED. It was
    `dict(os.environ).pop("PSModulePath")`. On Windows `os.environ` is a
    case-insensitive mapping whose keys are stored UPPER-CASED, so `dict()` of it
    yields a plain dict keyed `PSMODULEPATH` and the pop matched nothing. The
    launcher control then printed `PSModulePath: <unset>` and refused -- correct
    to refuse, but for a reason that was itself the same bug, because its
    diagnostic read the same plain dict. A fix and its check sharing a defect is
    how an inert repair certifies itself.

    So: drop the key case-insensitively, and pin the host to `pwsh` when it is
    present, since that is the host every successful run of `finalpass.ps1` on
    this machine has actually used.
    """
    e = {k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"}
    return e


def _ps_host():
    """`pwsh` if it exists, else Windows PowerShell. See `_ps_env`."""
    return shutil.which("pwsh") or "powershell"


def stage_render(cand, arm, only=None):
    dst = OUT_ROOT / "arms" / arm
    cmd = [_ps_host(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(FINALPASS),
           "-Exe", str(cand), "-Arm", arm, "-Flags", FLAGS,
           "-OutRoot", str(OUT_ROOT / "arms"), "-NoPresent"]
    if only:
        cmd += ["-Only", ",".join(only)]
    print(f"  {' '.join(cmd[5:])}")
    r = subprocess.run(cmd, capture_output=True, text=True, env=_ps_env())
    (OUT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "logs" / f"render-{arm}.txt").write_text(r.stdout + r.stderr, encoding="utf-8")
    tiffs = sorted(dst.glob("*.tiff"))
    # A subject-restricted run cannot produce COMPLETE.txt and must not pretend to
    # be a full arm: it is complete against what it was asked for, and the manifest
    # records `only` so no later reader can mistake it for a 26-subject pass.
    complete = (dst / "COMPLETE.txt").exists() or (bool(only) and len(tiffs) == len(only))
    print(f"  rendered {len(tiffs)} master(s); COMPLETE.txt "
          f"{'present' if (dst / 'COMPLETE.txt').exists() else 'ABSENT'}"
          f"{'  (subject-restricted run)' if only else ''}")
    if not complete:
        print("  *** ARM IS INCOMPLETE -- a partial arm must never be scored as a full one ***")
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
        if tail:
            print("  render said:\n    " + tail.replace("\n", "\n    "))
    return {"dir": str(dst), "n_masters": len(tiffs), "complete": complete,
            "only": list(only) if only else None, "exit": r.returncode}


def gate_fingerprint():
    """SHA-256 of the gate script, so a cached baseline cannot outlive it.

    ANOTHER LANE IS EXTENDING THIS GATE RIGHT NOW, to halos, sharpness and dust.
    A baseline scored by yesterday's gate, diffed against a candidate scored by
    today's, manufactures state changes out of the checks that were added -- and
    they would appear as subjects moving, attributed to the candidate. That is a
    regression report invented entirely by a cache.

    The baseline is therefore stamped with this value and re-measured whenever it
    moves. Re-running costs 472 s; reading a stale one costs a wrong verdict on
    a promotion decision.
    """
    return hashlib.sha256(GATE.read_bytes()).hexdigest()[:16].upper()


def run_gate(target):
    r = subprocess.run([sys.executable, str(GATE), str(target)],
                       capture_output=True, text=True, cwd=str(GATE.parent))
    states, partition = {}, None
    for line in r.stdout.splitlines():
        if line.startswith(" ") or not line.strip():
            continue
        m = PARTITION_RE.match(line)
        if m:
            partition = m.group(1)
            continue
        m = STATE_RE.match(line)
        if m and m.group(1) in ("PASS", "FAIL", "ACQUIT", "EXPIRED", "REVIEW", "SKIP"):
            states[m.group(2)] = m.group(1)
    return {"states": states, "partition": partition, "exit": r.returncode,
            "gate_sha": gate_fingerprint(), "stdout": r.stdout}


def diff_gate(baseline, cand, only=None):
    """Which subjects moved, and which of those moves block promotion.

    Pure: it takes two parsed gate results and returns the verdict material, so
    the rule can be commissioned on synthetic states without a 370 s gate run.
    `commission_recert.commission_gate_diff` is that commissioning.
    """
    moves, regressions, expiries = [], [], []
    for subj in sorted(set(baseline["states"]) | set(cand["states"])):
        # A targeted run rendered a subset. The 20 subjects it never rendered are
        # ABSENT, not regressed, and calling that a PASS->MISSING regression would
        # bury the real ones under noise the operator asked for.
        if only and subj not in only:
            continue
        b = baseline["states"].get(subj, "MISSING")
        c = cand["states"].get(subj, "MISSING")
        if b == c:
            continue
        moves.append({"subject": subj, "from": b, "to": c})
        # WHICH MOVES ARE REGRESSIONS, AND WHY SKIP IS ONE OF THEM.
        # A first version counted only PASS->FAIL. Measured against the HEAD
        # candidate f190a0ea it called that arm a 3-subject regression while
        # TWELVE subjects moved PASS->SKIP, because the gate crashed on them
        # (`ValueError: could not convert string to float: 'REJECT-FLAT'`, the
        # sentinel `orch_chroma.py` returns when its analysis window is flatter
        # than 64 DN -- which is what a blown highlight looks like).
        #
        # A subject the gate could not examine has not passed. Counting only
        # PASS->FAIL let a candidate escape judgement by breaking the judge, and
        # the more damage it did the more subjects fell out of the count. That
        # is the same failure shape as a summary in which a skipped check and a
        # passed check print as the same glyph.
        #
        # ACQUIT is likewise a state the gate reached by examining the subject,
        # so leaving it for FAIL or SKIP is a loss of standing and blocks too.
        if b in GOOD_STATES and c in ("FAIL", "MISSING", "SKIP"):
            regressions.append(subj)
        elif b == "ACQUIT" and c in ("EXPIRED", "REVIEW"):
            expiries.append(subj)
    return moves, regressions, expiries


def stage_gate(arm_dir, baseline, only=None):
    cand = run_gate(arm_dir)
    (OUT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "logs" / "gate-candidate.txt").write_text(cand["stdout"], encoding="utf-8")
    print(f"  baseline  : {baseline['partition']}")
    print(f"  candidate : {cand['partition']}")
    moves, regressions, expiries = diff_gate(baseline, cand, only)
    if not moves:
        print("  no subject changed state")
    for m in moves:
        tag = ""
        if m["subject"] in regressions:
            tag = "   <== REGRESSION"
        elif m["subject"] in expiries:
            tag = "   <== acquittal expired: NOT a pass, needs re-adjudication"
        print(f"  {m['from']:8s} -> {m['to']:8s}  {m['subject']}{tag}")
    return {"baseline_partition": baseline["partition"], "partition": cand["partition"],
            "moves": moves, "regressions": regressions, "expiries": expiries,
            "exit": cand["exit"]}


def _pair_two(a_path, b_path, sites, already_srgb=True, fits=None, exposure=1.0):
    """Band-separated pairing between two renders on identical crops."""
    a = tifffile.imread(str(a_path))
    b = tifffile.imread(str(b_path))
    rows = []
    for (y, x) in sites:
        fa = (fits or {}).get("a", {"shift": (0, 0), "gain": (1, 1, 1), "offset": (0, 0, 0)})
        fb = (fits or {}).get("b", fa)
        da = display_crop(a, y, x, fa["shift"], fa["gain"], fa["offset"], exposure,
                          already_srgb=already_srgb)
        db = display_crop(b, y, x, fb["shift"], fb["gain"], fb["offset"], exposure,
                          already_srgb=already_srgb)
        ma, mb = measure_crop(da), measure_crop(db)
        for band in BANDS:
            c = classify(ma[band], mb[band])
            rows.append({"y": y, "x": x, "band": band, "verdict": c["verdict"],
                         "d_floor": c["d_floor"], "d_structure": c["d_peak"],
                         "paid": c["paid"], "refused": c["refused"],
                         "base_floor": ma[band]["floor"], "cand_floor": mb[band]["floor"],
                         "base_structure": ma[band]["structure"],
                         "cand_structure": mb[band]["structure"]})
    del a, b
    return rows


def summarise(rows, label):
    """Collapse to per-band counts. NEVER to one number: a candidate that is
    quieter in `mottle` and softer in `struct` has made a trade, and a single
    score is exactly how a trade becomes invisible."""
    out = {}
    for band in BANDS:
        r = [x for x in rows if x["band"] == band]
        tested = [x for x in r if not x["refused"]]
        blur = [x for x in tested if x["verdict"].startswith("BLUR_TRADE")]
        clean = [x for x in tested if x["verdict"].startswith("CLEANER")]
        soft = [x for x in tested if x["verdict"].startswith("SOFTER")]
        out[band] = {
            "n": len(r), "tested": len(tested), "refused": len(r) - len(tested),
            "cleaner": len(clean), "blur_trade": len(blur), "softer": len(soft),
            "median_d_floor": float(np.median([x["d_floor"] for x in tested])) if tested else None,
            "median_d_structure": float(np.median([x["d_structure"] for x in tested
                                                   if x["d_structure"] is not None])) if tested else None,
        }
        s = out[band]
        print(f"  {label:10s} {band:7s} tested {s['tested']:3d} refused {s['refused']:3d}"
              f"  cleaner {s['cleaner']:3d}  blur_trade {s['blur_trade']:3d}  softer {s['softer']:3d}"
              f"  d_floor {('%+.4f' % s['median_d_floor']) if s['median_d_floor'] is not None else '   -'}"
              f"  d_struct {('%+.4f' % s['median_d_structure']) if s['median_d_structure'] is not None else '   -'}")
    return out


def stage_pair(arm_dir, arm, only=None):
    rows = []
    subjects = []
    missing = []
    for base in sorted(BASELINE_DIR.glob("*--SHIP-V4.tiff")):
        subj = base.name.split("--")[0]
        if only and subj not in only:
            continue
        cand = Path(arm_dir) / f"{subj}--{arm}.tiff"
        if not cand.exists():
            print(f"  {subj}: candidate master MISSING -- not scored, not passed")
            missing.append(subj)
            continue
        subjects.append(subj)
        for r in _pair_two(base, cand, CROPS):
            r["subject"] = subj
            rows.append(r)
    print(f"  paired {len(subjects)} subject(s) x {len(CROPS)} crops x {len(BANDS)} bands"
          f" = {len(rows)} cells" + (f"; {len(missing)} subject(s) MISSING" if missing else ""))
    return {"rows": rows, "subjects": subjects, "missing": missing,
            "summary": summarise(rows, "vs baseline")}


def stage_h2h(cand_exe, arm):
    """Candidate vs `enfuse` and `focus-stack` on the published sites.

    The comparator arms are fixed artifacts and are NOT rebuilt. Only our arm is
    re-rendered, from the same 17-frame half-bracket and the same warpmap, and
    the frame digest printed by the binary is checked against the one in
    `logs/align-A.log`. If the digest does not match, the frame set is not the
    one the published cells were measured on and the stage REFUSES -- comparing a
    different container against a fixed comparator is how an arm ends up
    differing in more than one way at once.
    """
    man = json.loads(H2H_MANIFEST.read_text())
    warp = H2H_ROOT / "119-A.warpmap.txt"
    work = OUT_ROOT / "h2h" / "half-A"
    out = OUT_ROOT / "h2h" / f"strehl-A--{arm}.tiff"
    for p in (warp, H2H_SRC):
        if not p.exists():
            return {"refused": f"missing {p}"}
    work.mkdir(parents=True, exist_ok=True)
    if not any(work.glob("*.ARW")):
        raws = sorted(H2H_SRC.glob("*.ARW"))
        for f in raws[::2]:                      # half-A: the 17 even-indexed frames
            shutil.copy2(f, work / f.name)
    n = len(list(work.glob("*.ARW")))

    # THE DIGEST IS PRINTED BY `align`, NOT BY `stack`. The first version of this
    # stage scraped `stack`'s output for it, found nothing, and refused every time
    # -- a check that can never pass is not a safe default, it is a stage that
    # never runs while reporting a reason that sounds like a finding. Ask the
    # command that actually emits it. Cost is 5.2 s for 17 frames, measured.
    #
    # `--out` is mandatory here: `align`'s default target is the SHARED warp-map
    # cache that every other lane's `stack` reads. A verification step must not
    # write into the input of nine concurrent runs.
    probe = OUT_ROOT / "h2h" / "digest-probe.warpmap.txt"
    a = subprocess.run([str(cand_exe), "align", str(work), "--out", str(probe)],
                       capture_output=True, text=True)
    m = re.search(r"digest\s+([0-9a-f]{16})", a.stdout + a.stderr)
    got = m.group(1) if m else None
    if got != H2H_DIGEST:
        return {"refused": f"half-A frame digest {got} != published {H2H_DIGEST} "
                           f"({n} frames copied); the reconstructed bracket is not the one "
                           f"the published cells were measured on"}
    print(f"  half-A verified: {n} frames, digest {got} == published")

    if not out.exists():
        e = dict(os.environ)
        e.update({"STREHL_FULLRES_GATHER": "1", "STREHL_WARPMAP": str(warp)})
        r = subprocess.run([str(cand_exe), "stack", str(work), "--out", str(out)] + H2H_FLAGS,
                           capture_output=True, text=True, env=e)
        (OUT_ROOT / "logs" / f"h2h-{arm}.txt").write_text(r.stdout + r.stderr, encoding="utf-8")
        if not out.exists():
            return {"refused": f"h2h render produced no output (exit {r.returncode})"}
    rows = []
    for site in man["sites"]:
        for comp in ("enfuse", "focus-stack"):
            cpath = Path(man["arms"][comp])
            if not cpath.exists():
                continue
            fits = {"a": {"shift": site["fits"][comp]["shift"],
                          "gain": site["fits"][comp]["gain"],
                          "offset": site["fits"][comp]["offset"]},
                    "b": {"shift": site["fits"]["strehl"]["shift"],
                          "gain": site["fits"]["strehl"]["gain"],
                          "offset": site["fits"]["strehl"]["offset"]}}
            for r in _pair_two(cpath, out, [(site["y"], site["x"])], already_srgb=False,
                               fits=fits, exposure=site["exposure"]):
                r.update({"site": site["label"], "comparator": comp})
                rows.append(r)
    for comp in ("enfuse", "focus-stack"):
        summarise([r for r in rows if r["comparator"] == comp], f"vs {comp}")
    return {"rows": rows, "n_frames": n}


def verdict(res, stages):
    """One line. A candidate is PROMOTABLE only if nothing regressed on the gate
    and no band bought its noise win out of structure.

    THE FIRST VERSION OF THIS FUNCTION CERTIFIED A RUN THAT MEASURED NOTHING.
    Invoked with `--stages identity` it printed "PROMOTABLE", because it looked
    only for reasons to refuse and an empty result set supplies none. That is the
    same shape as a gate whose threshold nothing can reach: absence of evidence
    was being read as evidence of absence. A verdict now requires its evidence to
    exist, and says which piece is missing when it does not.
    """
    missing = [s for s in ("render", "gate", "pair") if s not in res]
    if missing:
        return False, ("INCONCLUSIVE -- no verdict can be formed: stage(s) "
                       + ", ".join(missing) + " did not run. Nothing was measured, so nothing "
                       "is certified.")
    if not res["render"].get("complete"):
        return False, ("INCONCLUSIVE -- the render arm is INCOMPLETE "
                       f"({res['render'].get('n_masters')} masters). A partial arm must never be "
                       "scored as a full one.")
    reasons = []
    g = res.get("gate", {})
    if g.get("regressions"):
        # Name the transitions, not one of them. An earlier version wrote
        # "PASS->FAIL" for every blocking move; measured on candidate f190a0ea
        # that mislabelled 12 PASS->SKIP and 5 ACQUIT->FAIL as PASS->FAIL, which
        # is a verdict line misdescribing its own evidence. The transition mix is
        # diagnostic: PASS->SKIP means the gate crashed rather than judged.
        kinds = {}
        for m in g.get("moves", []):
            if m["subject"] in g["regressions"]:
                kinds[f"{m['from']}->{m['to']}"] = kinds.get(f"{m['from']}->{m['to']}", 0) + 1
        mix = ", ".join(f"{n}x {k}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))
        reasons.append(f"gate regression on {len(g['regressions'])} subject(s) [{mix}]: "
                       f"{', '.join(g['regressions'])}")
    if g.get("expiries"):
        reasons.append(f"{len(g['expiries'])} acquittal(s) expired and are unadjudicated "
                       f"({', '.join(g['expiries'])})")
    s = res.get("pair", {}).get("summary", {})
    for band, v in s.items():
        if not BANDS[band][3]:
            continue
        if v["tested"] == 0:
            reasons.append(f"{band}: 0 cells tested -- refused, not passed")
            continue
        if v["blur_trade"] > v["cleaner"]:
            reasons.append(f"{band}: {v['blur_trade']} blur-trade vs {v['cleaner']} clean cells "
                           f"-- the noise win was paid for out of structure")
        if v["median_d_structure"] is not None and v["median_d_structure"] < -0.02:
            reasons.append(f"{band}: median structure {v['median_d_structure']:+.4f} "
                           f"-- sharpness fell")
    ok = not reasons
    line = ("PROMOTABLE -- no gate regression, no band bought its noise win out of structure"
            if ok else "NOT PROMOTABLE -- " + "; ".join(reasons))
    only = (res.get("render") or {}).get("only")
    if only:
        # A targeted run answers a narrower question and must say which one. It is
        # evidence for the subjects it rendered and silence about the other 20.
        line = (f"PARTIAL ({len(only)}/26 subjects: {', '.join(only)}) -- " + line
                + ". NOT a full certification; a promotion needs a 26-subject pass.")
    return ok, line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--stages", default="identity,render,gate,pair,h2h,verdict")
    ap.add_argument("--only", default=None,
                    help="Comma-separated subjects. A TARGETED re-certification: renders and "
                         "pairs only these. The six mottle-convicted subjects are 463 of the "
                         "corpus's 4,825 frames (9.6%%), so a candidate can be scored against "
                         "the subjects it was built to change for a tenth of a full pass. "
                         "The result is marked partial and can never read as a 26-subject run.")
    ap.add_argument("--baseline-gate", default=str(OUT_ROOT / "logs" / "baseline-gate.json"))
    ap.add_argument("--adopt-render", action="store_true",
                    help="The arm is already rendered (e.g. by `finalpass.ps1 -Sha ...`, which "
                         "cuts the pin and writes PINNED provenance). Verify and adopt the "
                         "directory rather than re-invoking the renderer, which would pass -Exe "
                         "and rewrite that provenance as UNPINNED.")
    a = ap.parse_args()
    stages = a.stages.split(",")
    only = [s for s in a.only.split(",") if s] if a.only else None
    cand = Path(a.candidate)
    if not cand.exists():
        raise SystemExit(f"REFUSED: no such binary {cand}")
    if not (OUT_ROOT / "logs" / "commission-bands.txt").exists():
        raise SystemExit("REFUSED: commission_bands.py has not been run. An uncommissioned "
                         "metric may not certify anything.")
    ctext = (OUT_ROOT / "logs" / "commission-bands.txt").read_text(encoding="utf-8", errors="replace")
    if "COMMISSIONING PASSED" not in ctext:
        raise SystemExit("REFUSED: the last commissioning run did not pass.")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "logs").mkdir(parents=True, exist_ok=True)

    res, times = {}, {}
    t_all = time.time()
    for st in stages:
        t0 = time.time()
        print(f"\n=== {st} ===")
        if st == "identity":
            res["identity"] = stage_identity(cand)
        elif st == "render":
            if a.adopt_render:
                # The arm was rendered by `finalpass.ps1 -Sha ...` directly, so the
                # pin's provenance is already written. Re-invoking finalpass here
                # would find every master present and render nothing, but it would
                # pass `-Exe`, and a second pass must not overwrite a PINNED
                # provenance with one that says UNPINNED. Adopt the directory and
                # verify it instead -- COMPLETE.txt and a master count, the same
                # two things stage_render checks.
                d = OUT_ROOT / "arms" / a.arm
                tiffs = sorted(d.glob(f"*--{a.arm}.tiff"))
                comp = (d / "COMPLETE.txt").exists()
                print(f"  adopted {d}")
                print(f"  {len(tiffs)} master(s); COMPLETE.txt "
                      f"{'present' if comp else 'ABSENT'}")
                if not comp:
                    print("  *** ARM IS INCOMPLETE -- a partial arm must never be "
                          "scored as a full one ***")
                res["render"] = {"dir": str(d), "n_masters": len(tiffs),
                                 "complete": comp and len(tiffs) == 26,
                                 "only": list(only) if only else None, "adopted": True}
            else:
                res["render"] = stage_render(cand, a.arm, only=only)
        elif st == "gate":
            bp = Path(a.baseline_gate)
            now = gate_fingerprint()
            baseline = None
            if bp.exists():
                baseline = json.loads(bp.read_text())
                was = baseline.get("gate_sha")
                if was != now:
                    print(f"  the gate has CHANGED since the baseline was cached "
                          f"({was} -> {now}).")
                    print("  re-measuring the baseline: diffing two different gates would "
                          "report their difference as the candidate's.")
                    baseline = None
            if baseline is None:
                print("  scoring the baseline corpus (cached after this run)")
                baseline = run_gate(BASELINE_DIR)
                bp.write_text(json.dumps(baseline), encoding="utf-8")
            else:
                print(f"  baseline cache valid (gate {now})")
            res["gate"] = stage_gate(res.get("render", {}).get("dir",
                                     str(OUT_ROOT / "arms" / a.arm)), baseline, only=only)
        elif st == "pair":
            res["pair"] = stage_pair(res.get("render", {}).get("dir",
                                     str(OUT_ROOT / "arms" / a.arm)), a.arm, only=only)
        elif st == "h2h":
            res["h2h"] = stage_h2h(cand, a.arm)
            if res["h2h"].get("refused"):
                print(f"  REFUSED: {res['h2h']['refused']}")
        elif st == "verdict":
            pass
        times[st] = round(time.time() - t0, 1)
        print(f"  [{st} {times[st]}s]")
    times["TOTAL"] = round(time.time() - t_all, 1)

    ok, line = verdict(res, stages)
    res["timing_seconds"] = times
    res["verdict"] = line
    res["promotable"] = ok
    # rows are large; keep them out of the headline manifest but keep them.
    rows = {k: res[k].pop("rows", None) for k in ("pair", "h2h") if k in res}
    (OUT_ROOT / f"recert-{a.arm}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    (OUT_ROOT / f"recert-{a.arm}-cells.json").write_text(json.dumps(rows), encoding="utf-8")
    print("\n" + "=" * 92)
    print(f"TIMING: " + "  ".join(f"{k} {v}s" for k, v in times.items()))
    print(f"VERDICT: {line}")
    print(f"manifest: {OUT_ROOT / f'recert-{a.arm}.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
