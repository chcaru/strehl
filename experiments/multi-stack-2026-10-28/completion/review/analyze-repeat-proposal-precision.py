"""Fixed criteria and retained per-target precision diagnostics, no image I/O."""
import argparse,json,hashlib,sys
from pathlib import Path

def mean(v):return sum(v)/len(v)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("input",type=Path);ap.add_argument("output",type=Path);a=ap.parse_args();assert not a.output.exists()
 r=json.loads(a.input.read_text());rows=r["rows"];summary=r["temporal_summary"]
 lookup={(v["case"],v["bands"],v["arm"],v["seed"]):v for v in rows}
 fields=["averaged","single","ordinary_fallback","primary_fallback","saturated_fallback"]
 checked=0
 for v in rows:
  if v["arm"]=="equal-proposed":
   m=lookup[v["case"],v["bands"],"precision-missing-fixed-focus",v["seed"]]
   for x,y in zip(v["diagnostics"],m["diagnostics"]):assert {k:x[k] for k in fields}=={k:y[k] for k in fields}
   for k in ["against_clean_all_single","against_clean_passes"]:assert v[k]==m[k]
   checked+=1
 assert checked==r["missing_guide_bitwise_checks"]
 stats={(v["case"],v["bands"],v["arm"]):v for v in summary};flat=[];contrasts=[]
 for (case,bands,arm),v in stats.items():
  if arm!="precision-oracle-fixed-focus":continue
  eq=stats[case,bands,"equal-proposed"]
  single=stats[case,bands,"all-single"]
  clean=lookup[case,bands,arm,None]
  for c in range(4):
   seeds=[x for x in rows if x["case"]==case and x["bands"]==bands and x["arm"]==arm and x["seed"] is not None]
   def risk(which,target):return mean([lookup[case,bands,which,x["seed"]]["against_clean_passes"][target][c]["mse"] for x in seeds])
   contrasts.append({"case":case,"bands":bands,"color":c,
    "temporal_variance_precision_over_equal":v["sample_temporal_variance"][c]/eq["sample_temporal_variance"][c],
    "per_target_risk_precision_over_equal":[risk(arm,t)/risk("equal-proposed",t) for t in range(2)],
    "per_target_risk_precision_over_all_single":[risk(arm,t)/risk("all-single",t) for t in range(2)],
    "clean_per_target_transfer":[clean["against_clean_passes"][t][c]["centered_amplitude_transfer"] for t in range(2)]})
   if case.startswith("unequal-flat"):
    signal=20. if case.endswith("low") else 1200.+80.*c
    green=20. if case.endswith("low") else 1360.
    variance=lambda s,g:g*s+25.*g*g
    vg=[variance(green,g) for g in [.2,.8]];weight=[vg[1]/sum(vg),vg[0]/sum(vg)]
    expected=sum(weight[j]**2*(variance(signal,g)+1/12) for j,g in enumerate([.2,.8]))/4
    observed=v["sample_temporal_variance"][c]
    clean_delta=clean["against_clean_all_single"][c]["mean_difference"]
    passed=abs(clean_delta)<=.002 and observed<eq["sample_temporal_variance"][c]
    if bands==0:passed=passed and abs(observed/expected-1)<=.05
    flat.append({"case":case,"bands":bands,"color":c,"pass":passed,"observed_variance":observed,
      "analytic_variance_bands0_only":expected,"relative_error_bands0_only":observed/expected-1,
      "clean_dc_difference":clean_delta})
 clean_primary=[]
 for v in rows:
  if v["seed"] is None and v["arm"].startswith(("equal-primary","precision-primary")):
   target=0 if v["arm"].endswith("a") else 1
   clean_primary.append({"case":v["case"],"bands":v["bands"],"arm":v["arm"],"target":target,
     "own_target":v["against_clean_passes"][target],"other_target":v["against_clean_passes"][1-target],"diagnostics":v["diagnostics"]})
 result={"command":sys.argv,"analyzer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"input_sha256":hashlib.sha256(a.input.read_bytes()).hexdigest(),
   "criteria":"Frozen before result inspection: bands0 known green-luma precision weights and quantized plant variance within5%; both0/7 lower variance than equal, cleanDC<=.002DN. Full cases descriptive, no adverse outcome censored.",
   "missing_guide_output_bitwise_and_decision_checks":checked,"flat_controls":flat,"flat_pass":all(v["pass"] for v in flat) if flat else None,
   "contrasts":contrasts,"clean_primary":clean_primary,"limitations":["Exact oracle latent means, not physical guide calibration.","Analytic variance applies only bands0 internal estimator;7bands use normal nonlinear selector.","Both target risks retained; inverse-noise preference is not appearance preservation."]}
 a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"flat_pass":result["flat_pass"],"missing_checks":checked,"flat_controls":flat,"contrasts":contrasts},indent=2))
 if flat:assert result["flat_pass"],"predeclared flat commission failed"
if __name__=="__main__":main()
