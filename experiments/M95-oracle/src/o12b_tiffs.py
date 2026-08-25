import glob, numpy as np, tifffile, json, os
pats = [r"C:\dev\strehl-out\M95-ref\*.tif", r"C:\dev\strehl-out\M95-kernel\*.tif",
        r"C:\dev\strehl-out\M95-coverage\*.tif", r"C:\dev\strehl-out\M95-resample\*.tif"]
rows = []
seen = 0
for p in pats:
    for f in sorted(glob.glob(p))[:2]:
        a = tifffile.imread(f)
        ch = a[..., 0] if a.ndim == 3 else a
        s = ch.reshape(-1)
        if s.size > 4_000_000:
            s = s[:: s.size // 4_000_000]
        lv = int(np.unique(s).size)
        seen += 1
        print(f"  {os.path.basename(f):38s} {str(a.dtype):8s} {str(a.shape):22s} "
              f"levels {lv:6d}  {'NARROWED' if lv < 4096 else 'native'}")
        rows.append(dict(path=f, dtype=str(a.dtype), shape=list(a.shape), levels=lv,
                         narrowed=bool(lv < 4096)))
if seen == 0:
    raise SystemExit("COVERAGE FAILURE: probed no TIFFs")
print(f"\nTIFFs probed {seen}, NARROWED {sum(r['narrowed'] for r in rows)}")
json.dump(rows, open("out/o12b_tiffs.json", "w", encoding="utf-8"), indent=1)
