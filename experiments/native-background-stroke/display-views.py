from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
p=Path("experiments/native-background-stroke/run-1")
r=json.loads((p/"result.json").read_text())
out=p/"unscaled-views";out.mkdir()
lo,hi=r["display"]["vmin"],r["display"]["vmax"]
rows=[]
for index in r["indices"]:
    for phase in ("G1","G2"):
        arrays=[np.load(p/f"view-{index}-{gauge}-{phase}.npy",allow_pickle=False) for gauge in ("sensor","scene")]
        gray=np.concatenate([np.rint(np.clip((a.astype(np.float64)-lo)/(hi-lo),0,1)*255).astype(np.uint8) for a in arrays],axis=1)
        assert gray.shape==(155,320)
        path=out/f"frame-{index}-{phase}.png"
        Image.fromarray(gray).save(path)
        rows.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),index=index,phase=phase))
(out/"views.json").write_text(json.dumps(dict(rows=rows,left="sensor",right="scene",display=[lo,hi],samples="onePNGpixel per originalphase-grid view value, no resizing"),indent=2)+"\n",encoding="utf-8")
print("10 direct320x155graystrips saved; no resampling or new pixels.")
