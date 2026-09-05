"""Commission the 2.9.75 re-derived memory checks in v2954.py.

WHY THIS EXISTS
---------------
The five `m172 *` checks are not presence pins. They recompute GiB, headroom
and the N299/N33 ratio from the raw Job Object byte counts in M172's run
records and compare the result against what STATUS 2.9.75 says. That is the
strongest form of check in this verifier, and it is also the easiest to get
silently wrong: if the derivation and the prose were ever to drift apart in the
same direction -- say by both being edited from the same mistaken belief -- the
check would agree with itself and report XDOC forever.

So each arm below breaks exactly one side. Three mutate STATUS and must produce
an XFAIL for their named check. One mutates the SOURCE record instead, leaving
STATUS untouched: that is the only arm that proves the byte counts are actually
re-read from M172's artifacts each run rather than baked into the verifier.
One arm is inert and must disturb nothing.

Run from anywhere; paths are resolved absolutely because `cd` does not change
.NET's or a subprocess's notion of the current directory on this host.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V2954 = HERE / "v2954.py"
REC = ("experiments/M172-worker-memory/out/candidate/records/"
       "measured-n299-w16.json")

# (label, target relative path, anchor, replacement, expected failing check)
ARMS = [
    ("status gib drift", "docs/STATUS.md",
     "`2.863785` GiB", "`2.863786` GiB", "m172 n299 gib"),
    ("status headroom drift", "docs/STATUS.md",
     "`3.136` GiB of headroom", "`3.137` GiB of headroom", "m172 headroom gib"),
    ("status ratio drift", "docs/STATUS.md",
     "`1.001664`", "`1.001665`", "m172 ratio"),
    # The source-side arm. STATUS is left alone; the recorded byte count moves.
    # Both the byte-count check and every number derived from it must fail.
    ("source bytes drift", REC, None, None, "m172 n299 peak bytes"),
]
INERT = ("inert prose", "docs/STATUS.md",
         "That is not a marginal improvement",
         "That is not a small improvement")


def build_scratch():
    scratch = Path(tempfile.mkdtemp(prefix="oder-"))
    shutil.copytree(ROOT / "docs", scratch / "docs")
    src_exp = ROOT / "experiments"
    n = 0
    for p in src_exp.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".md", ".json"):
            continue
        rel = p.relative_to(src_exp)
        dst = scratch / "experiments" / rel
        if len(str(dst)) > 240:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        n += 1
    if n == 0:
        raise SystemExit("FATAL: copied zero experiment artifacts; every arm "
                         "below would fail for the wrong reason")
    if not (scratch / REC).exists():
        raise SystemExit("FATAL: scratch is missing %s, so the source-side arm "
                         "would report a catch that is really a copy failure"
                         % REC)
    return scratch


def run(scratch):
    p = subprocess.run([sys.executable, "-B", str(V2954), str(scratch)],
                       capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def xfailed(out, label):
    return re.search(r"(?m)^XFAIL\s+" + re.escape(label) + r"(\s|$)",
                     out) is not None


def xfail_total(out):
    m = re.search(r"(?m)^xdoc derived fail\s*:\s*(\d+)\s*$", out)
    if m is None:
        raise SystemExit("FATAL: could not read the xdoc fail total; no arm "
                         "below would be interpretable")
    return int(m.group(1))


def sub_once(text, old, new, label):
    hits = [m.start() for m in re.finditer(re.escape(old), text)]
    if len(hits) != 1:
        raise SystemExit("FATAL [%s]: anchor matched %d times, need exactly "
                         "1: %r" % (label, len(hits), old))
    return text.replace(old, new, 1)


def main():
    base = build_scratch()
    out0 = run(base)
    base_fail = xfail_total(out0)
    print("baseline: %d xdoc failure(s)\n" % base_fail)
    for _, _, _, _, expect in ARMS:
        if xfailed(out0, expect):
            raise SystemExit("FATAL: %r is ALREADY failing before its plant is "
                             "applied; its arm would be meaningless" % expect)
    shutil.rmtree(base, ignore_errors=True)

    caught = missed = 0
    for label, rel, old, new, expect in ARMS:
        scratch = build_scratch()
        target = scratch / rel
        if old is None:
            # Source-side: perturb the recorded peak by one byte.
            d = json.loads(target.read_text(encoding="utf-8"))
            k = d["memory"]["kernel_job_peak_memory"]
            k["peak_job_memory_used_bytes"] += 1
            target.write_text(json.dumps(d, indent=2), encoding="utf-8")
            note = "source-side; STATUS untouched"
        else:
            t = target.read_text(encoding="utf-8", errors="replace")
            target.write_text(sub_once(t, old, new, label), encoding="utf-8")
            note = "STATUS-side"
        out = run(scratch)
        hit = xfailed(out, expect)
        print("%-22s %-16s [%s; check %r %s]"
              % (label, "CAUGHT" if hit else "*** MISSED ***", note, expect,
                 "went XFAIL" if hit else "STAYED XDOC"))
        caught += 1 if hit else 0
        missed += 0 if hit else 1
        shutil.rmtree(scratch, ignore_errors=True)

    label, rel, old, new = INERT
    scratch = build_scratch()
    target = scratch / rel
    t = target.read_text(encoding="utf-8", errors="replace")
    target.write_text(sub_once(t, old, new, label), encoding="utf-8")
    out = run(scratch)
    n = xfail_total(out)
    quiet = n == base_fail
    print("%-22s %-16s [xdoc fail total %d vs baseline %d]"
          % (label, "inert, survived" if quiet else "*** INERT TRIPPED ***",
             n, base_fail))
    shutil.rmtree(scratch, ignore_errors=True)

    print("\ncaught %d, missed %d  (of %d planted)" % (caught, missed, len(ARMS)))
    print("inert survived %d, inert tripped %d  (of 1 inert)"
          % (1 if quiet else 0, 0 if quiet else 1))
    print("arms accounted  : %d of %d"
          % (caught + missed + 1, len(ARMS) + 1))
    ok = missed == 0 and quiet
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
