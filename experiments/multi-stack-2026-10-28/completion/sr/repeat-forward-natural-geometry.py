"""Geometry-only natural-boundary candidate; no raw or synthetic photons."""
import importlib.util,json,sys,hashlib,copy
from pathlib import Path
folder=Path(__file__).parent
s=importlib.util.spec_from_file_location("controls",folder/"repeat-forward-controls.py");c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
s=importlib.util.spec_from_file_location("natural",folder/"repeat-forward-natural.py");natural=importlib.util.module_from_spec(s);s.loader.exec_module(natural)
c.core.rows=natural.rows
p=json.loads((folder/"repeat-forward-natural-protocol.json").read_text());balanced=copy.deepcopy(p)
phases=[[x,y] for y in [0.,1.] for x in [0.,2/3,4/3]]
for source,(x,y) in zip(balanced["sources"],phases):source["consuming_color_pulls"]=[{"a":[1.,0.],"b":[x/2,y/2]} for _ in range(3)]
r={"command":sys.argv,"inputs":{n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in ["repeat-forward-model.py","repeat-forward-controls.py","repeat-forward-natural.py","repeat-forward-natural-protocol.json"]},"rows":{mode:c.structural(protocol,kind) for mode,protocol,kind in [("measured",p,"measured"),("balanced",balanced,"measured"),("duplicate",p,"duplicate-phase"),("one-axis",p,"one-axis")]},"raw_reads":0,"photons_generated":0,"product_admission":False}
out=Path(sys.argv[1]);assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
for mode,rows in r["rows"].items():print(mode,sum(v["eligible"] for v in rows),"of",len(rows),[(x["color"],x["held_acquisition"],x.get("reason",x.get("condition"))) for x in rows])
