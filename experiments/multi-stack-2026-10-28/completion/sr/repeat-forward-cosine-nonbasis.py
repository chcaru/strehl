"""Fixed noisy curved/edge plants with full sensor-aperture truth integration."""
import importlib.util,json,hashlib,sys
from pathlib import Path
folder=Path(__file__).parent
s=importlib.util.spec_from_file_location("bias",folder/"repeat-forward-cosine-bias.py");b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
assert sys.argv[2] in ["curved","edge"]
b.producer.expected_signal=b.truth_for(sys.argv[2])
b.producer.main()
p=Path(sys.argv[1]);result=json.loads(p.read_text())
for source in [Path(__file__),folder/"repeat-forward-cosine-bias.py"]:result["sources"][str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
result["truth_override"]="Independent sensor-square aperture integral: analytic Fourier/quadratic,16x16 Gauss smooth edge; all fields identical across acquisitions."
p.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
