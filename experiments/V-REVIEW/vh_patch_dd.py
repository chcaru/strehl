import io, sys
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\halo3.py"
t = io.open(P, encoding="utf-8").read()

A = """    esf = np.median(prof, axis=0)
    a, b = int(PLATEAU[0] * R), int(PLATEAU[1] * R)
    plateau = float(np.median(esf[a:b + 1]))
    excess = esf - plateau
    k = int(np.argmax(excess[5:a])) + 5
    over = float(excess[k])
    # NOISE FLOOR OF THIS VERY STATISTIC, measured not assumed: the same max
    # taken over the plateau region, where no rim can live.
    floor = float(np.max(excess[a:b + 1]))
    return dict(overshoot=over, at_px=float(k), floor=floor,
                n_edges=int(prof.shape[0]), plateau=plateau,
                esf=esf.tolist()), None
"""
if t.count(A) != 1:
    sys.exit("ANCHOR NOT FOUND (%d) -- refusing to patch" % t.count(A))

B = """    esf = np.median(prof, axis=0)
    a, b = int(PLATEAU[0] * R), int(PLATEAU[1] * R)
    plateau = float(np.median(esf[a:b + 1]))

    # A HALO IS A LOCAL BRIGHTENING, NOT A GLOBAL ONE.
    # Measured and refuted: scoring the excursion ABOVE THE FAR PLATEAU cannot
    # detect a rim inside a deep penumbra -- 30 px from a bee's edge the scene
    # is genuinely ~15000 DN dark, so a 3200 DN rim never clears the plateau
    # and read CLEAN -- while a broad scene gradient DOES clear it and read
    # HALO at 6000 DN. The reference was wrong in both directions.
    # The right reference is the profile's own running maximum: crossing out of
    # the subject the level must rise monotonically. A rim makes it rise and
    # then FALL BACK. That drawdown is local, so penumbra depth is irrelevant.
    run = np.maximum.accumulate(esf)
    dd = run - esf
    kt = int(np.argmax(dd))
    amp = float(dd[kt])
    kp = int(np.argmax(esf[:kt + 1])) if kt > 0 else 0
    width = float(kt - kp)
    # NOISE FLOOR OF THIS VERY STATISTIC, measured per subject, taken over the
    # plateau where no rim can live.
    floor = float(np.max(np.maximum.accumulate(esf[a:b + 1]) - esf[a:b + 1]))
    return dict(overshoot=amp, at_px=float(kp), width=width, floor=floor,
                n_edges=int(prof.shape[0]), plateau=plateau,
                esf=esf.tolist()), None
"""
t = t.replace(A, B, 1)

C = """        v = ("HALO" if (r["overshoot"] > a.thresh and
                        r["overshoot"] > 2.0 * max(r["floor"], 1.0)) else "CLEAN")
"""
if t.count(C) != 1:
    sys.exit("ANCHOR 2 NOT FOUND (%d)" % t.count(C))
D = """        # amplitude must beat the threshold AND this subject's own measured
        # noise floor; width rejects a broad scene gradient, which falls off
        # over hundreds of px rather than the tens a rim occupies.
        v = ("HALO" if (r["overshoot"] > a.thresh and
                        r["overshoot"] > 2.0 * max(r["floor"], 1.0) and
                        r["width"] <= MAX_RIM_WIDTH) else "CLEAN")
"""
t = t.replace(C, D, 1)

E = "MIN_EDGE_PTS = 300\n"
if t.count(E) != 1: sys.exit("ANCHOR 3 NOT FOUND")
t = t.replace(E, E + "MAX_RIM_WIDTH = 150.0   # px a rim may take to fall back; a gradient takes more\n", 1)

F = """        print("%-36s %-9s %9.1f %9.1f %7.0f %7d  floor %.0f DN" % (
            s, v, r["overshoot"], r["floor"], r["at_px"], r["n_edges"],
            r["floor"]))
"""
if t.count(F) != 1: sys.exit("ANCHOR 4 NOT FOUND")
G = """        print("%-36s %-9s %9.1f %9.1f %7.0f %7d  width %.0f px" % (
            s, v, r["overshoot"], r["floor"], r["at_px"], r["n_edges"],
            r["width"]))
"""
t = t.replace(F, G, 1)
io.open(P, "w", newline="\n", encoding="utf-8").write(t)
print("patched halo3.py: max-drawdown statistic with width gate")
