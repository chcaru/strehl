"""Exercise held-photon exclusion through the actual frozen patch producer.
The recording ndarray forwards exactly to ndarray matmul; it changes no arithmetic.
"""
import importlib.util,copy,json,hashlib,sys
from pathlib import Path
folder=Path(__file__).parent
s=importlib.util.spec_from_file_location("producer",folder/"repeat-forward-cosine-controls.py");h=importlib.util.module_from_spec(s);s.loader.exec_module(h);np=h.np
original_fit=h.core.linear_fit;original_rng=np.random.default_rng

class Recorded(np.ndarray):
    def __new__(cls,array,record):
        result=np.asarray(array).view(cls);result.record=record;return result
    def __array_finalize__(self,other):self.record=getattr(other,"record",None)
    def __matmul__(self,other):
        result=np.asarray(self)@np.asarray(other)
        self.record["products"].append(hashlib.sha256(result.tobytes()).hexdigest())
        return result
    def __sub__(self,other):return np.asarray(self)-np.asarray(other)

def run(p,poison):
    records=[]
    def fit(*args,**kwargs):
        f=original_fit(*args,**kwargs);r={"operator":hashlib.sha256(f["B"].tobytes()+f["sigma"].tobytes()).hexdigest(),"products":[]};records.append(r);f["B"]=Recorded(f["B"],r);return f
    class Draw:
        def __init__(self,seed):self.base=original_rng(seed);self.change=seed.entropy[3]==5
        def standard_normal(self,n):
            x=self.base.standard_normal(n)
            if self.change and poison=="finite":x+=5
            if self.change and poison=="clipped":x[:]=1e7
            return x
    h.core.linear_fit=fit;np.random.default_rng=Draw
    try:rows,footprints=h.patch_job(p,"high",0)
    finally:h.core.linear_fit=original_fit;np.random.default_rng=original_rng
    return rows,records

def main():
    out=Path(sys.argv[1]);assert not out.exists()
    p=json.loads((folder/"repeat-forward-cosine-protocol.json").read_text());p["seeds"]=[208,209]
    baseline,br=run(p,"none");changed,cr=run(p,"finite");clipped,kr=run(p,"clipped")
    assert len(br)==len(cr)==len(kr)==36
    for a,b,c in zip(br,cr,kr):assert a["operator"]==b["operator"]==c["operator"],"held values changed frozen model"
    checks=[]
    for color in range(3):
        full=color*12+10;row=color*6+5
        # Products are clean prediction followed by both noisy predictions.
        assert len(br[full]["products"])==3
        assert br[full]["products"]==cr[full]["products"]==kr[full]["products"]
        assert all(v["training_support"] and not v["held_support"] for v in clipped[row]["seeds"])
        assert all(a["whitened_squared_residual"]!=b["whitened_squared_residual"] for a,b in zip(baseline[row]["seeds"],changed[row]["seeds"]))
        assert any(br[color*12+hold*2]["products"]!=cr[color*12+hold*2]["products"] for hold in range(5)),"poison never reached training folds"
        checks.append({"color":color,"held_acquisition":p["target_globals"][5],"exact_operator_and_prediction_bits":True,"finite_poison_changes_only_held_score_in_its_fold":True,"clipped_held_retains_training_prediction_but_refuses_scoring":True})
    sources=[Path(__file__),folder/"repeat-forward-cosine-controls.py",folder/"repeat-forward-cosine.py",folder/"repeat-forward-model.py",folder/"repeat-forward-cosine-protocol.json"]
    out.write_text(json.dumps({"schema":"strehl.original-forward-held-isolation.v1","command":sys.argv,"sources":{str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},"checks":checks,"all_passed":True,"original_reads":0,"product_admission":False,"scope":"Actual patch producer with independent known variance oracle and conditional fixed geometry. Does not establish independence for a future noisy-guide caller."},indent=2)+"\n")
if __name__=="__main__":main()
