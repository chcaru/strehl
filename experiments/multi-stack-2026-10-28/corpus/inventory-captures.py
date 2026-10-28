"""Read-only capture inventory; embedded previews, never CFA decode."""
from pathlib import Path
import subprocess, json, hashlib, os, io, time
from PIL import Image, ImageOps, ImageDraw
ROOTS = [
r"D:\personal\macro\requests\7-aperture-pairs",
r"D:\personal\macro\requests\30-calibration-grid",
r"D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl",
r"D:\personal\macro\insects",
r"D:\personal\macro\flower-marigold-cpl",
r"D:\personal\macro\minerals\peacock-ore",
r"D:\personal\macro\requests\8-tilted-planar",
r"D:\personal\macro\requests\19-razor-edge",
]
OUT=Path(__file__).resolve().parent
PREV=OUT/"previews"; PREV.mkdir(exist_ok=True)
EXIF=r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe"
TAGS=["Model","ISO","ExposureTime","FNumber","DateTimeOriginal","SubSecTimeOriginal","ImageWidth","ImageHeight","FocusPosition2","FocusDistance","FocusDistance2","FocusMode","FocusMode2","SequenceNumber","ShutterCount","LensModel","DriveMode","WhiteBalance","ImageStabilization"]
env=os.environ.copy()
env.update(LC_ALL="C",LC_CTYPE="C",LANG="C")
def exif(args):
    p=subprocess.run([EXIF,*args],capture_output=True,env=env)
    if p.returncode: raise RuntimeError(p.stderr.decode(errors="replace"))
    return p.stdout
def sha_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(4<<20),b""): h.update(data)
    return h.hexdigest()
st=time.time()
brackets=[]
for root_idx,root_s in enumerate(ROOTS):
    root=Path(root_s)
    for folder,ds,fs in os.walk(root):
        raws=sorted([Path(folder)/x for x in fs if x.lower().endswith(".arw")],key=lambda p:p.name)
        if not raws:continue
        bid=f"b{len(brackets):02d}"
        records=[{"name":p.name,"bytes":p.stat().st_size,"mtime_ns":p.stat().st_mtime_ns} for p in raws]
        indices=sorted(set([0,len(raws)//2,len(raws)-1]))
        brackets.append({"id":bid,"family":root_idx,"root":str(root),"directory":str(Path(folder)),"relative":str(Path(folder).relative_to(root)),"count":len(raws),"total_bytes":sum(x["bytes"] for x in records),"files":records,"representatives":[{"index":i,"path":str(raws[i])} for i in indices]})
samples=[s for b in brackets for s in b["representatives"]]
meta=json.loads(exif(["-j","-n","-fast2",*["-"+t for t in TAGS],*[s["path"] for s in samples]]))
by_path={str(Path(m["SourceFile"])).lower():m for m in meta}
for b in brackets:
    for s in b["representatives"]:
        s["metadata"]=by_path[str(Path(s["path"])).lower()]
        s["sha256"]=sha_file(Path(s["path"]))
    print(b["id"],b["count"],b["relative"],flush=True)
inventory={"schema":"strehl.multi-stack-corpus.v1","base":"c149e52834fc1c86c2af0fe022713c39fa25f33c","method":"Complete directory census; first/middle/last metadata and full-file SHA256; embedded JPEG previews only, no CFA decode.","brackets":brackets,"count":sum(b["count"] for b in brackets),"seconds":time.time()-st}
(OUT/"inventory.json").write_text(json.dumps(inventory,indent=2)+"\n",encoding="utf-8")
groups={}
for b in brackets:
    # Middle preview of every bracket; endpoints additionally for insects and marigold.
    chosen=b["representatives"] if b["family"] in (3,4) else b["representatives"][1:2]
    thumbs=[]
    for s in chosen:
        payload=exif(["-b","-PreviewImage",s["path"]])
        if not payload: payload=exif(["-b","-JpgFromRaw",s["path"]])
        if not payload: payload=exif(["-b","-ThumbnailImage",s["path"]])
        image=Image.open(io.BytesIO(payload)).convert("RGB")
        path=PREV/f'{b["id"]}-{s["index"]:04}.jpg'
        path.write_bytes(payload)
        s["preview"]={"path":str(path.relative_to(OUT)),"dimensions":list(image.size),"sha256":hashlib.sha256(payload).hexdigest()}
        cell=Image.new("RGB",(480,370),(22,22,22))
        image.thumbnail((480,320),Image.Resampling.LANCZOS)
        cell.paste(image,((480-image.width)//2,0))
        draw=ImageDraw.Draw(cell)
        draw.text((8,325),f'{b["id"]}  frame {s["index"]}/{b["count"]-1}  {Path(s["path"]).name}',fill="white")
        label=b["relative"]
        draw.text((8,343),label[-75:],fill="white")
        groups.setdefault(b["family"],[]).append(cell)
    print("preview",b["id"],flush=True)
for fam,cells in groups.items():
    # At most 12 images per sheet, so every orientation overview stays interpretable.
    for start in range(0,len(cells),12):
        chunk=cells[start:start+12]
        cols=3; rows=(len(chunk)+cols-1)//cols
        sheet=Image.new("RGB",(cols*480,rows*370),(10,10,10))
        for i,cell in enumerate(chunk):sheet.paste(cell,((i%cols)*480,(i//cols)*370))
        sheet.save(OUT/f"contact-{fam}-{start//12}.jpg",quality=92)
inventory["seconds"]=time.time()-st
(OUT/"inventory.json").write_text(json.dumps(inventory,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"brackets":len(brackets),"raws":inventory["count"],"sampled_full_hashes":len(samples),"elapsed_seconds":inventory["seconds"]}),flush=True)
