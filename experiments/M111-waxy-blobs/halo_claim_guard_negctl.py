"""Negative control for halo_claim_guard.py.

Plants one defect at a time into the report, requires the guard to go RED, and
restores from a TEMP copy between plants. Never uses `git checkout`.

Each mutation is anchored on a UNIQUE FULL-LINE string and hard-errors if it does
not land, so a silent no-op cannot be mistaken for a passing plant.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT = os.path.join(ROOT, "docs", "research", "M111-waxy-blobs.md")
GUARD = os.path.join(ROOT, "experiments", "M111-waxy-blobs", "halo_claim_guard.py")

BACKUP = os.path.join(tempfile.gettempdir(), "M111-report-negctl-backup.md")
shutil.copy2(REPORT, BACKUP)
print("backup -> %s" % BACKUP)


def run_guard():
    r = subprocess.run([sys.executable, GUARD], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def restore():
    shutil.copy2(BACKUP, REPORT)


def plant(tag, old, new):
    """Replace `old` with `new` inside the single fact row starting with `tag`."""
    lines = io.open(REPORT, encoding="utf-8").read().split("\n")
    hits = [i for i, l in enumerate(lines)
            if l.startswith("* **%s " % tag) or l.startswith("* **%s." % tag)]
    if len(hits) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND: %s matched %d rows" % (tag, len(hits)))
    row = lines[hits[0]]
    if row.count(old) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND: %r occurs %d times in %s"
                         % (old, row.count(old), tag))
    lines[hits[0]] = row.replace(old, new)
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


DEFECTS = [
    ("D1 last-digit on BMF", "P46", "4.428", "4.429"),
    ("D2 moved-frac inflated", "P50", "0.394", "0.494"),
    ("D3 last-digit on control RMSE", "P51", "+558.4%", "+558.5%"),
    ("D4 bar verdict flipped", "P49", "V3 false", "V3 true"),
    ("D5 complement count off by one", "P54", "**220**", "**221**"),
    ("D6 sigma transposed", "P46", "5.108", "5.180"),
    ("D7 fine-band retention inflated", "P49", "0.905812", "0.945812"),
]

rc, out = run_guard()
if rc != 0:
    restore()
    raise SystemExit("BASELINE NOT GREEN, cannot run negative control:\n%s" % out)
print("baseline GREEN\n")

caught, missed = 0, []
for name, tag, old, new in DEFECTS:
    restore()
    plant(tag, old, new)
    rc, out = run_guard()
    verdict = "CAUGHT" if rc != 0 else "MISSED"
    if rc != 0:
        caught += 1
    else:
        missed.append(name)
    first = next((l for l in out.split("\n") if l.startswith("FAIL")), out.strip().split("\n")[-1])
    print("%-34s %s   %s" % (name, verdict, first[:96]))

restore()
rc, out = run_guard()
print("\nrestored, guard: %s" % out.strip().split("\n")[-1])
if rc != 0:
    raise SystemExit("RESTORE FAILED, report is not back to baseline")

# --- second direction: mutate the SOURCE, leave the report alone ---------
# Every defect above was caught by the literal-presence arm. That arm compares the
# report against constants written into this file, so on its own it cannot prove the
# guard reads the source at all. These plants perturb a COPY of the source JSON and
# require the NUMERIC arm to fire, which is the only arm that reads it.
print("\n--- source-mutation arm (numeric comparison) ---")
sandbox = os.path.join("C:\\", "dev", "strehl-out", "M111-halo-control", "negctl-data")
os.makedirs(sandbox, exist_ok=True)
SRC = os.path.join(ROOT, "experiments", "M87-occlusion", "data")
for fn in ("56-bmf.json", "22-plant-truth.json"):
    shutil.copy2(os.path.join(SRC, fn), os.path.join(sandbox, fn))

import json


def mutate_source(fn, path, value):
    fp = os.path.join(sandbox, fn)
    doc = json.load(io.open(fp, encoding="utf-8"))
    node = doc
    for key in path[:-1]:
        node = node[key]
    before = node[path[-1]]
    node[path[-1]] = value
    io.open(fp, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    return before


SOURCE_DEFECTS = [
    ("S1 BMF drifts at source", "56-bmf.json", ("regions", "DAMAGE", "BMF"), 4.6),
    ("S2 fine-band drifts at source", "56-bmf.json", ("regions", "DAMAGE", "fine"), 0.8),
    ("S3 moved_frac drifts at source", "22-plant-truth.json",
     ("occluding (KB=90, two depths)", "local-d40", "moved_frac"), 0.55),
    # S4 commissions the sign-aware fix for the defect V-M111 found. The old
    # comparison abs(abs(stated) - abs(value)) passes a pure sign flip. d20 is
    # deliberately chosen because the structural dose-response check uses d10
    # and d40 only, so this defect is visible to the numeric arm ALONE.
    ("S4 control ISO sign flipped", "22-plant-truth.json",
     ("CONTROL non-occluding (KB=KF=40, one depth)", "local-d20", "iso_delta_pct"),
     141.952151),
]
env = dict(os.environ, M111_HALO_DATA=sandbox)
scaught = 0
for name, fn, path, value in SOURCE_DEFECTS:
    for f in ("56-bmf.json", "22-plant-truth.json"):
        shutil.copy2(os.path.join(SRC, f), os.path.join(sandbox, f))
    mutate_source(fn, path, value)
    r = subprocess.run([sys.executable, GUARD], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    body = (r.stdout or "") + (r.stderr or "")
    numeric = [l for l in body.split("\n") if "source says" in l or "at source" in l
               or "is not fine/blur_fine" in l]
    ok = r.returncode != 0 and numeric
    scaught += 1 if ok else 0
    if not ok:
        missed.append(name)
    print("%-34s %s   %s" % (name, "CAUGHT" if ok else "MISSED",
                             (numeric[0] if numeric else body.strip().split("\n")[-1])[:96]))

for f in ("56-bmf.json", "22-plant-truth.json"):
    shutil.copy2(os.path.join(SRC, f), os.path.join(sandbox, f))

print("\n%s  %d/%d report defects, %d/%d source defects caught"
      % ("GREEN" if not missed else "RED", caught, len(DEFECTS), scaught, len(SOURCE_DEFECTS)))
sys.exit(0 if not missed else 1)
