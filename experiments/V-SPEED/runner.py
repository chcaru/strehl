"""V-SPEED timing harness.

Times three focus-stacking pipelines from the SAME start artifact (a directory
of Sony .ARW files) to the SAME end artifact (one merged image file on disk).

  arm 1  strehl      strehl stack <dir> --out <f> --srgb --auto-exposure
  arm 2  enfuse      develop -> align_image_stack -> enfuse
  arm 3  focus-stack develop -> focus-stack        (it aligns internally)

The `develop` stage is identical work for arms 2 and 3, so it is executed once
per round and its measured wall clock is charged to BOTH. Neither comparator
can read RAW, so the stage is not an extra bolted on to flatter arm 1; it is
the cost of the toolchain.

Discipline discharged here:
  rule 47 / brief item 4 -- every binary is hashed and every flag is recorded.
  brief item 1 -- V_SPEED_PLANT_STAGE / V_SPEED_PLANT_S plant a known delay
                  inside the timed region of ONE named stage, so commissioning
                  runs the production code path.
  brief item 3 -- rounds alternate arm order (forward / reverse), which is
                  AGENTS.md rule 16's alternating sweep.

Usage:
  python runner.py --subject <name> --src <dir> --rounds N [--tag T]
                   [--only stage,stage] [--start-round K]
"""

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

STREHL = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
STREHL_SHA_PREFIX = "44C2F2CD2E5B2894"
HUGIN_BIN = r"C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin"
AIS = os.path.join(HUGIN_BIN, "align_image_stack.exe")
ENFUSE = os.path.join(HUGIN_BIN, "enfuse.exe")
FS = r"C:\dev\strehl-out\V-LINEAR2\fs15\focus-stack\focus-stack.exe"
DEVELOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "develop.py")

ROOT = r"C:\dev\strehl-out\V-SPEED"
WORKERS = 16  # = physical cores; see docs/research/V-SPEED.md section 4.

