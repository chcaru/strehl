"""Drive fitdrift -> veilgrid -> classify over many subjects, in parallel.

Resumable: a stage whose output already exists is skipped, so a run that dies
half way costs only what it had not already done.  Each subject's log is
printed whole when it finishes rather than interleaved.

Concurrency is deliberately modest.  The raws live on a single spinning
volume and every stage is decode-bound, so past about eight workers the disk
is the limit and more processes only lengthen the tail.
"""
import argparse
import concurrent.futures as cf
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
RAWROOT = pathlib.Path(r"D:\personal\macro")


def run(cmd):
    p = subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                       cwd=str(HERE))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def one(subject, out, blocks, force):
    t0 = time.time()
    o = pathlib.Path(out)
    log = [f"########## {subject}"]
    stages = [
        (o / "drift" / f"{subject}.npz",
         ["fitdrift.py", "--subject", subject, "--out", out, "--minin", "4"]),
        (o / "tensors" / f"{subject}.npz",
         ["veilgrid.py", "--subject", subject, "--out", out,
          "--blocks", blocks]),
        (o / "classify" / f"{subject}.json",
         ["classify.py", "--subject", subject, "--out", out,
          "--norms", "plain", "--maps", "resp/plain,fixed/plain"]),
    ]
    for target, cmd in stages:
        if target.exists() and not force:
            log.append(f"-- skip {cmd[0]} ({target.name} exists)")
            continue
        rc, txt = run(cmd)
        log.append(f"-- {cmd[0]} rc={rc}")
        log.append(txt.rstrip())
        if rc != 0:
            return subject, False, "\n".join(log) + \
                f"\n########## {subject} FAILED [{time.time() - t0:.0f}s]"
    return subject, True, "\n".join(log) + \
        f"\n########## {subject} ok [{time.time() - t0:.0f}s]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", default="")
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--blocks", default="48,96,192,384")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    subs = ([s for s in a.subjects.split(",") if s] if a.subjects else
            sorted(d.name for d in RAWROOT.iterdir()
                   if d.is_dir() and any(d.glob("*.ARW"))))
    print(f"{len(subs)} subjects, {a.workers} workers, blocks {a.blocks}")
    ok, bad = [], []
    t0 = time.time()
    with cf.ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(one, s, a.out, a.blocks, a.force) for s in subs]
        for f in cf.as_completed(futs):
            s, good, txt = f.result()
            print(txt, flush=True)
            (ok if good else bad).append(s)
            print(f"### progress {len(ok)} ok / {len(bad)} failed / "
                  f"{len(subs)} [{time.time() - t0:.0f}s]", flush=True)
    print(f"\nOK ({len(ok)}): {' '.join(sorted(ok))}")
    print(f"FAILED ({len(bad)}): {' '.join(sorted(bad))}")


if __name__ == "__main__":
    main()
