"""Read the fixed colour and displaced controls with existing TIFF and metric code."""
from pathlib import Path
import importlib.util,json,sys,hashlib,time,io
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);v=importlib.util.module_from_spec(s);sys.modules[name]=v;s.loader.exec_module(v);return v
q=load("boundary_control_score",HERE/"score.py")
m=q.module("boundary_control_metrics","independent-quality-metrics.py")
reader=q.module("boundary_control_reader","independent-rgb-tiff.py")
budget=m.Budget("score",start_cpu=time.process_time(),start_wall=time.perf_counter())
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def ref(p):
 raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
out=HERE/"control-readout-1";out.mkdir()
plan=dict(schema="native-boundary-radiance-control-readout-v1",source=ref(Path(__file__)),expected_failure_inputs=["identical grayscale channels cannot witness genuine-colour identity","displaced boundary that changes no pixel is an inactive model destroyer"],metric_scope="wrong-model error ordering is reported, not used to rescue the rejected candidate")
(out/"plan.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
def image(row):
 p,_=q.bound_bytes(row["output"],ROOT);_,raw=q.bound_bytes(row["receipt"],ROOT);meta=json.loads(raw)["output"]
 a,e=reader.read_rgb_tiff(p,(meta["height"],meta["width"],3),row["output"]["sha256"],budget)
 return a,e
colour_index=read(HERE/"run-color-1/run-index.json")
before,eb=image(colour_index["rows"][0]);after,ea=image(colour_index["rows"][1])
assert m.np.array_equal(before,after)
rmg=before[:,:,0].astype("f8")-before[:,:,1]
bmg=before[:,:,2].astype("f8")-before[:,:,1]
colour=dict(decoded_pixel_identity=True,red_green_nonzero=int(m.np.count_nonzero(rmg)),blue_green_nonzero=int(m.np.count_nonzero(bmg)),red_green_range=float(m.np.ptp(rmg)),blue_green_range=float(m.np.ptp(bmg)),pixels=before.shape[0]*before.shape[1])
assert colour["red_green_range"]>0 and colour["blue_green_range"]>0 and colour["red_green_nonzero"]>0 and colour["blue_green_nonzero"]>0,"colour fixture cannot expose erasure"
del before,after,rmg,bmg
matrix=read(HERE/"run-textured-1/run-index.json")
rows={r["mode"]:r for r in matrix["rows"] if r["seed"] is None}
rows["displaced"]=read(HERE/"run-displaced-1/run-index.json")["rows"][0]
mask=m.regions((226,300),(10,8),budget)
scalar=m.np.load(q.OLD/"independent-quality-target-1/scalar.npy",allow_pickle=False)
assert ref(q.OLD/"independent-quality-target-1/scalar.npy")["sha256"]==q.TARGET_SHA
records=[];pixel_hashes={}
for mode,row in rows.items():
 rgb,e=image(row);pixel_hashes[mode]=hashlib.sha256(rgb.tobytes()).hexdigest()
 rgb=rgb.astype("f8")*(14848.0/65535.0)
 for ci,channel in enumerate(("R","G","B")):
  target=scalar[8:234,10:310]*(.25*q.module("boundary_control_constants","independent-quality-readout.py").FACTORS[ci]*q.module("boundary_control_wb","independent-quality-readout.py").WB[ci])
  for region in ("window","boundary"):
   records.append(dict(mode=mode,channel=channel,region=region,**m.errors(rgb[:,:,ci],target,mask[region],budget)))
 del rgb
assert pixel_hashes["apply"]!=pixel_hashes["displaced"],"displaced model did not change decoded output"
ordering=[]
for channel in ("R","G","B"):
 a=next(r for r in records if (r["mode"],r["channel"],r["region"])==("apply",channel,"boundary"))
 d=next(r for r in records if (r["mode"],r["channel"],r["region"])==("displaced",channel,"boundary"))
 ordering.append(dict(channel=channel,correct_model_mse_dn2=a["mse_dn2"],displaced_mse_dn2=d["mse_dn2"],displaced_is_worse=d["mse_dn2"]>a["mse_dn2"]))
result=dict(schema="native-boundary-radiance-control-readout-v1",colour=colour,noise_off_errors=records,displaced_ordering=ordering,pixel_hashes=pixel_hashes,inputs=[ref(HERE/p/"run-index.json") for p in ("run-color-1","run-textured-1","run-displaced-1")],work=budget.receipt(),scope="independent decoder colour witness and fixed wrong-model diagnostic; no quality acceptance")
(out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps(dict(colour=colour,displaced_ordering=ordering)))

