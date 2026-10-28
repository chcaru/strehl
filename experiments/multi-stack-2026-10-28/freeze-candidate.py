"""Freeze tested executables with their owned source snapshot."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
number=sys.argv[1]
out=root/f"outputs/multi-stack/candidate-{number}"
out.mkdir(exist_ok=False)
files=[root/"Cargo.lock",root/"Cargo.toml"]+sorted((root/"crates").rglob("*.rs"))+sorted((root/"crates").rglob("Cargo.toml"))
sha=lambda p:hashlib.file_digest(p.open("rb"),"sha256").hexdigest()
receipt={"build_id":f"c149e52834fc-multi-stack-candidate{number}","base":"c149e52834fc1c86c2af0fe022713c39fa25f33c","executables":{},"owned_source_sha256":{}}
for name in ["strehl.exe","strehl-ui.exe"]:
 shutil.copy2(root/"target/release"/name,out/name)
 receipt["executables"][name]=sha(out/name)
with zipfile.ZipFile(out/"owned-source.zip","x",zipfile.ZIP_DEFLATED) as z:
 for file in files:
  key=str(file.relative_to(root));z.write(file,key);receipt["owned_source_sha256"][key]=sha(file)
(out/"build.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"build_id":receipt["build_id"],"executables":receipt["executables"]},indent=2))
