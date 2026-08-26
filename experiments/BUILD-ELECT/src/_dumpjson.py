import json, pathlib
for tag, p in (("flower-bud", r"C:\dev\strehl-out\BUILD-ELECT\h5-flower-bud.json"),
               ("bee", r"C:\dev\strehl-out\BUILD-ELECT\bee\h5-bee.json")):
    d = json.loads(pathlib.Path(p).read_text())["res"]
    print("=" * 72); print(tag)
    print(f"{'roi':<14}" + "".join(f"{s:>16}" for s in ("mean|g|","max|g|","hp max|g|","_lp max|g|")))
    for roi, st in d.items():
        row = f"{roi:<14}"
        for s in ("mean|g|","max|g|","hp max|g|","_lp max|g|"):
            v = st[s]
            row += f"{'f%d %.2fx' % (v['argmax'], v['range']):>16}"
        print(row)
        print(f"{'':14}" + "".join(f"{'pk %.1f' % st[s]['peak']:>16}" for s in ("mean|g|","max|g|","hp max|g|","_lp max|g|")))
