"""Read-only analysis of the actual consumer's seeded incremental-noise arms."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / (sys.argv[1] if len(sys.argv)>1 else "outputs/multi-stack/completion/noise-transfer-02")
fixture = json.loads((ROOT / "outputs/multi-stack/completion/noise-transfer-input-01/fixture.json").read_text())
report = json.loads((RUN / "report.json").read_text())
rows = {(r["scene"],r["arm"]):r for r in report["results"]}
scenes = ["flat","original-texture"]
arms = ["short","long","combined","equal","precision","noisy-guide","missing-guide"]
if ("flat","frozen-focus") in rows:
    arms += ["frozen-focus","frozen-focus-noisy"]
sha = lambda p: hashlib.file_digest(p.open("rb"),"sha256").hexdigest()
def plane(scene,arm,kind):
    a=np.fromfile(RUN / f"{scene}-{arm}-{kind}.f32","<f4").reshape(4,128,128)
    assert np.isfinite(a).all()
    return a

# Flat controls first. Independently evaluate the stated affine temporal model;
# this is a simulation-consistency check, not calibration from the same constant.
gain=fixture["gain_short_to_common"]
n=fixture["noise_planes"][0];g=n["gain_dn_per_e"];r=n["read_noise_e"]
short=(g*1200/gain+(g*r)**2)*gain**2
long=g*1200+(g*r)**2
expected={"short":short,"long":long,"equal":(short+long)/4,"precision":short*long/(short+long)}
flat=[]
for arm,value in expected.items():
    for c,stats in enumerate(rows[("flat",arm)]["planes"]):
        assert abs(stats["temporal_variance"]/value-1)<0.03
        assert abs(stats["mean_bias"])<0.15
        flat.append({"arm":arm,"channel":c,"expected":value,"measured":stats["temporal_variance"]})

# Missing prediction must exercise the exact equal-weight producing path.
for scene in scenes:
    for kind in ["clean","mean","variance"]:
        assert np.array_equal(plane(scene,"equal",kind).view("u4"),plane(scene,"missing-guide",kind).view("u4"))

# Commission the image-transfer observer on corruptions of the same known
# conditional signal: low variance alone must not accept a blank or blurred arm.
truth=plane("original-texture","equal","clean")
scale=float(np.sqrt(np.mean((truth-truth.mean(axis=(1,2),keepdims=True))**2)))
foils={"identity":truth,"blur":np.stack([gaussian_filter(p,1.5) for p in truth]),
       "constant":np.broadcast_to(truth.mean(axis=(1,2),keepdims=True),truth.shape),
       "one_quad_shift":np.roll(truth,1,axis=2)}
foils["sharpen"]=truth+0.75*(truth-foils["blur"])
observer={k:float(np.sqrt(np.mean((v-truth)**2))/scale) for k,v in foils.items()}
assert observer["identity"]==0 and all(v>0.01 for k,v in observer.items() if k!="identity")

comparisons=[]
for scene in scenes:
    for arm in [a for a in ["precision","noisy-guide","frozen-focus","frozen-focus-noisy"] if a in arms]:
        a=rows[(scene,arm)]["planes"];b=rows[(scene,"equal")]["planes"]
        variance_ratio=[x["temporal_variance"]/y["temporal_variance"] for x,y in zip(a,b)]
        clean=plane(scene,arm,"clean");equal=plane(scene,"equal","clean")
        mean=plane(scene,arm,"mean")
        comparisons.append({"scene":scene,"arm":arm,"temporal_variance_ratio_to_equal":variance_ratio,
            "temporal_sigma_ratio_to_equal":np.sqrt(variance_ratio).tolist(),
            "clean_difference_to_equal_rmse_per_plane":np.sqrt(np.mean((clean-equal)**2,axis=(1,2))).tolist(),
            "mean_to_own_clean_normalized_rmse":float(np.sqrt(np.mean((mean-clean)**2))/max(scale,1)),
            "scope":"Conditional transfer to this arm's clean output; clean-arm differences retained, not dismissed as noise."})
        assert all(v<1 for v in variance_ratio)

# Use the exact planted unblurred CFA fixture as a COMMON conditional signal
# reference, rather than letting each arm validate against its own clean image.
# Existing captured noise is part of this fixed fixture. Production sharpening
# is deliberately retained and appears as gain/distortion in these observables.
truth=np.fromfile(ROOT / "outputs/multi-stack/completion/noise-transfer-input-01/original-texture-0.f32","<f4").reshape(4,128,128)
window=np.outer(np.hanning(128),np.hanning(128))
fy,fx=np.meshgrid(np.fft.fftfreq(128),np.fft.fftfreq(128),indexing="ij")
radius=np.sqrt(fx*fx+fy*fy)
bands=[(0,0.0625),(0.0625,0.125),(0.125,0.25),(0.25,0.5)]
common_signal=[]
for arm in arms:
    for kind in ["clean","mean"]:
        candidate=plane("original-texture",arm,kind)
        channels=[]
        for c in range(4):
            a=(truth[c]-truth[c].mean())*window
            b=(candidate[c]-candidate[c].mean())*window
            fa=np.fft.fft2(a);fb=np.fft.fft2(b)
            spectra=[]
            for low,high in bands:
                mask=(radius>low)&(radius<=high)
                power=float(np.sum(np.abs(fa[mask])**2))
                cross=np.sum(np.conj(fa[mask])*fb[mask])
                spectra.append({"cycles_per_quad":[low,high],"signal_projection_gain":float(cross.real/power),
                    "relative_error_rms":float(np.sqrt(np.sum(np.abs(fb[mask]-fa[mask])**2)/power))})
            channels.append({"mean_bias_dn":float(np.mean(candidate[c]-truth[c])),
                "rmse_dn":float(np.sqrt(np.mean((candidate[c]-truth[c])**2))),"bands":spectra})
        common_signal.append({"arm":arm,"kind":kind,"channels":channels})

result={"schema":"strehl.incremental-noise-analysis.v1","label":"MEASURED conditional simulated-noise result through the production consumer",
    "flat_model_consistency":flat,"missing_guide_equal_exact_bits":True,"observer_corruption_normalized_rmse":observer,
    "comparisons":comparisons,"common_unblurred_fixture_signal_transfer":common_signal,"trials":48,"workers":4,
    "limits":["The source texture contains existing camera noise, treated as fixed signal in this experiment.",
        "Guides are disjoint simulated acquisitions. The noisy guide is fixed across trials and box filtered at radius8; the ideal guide is an explicit best-case control.",
        "No real alignment, focus correspondence or camera model is validated by this simulation.",
        "Signal projection is insensitive to some local defects; full photographs and held-out original measurements remain required."],
    "inputs":{"report.json":sha(RUN/"report.json"),"source":sha(Path(__file__))}}
(RUN/"analysis.json").write_text(json.dumps(result,indent=2)+"\n")
(RUN/"analysis-source.py").write_bytes(Path(__file__).read_bytes())
print(json.dumps({"flat_expected":expected,"observer":observer,"comparisons":comparisons},indent=2))
