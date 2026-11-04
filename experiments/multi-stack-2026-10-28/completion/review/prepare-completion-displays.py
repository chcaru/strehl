"""Existing-master review only; bounded strips, fixed control-derived display, no RAW."""
import os
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
from pathlib import Path
import importlib.util,json,sys
import tifffile
R=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location("review",R/"experiments/multi-stack-2026-10-28/challenge/prepare-review.py")
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
O=R/"outputs/multi-stack/completion/independent-photographs"
C=R/"outputs/multi-stack/completion"
P=R/"experiments/multi-stack-2026-10-28/completion/review"
phase=sys.argv[1]
if phase=="control":
    O.mkdir(exist_ok=False)
    source=C/"interleave-02/independent-pass-02/master.tiff"
    with tifffile.TiffFile(source) as tf: baseline=json.loads(tf.pages[0].description.split("DisplayBaseline: ",1)[1])
    photo=source.with_name("photograph.tiff")
    with tifffile.TiffFile(photo) as tf:icc=tf.pages[0].tags[34675].value
    (O/"display-srgb.icc").write_bytes(icc)
    h.write_json(O/"interleave-transform.json",{"schema":"strehl.independent-review-transform.v1","parameter_source":str(source),"parameter_source_sha256":h.digest(source),"display_baseline":baseline,"display_icc_file":"display-srgb.icc","display_icc_sha256":h.digest(O/"display-srgb.icc"),"policy":"Odd-half control only; frozen before candidate viewing. Dense ordinary reference has separate geometry and no pixelwise causal difference is claimed."})
    h.render(source,O/"interleave-odd",O/"interleave-transform.json","odd",compare=photo)
elif phase=="dense-control":
    h.render(C/"interleave-dense-01/master.tiff",O/"interleave-dense",O/"interleave-transform.json","dense")
elif phase=="interleave":
    rois=json.loads((P/"interleave-rois-frozen.json").read_text())["rois"]
    baseline=json.loads((O/"interleave-transform.json").read_text())["display_baseline"]
    icc=(O/"display-srgb.icc").read_bytes()
    a=tifffile.memmap(C/"interleave-02/independent-pass-02/master.tiff",mode="r")
    h.write_json(O/"interleave-odd/native-readback.json",h.emit_crops(a,O/"interleave-odd",baseline,icc,rois,"odd"))
    dense=tifffile.memmap(C/"interleave-dense-01/master.tiff",mode="r")
    h.write_json(O/"interleave-dense/native-readback.json",h.emit_crops(dense,O/"interleave-dense",baseline,icc,rois,"dense"))
    for label,folder in [("even",C/"interleave-02/independent-pass-01"),("interleave",C/"interleave-02")]:
        h.render(folder/"master.tiff",O/f"interleave-{label}",O/"interleave-transform.json",label,rois=rois if label!="dense" else None)
elif phase=="hdr":
    old=R/"outputs/multi-stack/slide-hdr-pair-6"
    new=C/"hdr-precision-01"
    a=json.loads((old/"alignment.json").read_text());b=json.loads((new/"alignment.json").read_text())
    assert a["warpmap"]==b["warpmap"],"HDR geometry changed: freeze remap before viewing"
    ra=json.loads((old/"render-report.json").read_text());rb=json.loads((new/"render-report.json").read_text())
    assert ra["canvas"]==rb["canvas"] and ra.get("development_reference_pass",ra["reference_pass"])==rb["development_reference_pass"]
    assert [(f["path"],f["photometric_gain"]) for f in ra["frames"]]==[(f["path"],f["photometric_gain"]) for f in rb["frames"]]
    rois=json.loads((R/"experiments/multi-stack-2026-10-28/review/hdr-roi-mapped-frozen.json").read_text())["rois"]
    for roi in rois:roi["origins"]["precision"]=next(iter(roi["origins"].values()))
    transform=R/"experiments/multi-stack-2026-10-28/review/hdr-physical-reference-transform.json"
    h.render(new/"master.tiff",O/"hdr-precision",transform,"precision",rois=rois)
else:raise ValueError(phase)
