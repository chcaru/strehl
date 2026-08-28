# Replace the local-max rim finder with a robust-trend RESIDUAL finder.
# Anchored on a unique full line; hard-errors if the anchor does not land.
import io, sys
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\halo2.py"
t = io.open(P, encoding="utf-8").read()

A = """    best = None
    for k in range(len(val)):
        left = val[:k].min() if k > 0 else val[k]
        right = val[k + 1:].min() if k + 1 < len(val) else val[k]
        amp = val[k] - max(left, right)      # must rise above BOTH sides
        if amp <= 0:
            continue
        half = val[k] - 0.5 * amp
        i = k
        while i > 0 and val[i - 1] >= half: i -= 1
        j = k
        while j < len(val) - 1 and val[j + 1] >= half: j += 1
        width = float(mid[j] - mid[i]) if j > i else float(qual[k]["hi"] - qual[k]["lo"])
        if best is None or amp > best["amp"]:
            best = dict(amp=float(amp), at=float(mid[k]), width=width,
                        peak=float(val[k]))
"""
if t.count(A) != 1:
    sys.exit("ANCHOR NOT FOUND (%d occurrences) -- refusing to patch" % t.count(A))

B = """    # RIM AS A RESIDUAL, not as a local maximum.
    # Commissioned and REFUTED: requiring a peak above both neighbours cannot
    # work. halo_profile's own header says why -- the subject's penumbra rises
    # 4000-5000 DN per band near the edge, so a rim riding on it never breaks
    # monotonicity. Measured: a 3200 DN rim, narrow AND broad, read "monotone".
    # So fit the smooth penumbra trend and look for a LOCALIZED departure from
    # it. A gradient is smooth and is absorbed by the trend; a rim is not.
    # The fit is robust: refit with the two largest positive residuals dropped,
    # so a strong rim cannot drag the trend up to hide itself.
    x = np.log(mid)
    deg = min(3, len(val) - 2)
    co = np.polyfit(x, val, deg)
    r0 = val - np.polyval(co, x)
    if len(val) > deg + 3:
        keep = np.argsort(r0)[:-2]
        co = np.polyfit(x[keep], val[keep], deg)
    resid = val - np.polyval(co, x)

    best = None
    k = int(np.argmax(resid))
    if resid[k] > 0:
        amp = float(resid[k])
        half = 0.5 * amp
        i = k
        while i > 0 and resid[i - 1] >= half: i -= 1
        j = k
        while j < len(val) - 1 and resid[j + 1] >= half: j += 1
        width = float(mid[j] - mid[i]) if j > i else float(qual[k]["hi"] - qual[k]["lo"])
        best = dict(amp=amp, at=float(mid[k]), width=width, peak=float(val[k]))
"""
t = t.replace(A, B, 1)

# the step-scale gate must now be measured on the DETRENDED profile, or the
# penumbra's own steep rise sets a step scale no rim can ever beat.
C = "    steps = np.abs(np.diff(val))\n    stepscale = float(np.median(steps)) if steps.size else 0.0\n"
if t.count(C) != 1:
    sys.exit("ANCHOR 2 NOT FOUND (%d) -- refusing to patch" % t.count(C))
D = ("    # NOTE: measured on the detrended profile below, not on val: the raw\n"
     "    # band step is dominated by the penumbra and would veto every rim.\n"
     "    stepscale = None\n")
t = t.replace(C, D, 1)

E = "    resid = val - np.polyval(co, x)\n"
if t.count(E) != 1:
    sys.exit("ANCHOR 3 NOT FOUND (%d)" % t.count(E))
t = t.replace(E, E + "    dsteps = np.abs(np.diff(resid))\n"
              "    stepscale = float(np.median(dsteps)) if dsteps.size else 0.0\n", 1)

io.open(P, "w", newline="\n", encoding="utf-8").write(t)
print("patched halo2.py: rim = localized residual from a robust smooth trend")
