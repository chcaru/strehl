"""Control-first saved-master readback; no engine or RAW reads."""
import os
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"): os.environ[k]="1"
from pathlib import Path
import importlib.util,json,sys
import tifffile
R=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location("review",R/"experiments/multi-stack-2026-10-28/challenge/prepare-review.py")
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
C=R/"outputs/multi-stack/completion"
O=C/"pitch8-independent-review"
P=R/"experiments/multi-stack-2026-10-28/completion/review"
S=C/"interleave-pitch8-01"
phase=sys.argv[1]
if phase=="control":
    O.mkdir(exist_ok=False)
    source=S/"independent-pass-01/master.tiff"
    with tifffile.TiffFile(source) as tf: baseline=json.loads(tf.pages[0].description.split("DisplayBaseline: ",1)[1])
    photo=source.with_name("photograph.tiff")
    with tifffile.TiffFile(photo) as tf: icc=tf.pages[0].tags[34675].value
    (O/"display-srgb.icc").write_bytes(icc)
    h.write_json(O/"transform.json",{"schema":"strehl.independent-review-transform.v1","parameter_source":str(source),"parameter_source_sha256":h.digest(source),"display_baseline":baseline,"display_icc_file":"display-srgb.icc","display_icc_sha256":h.digest(O/"display-srgb.icc"),"policy":"First half only, frozen before candidate pixels. Native slices no resampling. Both passes are disjoint selections from one sweep, not independent temporal repeats."})
    h.render(source,O/"even8",O/"transform.json","even8",compare=photo)
elif phase=="all":
    rois=json.loads((P/"pitch8-rois-frozen.json").read_text())["rois"]
    baseline=json.loads((O/"transform.json").read_text())["display_baseline"]
    a=tifffile.memmap(S/"independent-pass-01/master.tiff",mode="r")
    h.write_json(O/"even8/native-readback.json",h.emit_crops(a,O/"even8",baseline,(O/"display-srgb.icc").read_bytes(),rois,"even8"))
    for label,path in [("offset4",S/"independent-pass-02"),("combined",S),("dense",C/"interleave-dense-01")]:
        h.render(path/"master.tiff",O/label,O/"transform.json",label,rois=rois)
else: raise ValueError(phase)
