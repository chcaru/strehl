"""Saved-result census only. No source pixels or model selection."""
import json,sys,hashlib,collections,math
from pathlib import Path
CASES=["flat-bright","flat-low","high","weak","common-lowpass","unequal-psf","blue-blur","wrong-geometry","wrong-blue-phase","motion","blue-motion","drift","phase-drift","blue-illumination","opposite","clipped","duplicate-phase","one-axis","measured-high","curved","edge"]
def main():
    root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
    summary=[];inputs={}
    for case in CASES:
        path=root/f"repeat-forward-cosine-{case}-01.json";d=json.loads(path.read_text());inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        e=d["fold_seed_evidence"];seeds=sorted({v["seed"] for v in e})
        row={"case":case,"counts":d["counts"],"seeds":seeds,"complete_cohort_consistent_seeds":[s for s in seeds if all(v["state"]=="ForwardModelConsistent" for v in e if v["seed"]==s)],"patch_models_available":sum(v["support"] for v in d["rows"]),"patch_models_total":len(d["rows"]),"by_color":[]}
        for color in range(3):
            ee=[v for v in e if v["color"]==color];rr=[v for v in d["rows"] if v["color"]==color and v["support"]];eeavailable=[v for v in ee if "prediction_truth_mse" in v];transfers=[v["clean"]["amplitude_transfer"] for v in rr if v["clean"]["amplitude_transfer"] is not None]
            row["by_color"].append({"color":color,"counts":dict(collections.Counter(v["state"] for v in ee)),"prediction_over_same_count_native_mse":None if not eeavailable else sum(v["prediction_truth_mse"]*v["held_samples"] for v in eeavailable)/sum(v["native_truth_mse"]*v["held_samples"] for v in eeavailable),"clean_transfer_range":None if not transfers else [min(transfers),max(transfers)],"whitened_energy_available_range":None if not eeavailable else [min(v["whitened_energy_per_sample"] for v in eeavailable),max(v["whitened_energy_per_sample"] for v in eeavailable)],"per_held_acquisition":{str(h):dict(collections.Counter(v["state"] for v in ee if v["held_acquisition"]==h)) for h in sorted({v["held_acquisition"] for v in ee})}})
        summary.append(row)
    path=root/"repeat-forward-cosine-bias-01.json";d=json.loads(path.read_text());inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();bias=[]
    for context in sorted({tuple(v["context"]) for v in d["rows"]}):
        for truth in ["tone0","tone1","tone2","curved","edge"]:
            for color in range(3):
                rr=[v for v in d["rows"] if tuple(v["context"])==context and v["truth"]==truth and v["color"]==color];good=[v for v in rr if v["support"]];transfers=[v["clean"]["amplitude_transfer"] for v in good if v["clean"]["amplitude_transfer"] is not None];n=sum(v["held_samples"] for v in good)
                bias.append({"context":context,"truth":truth,"color":color,"available":len(good),"total":len(rr),"transfer_available":len(transfers),"prediction_mse":None if not n else sum(v["clean"]["prediction_mse"]*v["held_samples"] for v in good)/n,"native_mse":None if not n else sum(v["clean"]["native_mse"]*v["held_samples"] for v in good)/n,"transfer_range":None if not transfers else [min(transfers),max(transfers)]})
    result={"schema":"strehl.original-forward-complete-synthetic-census.v1","command":sys.argv,"inputs":inputs,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"cases":summary,"known_field_bias":bias,"original_reads":0,"product_admission":False,"scope":"Whole-cohort status is a conservative conjunction of all18 color/fold results for each noise seed. Folds overlap training samples and are not independent replicates; no iid rate/CI claim. Inconsistent rejects the fixed field model, never physical same-PSF truth. Context comparison is retained commissioning, never real-data model selection."}
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    for r in summary:print(r["case"],r["counts"],"whole",len(r["complete_cohort_consistent_seeds"]))
if __name__=="__main__":main()
