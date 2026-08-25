import hashlib, os
r = os.path.join(os.environ["LOCALAPPDATA"], "strehl", "warpmaps")
pre  = os.path.join(r, "dry-erase-marker-head-cpl-57fff568a7ede183.warpmap.txt")  # pre-fix key, 11:53
post = os.path.join(r, "dry-erase-marker-head-cpl-217a1d6e743b0829.warpmap.txt")  # post-fix key, 15:03
a = open(pre,"rb").read(); b = open(post,"rb").read()
print("pre-fix  key entry :", len(a), hashlib.sha256(a).hexdigest()[:16].upper())
print("post-fix key entry :", len(b), hashlib.sha256(b).hexdigest()[:16].upper())
print("BYTE-IDENTICAL     :", a == b)
if a != b:
    la, lb = a.decode().splitlines(), b.decode().splitlines()
    print("line count", len(la), len(lb))
    d = [(i, x, y) for i,(x,y) in enumerate(zip(la,lb)) if x != y]
    print("differing lines:", len(d))
    for i,x,y in d[:6]: print(f"  L{i}: {x[:70]!r} != {y[:70]!r}")
