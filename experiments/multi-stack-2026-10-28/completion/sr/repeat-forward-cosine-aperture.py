"""Independent numerical-aperture oracle for exact cosine sampling rows."""
import importlib.util,json,sys,hashlib
from pathlib import Path
folder=Path(__file__).parent;s=importlib.util.spec_from_file_location("cosine",folder/"repeat-forward-cosine.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);np=m.np
p=json.loads((folder/"repeat-forward-cosine-protocol.json").read_text());full=p["full_quad_geometry"];center=np.array(p["positions_sensor"][0]);pull={"a":[1.017,.021],"b":[.31,-.27]};n=p["basis_axis"];side=p["fit_side_sensor"]
q,w=np.polynomial.legendre.leggauss(32);offsets=np.array([[x/2,y/2] for y in q for x in q]);weights=np.array([x*y/4 for y in w for x in w]);a,b=np.array(pull["a"]),np.array(pull["b"]);mat=np.array([[a[0],-a[1]],[a[1],a[0]]]);gauge=np.array(full)+.5;inv=np.linalg.inv(mat);results=[]
for color in range(3):
 sites=m.base.original_sites(pull,full,center,8,color);rows=m.rows(sites,pull,full,center,side,n);assert np.array_equal(rows[:,0],np.ones(len(sites),dtype=np.float32))
 ref=(sites[:,None,:]+offsets-gauge-2*b)@inv.T+gauge-center+side/2
 for k,l in [(0,0),(3,7),(17,0),(0,17),(17,17),(9,13)]:
  expected=(np.cos(np.pi*k*ref[:,:,0]/side)*np.cos(np.pi*l*ref[:,:,1]/side))@weights
  error=float(np.max(np.abs(expected-rows[:,k*n+l])));assert error<5e-6,(color,k,l,error)
  results.append({"color":color,"mode":[k,l],"max_abs_error":error})
out=Path(sys.argv[1]);assert not out.exists();out.write_text(json.dumps({"command":sys.argv,"sources":{n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in [Path(__file__).name,"repeat-forward-cosine.py","repeat-forward-model.py","repeat-forward-cosine-protocol.json"]},"rows":results,"checks_pass":18,"original_reads":0},indent=2)+'\n',encoding='utf-8');print('18 independent aperture checks passed')
