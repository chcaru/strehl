import json
for f in ("measure-subjects.json","measure-min.json"):
    d = json.load(open(r"C:\dev\strehl-out\BUILD-THESIS\\"+f))
    print("=== "+f)
    for r in d:
        ms = [t["match"] for t in r["tiles"]]
        med = sorted(ms)[len(ms)//2] if ms else None
        print(f"  {r['subject']:20s} ecc={r['ecc']:.4f} fitted_s={r['scale']:.4f} "
              f"logged={r['fov_scale_logged']} Ta={r['tiles'][0]['tile_px_argmax'] if r['tiles'] else '-'} "
              f"kept={r['tiles_kept']} drop={r['tiles_dropped_unmatchable']} "
              f"sig_a/m={r['sigma_ratio_argmax_over_merge']:.3f} medNCC={med:.3f}" if ms else
              f"  {r['subject']:20s} NO TILES")
