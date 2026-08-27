import json, hashlib
pre  = json.load(open(r"C:\Users\chris\AppData\Local\Temp\V-TRIAGE-pin\triage.json",  encoding="utf-8"))
post = json.load(open(r"C:\Users\chris\AppData\Local\Temp\V-TRIAGE-pin2\triage.json.live", encoding="utf-8"))
def h(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()[:16]
print("top-level keys  pre : %s" % sorted(pre.keys()))
print("top-level keys  post: %s" % sorted(post.keys()))
print()
for k in sorted(set(pre) | set(post)):
    a, b = pre.get(k), post.get(k)
    print("  %-12s pre=%s post=%s   %s"
          % (k, h(a) if a is not None else "-------- ",
             h(b) if b is not None else "-------- ",
             "SAME" if h(a) == h(b) else "*** DIFFERS ***"))
print()
print("rows identical? %s   (n_pre=%d n_post=%d)"
      % (h(pre["rows"]) == h(post["rows"]), len(pre["rows"]), len(post["rows"])))
print()
# which field definitions changed
pf, qf = pre.get("fields", {}), post.get("fields", {})
print("field-def keys added  : %s" % sorted(set(qf) - set(pf)))
print("field-def keys removed: %s" % sorted(set(pf) - set(qf)))
ch = [k for k in set(pf) & set(qf) if pf[k] != qf[k]]
print("field-def TEXT changed: %s" % sorted(ch))
