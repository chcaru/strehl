import io, sys
F = "vc_ca.py"
t = io.open(F, encoding="utf-8").read()

# site tuple gains `align`; the normal-projection factor was never divided out.
old1 = """            if al < 0:
                n = -n                                     # make n point OUTWARD
            out.append((py, px, n[0], n[1], r, m))"""
new1 = """            if al < 0:
                n = -n                                     # make n point OUTWARD
                al = -al
            out.append((py, px, n[0], n[1], r, m, al))"""
if t.count(old1) != 1: sys.exit("ANCHOR1 (%d)" % t.count(old1))
t = t.replace(old1, new1, 1)

old2 = """    for (py, px, nx, ny, r, m) in S:"""
new2 = """    for (py, px, nx, ny, r, m, al) in S:"""
if t.count(old2) != 1: sys.exit("ANCHOR2 (%d)" % t.count(old2))
t = t.replace(old2, new2, 1)

# THE DEFECT: an edge only reveals the component of the displacement along its
# normal, s = d_radial * (n . rhat). Dividing by `al` recovers d_radial itself.
old3 = """        dR.append(sr); dB.append(sb)
        ppmR.append(sr / r * 1e6); ppmB.append(sb / r * 1e6)
        used.append((py, px, nx, ny, r, m))"""
new3 = """        sr /= al; sb /= al          # normal component -> radial displacement
        dR.append(sr); dB.append(sb)
        ppmR.append(sr / r * 1e6); ppmB.append(sb / r * 1e6)
        used.append((py, px, nx, ny, r, m, al))"""
if t.count(old3) != 1: sys.exit("ANCHOR3 (%d)" % t.count(old3))
t = t.replace(old3, new3, 1)

io.open(F, "w", newline="\n", encoding="utf-8").write(t)
print("patched vc_ca.py: align (n.rhat) now divided out")
