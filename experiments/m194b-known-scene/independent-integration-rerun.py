"""Re-read the exact preserved v2 corruption fixtures under bound reader v3."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    first=json.loads((HERE/"independent-integration-initial.json").read_text())
    revision_path=HERE/"reader-revision-v3.json"
    revision_hash="f8740c75c5d65842d8b1993807ad99b27e988c7fb659e6f52fcd3848a6f65f00"
    assert sha(revision_path)==revision_hash
    revision=json.loads(revision_path.read_text())
    spec=importlib.util.spec_from_file_location("independent_final_integration",HERE/"score-benchmark.py")
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    original=reader.score_run(Path(first["index_path"]),first["index_sha256"],(revision_path,revision_hash))
    rows=[]
    for row in first["cases"]:
        folder=Path(first["work"])/row["name"]
        index_path=folder/"run-index.json"
        assert sha(index_path)==row["index_sha256"]
        control=copy.deepcopy(revision)
        control["render_index_sha256"]=row["index_sha256"]
        control["reason"]+="; exact preserved independent fixture: "+row["name"]
        control_path=folder/"reader-revision-v3.json"
        control_path.write_text(json.dumps(control,indent=2)+"\n")
        try:
            result=reader.score_run(index_path,row["index_sha256"],(control_path,sha(control_path)))
            accepted=True;error=None
            if row["name"]=="no-op":assert result["summary"]==original["summary"]
        except Exception as exc:
            accepted=False;error=f"{type(exc).__name__}: {exc}"
        rows.append(dict(name=row["name"],accepted=accepted,error=error,index_sha256=row["index_sha256"],same_fixture_bytes=True))
    final=reader.score_run(Path(first["index_path"]),first["index_sha256"],(revision_path,revision_hash))
    checks=dict(original40=original["output_count"]==40,no_op_accepted=rows[0]["accepted"],
                ten_same_mutations_refused=all(not row["accepted"] for row in rows[1:]),original_reread_unchanged=final==original)
    result=dict(schema="m194b-independent-integration-final-v1",pass_=all(checks.values()),checks=checks,
                preserved_initial_result_sha256=sha(HERE/"independent-integration-initial.json"),index_sha256=first["index_sha256"],reader_revision_sha256=revision_hash,
                cases=rows,source_sha256={"score.py":sha(HERE/"score.py"),"score-benchmark.py":sha(HERE/"score-benchmark.py")})
    (HERE/"independent-integration-final.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result));assert result["pass_"]


if __name__=="__main__":main()
