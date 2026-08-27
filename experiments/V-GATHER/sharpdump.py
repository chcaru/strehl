import io, json, os
d = os.path.dirname(os.path.abspath(__file__))
for f in ("sharp.json", "sharp2.json"):
    p = os.path.join(d, f)
    if not os.path.exists(p):
        continue
    doc = json.load(io.open(p, encoding="utf-8"))
    print("== %s" % f)
    for k, v in sorted(doc.items()):
        if "refused" in v:
            print("  %-34s REFUSED  coarse=%s refined=%s frames=%s  %s"
                  % (k, v.get("n_coarse"), v.get("n_refined"),
                     v.get("n_frames"), v["refused"][:60]))
        else:
            print("  %-34s %+.2f%%  coarse=%s refined=%s qual=%s"
                  % (k, 100 * v["deficit_median"], v.get("n_coarse"),
                     v.get("n_refined"), v.get("n_qualified")))