ENFUSE_FLAGS = [
    "--exposure-weight=0",
    "--saturation-weight=0",
    "--contrast-weight=1",
    "--hard-mask",
]
# --use-given-order is not optional: align_image_stack sorts by exposure value
# by default, which on a constant-exposure focus stack is an arbitrary order
# (V-LINEAR2 sec 2). -m optimises field of view, -C auto-crops to the common
# area. -l declares LINEAR input and is therefore added only in linear mode.
AIS_FLAGS = ["-m", "-C", "--use-given-order"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def check_binaries():
    got = sha256(STREHL)
    if not got.startswith(STREHL_SHA_PREFIX):
        raise SystemExit(
            f"REFUSING TO TIME: strehl sha256 {got[:16]} != {STREHL_SHA_PREFIX}"
        )
    return {os.path.basename(p): sha256(p) for p in (STREHL, AIS, ENFUSE, FS)}


def time_stage(name, cmd, logpath, cwd=None):
    """Run cmd, return the timed record. A plant, if armed for this stage,
    happens INSIDE the timed region and on the production path."""
    plant_stage = os.environ.get("V_SPEED_PLANT_STAGE", "")
    plant_s = float(os.environ.get("V_SPEED_PLANT_S", "0") or 0)
    os.makedirs(os.path.dirname(logpath), exist_ok=True)
    t0 = time.perf_counter()
    if plant_stage == name and plant_s > 0:
        time.sleep(plant_s)
    with open(logpath, "wb") as lf:
        proc = subprocess.run(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT)
    wall = time.perf_counter() - t0
    return {
        "stage": name,
        "wall_s": wall,
        "rc": proc.returncode,
        "planted_s": plant_s if plant_stage == name else 0.0,
        "cmd": subprocess.list2cmdline(cmd),
        "log": logpath,
    }


def stat(path):
    if not os.path.exists(path):
        return {"exists": False}
    return {"exists": True, "bytes": os.path.getsize(path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--start-round", type=int, default=0)
    ap.add_argument("--tag", default="main")
    ap.add_argument("--only", default="")
    ap.add_argument("--mode", default="srgb", choices=["srgb", "linear"])
    ap.add_argument("--tifdir", default=None)
    args = ap.parse_args()

    only = set(x for x in args.only.split(",") if x)
    hashes = check_binaries()

    base = os.path.join(ROOT, args.subject)
    tifdir = args.tifdir or os.path.join(base, f"tif-{args.mode}")
    aligndir = os.path.join(base, "aligned")
    outdir = os.path.join(base, "out")
    logdir = os.path.join(base, "logs")
    for d in (tifdir, aligndir, outdir, logdir):
        os.makedirs(d, exist_ok=True)

    nframes = len([n for n in os.listdir(args.src) if n.lower().endswith(".arw")])
    jsonl = os.path.join(ROOT, f"timings-{args.tag}.jsonl")

    def emit(rec):
        rec["subject"] = args.subject
        rec["frames"] = nframes
        rec["tag"] = args.tag
        rec["mode"] = args.mode
        rec["t_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(
            f"  {rec['round']:>2} {rec['stage']:<12} {rec['wall_s']:8.2f}s "
            f"rc={rec['rc']}" + (f"  PLANT {rec['planted_s']}s" if rec.get("planted_s") else ""),
            flush=True,
        )

    print(f"subject={args.subject} frames={nframes} src={args.src}", flush=True)
    print(json.dumps(hashes), flush=True)

    for r in range(args.start_round, args.start_round + args.rounds):
        forward = (r % 2) == 0
        print(f"== round {r} ({'forward' if forward else 'reverse'}) ==", flush=True)

        def run_develop():
            if only and "develop" not in only:
                return
            rec = time_stage(
                "develop",
                [sys.executable, DEVELOP, args.src, tifdir, str(WORKERS), args.mode],
                os.path.join(logdir, f"r{r}-develop.log"),
            )
            rec["round"] = r
            rec["workers"] = WORKERS
            emit(rec)

        def run_strehl():
            if only and "strehl" not in only:
                return
            out = os.path.join(outdir, f"r{r}-strehl.tif")
            if os.path.exists(out):
                os.remove(out)
            rec = time_stage(
                "strehl",
                [STREHL, "stack", args.src, "--out", out, "--srgb", "--auto-exposure"],
                os.path.join(logdir, f"r{r}-strehl.log"),
            )
            rec["round"] = r
            rec["artifact"] = stat(out)
            emit(rec)

        def run_align():
            if only and "align" not in only:
                return
            if os.path.isdir(aligndir):
                shutil.rmtree(aligndir)
            os.makedirs(aligndir, exist_ok=True)
            tifs = sorted(glob.glob(os.path.join(tifdir, "*.tif")))
            ais_flags = (["-l"] if args.mode == "linear" else []) + AIS_FLAGS
            rec = time_stage(
                "align",
                [AIS] + ais_flags + ["-a", "al_"] + tifs,
                os.path.join(logdir, f"r{r}-align.log"),
                cwd=aligndir,
            )
            rec["round"] = r
            rec["n_in"] = len(tifs)
            rec["n_out"] = len(glob.glob(os.path.join(aligndir, "al_*.tif")))
            emit(rec)

        def run_enfuse():
            if only and "enfuse" not in only:
                return
            out = os.path.join(outdir, f"r{r}-{args.mode}-enfuse.tif")
            if os.path.exists(out):
                os.remove(out)
            al = sorted(glob.glob(os.path.join(aligndir, "al_*.tif")))
            rec = time_stage(
                "enfuse",
                [ENFUSE] + ENFUSE_FLAGS + [f"--output={out}"] + al,
                os.path.join(logdir, f"r{r}-enfuse.log"),
            )
            rec["round"] = r
            rec["n_in"] = len(al)
            rec["artifact"] = stat(out)
            emit(rec)

        def run_fs():
            if only and "focus-stack" not in only:
                return
            out = os.path.join(outdir, f"r{r}-{args.mode}-fs.tif")
            if os.path.exists(out):
                os.remove(out)
            tifs = sorted(glob.glob(os.path.join(tifdir, "*.tif")))
            rec = time_stage(
                "focus-stack",
                [FS, f"--output={out}"] + tifs,
                os.path.join(logdir, f"r{r}-fs.log"),
            )
            rec["round"] = r
            rec["n_in"] = len(tifs)
            rec["artifact"] = stat(out)
            emit(rec)

        run_develop()
        consumers = [run_strehl, run_align, run_enfuse, run_fs]
        if not forward:
            consumers = [run_fs, run_enfuse, run_align, run_strehl]
            # enfuse must not run before align in a reverse round; align first.
            consumers = [run_fs, run_align, run_enfuse, run_strehl]
        for fn in consumers:
            fn()


if __name__ == "__main__":
    main()
