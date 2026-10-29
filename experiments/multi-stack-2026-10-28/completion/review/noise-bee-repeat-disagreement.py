"""Saved-observation diagnosis only; no original reads, correction, or admission."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pearson(x, y):
    x, y = x - x.mean(), y - y.mean()
    den = np.linalg.norm(x) * np.linalg.norm(y)
    return None if den < 1e-12 else float(x @ y / den)


def moments(x, y, vx, vy):
    d = y - x
    offset = d.mean()
    g = float(x @ y / (x @ x)) if x @ x > 1e-20 else None
    xc, yc = x - x.mean(), y - y.mean()
    a = float(xc @ yc / (xc @ xc)) if xc @ xc > 1e-20 else None
    b = None if a is None else float(y.mean() - a * x.mean())
    raw = float(np.mean(d * d))
    centered = float(np.mean((d - offset) ** 2))
    gain_residual = None if g is None else y - g * x
    affine_residual = None if a is None else y - a * x - b
    return {
        "mean_x_dn": float(x.mean()), "mean_y_dn": float(y.mean()),
        "signed_dc_y_minus_x_dn": float(offset), "raw_mse_dn2": raw,
        "dc_energy_dn2": float(offset * offset), "centered_mse_dn2": centered,
        "dc_fraction": None if raw == 0 else float(offset * offset / raw),
        "plugin_expected_raw_noise_dn2": float(np.mean(vx + vy)),
        "raw_to_plugin_noise": None if np.mean(vx + vy) == 0 else float(raw / np.mean(vx + vy)),
        "same_data_gain_y_from_x": g,
        "same_data_gain_residual_mse_dn2": None if g is None else float(np.mean(gain_residual ** 2)),
        "same_data_affine_y_from_x": [a, b],
        "same_data_affine_residual_mse_dn2": None if a is None else float(np.mean(affine_residual ** 2)),
        "signed_ac_correlation": pearson(x, y),
        "centered_ac_energy_ratio_y_over_x": None if xc @ xc == 0 else float(yc @ yc / (xc @ xc)),
    }


def evaluate(points):
    x = np.array([p["x"] for p in points], dtype=float)
    y = np.array([p["y"] for p in points], dtype=float)
    cx = np.array([p["covariance_x"] for p in points], dtype=float)
    cy = np.array([p["covariance_y"] for p in points], dtype=float)
    assert len(points) == 256 and np.isfinite(x).all() and np.isfinite(y).all()
    grid = np.array([p["grid"] for p in points], dtype=float)
    expected = np.array([[xx, yy] for yy in range(8, 256, 16) for xx in range(8, 256, 16)])
    assert np.array_equal(grid, expected), "exact frozen full grid, no survivor pruning"
    xi, yi = x.sum(1), y.sum(1)
    vx, vy = cx.sum((1, 2)), cy.sum((1, 2))
    identity = moments(xi, yi, vx, vy)
    d = yi - xi
    spatial = np.column_stack([np.ones(256), (grid[:, 0]-128)/128, (grid[:, 1]-128)/128])
    coeff, _, rank, sv = np.linalg.lstsq(spatial, d, rcond=None)
    spatial_res = d - spatial @ coeff
    phase = np.array([p["source_plane_centers"] for p in points], dtype=float) % 1
    phase_report = []
    for s in range(2):
        for axis in range(2):
            v = phase[:, s, axis]
            sorted_phase = np.sort(v)
            circular_span = 1-float(np.diff(np.r_[sorted_phase, sorted_phase[0]+1]).max())
            phase_report.append({"source": s, "axis": axis, "min": float(v.min()), "max": float(v.max()),
                "std": float(v.std()), "minimum_circular_span": circular_span, "raw_difference_correlation": pearson(v, d),
                "spatial_detrended_difference_correlation": pearson(v, spatial_res)})
    # This sparse 32-sensor-step derivative is only a coarse spatial nuisance proxy.
    # It is not a registration correction or fine-band optical transfer estimate.
    common = ((xi+yi)/2).reshape(16,16)
    gy, gx = np.gradient(common, 32, 32)
    design = np.column_stack([spatial, gx.ravel(), gy.ravel()])
    gc, _, grank, gsv = np.linalg.lstsq(design, d, rcond=None)
    return {"identity": identity,
        "bands": [moments(x[:,b], y[:,b], cx[:,b,b], cy[:,b,b]) for b in range(3)],
        "same_data_spatial_plane": {"coefficients_dn": coeff.tolist(), "rank": int(rank),
            "residual_mse_dn2": float(np.mean(spatial_res**2)), "condition": float(sv[0]/sv[-1])},
        "same_data_spatial_plus_sparse_gradient": {"coefficients": gc.tolist(), "rank": int(grank),
            "residual_mse_dn2": float(np.mean((d-design@gc)**2)), "condition": float(gsv[0]/gsv[-1])},
        "phase_covariates": phase_report}


def controls():
    x = np.linspace(100.,200.,256); v = np.ones(256)
    offset = moments(x, x+7, v, v)
    assert abs(offset["dc_fraction"]-1)<1e-12 and offset["centered_mse_dn2"]<1e-20
    gain = moments(x,x*1.03,v,v)
    assert abs(gain["same_data_gain_y_from_x"]-1.03)<1e-12 and gain["same_data_gain_residual_mse_dn2"]<1e-20
    # Equal means cannot demonstrate retained AC signal; an affine same-data fit can erase blur.
    blur = moments(x,150.+.8*(x-150.),v,v)
    assert abs(blur["signed_dc_y_minus_x_dn"])<1e-12 and abs(blur["centered_ac_energy_ratio_y_over_x"]-.64)<1e-12
    assert blur["same_data_affine_residual_mse_dn2"]<1e-20
    opposite = moments(x,300.-x,v,v)
    assert opposite["signed_ac_correlation"] < -.99999
    assert abs(offset["raw_mse_dn2"]-offset["dc_energy_dn2"]-offset["centered_mse_dn2"])<1e-10
    return {"controls": 4, "pass": True, "lesson": "Same-data affine correction can erase actual AC attenuation; diagnostic fits never admit a pair."}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("input",type=Path,nargs="?");ap.add_argument("--output",type=Path);ap.add_argument("--controls",action="store_true");a=ap.parse_args()
    if a.controls:
        print(json.dumps(controls(),indent=2));return
    assert a.input and a.output and not a.output.exists()
    result_path=a.input/"result.json";r=json.loads(result_path.read_text());eq=json.loads((a.input/"equivalence.json").read_text())
    assert eq["new_result_sha256"]==sha(result_path) and r["all_admission_false"] and r["raw_decodes"]==0
    rows=[]; loaded={};bound={}
    for row in r["rows"]:
        rec=row["observation_receipt"];p=a.input/rec["path"];assert sha(p)==rec["sha256"]
        ob=json.loads(p.read_text());assert not ob["refusals"] and ob["patch"]==row["patch"] and ob["color"]==row["color"]
        key=(row["patch"],row["color"]);loaded[key]=ob["points"];bound[rec["path"]]=sha(p)
        rows.append({"patch":key[0],"color":key[1],"points":len(ob["points"]),"original_decision":row["evidence"]["diagnostic_decision"],**evaluate(ob["points"])})
    patches=list(dict.fromkeys(k[0] for k in loaded));assert len(patches)==2
    cross=[]
    for train,test in [patches,patches[::-1]]:
        ratios=[]
        for c in range(4):
            ps=loaded[(train,c)];mx=np.mean([sum(p["x"]) for p in ps]);my=np.mean([sum(p["y"]) for p in ps]);assert mx>0 and my>0
            ratios.append(float(np.log(my/mx)))
        g=float(np.exp(np.median(ratios)))
        for c in range(4):
            ps=loaded[(test,c)];x=np.array([p["x"] for p in ps]);y=np.array([p["y"] for p in ps]);cx=np.array([p["covariance_x"] for p in ps]);cy=np.array([p["covariance_y"] for p in ps])
            cross.append({"train_patch":train,"diagnostic_validation_patch":test,"color":c,"single_neutral_gain_y_from_x":g,"train_color_log_ratios":ratios,
                "identity_after_y_divide_gain":moments(x.sum(1),y.sum(1)/g,cx.sum((1,2)),cy.sum((1,2))/(g*g)),
                "bands_after_y_divide_gain":[moments(x[:,b],y[:,b]/g,cx[:,b,b],cy[:,b,b]/(g*g)) for b in range(3)]})
    out={"schema":"strehl.bee-saved-disagreement-diagnostic.v1","command":sys.argv,"source_sha256":sha(Path(__file__)),"input_result_sha256":sha(result_path),"observations":bound,"controls":controls(),"rows":rows,"two_patch_neutral_gain_cross_diagnostics":cross,"all_admission_false":True,
        "limitations":["Post hoc descriptive decomposition only; no threshold, correction, or compatibility status changed.","Same-data gain/affine/spatial fits are optimistic; both axes noisy and covariance is shared-Q plug-in. No probability or causal nuisance identification.","Two existing validation patches cross-fitted here only diagnose scalar consistency; they cannot be rebranded as fresh calibration/validation.","Fractional source phase varies with spatial coordinates; correlation cannot separate phase alias from scene/placement/illumination.","Sparse gradients at32sensor step cannot diagnose fine subpixel displacement."]}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(json.dumps([{"patch":v["patch"],"c":v["color"],"dc":v["identity"]["signed_dc_y_minus_x_dn"],"dc_fraction":v["identity"]["dc_fraction"],"raw_noise":v["identity"]["raw_to_plugin_noise"],"gain":v["identity"]["same_data_gain_y_from_x"],"spatial_mse":v["same_data_spatial_plane"]["residual_mse_dn2"]} for v in rows],indent=2))

if __name__=="__main__":main()
