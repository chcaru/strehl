import io, sys
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\halo3.py"
t = io.open(P, encoding="utf-8").read()

A = """    prof = uniform_filter1d(prof, SMOOTH, axis=1, mode="nearest")
    a, b = int(PLATEAU[0] * R), int(PLATEAU[1] * R)
    plateau = np.median(prof[:, a:b + 1], axis=1)
    excess = prof - plateau[:, None]
    # only the region that has cleared the subject can overshoot
    over = np.max(excess[:, 5:a], axis=1)
    at = (5 + np.argmax(excess[:, 5:a], axis=1)).astype(float)
    return dict(overshoot=float(np.median(over)),
                over_p75=float(np.percentile(over, 75)),
                over_p90=float(np.percentile(over, 90)),
                at_px=float(np.median(at[over > 0])) if np.any(over > 0) else 0.0,
                n_edges=int(by.size),
                frac_pos=float(np.mean(over > 0))), None
"""
if t.count(A) != 1:
    sys.exit("ANCHOR NOT FOUND (%d) -- refusing to patch" % t.count(A))

B = """    prof = uniform_filter1d(prof, SMOOTH, axis=1, mode="nearest")

    # KEEP ONLY RAYS THAT STAY IN OPEN BACKGROUND. If a ray re-enters the
    # subject or crosses another part, its samples are not background and its
    # plateau is meaningless. The distance transform along the ray must keep
    # up with s; a ray that grazes other structure falls behind.
    dr = map_coordinates(d, [cy.ravel(), cx.ravel()], order=1,
                         mode="nearest").reshape(cy.shape)
    good = np.all(dr[:, 5:] >= 0.6 * s[None, 5:], axis=1)
    if int(good.sum()) < MIN_EDGE_PTS:
        return None, ("only %d of %d normals stay in open background for %d px; "
                      "the silhouette has no clear run to measure against"
                      % (int(good.sum()), prof.shape[0], R))
    prof = prof[good]

    # AVERAGE THE ALIGNED PROFILES BEFORE TAKING ANY MAXIMUM.
    # Taking the max per-edge first is a search that cannot fail: the max of
    # noise over 135 samples is always positive, and it read HALO 7745 DN on a
    # known-clean subject. Averaging first makes noise fall as 1/sqrt(n) while
    # a rim, which sits at a consistent distance from every edge, survives.
    esf = np.median(prof, axis=0)
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
t = t.replace(A, B, 1)

C = """        v = "HALO" if r["overshoot"] > a.thresh else "CLEAN"
"""
if t.count(C) != 1:
    sys.exit("ANCHOR 2 NOT FOUND (%d)" % t.count(C))
D = """        # a reading must beat BOTH the absolute threshold and this subject's
        # own measured noise floor for the identical statistic
        v = ("HALO" if (r["overshoot"] > a.thresh and
                        r["overshoot"] > 2.0 * max(r["floor"], 1.0)) else "CLEAN")
"""
t = t.replace(C, D, 1)

E = """        print("%-36s %-9s %9.1f %9.1f %7.0f %7d  %.0f%% of edges overshoot" % (
            s, v, r["overshoot"], r["over_p90"], r["at_px"], r["n_edges"],
            100*r["frac_pos"]))
"""
if t.count(E) != 1:
    sys.exit("ANCHOR 3 NOT FOUND (%d)" % t.count(E))
F = """        print("%-36s %-9s %9.1f %9.1f %7.0f %7d  floor %.0f DN" % (
            s, v, r["overshoot"], r["floor"], r["at_px"], r["n_edges"],
            r["floor"]))
"""
t = t.replace(E, F, 1)
t = t.replace('"median DN",\n          "p90 DN","at px","edges","note"',
              '"overshoot",\n          "noisefloor","at px","edges","note"', 1)
io.open(P, "w", newline="\n", encoding="utf-8").write(t)
print("patched halo3.py: average-then-max, ray purity, measured noise floor")
