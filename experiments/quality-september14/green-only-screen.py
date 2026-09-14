"""Fixed chip patches: coherent green only through the actual product developer."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib,numpy as np,tifffile
from PIL import Image
HERE=Path(__file__).resolve().parent
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=module("quincunx",HERE/"quincunx-chroma.py")
c=module("coherent",HERE/"coherent-chroma.py")
def save(p,v):
    with p.open("x",encoding="utf-8") as f:json.dump(v,f,indent=2);f.write("\n")
out=HERE/"green-only-comparison-1";out.mkdir()
source=HERE/"matched-chip-on-1";receipt=json.loads((source/"receipt.json").read_text())
exe=HERE/"patch-render-build-2/saved-rgb-render.exe"
assert hashlib.sha256(exe.read_bytes()).hexdigest()=="3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49"
records=[]
for patch in receipt["patches"]:
    w,h=patch["width"],patch["height"];stem=patch["stem"];folder=out/stem;folder.mkdir()
    cf=source/(stem+"-cfa.f32");rgb=source/(stem+"-mhc-camera-rgb.f32")
    a=np.fromfile(cf,dtype="<f4").reshape(h,w);mhc=np.fromfile(rgb,dtype="<f4").reshape(h,w,3)
    candidates=[]
    green_only=mhc.copy();green_only[...,1]=c.coherent_green(a)
    for name,arr in [("coherent-green",green_only)]:
        assert np.isfinite(arr).all() and all(q.sample_equality(a,arr).values())
        path=folder/(name+"-camera-rgb.f32");arr.astype("<f4",copy=False).tofile(path)
        candidates.append(dict(name=name,rgb=str(path)))
    cfg=dict(receipt=str(source/"receipt.json"),width=w,height=h,baseline_rgb=str(rgb),
        baseline_tiff=str(source/(stem+".tiff")),out=str(folder/"render"),candidates=candidates,
        xyz_to_cam=[[.7460,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]])
    config=folder/"config.json";save(config,cfg)
    command=[str(exe),str(config)]
    r=subprocess.run(command,capture_output=True,text=True,timeout=30)
    (folder/"render.log").write_text(r.stdout+r.stderr,encoding="utf-8")
    assert r.returncode==0,r.stderr
    result=json.loads((folder/"render/receipt.json").read_text());assert result["baseline_differing_u16_samples"]==0
    for name in result["outputs"]:
        image=tifffile.imread(folder/"render"/(name+".tiff"))[8:-8,8:-8]
        Image.fromarray((image.astype(np.uint32)*255//65535).astype(np.uint8)).save(folder/"render"/(name+"-native.png"))
    records.append(dict(stage=patch["stage"],command=command,baseline_exact=True,shape=[h,w],trim=8,
        reference_output_origin=[patch["reference_output_xywh"][0]+4,patch["reference_output_xywh"][1]+4],
        display="actual product sRGB16, floor(code*255/65535), trim8, no spatial resampling"))
    print(patch["stage"],"actual product development exact; green-only arm written",flush=True)
save(out/"receipt.json",dict(records=records,scope="bounded saved-patch candidates; no RAW decode or full merge changes"))
