"""Known-field approximation census; no random photons or actual capture reads.
All five contexts and all fixed positions retained. Not a model-selection API.
"""
import importlib.util,json,hashlib,sys,copy,math,concurrent.futures
from pathlib import Path
folder=Path(__file__).parent
spec=importlib.util.spec_from_file_location("producer",folder/"repeat-forward-cosine-controls.py")
producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
np=producer.np
FREQUENCIES=[[(.28,.06,1.,.3),(.08,.29,.7,1.1),(.27,-.22,.45,.7)],[(.29,.25,1.,.3),(.31,-.25,.7,1.1),(.06,.28,.45,.7)],[(.28,.06,1.,.3),(.08,.29,.7,1.1),(.27,-.22,.45,.7)]]
CASES=["tone0","tone1","tone2","curved","edge"]

def truth_for(case):
    def truth(sites,pull,full,origin,unused_case,source,color):
        a=np.asarray(pull["a"]);b=np.asarray(pull["b"])
        inverse=np.linalg.inv(np.array([[a[0],-a[1]],[a[1],a[0]]]))
        reference=(sites-np.asarray(full)-.5-2*b)@inverse.T+np.asarray(full)+.5-origin
        result=np.full(len(sites),1200.+180*color)
        frequencies=[FREQUENCIES[color][int(case[-1])]] if case.startswith("tone") else FREQUENCIES[color]
        for fx,fy,strength,phase in frequencies:
            f=np.array([fx,fy]); result+=120*strength*np.prod(np.sinc(f@inverse))*np.sin(2*math.pi*(reference@f)+phase)
        if case=="curved":
            # Exact square-aperture second moments under the inverse physical map.
            aperture_variance=np.sum(inverse**2,axis=1)/12
            result+=.02*((reference[:,0]-80)**2+aperture_variance[0])+.01*((reference[:,1]-80)**2+aperture_variance[1])
        if case=="edge":
            # Independent quadrature of the pre-aperture smooth edge; unlike a
            # point evaluation this includes every original sensor-square area.
            q,w=np.polynomial.legendre.leggauss(16)
            offsets=np.array([[x/2,y/2] for y in q for x in q])@inverse.T
            weights=np.array([x*y/4 for y in w for x in w])
            z=reference[:,None,:]+offsets[None,:,:]
            result+=180*(np.tanh((z[:,:,0]+.3*z[:,:,1]-80)/.8)@weights)
        return result.astype(np.float32)
    return truth

def main():
    destination=Path(sys.argv[1]);assert not destination.exists()
    protocol=folder/"repeat-forward-cosine-protocol.json";p=json.loads(protocol.read_text());p["seeds"]=[]
    all_rows=[]
    for side,score,n,low in p["bias_variants"]:
        q=copy.deepcopy(p);q.update(fit_side_sensor=side,score_side_sensor=score,basis_axis=n,restricted_basis_axis=low)
        for case in CASES:
            producer.expected_signal=truth_for(case)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                outputs=list(pool.map(lambda j:producer.patch_job(q,"high",j),range(25)))
            rows=[v for result,footprints in outputs for v in result]
            for row in rows:row.update(context=[side,score,n,low],truth=case)
            all_rows.extend(rows)
            print("complete",[side,score,n,low],case,"supported",sum(v["support"] for v in rows),flush=True)
    sources=[Path(__file__),protocol,folder/"repeat-forward-cosine-controls.py",folder/"repeat-forward-cosine.py",folder/"repeat-forward-model.py"]
    result={"schema":"strehl.original-forward-known-field-bias.v1","command":sys.argv,"sources":{str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},"rows":all_rows,"frequencies_by_color":FREQUENCIES,"workers":4,"original_reads":0,"product_admission":False,"scope":"Known continuous fields independently integrated over source sensor-square apertures. Fixed oracle temporal noise weights only; no noisy values. Every context, fold, color and failed patch retained. This compares model approximation bias, not measured camera PSF. No model choice from real residuals."}
    destination.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":main()
