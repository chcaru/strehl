"""Read final synthetic TIFFs, archive hashes, and compare independent arms."""
import hashlib
import json
from pathlib import Path
import re
import tifffile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    groups={}
    records=[]
    for mode in ["normal","debug"]:
        text=(HERE/f"independent-{mode}-test.log").read_text(encoding="utf-8")
        assert "test result: ok. 5 passed; 0 failed" in text
        dirs=[Path(line.rsplit(" PASS ",1)[1]).resolve() for line in text.splitlines()
              if "M194 INDEPENDENT" in line and " PASS " in line]
        assert len(dirs)==5
        groups[mode]={}
        for directory in dirs:
            assert directory.is_relative_to(HERE/"work")
            label=re.fullmatch(r"independent-(.+)-\d+-\d+",directory.name)[1]
            groups[mode][label]={}
            for p in sorted(directory.glob("*.tif")):
                with tifffile.TiffFile(p) as f:
                    page=f.pages[0]
                    pixels=page.asarray()
                    record=dict(mode=mode, group=label, name=p.name, path=str(p.relative_to(ROOT)),
                                bytes=p.stat().st_size, sha256=sha(p), shape=list(pixels.shape),
                                dtype=str(pixels.dtype), pixels_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
                                software=page.tags["Software"].value if "Software" in page.tags else None)
                records.append(record)
                groups[mode][label][p.name]=record
    comparisons=[]
    for group,files in groups["normal"].items():
        for name,record in files.items():
            other=groups["debug"][group][name]
            # No source/build change occurs between these two invocations.
            assert record["sha256"]==other["sha256"], (group,name)
            comparisons.append(dict(group=group,name=name,sha256=record["sha256"],byte_exact=True))
    output=dict(schema="m194-independent-tiff-artifacts-v1", pass_=True,
                artifact_count=len(records), normal_debug_common_files=len(comparisons),
                artifacts=records, normal_debug_comparisons=comparisons)
    (HERE/"independent-artifacts.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({k:v for k,v in output.items() if k not in ["artifacts","normal_debug_comparisons"]}))


if __name__=="__main__":
    main()
