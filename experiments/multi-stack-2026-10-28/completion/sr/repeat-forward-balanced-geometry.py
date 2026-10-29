"""Independent balanced six-phase structural positive; no photons/no model changes."""
from pathlib import Path
import importlib.util,json,sys,copy,hashlib
path=Path(__file__).with_name("repeat-forward-controls.py");s=importlib.util.spec_from_file_location("controls",path);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
p=json.loads(path.with_name("repeat-forward-protocol.json").read_text());q=copy.deepcopy(p)
phases=[[x,y] for y in [0.,1.] for x in [0.,2/3,4/3]]
for source,(x,y) in zip(q["sources"],phases):source["consuming_color_pulls"]=[{"a":[1.,0.],"b":[x/2,y/2]} for _ in range(3)]
r={"schema":"strehl.balanced-phase-forward-geometry.v1","command":sys.argv,"phases_sensor":phases,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"model_sha256":hashlib.sha256(c.core_path.read_bytes()).hexdigest() if hasattr(c,"core_path") else hashlib.sha256(path.with_name("repeat-forward-model.py").read_bytes()).hexdigest(),"rows":c.structural(q,"measured"),"original_reads":0,"product_admission":False}
out=Path(sys.argv[1]);assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r,indent=2))
