"""Re-run M189's unmodified v2 main, redirecting only its output directory."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "M189-noise-colour-detail"
sys.path.insert(0, str(SOURCE))
import commission_v2

before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
          for p in SOURCE.iterdir() if p.is_file()}
commission_v2.OUT = HERE / "out" / "reproduction"
commission_v2.main()
original = json.loads((SOURCE / "out/v2-commission.json").read_text())
rerun = json.loads((commission_v2.OUT / "v2-commission.json").read_text())
keys = ("fixture", "measurements", "score_ratios", "local_score_ratios",
        "raw_coherent_ratios")
matches = {key: original[key] == rerun[key] for key in keys}
assert all(matches.values()), matches
assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in SOURCE.iterdir() if p.is_file()}
evidence = {"numerical_payload_exact": matches, "original_source_unchanged": True,
            "argv": sys.argv, "source_sha256": before}
(HERE / "out/reproduction-check.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("REPRODUCTION: all measurements, ratios, fixture fields and scene hashes EXACT")
print("SOURCE_FILES: unchanged")
