"""Fixed M194e error bars; no producer, geometry fitting, or authority."""
import numpy as np


def edge_mask():
    y,x=np.indices((48,64))
    return np.abs(x-32-.15*(y-24))/np.hypot(1.,.15)<=8


def compare(actual,reference):
    for value in (actual,reference):
        if value.shape!=(48,64) or value.dtype!=np.dtype("<f8") or not np.isfinite(value).all():
            raise ValueError("finite64x48 little-endian float64 required")
    difference=actual-reference
    edge=edge_mask()
    stats={}
    for name,values in (("whole",difference), ("edge",difference[edge])):
        maximum=float(np.max(np.abs(values)))
        rms=float(np.sqrt(np.mean(values*values)))
        stats[name]=dict(count=values.size,maximum_e=maximum,rms_e=rms,
                         maximum_pass=maximum<=.004,rms_pass=rms<=.0008)
    stats["pass"]=all(s["maximum_pass"] and s["rms_pass"] for s in (stats["whole"],stats["edge"]))
    return stats
