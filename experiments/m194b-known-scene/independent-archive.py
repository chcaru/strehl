"""Archive independent command/JSON evidence from intentionally ignored work."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent


def main():
    archive=HERE/"independent-evidence.zip"
    files=[]
    for directory in sorted((HERE/"work").glob("independent-*")):
        files.extend(p for p in sorted(directory.rglob("*")) if p.is_file() and p.suffix in {".log",".json"})
    records=[]
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for p in files:
            data=p.read_bytes();name=p.relative_to(HERE).as_posix()
            output.writestr(name,data)
            records.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    with zipfile.ZipFile(archive) as checked:
        assert checked.testzip() is None
        assert len(checked.infolist())==len(records)
        for record in records:assert hashlib.sha256(checked.read(record["path"])).hexdigest()==record["sha256"]
    result=dict(schema="m194b-independent-evidence-archive-v1",archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=archive.stat().st_size,file_count=len(records),files=records,scope="lossless command logs and JSON; large generated CFA/array/TIFF payloads remain local and are bound by recorded digests")
    (HERE/"independent-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="files"}))


if __name__=="__main__":main()
