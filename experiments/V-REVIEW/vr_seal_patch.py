import os
F = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\vr_lib.py"
d = open(F, "rb").read()

anchor = b'def render_frame(subj, k, out_tiff, timeout=900):\r\n'
assert d.count(anchor) == 1, "render_frame not found once"

seal = (b'def seal_render(out_tiff, cmd=None, env=None):\r\n'
        b'    """Write the same seal the acceptance harness writes on a master.\r\n'
        b'\r\n'
        b'    A render without a seal cannot be audited the way a shipped master\r\n'
        b'    can. The seal is the whole reason a cross-gauge comparison is\r\n'
        b'    detectable after the fact rather than merely suspected.\r\n'
        b'    """\r\n'
        b'    h = _sha256(EXE)\r\n'
        b'    with open(out_tiff + ".ok", "w") as f:\r\n'
        b'        f.write(h)\r\n'
        b'    with open(out_tiff + ".provenance.txt", "w") as f:\r\n'
        b'        f.write("binary   %s\\n" % EXE)\r\n'
        b'        f.write("pin      %s\\n" % EXE_PIN)\r\n'
        b'        f.write("sha256   %s\\n" % h)\r\n'
        b'        f.write("corpus   %s (seal %s)\\n" % (ARM, CORPUS_SEAL))\r\n'
        b'        if cmd is not None:\r\n'
        b'            f.write("command  %s\\n" % " ".join(cmd))\r\n'
        b'        for k in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE",\r\n'
        b'                  "STREHL_EDGE_TAU", "STREHL_EDGE_CONF",\r\n'
        b'                  "STREHL_ONLY_FRAME"):\r\n'
        b'            v = "<cleared>" if env is None else env.get(k, "<cleared>")\r\n'
        b'            f.write("%-18s %s\\n" % (k, v))\r\n'
        b'    return out_tiff + ".ok"\r\n'
        b'\r\n'
        b'\r\n')

d = d.replace(anchor, seal + anchor)

old_ret = (b'        raise RuntimeError("render failed rc=%d\\n%s" % (p.returncode, log[-2000:]))\r\n'
           b'    return log\r\n')
assert d.count(old_ret) == 1, "render_frame tail not found once"
new_ret = (b'        raise RuntimeError("render failed rc=%d\\n%s" % (p.returncode, log[-2000:]))\r\n'
           b'    seal_render(out_tiff, cmd, env)\r\n'
           b'    return log\r\n')
d = d.replace(old_ret, new_ret)
open(F, "wb").write(d)
print("patched", len(d))
