"""Display retained originals; does not rerun or qualify the refused diagnostic."""
from pathlib import Path
import json,hashlib,importlib.util,sys,math
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
root=HERE.parents[1]
def read(p):return json.loads(p.read_text())
def binding(p):return {"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
def check(p,b):assert binding(p)=={k:b[k] for k in ("bytes","sha256")}
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+"\n")
r=HERE/"run-1"
check(r/"decode-comparison.json",{"bytes":4091,"sha256":"44d187f25f0bc84c272b776981e1a662720bbf6f82ce17ce1feca39122a1a602"})
comparison=read(r/"decode-comparison.json")
assert comparison["all_identical"] and [v["different_sensels"] for v in comparison["rows"]]==[0,0]
spec=importlib.util.spec_from_file_location("cached_context",HERE/"inspect.py")
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
a.fixed()
warp=a.sampler.clib.parse_warpmap(str(a.old.MAP))
views={};masks={};counts=[];inputs=[]
ox,oy,rw,rh=a.RAW_ROI
tx,ty,tw,th=a.TARGET
for i in a.INDICES:
 receipt=read(r/f"primary-{i}.json")
 assert receipt["sources"]==a.source_bindings()
 rawpath,_=a.input_path(i);check(rawpath,receipt["raw_input"])
 path=r/f"raw-{i}.npy";check(path,receipt["raw"])
 patch=np.load(path,allow_pickle=False);assert patch.shape==(rh,rw) and patch.dtype==np.uint16
 inputs.append({"index":i,"raw":receipt["raw"],"metadata":receipt["original_metadata"]})
 yy,xx=np.indices(patch.shape);xx+=ox;yy+=oy
 boxes={"sensor":(float(tx),float(ty),float(tx+tw),float(ty+th))}
 aa,bb=warp["placements"][i]
 pts=[tuple(2*v for v in a.sampler.clib.apply_at(aa,bb,x/2,y/2,1758,1172)) for x,y in ((tx,ty),(tx+tw,ty),(tx,ty+th),(tx+tw,ty+th))]
 boxes["scene_bounding_box"]=(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
 for gauge,(x0,y0,x1,y1) in boxes.items():
  assert ox<=x0<x1<=ox+rw and oy<=y0<y1<=oy+rh
  region=(xx>=x0)&(xx<x1)&(yy>=y0)&(yy<y1)
  counts.append({"index":i,"gauge":gauge,"native_bounds":[x0,y0,x1,y1],"samples":int(region.sum()),"at_or_above_product_white15360":int(((patch>=15360)&region).sum()),"at_or_above_libraw_white16383":int(((patch>=16383)&region).sum())})
 for name,(dx,dy) in a.PHASES.items():
  raw=patch[dy::2,dx::2];ch=receipt["decoder"]["raw_pattern"][dy][dx]
  views[(i,name)]=raw.astype(np.float32)-np.float32(receipt["decoder"]["black_level_per_channel"][ch])
  mask=np.zeros(raw.shape+(3,),dtype=np.uint8)
  mask[raw>=15360]=(255,0,255);mask[raw>=16383]=(255,255,0)
  masks[(i,name)]=mask
out=HERE/"view-2";out.mkdir()
lo,hi=np.percentile(np.concatenate([v.ravel() for v in views.values()]),[2,98]).tolist()
assert hi>lo
files=[]
for label,low,high in (("fixed-dn",0.,14848.),("pooled-inspection-only",lo,hi),("white-threshold-masks",None,None)):
 canvas=Image.new("RGB",(764,614),"white");draw=ImageDraw.Draw(canvas)
 for row,name in enumerate(a.PHASES):
  for col,i in enumerate(a.INDICES):
   left,top=10+382*col,25+286*row
   pixels=masks[(i,name)] if low is None else np.rint(np.clip((views[(i,name)]-low)/(high-low),0,1)*255).astype(np.uint8)
   canvas.paste(Image.fromarray(pixels).convert("RGB"),(left,top))
   dx,dy=a.PHASES[name]
   draw.text((left,top-15),f"frame{i} {name}: native({ox+dx},{oy+dy}), step2",fill="black")
 if low is None:
  draw.text((10,584),"Magenta: code>=product white15360. Yellow: code>=LibRaw white16383.",fill="black")
 else:
  draw.text((10,584),f"{label}: {low:.1f}..{high:.1f} black-sub DN. No spatial resampling.",fill="black")
 draw.text((10,599),"All full-ROI green samples retained; no correction or diagnostic pass.",fill="black")
 p=out/(label+".png");canvas.save(p);files.append({"name":p.name,**binding(p),"range_dn":None if low is None else[low,high]})
save(out/"receipt.json",{"status":"DISPLAY_ONLY_ORIGINAL_GATE_STILL_FAILED","source":binding(Path(__file__)),"amendment":binding(HERE/"display-amendment.md"),"comparison":binding(r/"decode-comparison.json"),"inputs":inputs,"target_threshold_counts":counts,"views":files,"sampling":"one original green sample per displayed pixel, native spacing2; no resizing or per-panel normalization","limits":"Scene counts use axis-aligned mapped target bounding boxes; no absence, attenuation, physical-dust, noise or correction inference from saturated samples."})
print(json.dumps({"target_threshold_counts":counts,"files":files},indent=2))
