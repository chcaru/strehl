import subprocess, pathlib, re
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\head")
print("=== do the TONE ANCHORS move with --exposure? ===")
print("  (if they do, a slope measured through the curve conflates anchor change with gain)\n")
for v in ["-2","-1","0","1","2"]:
    o=OUT/("tb.tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","pyramid","--exposure",v],capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    tone=[l.strip() for l in log.splitlines() if l.strip().startswith("tone")]
    expo=[l.strip() for l in log.splitlines() if l.strip().startswith("exposure")]
    print("  --exposure %-4s  %s" % (v, tone[0][:88] if tone else "(no tone line)"))
    print("  %-15s  %s" % ("", expo[0][:88] if expo else ""))
    if o.exists(): o.unlink()
