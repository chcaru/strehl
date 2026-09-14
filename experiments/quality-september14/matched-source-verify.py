"""Independent saved-output checks. No RAW decode or product execution."""
from pathlib import Path
import hashlib,json
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
labels=["printer-on","printer-off","printer-placebo","chip-on"]
for label in labels:
    assert (HERE/f"matched-{label}-1/completion.json").exists(),f"await {label} completion"
out=HERE/"matched-source-verification.json"
assert not out.exists(),"one fixed verification; preserve prior result"
records={label:read(HERE/f"matched-{label}-1/receipt.json") for label in labels}
hashes={label:sha(HERE/f"matched-{label}-1/replay.tiff") for label in labels}
assert len({hashes[x] for x in labels[:3]})==1,"observer changes complete pinned-tone output"
on,off,placebo=[records[x] for x in labels[:3]]
for key in ["tone_bits","wb_bits","levels","crop_quad_xywh","source_frame_count","native_map_reference"]:
    assert on[key]==off[key]==placebo[key],key
assert [off[k] for k in ["raw_count","gathered_count","merged_count"]]==[0,0,0]
assert off["patches"]==[]
assert [on[k] for k in ["raw_count","gathered_count","merged_count"]]==[2,2,2]
assert [placebo[k] for k in ["raw_count","gathered_count","merged_count"]]==[1,1,1]
assert on["configuration"]["regions"]!=placebo["configuration"]["regions"],"placebo must change sampled region"
image_checks=[]
for label in labels:
    folder=HERE/f"matched-{label}-1";record=records[label]
    process=read(HERE/f"matched-{label}-process.json")
    assert process["exit_code"]==0 and process["error"] is None and process["cleanup_errors"]==[]
    assert process["terminal_job_accounting"] and not process["termination"]["attempted"]
    inv=read(HERE/f"matched-{label}-invocation.json")
    assert sha(Path(inv["map"]["path"]))==inv["map"]["sha256"]
    assert record["configuration"]["map"]==inv["configuration"]["map"]
    replay=tifffile.memmap(folder/"replay.tiff")
    assert replay.dtype==np.uint16 and replay.ndim==3 and replay.shape[2]==3
    for p in record["patches"]:
        assert p["trim"]==4 and all(v%2==0 for v in p["padded_origin_xy"])
        if p["stage"]!="merged":continue
        patch=tifffile.imread(folder/(p["stem"]+".tiff"))
        x,y,w,h=p["reference_output_xywh"]
        assert np.array_equal(patch[4:4+h,4:4+w],replay[y:y+h,x:x+w]),"patch writer differs from complete writer"
        # Independently selected asymmetric inner rectangle, unrelated to root's full crop check.
        ix,iy,iw,ih=31,27,137,119
        part=patch[4+iy:4+iy+ih,4+ix:4+ix+iw]
        target=replay[y+iy:y+iy+ih,x+ix:x+ix+iw]
        assert np.array_equal(part,target)
        wrong=replay[y+iy:y+iy+ih,x+ix+1:x+ix+1+iw]
        differing=int(np.count_nonzero(part!=wrong))
        assert differing>0,"one-pixel wrong-origin destroyer lacks power"
        image_checks.append(dict(label=label,patch=p["stem"],full_equal_channels=w*h*3,
            independent_inner_xywh=[ix,iy,iw,ih],inner_equal_channels=part.size,
            wrong_origin_differing_channels=differing))
    del replay

# Independent RAW values already retained by rawpy and separately checked against rawler.
source_folder=HERE/"chip-source-review-1"
source=read(source_folder/"receipt.json")
raw=np.load(source_folder/"source-visible-union.npy",allow_pickle=False)
assert source["independent_decode_different_sensels"]==0
assert hashlib.sha256(raw.tobytes()).hexdigest()==source["raw_u16_sha256"]
chip=records["chip-on"]
p=next(p for p in chip["patches"] if p["stage"]=="raw")
observed=np.fromfile(HERE/"matched-chip-on-1"/(p["stem"]+"-cfa.f32"),dtype="<f4").reshape(p["height"],p["width"])
gain=np.array(chip["wb_bits"],dtype="<u4").view("<f4")
black,white=np.array(chip["levels"],dtype=np.float32)
assert all(x==float(black) for x in source["decoder"]["black"])
sx,sy,sw,sh=source["union_xywh"];px,py=p["padded_origin_xy"]
x0,y0=max(sx,px),max(sy,py)
x1,y1=min(sx+sw,px+p["width"]),min(sy+sh,py+p["height"])
assert x1>x0 and y1>y0
cut=raw[y0-sy:y1-sy,x0-sx:x1-sx].astype(np.float32)
yy,xx=np.indices(cut.shape);xx+=x0;yy+=y0
phase_gain=np.where((yy%2==0)&(xx%2==0),gain[0],np.where((yy%2==1)&(xx%2==1),gain[2],gain[1])).astype(np.float32)
expected=np.maximum(cut-black,np.float32(0))*phase_gain*np.float32(1)/(white-black)
actual=observed[y0-py:y1-py,x0-px:x1-px]
different=int(np.count_nonzero(actual.view(np.uint32)!=expected.view(np.uint32)))
assert different==0,"source CFA normalization differs from independent retained sensels"
wrong_gain=np.maximum(cut-black,np.float32(0))*np.roll(phase_gain,1,axis=1)/(white-black)
assert np.count_nonzero(wrong_gain!=actual)>0,"wrong-phase gain destroyer lacks power"
result=dict(status="PASS",scope="saved artifacts only; pinned-tone observer neutrality, patch replay equality and one independent original-CFA normalization; no photographic quality claim",
    replay_sha256=hashes,printer_on_off_placebo_identical=True,image_checks=image_checks,
    raw_check=dict(source=source["source"],intersection_native_xywh=[x0,y0,x1-x0,y1-y0],
        sensels=actual.size,different_bits=different,wb_from_first_frame_bits=chip["wb_bits"],
        source_white_level=source["decoder"]["white"],consumer_white_level=float(white)),
    caveats=["Old automatic baseline is not the pinned-tone control.",
        "Raw source panels have no CA or geometric resampling; gathered and merged share the output grid.",
        "Noise and color stage differences are descriptive, not true scene error."])
with out.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2);f.write("\n")
print(json.dumps(result,indent=2))
