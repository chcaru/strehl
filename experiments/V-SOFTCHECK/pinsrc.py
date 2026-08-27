"""Read the SHIPPING source for the merge, at the pin, as BYTES.

The working tree has drifted from 9b05d0b7 and `git show > file` re-encodes on
Windows, which has produced a false failure on this project before.  Every quote
below comes from subprocess stdout decoded explicitly.

Purpose: the pyramid weighting scheme was RELAYED to me, not measured by me, and
three relayed structural claims have been wrong tonight.  Confirm or refute each
constant against the pin before any of it shapes an experiment.
"""
import subprocess, re, sys
PIN="9b05d0b7"
def blob(path):
    r=subprocess.run(["git","show",f"{PIN}:{path}"],capture_output=True)
    if r.returncode!=0:
        return None
    return r.stdout.decode("utf-8",errors="replace")
src=blob("crates/strehl-core/src/pyramid.rs")
print(f"pyramid.rs at {PIN}: {'ABSENT' if src is None else str(len(src))+' chars'}")
if src is None: sys.exit("cannot proceed without the shipping merge source")
claims={
 "DEFAULT_MERGE_BACKEND": r"DEFAULT_MERGE_BACKEND[^\n]*",
 "MAX_EXPONENT":          r"MAX_EXPONENT[^\n]*=[^\n]*",
 "exponent 2.0":          r"exponent\s*:\s*[0-9.]+",
 "sharpen_per_octave":    r"sharpen_per_octave\s*:\s*[0-9.]+",
 "SoftPower":             r"SoftPower[^\n]*",
 "SNR_REF":               r"SNR_REF[^\n]*",
}
for name,pat in claims.items():
    hits=[]
    for f in ["crates/strehl-core/src/pyramid.rs","crates/strehl-core/src/merge.rs",
              "crates/strehl-cli/src/merge_cmd.rs"]:
        s=blob(f)
        if s: hits += [(f,m.strip()) for m in re.findall(pat,s)][:2]
    print(f"\n  {name}:")
    if not hits: print("    NOT FOUND at pin  <-- relayed claim unconfirmed")
    for f,h in hits[:3]: print(f"    {f.split('/')[-1]}: {h[:110]}")
# the weight formula itself, quoted rather than paraphrased
m=re.search(r"[^\n]*powf[^\n]*", src)
print(f"\n  weight exponentiation site: {m.group(0).strip()[:120] if m else 'NOT FOUND'}")
