"""Geometry-only exact-zero column diagnostic; no modified model/no photon reads."""
import importlib.util,json,sys,hashlib
from pathlib import Path
path=Path(__file__).with_name("repeat-forward-controls.py");s=importlib.util.spec_from_file_location("controls",path);c=importlib.util.module_from_spec(s);s.loader.exec_module(c);np=c.np;core=c.core
protocol_path=path.with_name("repeat-forward-protocol.json");p=json.loads(protocol_path.read_text());full=p["full_quad_geometry"];center=np.array(p["positions_sensor"][0]);side=p["fit_side_sensor"];rows=[]
for color,pulls in enumerate(c.pull_set(p,"measured")):
 sites=[core.original_sites(pull,full,center,side,color) for pull in pulls]
 aa=[core.rows(x,pull,full,center,side,p["basis_axis"]) for x,pull in zip(sites,pulls)]
 for hold in range(6):
  ids={tuple(x):i for i,x in enumerate(sites[hold])};hs=core.original_sites(pulls[hold],full,center,p["score_side_sensor"],color);hi=[ids[tuple(x)] for x in hs]
  at=np.concatenate([a for j,a in enumerate(aa) if j!=hold]);ah=aa[hold][hi];zero=np.all(at==0,axis=0);safe=bool(np.all(ah[:,zero]==0))
  r={"color":color,"hold":p["target_globals"][hold],"exact_zero_train_columns":int(zero.sum()),"held_zero_for_same_columns":safe}
  if safe:
   at=at[:,~zero];ah=ah[:,~zero]
   try:
    f=core.linear_fit(at,ah,np.full(len(at),276,dtype=np.float32),np.full(len(ah),276,dtype=np.float32))
    r.update({k:v for k,v in f.items() if k not in ["B","sigma","covariance","residual_cholesky"]})
   except core.Unknown as e:r["reason"]=str(e)
  rows.append(r)
out=Path(sys.argv[1]);assert not out.exists();out.write_text(json.dumps({"command":sys.argv,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"protocol_sha256":hashlib.sha256(protocol_path.read_bytes()).hexdigest(),"rows":rows,"raw_reads":0,"changed_model":False},indent=2)+"\n",encoding="utf-8");print(json.dumps(rows,indent=2))
