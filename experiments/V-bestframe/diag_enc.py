from pathlib import Path
import re
p = Path(r"C:\dev\strehl-out\V-BESTFRAME\survey.log")
raw = p.read_bytes()
print("bytes:", len(raw), " first 24:", raw[:24])
txt = p.read_text(errors="ignore")
print("chars after read_text:", len(txt), " lines:", len(txt.splitlines()))
HDR = re.compile(r"^(\S+): (\d+) frames on disk, probing (\d+) ADJACENT PAIRS")
hits = [l for l in txt.splitlines() if HDR.match(l)]
print("HDR matches:", len(hits))
cand = [l for l in txt.splitlines() if "frames on disk" in l]
print("lines containing 'frames on disk':", len(cand))
if cand:
    print("repr of first such line:", repr(cand[0][:90]))
