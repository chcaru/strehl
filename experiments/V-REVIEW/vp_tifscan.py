"""Integrity scan: which files in the acceptance corpora are not readable TIFFs?

A gate that cannot open a file may report it as skipped -- or, worse, not
report it at all. Either way an unreadable master must never be invisible.
"""
import glob, os, datetime, tifffile

for root in [r"C:\dev\strehl-out\acceptance\SHIP-V3",
             r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"]:
    files = sorted(glob.glob(os.path.join(root, "*.tif*")))
    ok = bad = 0
    print(f"\n=== {root}  ({len(files)} files) ===")
    for f in files:
        try:
            with tifffile.TiffFile(f) as tf:
                _ = tf.pages[0].shape
            ok += 1
        except Exception as e:
            bad += 1
            st = os.stat(f)
            mt = datetime.datetime.fromtimestamp(st.st_mtime)
            with open(f, "rb") as fh:
                head = fh.read(8)
            print(f"  UNREADABLE {os.path.basename(f)}")
            print(f"      bytes={st.st_size:,}  mtime={mt:%Y-%m-%d %H:%M:%S}")
            print(f"      head={head!r}  err={type(e).__name__}: {e}")
    print(f"  readable={ok}  unreadable={bad}  total={ok+bad}  (sums={ok+bad==len(files)})")
