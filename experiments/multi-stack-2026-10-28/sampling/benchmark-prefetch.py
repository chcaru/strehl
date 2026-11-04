"""ABBA cold-transfer, warm-original-CFA benchmark; fresh separate cache per arm."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
base=root/"outputs/multi-stack"
order=[("a1",6),("b1",7),("b2",7),("a2",6)]
for label,version in order:
 cache=base/f"prefetch-cache-{label}";cache.mkdir(exist_ok=False)
 for source in (base/"source-cache").iterdir():
  if source.suffix==".cfa" or source.name.startswith("alignment-"):
   shutil.copy2(source,cache/source.name)
 assert len(list(cache.glob("*.cfa")))==10
 assert not list(cache.glob("transfer-*"))
for label,version in order:
 command=[sys.executable,"-X","faulthandler","experiments/multi-stack-2026-10-28/run-command.py","--receipt",f"outputs/multi-stack/prefetch-{label}-run","--cwd",str(root),"--env","RAYON_NUM_THREADS=16","--env","STREHL_EXPERIMENT_CONTEXT=ABBA-cold-transfer-warm-originals-no-other-owned-render-or-build","--",f"outputs/multi-stack/candidate-{version}/strehl.exe","session","stack","outputs/multi-stack/manifests/insect-middle-five.json","--out-dir",f"outputs/multi-stack/prefetch-{label}","--alignment","outputs/multi-stack/pilot-4/alignment.json","--cache",f"outputs/multi-stack/prefetch-cache-{label}","--threads","16","--memory-limit-gib","16"]
 subprocess.run(command,cwd=root,check=True)
print("All four benchmark arms completed")
