"""M118 arm 1 -- render every resampler arm from ONE solve per subject.

Method (verified live at the pinned SHA before the pre-registration was written):
`strehl align --out` writes `resampler <name>` as text into the sidecar;
`STREHL_WARPMAP=<sidecar> strehl stack` loads it through `merge_cmd.rs::alignment_for`,
which validates stack identity and frame count ONLY -- it does not check the
resampler and it never caches back. So N arms share ONE solve and differ in
exactly one line of text, which is the cleanest possible kernel A/B: the warps
are identical by construction.

The CACHE path does check the resampler and would re-solve. Every arm therefore
also gets its own STREHL_CACHE_DIR (fact 1561).

Exit codes are read through subprocess.returncode, which is immune to the
PowerShell `Select-Object -First` trap (rule 46/47).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M118-target\release\strehl.exe")
OUT = Path(r"C:\dev\strehl-out\M118")
CORPUS = Path(r"D:\personal\macro")

ARMS = ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"]
BASELINE = "catmull-rom"

SUBJECTS = {
    "bee-3-cpl": 299,
    "wrapped-text-1": 130,
    "flat-on-ruler-cpl": 79,
}

GATE = "4"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def run(argv, env_extra, log: Path):
    """Run a strehl subcommand. Returns (returncode, stdout+stderr, seconds)."""
    env = dict(os.environ)
    # Rule 47: name every variable this tool reads, including the ones we clear.
    for var in ("STREHL_ALIGN", "STREHL_FIX_HALO", "STREHL_PHOTOMETRIC",
                "STREHL_DUMP_ELECTION", "STREHL_DUMP_NEFF", "STREHL_WARPMAP",
                "STREHL_CACHE_DIR"):
        env.pop(var, None)
    env.update(env_extra)
    t0 = time.time()
    r = subprocess.run([str(EXE), *argv], capture_output=True, text=True, env=env)
    dt = time.time() - t0
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "ARGV: " + " ".join([str(EXE), *argv]) + "\n"
        + "ENV : " + json.dumps(env_extra, indent=2) + "\n"
        + f"EXIT: {r.returncode}\nSECS: {dt:.1f}\n\n" + r.stdout + "\n" + r.stderr,
        encoding="utf-8",
    )
    return r.returncode, r.stdout + "\n" + r.stderr, dt


def make_sidecar(base: Path, arm: str, dest: Path) -> None:
    """Copy `base` and rewrite its resampler line to `arm`.

    Hard-errors if the anchor does not land or is not unique. A bare replace that
    silently misses reads GREEN and would make every downstream number a
    measurement of the baseline five times over.
    """
    text = base.read_text(encoding="utf-8")
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith("resampler ")]
    if len(hits) != 1:
        raise SystemExit(f"FATAL: expected exactly 1 'resampler' line in {base}, found {len(hits)}")
    was = lines[hits[0]]
    lines[hits[0]] = f"resampler {arm}"
    dest.write_text("\n".join(lines), encoding="utf-8")
    back = [ln for ln in dest.read_text(encoding="utf-8").split("\n") if ln.startswith("resampler ")]
    if back != [f"resampler {arm}"]:
        raise SystemExit(f"FATAL: sidecar edit did not land for {arm}: {back}")
    if arm != BASELINE and was == f"resampler {arm}":
        raise SystemExit(f"FATAL: sidecar for {arm} was already {arm}; the A/B would be null")


def solve(subject: str, limit: int, sdir: Path) -> Path:
    """One solve per subject, at the reference the merge itself would choose."""
    base = sdir / f"{subject}--solve.txt"
    if base.exists():
        print(f"  solve: reusing {base.name}")
        return base
    ref = limit // 2  # merge_reference: the middle frame
    code, out, dt = run(
        ["align", str(CORPUS / subject), "--limit", str(limit),
         "--reference", str(ref), "--out", str(base)],
        {"STREHL_CACHE_DIR": str(sdir / "cache-solve")},
        sdir / "logs" / f"{subject}--align.log",
    )
    if code != 0:
        raise SystemExit(f"FATAL: align {subject} exited {code}\n{out[-3000:]}")
    placed = re.search(r"placed (\d+)/(\d+) frames", out)
    print(f"  solve: {dt:.1f}s  {placed.group(0) if placed else '?'}  ref={ref}")
    if placed and placed.group(1) != placed.group(2):
        print(f"  WARNING: {placed.group(0)} -- not all frames placed")
    return base


def parse_stats(out: str) -> dict:
    d = {}
    for key, pat in [
        ("mean_n_eff", r"mean n_eff\s*:?\s*([0-9.]+)"),
        ("coverage", r"coverage\s*:?\s*([0-9.]+)"),
        ("resampler", r"resampler\s*:\s*(\w+)"),
        ("exposure", r"--exposure=(-?[0-9.]+)"),
        ("alignment", r"alignment\s*:\s*(.+)"),
    ]:
        m = re.search(pat, out)
        if m:
            d[key] = m.group(1).strip()
    return d


def render_subject(subject: str, limit: int) -> dict:
    sdir = OUT / subject
    sdir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {subject}  limit={limit}")
    base = solve(subject, limit, sdir)

    rec = {"subject": subject, "limit": limit, "gate": GATE,
           "solve_sidecar": str(base), "arms": {}}

    # Pin the viewing exposure on the BASELINE arm; every other arm is then
    # rendered at that exact value. Letting --auto-exposure re-choose per arm
    # would make the contact sheet a comparison of exposures.
    pinned_exposure = None

    for arm in [BASELINE] + [a for a in ARMS if a != BASELINE]:
        side = sdir / f"{subject}--{arm}.txt"
        make_sidecar(base, arm, side)
        cache = sdir / f"cache-{arm}"
        env = {"STREHL_WARPMAP": str(side), "STREHL_CACHE_DIR": str(cache)}

        meas = sdir / f"{subject}__{arm}__measure.tif"
        idx = sdir / f"{subject}__{arm}__index.tif"
        neff = sdir / f"{subject}__{arm}__neff.tif"
        code, out, dt = run(
            ["stack", str(CORPUS / subject), "--limit", str(limit), "--gate", GATE,
             "-o", str(meas), "--index-map", str(idx), "--n-eff-map", str(neff)],
            env, sdir / "logs" / f"{subject}--{arm}--measure.log")
        if code != 0:
            raise SystemExit(f"FATAL: stack {subject}/{arm} exited {code}\n{out[-3000:]}")
        st = parse_stats(out)
        if "sidecar-override" not in st.get("alignment", ""):
            raise SystemExit(
                f"FATAL: {subject}/{arm} did NOT take the sidecar-override path "
                f"(alignment: {st.get('alignment')}). The arm would be the default kernel.")
        rec["arms"][arm] = {"measure": str(meas), "measure_sha": sha256(meas),
                            "index": str(idx), "neff": str(neff),
                            "measure_secs": round(dt, 1), "stats": st,
                            "sidecar": str(side)}
        print(f"  {arm:<12} measure {dt:6.1f}s  {rec['arms'][arm]['measure_sha'][:16]}  "
              f"n_eff={st.get('mean_n_eff')}")

        # viewing render
        view = sdir / f"{subject}__{arm}__view.tif"
        vargs = ["stack", str(CORPUS / subject), "--limit", str(limit), "--gate", GATE,
                 "-o", str(view), "--srgb"]
        vargs += ["--auto-exposure"] if pinned_exposure is None else [f"--exposure={pinned_exposure}"]
        code, out, dt = run(vargs, env, sdir / "logs" / f"{subject}--{arm}--view.log")
        if code != 0:
            raise SystemExit(f"FATAL: view {subject}/{arm} exited {code}\n{out[-3000:]}")
        vst = parse_stats(out)
        if pinned_exposure is None:
            pinned_exposure = vst.get("exposure")
            if pinned_exposure is None:
                raise SystemExit("FATAL: --auto-exposure printed no --exposure=N to pin")
            print(f"  exposure pinned at {pinned_exposure} from the {BASELINE} arm")
        rec["arms"][arm]["view"] = str(view)
        rec["arms"][arm]["view_sha"] = sha256(view)
        rec["arms"][arm]["view_secs"] = round(dt, 1)

    rec["pinned_exposure"] = pinned_exposure

    # ---- B5 null + B7 poisoning, in one construct -------------------------
    # The baseline was rendered FIRST (cold). Re-render it now, after every other
    # arm has run, from a WIPED cache and a byte-identical command line. Equal
    # hashes discharge both the reproducibility null and the adversarial
    # poisoning check; a difference means an arm received a kernel nobody asked for.
    arm = BASELINE
    side = sdir / f"{subject}--{arm}.txt"
    cache = sdir / f"cache-{arm}"
    if cache.exists():
        shutil.rmtree(cache)
    repeat = sdir / f"{subject}__{arm}__measure_REPEAT.tif"
    code, out, dt = run(
        ["stack", str(CORPUS / subject), "--limit", str(limit), "--gate", GATE,
         "-o", str(repeat), "--index-map", str(sdir / f"{subject}__{arm}__index_REPEAT.tif"),
         "--n-eff-map", str(sdir / f"{subject}__{arm}__neff_REPEAT.tif")],
        {"STREHL_WARPMAP": str(side), "STREHL_CACHE_DIR": str(cache)},
        sdir / "logs" / f"{subject}--{arm}--REPEAT.log")
    if code != 0:
        raise SystemExit(f"FATAL: repeat exited {code}")
    rec["null_repeat_sha"] = sha256(repeat)
    rec["null_pass"] = rec["null_repeat_sha"] == rec["arms"][arm]["measure_sha"]
    print(f"  NULL/POISON  {arm} cold-after-all-arms: "
          f"{'BYTE-IDENTICAL (pass)' if rec['null_pass'] else 'DIFFERS (FAIL)'}")

    # ---- B6 P1 wiring plant ----------------------------------------------
    # The null above cannot distinguish "reproducible" from "the sidecar is
    # ignored". Plant a different kernel on the same wiring and require the hash
    # to MOVE. Without this the null is fact 1548's bar that reads 0 px on its
    # own broken plant.
    distinct = {a: rec["arms"][a]["measure_sha"] for a in ARMS}
    rec["plant_P1_distinct_hashes"] = len(set(distinct.values()))
    rec["plant_P1_pass"] = rec["plant_P1_distinct_hashes"] == len(ARMS)
    print(f"  PLANT P1     {rec['plant_P1_distinct_hashes']}/{len(ARMS)} distinct hashes: "
          f"{'pass' if rec['plant_P1_pass'] else 'FAIL -- the sidecar edit is a NO-OP'}")

    (Path(__file__).parent.parent / "out").mkdir(parents=True, exist_ok=True)
    dst = Path(__file__).parent.parent / "out" / f"r1_{subject}.json"
    dst.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec


if __name__ == "__main__":
    want = sys.argv[1:] or list(SUBJECTS)
    for s in want:
        render_subject(s, SUBJECTS[s])
