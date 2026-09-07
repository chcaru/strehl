"""Small exploratory shape control before reusing the M25 scene producer."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(ROOT / "experiments/m25-simulator/src"))
from strehl_sim.render import similarity_warp

plane = np.zeros((9,13),dtype=float)
plane[4,6] = 1
rgb = np.stack([plane,plane*2,plane*3],axis=-1)
rows = []
for name, image, scale, accepted in (("scalar-identity",plane,1.0,True),
        ("scalar-scale",plane,1.01,True),("rgb-identity",rgb,1.0,True),("rgb-scale",rgb,1.01,False)):
    try:
        result = similarity_warp(image,scale,6.5,4.5,0,0,0,3)
        assert accepted, name
        rows.append({"name":name,"accepted":True,"shape":list(result.shape)})
    except ValueError as error:
        assert not accepted and "too many values to unpack" in str(error),str(error)
        rows.append({"name":name,"accepted":False,"error":str(error)})
source = ROOT / "experiments/m25-simulator/src/strehl_sim/render.py"
result = {"scope":"Exploratory API-shape control, not scene/optics commissioning",
          "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"controls":rows}
(HERE / "producer-scope.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
