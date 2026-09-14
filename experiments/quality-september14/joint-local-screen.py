"""Same eight RAW patches, original versus independently checked local geometry."""
from pathlib import Path
import importlib.util
import hashlib
import json
import subprocess
import time
import numpy as np
import tifffile
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=HERE/"joint-local-comparison-1"
SHA="3e5b208df4f3f43d97ef2669c95a8252b6eb9526c86216c685bb555f674e15d4"

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def save(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False,
                  default=lambda v:v.item() if isinstance(v,np.generic) else v.tolist())
        stream.write("\n")

def main():
    OUT.mkdir()
    assert hashlib.sha256((HERE/"joint-cfa-lanczos.py").read_bytes()).hexdigest()==SHA
    solver=module("local_screen_solver",HERE/"joint-cfa-lanczos.py")
    inputs=module("local_screen_inputs",HERE/"joint-inputs.py")
    shape,data,receipt=inputs.load()
    alignment=json.loads((HERE/"local-green-translation-1/result.json").read_text())
    assert alignment["source_map_sha256"]==receipt["map_sha256"]
    frames={f["index"]:f for f in receipt["frames"]}
    xy=data["xy"]; corrected=xy.copy()
    for row in alignment["frames"]:
        index=row["frame"]
        if index==145:
            assert row["at_translation_bound"]
            continue
        assert not row["at_translation_bound"] and row["converged"]
        if index!=149:assert row["validation_ratio"]<1
        delta=complex(*row["delta_source_native"])/complex(*frames[index]["a"])
        mask=data["frame"]==index
        corrected[mask]-=np.array([delta.real,delta.imag])
    assert np.array_equal(corrected[data["frame"]==149],xy[data["frame"]==149])
    admitted=data["valid"]&(data["frame"]!=145)
    hold=np.isin(data["frame"],[147,151])
    arms=(("old-map-eight",xy,admitted),("local-map-eight",corrected,admitted),
          ("old-map-six-heldout",xy,admitted&~hold),("local-map-six-heldout",corrected,admitted&~hold))
    images={};candidates=[]
    for name,positions,valid in arms:
        started=time.process_time()
        rgb,d=solver.reconstruct(shape,positions,data["values"],data["variance"],data["channels"],valid)
        d["cpu_seconds"]=time.process_time()-started
        arrays={key:d.pop(key) for key in ("predictions","data_residuals","support_counts","used_mask")}
        np.savez_compressed(OUT/(name+"-diagnostics.npz"),**arrays)
        save(OUT/(name+"-diagnostics.json"),d)
        assert np.isfinite(rgb).all() and all(c["converged"] for c in d["channels"])
        path=OUT/(name+"-camera-rgb.f32");rgb.astype("<f4",copy=False).tofile(path)
        candidates.append(dict(name=name,rgb=str(path)));images[name]=rgb
        print(name,f"{d['cpu_seconds']:.3f} CPU s",flush=True)
    # Every arm predicts the SAME held physical samples at corrected coordinates.
    # These coordinates were estimated from green low-pass guides that include
    # the held frames: RAW values are held out of reconstruction, NOT registration.
    h,w=shape
    common=hold&admitted&(corrected[:,0]>=32)&(corrected[:,0]<w-33)&(corrected[:,1]>=32)&(corrected[:,1]<h-33)
    rows=[]
    for name,rgb in images.items():
        for channel in range(3):
            indices=np.flatnonzero(common&(data["channels"]==channel))
            error=solver._design(shape,corrected[indices])@rgb[...,channel].ravel()-data["values"][indices]
            rows.append(dict(arm=name,channel=channel,observations=len(indices),
                             rmse=float(np.sqrt(np.mean(error*error,dtype=np.float64)))))
    save(OUT/"heldout.json",dict(frames=[147,151],results=rows,
        scope="Both six-frame fits exclude these RAW measurements. Eight-frame fits include them. Held frames participate in low-pass registration, so this is conditional validation of reconstruction, not fully independent end-to-end validation. Error can favour blur."))
    source=HERE/"matched-chip-on-1";stem="pale-circuit-frame149-raw"
    exe=HERE/"patch-render-build-2/saved-rgb-render.exe"
    assert hashlib.sha256(exe.read_bytes()).hexdigest()=="3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49"
    cfg=dict(receipt=str(source/"receipt.json"),width=w,height=h,
        baseline_rgb=str(source/(stem+"-mhc-camera-rgb.f32")),baseline_tiff=str(source/(stem+".tiff")),
        out=str(OUT/"render"),candidates=candidates,
        xyz_to_cam=[[.746,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]])
    save(OUT/"render-config.json",cfg)
    command=[str(exe),str(OUT/"render-config.json")]
    r=subprocess.run(command,capture_output=True,text=True,timeout=30)
    (OUT/"render.log").write_text(r.stdout+r.stderr,encoding="utf-8");assert r.returncode==0,r.stderr
    rendered=json.loads((OUT/"render/receipt.json").read_text());assert rendered["baseline_differing_u16_samples"]==0
    for name in rendered["outputs"]:
        im=tifffile.imread(OUT/"render"/(name+".tiff"))[32:-32,32:-32]
        Image.fromarray((im.astype(np.uint32)*255//65535).astype(np.uint8)).save(OUT/"render"/(name+"-native.png"))
    save(OUT/"receipt.json",dict(solver_sha256=SHA,baseline_product_pixels_exact=True,
        admitted_frames=list(range(146,154)),excluded_frame145="Translation reached search bound; excluded in BOTH geometry arms",
        intervention="Original sensor values/noise/clip flags unchanged; only inverse coordinates subtract delta_source/a. No photometric gain/bias applied.",
        corrected_reference149_unchanged=True,render_command=command,trim=32,
        local_alignment_sha256=hashlib.sha256((HERE/"local-green-translation-1/result.json").read_bytes()).hexdigest()))

if __name__=="__main__":main()
