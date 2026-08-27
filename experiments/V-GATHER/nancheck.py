import io, json, math, os
d = os.path.dirname(os.path.abspath(__file__))
for name in ("cert.json", "rim.json", "dust.json", "sharp.json"):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        continue
    raw = io.open(p, encoding="utf-8").read()
    bad_tokens = [t for t in ("NaN", "Infinity", "-Infinity") if t in raw]
    obj = json.loads(raw)
    nan_paths = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "[%d]" % i)
        elif isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            nan_paths.append(path)

    walk(obj, name)
    print("%-12s subjects=%-3d raw non-finite tokens=%-20s non-finite values=%d"
          % (name, len(obj), bad_tokens or "none", len(nan_paths)))
    for q in nan_paths[:20]:
        print("     ", q)
