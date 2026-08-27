import subprocess, pathlib, re
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
for flag in ["--pyramid-select","--pyramid-base","--fix-ca","--resampler","--photometric","--merge"]:
    r=subprocess.run([NEW,"stack",SUB,"--limit","2","--out",r"C:\dev\strehl-out\V-REVIEW\h.tiff",flag,"ZZbogusZZ"],capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    err=[l.strip() for l in log.splitlines() if "valid" in l.lower() or "unknown" in l.lower() or "possible" in l.lower() or "known" in l.lower()]
    print("%-18s -> %s" % (flag, (" | ".join(err))[:300] if err else "(no value list) "+log.strip().splitlines()[-1][:160] if log.strip() else "(silent)"))
