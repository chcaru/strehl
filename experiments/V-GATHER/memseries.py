import json,glob,os
OUT=r"C:\dev\strehl-out\V-GATHER\mem"
for f in sorted(glob.glob(os.path.join(OUT,"*.series.json"))):
    d=json.load(open(f))
    if isinstance(d,dict): d=[d]
    ts=[r["t"] for r in d]; mv=[r["priv_MiB"] for r in d]
    pk=max(mv); it=mv.index(pk)
    print(f"\n{os.path.basename(f).replace('.series.json','')}: peak {pk} MiB at t={ts[it]:.1f}s of {ts[-1]:.1f}s ({100*ts[it]/ts[-1]:.0f}% through)")
    print("  t(s) :", " ".join(f"{ts[i]:6.0f}" for i in range(0,len(ts),max(1,len(ts)//14))))
    print("  MiB  :", " ".join(f"{mv[i]:6d}" for i in range(0,len(mv),max(1,len(mv)//14))))
