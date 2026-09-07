"""Localize already reported component maxima; no new acceptance threshold."""
import json
from pathlib import Path
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent


def main():
    indices=[HERE.parent/"m194b-known-scene/baseline-1/run-index.json",HERE/"candidate-2/run/run-index.json"]
    versions=[]
    for p in indices:
        rows={}
        for case in json.loads(p.read_text())["cases"]:
            for arm in case["arms"]:
                receipt=Path(arm["receipt_path"])
                if not receipt.is_absolute():receipt=p.parent/receipt
                rows[(case["scene"],case["repeat"],arm["name"])]=Path(json.loads(receipt.read_text())["output"]["path"])
        versions.append(rows)
    rows=[]
    for key,a in versions[0].items():
        before=tifffile.imread(a).astype(float);after=tifffile.imread(versions[1][key]).astype(float)
        d=abs(after-before)*14848/65535
        y,x,c=map(int,np.unravel_index(np.argmax(d),d.shape))
        roi=d[50:162,46:238]
        ry,rx,rc=map(int,np.unravel_index(np.argmax(roi),roi.shape))
        rows.append(dict(scene=key[0],repeat=key[1],arm=key[2],max_dn=float(d[y,x,c]),
                         max_native_xy_channel=[x+18,y+14,c],max_in_scored_roi=64<=x+18<256 and 64<=y+14<176,
                         baseline_at_max_dn=float(before[y,x,c]*14848/65535),candidate_at_max_dn=float(after[y,x,c]*14848/65535),
                         max_roi_dn=float(roi[ry,rx,rc]),max_roi_native_xy_channel=[rx+64,ry+64,rc],
                         roi_components_above10dn=int(np.count_nonzero(roi>10)),roi_components=int(roi.size)))
    out=dict(schema="m194c-independent-extreme-localization-v1",scope="descriptive localization of a comparison's reported maximum, chosen after observing that maximum; no new quality bar",
             rows=rows,worst=max(rows,key=lambda r:r["max_dn"]),worst_roi=max(rows,key=lambda r:r["max_roi_dn"]))
    (HERE/"independent-comparison-extremes.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({k:out[k] for k in ["worst","worst_roi","scope"]}))


if __name__=="__main__":main()
