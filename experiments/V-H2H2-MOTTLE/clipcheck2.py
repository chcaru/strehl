"""Clip fraction and median for masters named on the command line."""

import os
import sys

import numpy as np
import tifffile

print(f"  {'master':<16}{'max':>8}{'median':>10}{'clip%':>10}")
for p in sys.argv[1:]:
    a = tifffile.imread(p)
    top = 65535 if a.dtype == np.uint16 else a.max()
    clip = float((a >= top).mean() * 100.0)
    print(
        f"  {os.path.basename(p):<16}{int(a.max()):>8}{int(np.median(a)):>10}{clip:>10.4f}"
    )
