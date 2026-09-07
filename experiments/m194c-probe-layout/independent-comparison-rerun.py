"""Check the report's final-build repeat claim using actual retained TIFF bytes."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    versions=[]
    for name,expected in [("candidate-1","f948761d6c7ea68d2bd42e95846cf9683c5cc70580c1c366043585fdaa5441d0"),
                          ("candidate-2","71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab")]:
        p=HERE/name/"run/run-index.json";assert sha(p)==expected
        rows={}
        for case in json.loads(p.read_text())["cases"]:
            for arm in case["arms"]:
                rp=Path(arm["receipt_path"])
                if not rp.is_absolute():rp=p.parent/rp
                assert sha(rp)==arm["receipt_sha256"]
                r=json.loads(rp.read_text());h=sha(r["output"]["path"]);assert h==r["output"]["sha256"]
                rows[(case["scene"],case["repeat"],arm["name"])]=h
        versions.append(rows)
    assert len(versions[0])==len(versions[1])==40 and versions[0]==versions[1]
    out=dict(schema="m194c-independent-build-repeat-v1",pass_=True,actual_whole_tiff_pairs=40,
             rows=[dict(scene=k[0],repeat=k[1],arm=k[2],sha256=v) for k,v in versions[0].items()],
             scope="final test/reader source-binding rerun is byte-identical, not an independent noise realization")
    (HERE/"independent-comparison-rerun.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(dict(pass_=True,actual_whole_tiff_pairs=40)))


if __name__=="__main__":main()
