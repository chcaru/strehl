import json, os, sys, tri
s = sys.argv[1] if len(sys.argv) > 1 else "wrapped-text-2"
f = json.load(open(os.path.join(tri.OUT, "focus", s + ".json")))
bs = f["blocks"]
ny, nx = f["grid"]
print(f"{s}: {f['n_frames']} frames, grid {nx} across x {ny} down, "
      f"level {f['level_dn']}")
print("\nBEST-SOURCE high-frequency amplitude per block, DN "
      "(* = peak at a bracket end -> no frame beyond it):")
for r in range(ny):
    row = []
    for c in range(nx):
        b = next(q for q in bs if q["r"] == r and q["c"] == c)
        row.append(f"{b['hf_max_dn']:8.1f}{'*' if b['at_end'] else ' '}")
    print(f"  r={r} " + "".join(row))
print("\nsharpest frame index per block (bracket runs 0..%d):" % (f["n_frames"] - 1))
for r in range(ny):
    row = []
    for c in range(nx):
        b = next(q for q in bs if q["r"] == r and q["c"] == c)
        row.append(f"{b['best_frame']:8d} ")
    print(f"  r={r} " + "".join(row))
print("\ncontrast of peak over the flattest frame (hf_max/hf_min):")
for r in range(ny):
    row = []
    for c in range(nx):
        b = next(q for q in bs if q["r"] == r and q["c"] == c)
        row.append(f"{b['hf_max_dn']/max(b['hf_min_dn'],1e-6):8.2f} ")
    print(f"  r={r} " + "".join(row))
