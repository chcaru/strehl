"""Fixed pale-circuit sensor-level census from retained independent RAW bytes."""
from pathlib import Path
import json,hashlib
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
source=HERE/"chip-source-review-1"
receipt=json.loads((source/"receipt.json").read_text())
raw=np.load(source/"source-visible-union.npy",allow_pickle=False)
assert hashlib.sha256(raw.tobytes()).hexdigest()==receipt["raw_u16_sha256"]
assert receipt["independent_decode_different_sensels"]==0
r=next(r for r in receipt["regions"] if r["name"]=="pale-circuit")
ux,uy,uw,uh=receipt["union_xywh"]
x,y=r["sensor_x"]-ux,r["sensor_y"]-uy
patch=raw[y:y+r["height"],x:x+r["width"]]
assert patch.shape==(384,384) and r["sensor_x"]%2==r["sensor_y"]%2==0
out=HERE/"chip-clip-census-1";out.mkdir()
counts=[]
for name,dx,dy in [("R",0,0),("G1",1,0),("G2",0,1),("B",1,1)]:
    v=patch[dy::2,dx::2]
    counts.append(dict(phase=name,sensels=v.size,maximum=int(v.max()),
        at_or_above_profile15360=int(np.count_nonzero(v>=15360)),
        profile15360_to16382=int(np.count_nonzero((v>=15360)&(v<16383))),
        exactly_container16383=int(np.count_nonzero(v==16383)),
        above_container16383=int(np.count_nonzero(v>16383))))
profile=patch>=15360; hard=patch==16383
positions=[]
for label,mask in [("profile15360",profile),("container16383",hard)]:
    yy,xx=np.nonzero(mask)
    np.save(out/(label+"-mask.npy"),mask,allow_pickle=False)
    positions.append(dict(label=label,count=int(mask.sum()),
        local_bbox_xywh=None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()-xx.min()+1),int(yy.max()-yy.min()+1)]))
img=tifffile.imread(HERE/"matched-chip-on-1/pale-circuit-frame149-raw.tiff")[4:-4,4:-4]
assert img.shape==(384,384,3)
fig,axes=plt.subplots(1,3,figsize=(12,4),dpi=120)
axes[0].imshow(img.astype(float)/65535,interpolation="nearest")
axes[0].set_title("Focused source: same MHC / tone")
for ax,mask,title,color in [(axes[1],profile,"RAW >= 15360 (profile level)",[0,1,1]),
    (axes[2],hard,"RAW == 16383 (container ceiling)",[1,0,1])]:
    ax.imshow(img.astype(float)/65535,interpolation="nearest")
    overlay=np.zeros((384,384,4));overlay[mask,:3]=color;overlay[mask,3]=0.9
    ax.imshow(overlay,interpolation="nearest")
    ax.set_title(title+f"\n{int(mask.sum())} sensels")
for ax in axes:ax.set_xticks([0,96,192,288,383]);ax.set_yticks([0,96,192,288,383])
fig.suptitle("DSC00150.ARW / fixed pale-circuit ROI / native sensor origin (1336,1108)")
fig.tight_layout();fig.savefig(out/"clip-locations.png");plt.close(fig)
result=dict(status="CENSUS_COMPLETE",source=receipt["source"],source_raw_sha256=receipt["raw_u16_sha256"],
    sensor_xywh=[r["sensor_x"],r["sensor_y"],384,384],sensels=int(patch.size),counts_by_phase=counts,
    positions=positions,scope="Presence/location only on a fixed original frame and ROI, no per-pixel winner selection. Profile threshold is not equated with ADC clipping; exact ceiling values are strong evidence of pinning but do not identify the sole fringe cause.")
(out/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
