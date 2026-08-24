"""M102 S1 -- FEASIBILITY SPIKE, run before pre-registration.

The question this settles: can a synthetic stack enter the pipeline through
the SAME decode path a real capture does? The shipped CLI ingests `.arw` via
`rawler`, and synthetic Sony ARW is not writable. If `rawler` accepts an
uncompressed CFA DNG, the whole simulator can be scored end-to-end against
the real binary. If it does not, the architecture must change and the
milestone's bars change with it.

This is a spike, not an arm. It is declared as such because pre-registration
after seeing data is worthless, and a feasibility probe that decides the
ARCHITECTURE is not a probe that decides a RESULT. No bar in
PREREGISTRATION.md depends on any number produced here beyond
"the decoder accepts the file, yes or no".

Run:
  python experiments/M102-simulator/src/s1_spike_dng.py
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m102lib as M  # noqa: E402

STREHL = r"C:\dev\strehl-out\M100\vt2-target\release\strehl.exe"


def main():
    d = os.path.join(M.WORK, "spike")
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

    h, w = 128, 192
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(3):
        scene = 400.0 + 300.0 * np.sin(xx / 7.0) * np.cos(yy / 9.0)
        cfa = np.clip(scene + M.BLACK + 40.0 * i, 0, M.WHITE)
        M.write_dng(os.path.join(d, f"DSC{i + 1:05d}.ARW"),
                    cfa.astype(np.uint16), iso=100)

    sizes = [os.path.getsize(os.path.join(d, f)) for f in sorted(
        os.listdir(d))]
    print(f"wrote {len(sizes)} file(s), {sizes[0]} bytes each"
          f" (expect {8 + w * h * 2} + header/tags)")

    r = subprocess.run([STREHL, "probe", d], capture_output=True, text=True,
                       timeout=300)
    print(f"\n--- strehl probe exit {r.returncode}")
    print((r.stdout or "")[:2600])
    if r.returncode != 0:
        print("--- stderr")
        print((r.stderr or "")[:2000])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
