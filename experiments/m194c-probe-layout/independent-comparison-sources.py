"""Supplemental source-set controls in a private, noncompiled fixture tree."""
import importlib.util
import json
from pathlib import Path
import uuid

HERE=Path(__file__).resolve().parent


def main():
    spec=importlib.util.spec_from_file_location("independent_source_subject",HERE/"run-candidate.py")
    subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
    source_sha=subject.sha(HERE/"run-candidate.py")
    # First read the real current declarations; no build or source edits.
    real=subject.supplemental();subject.check_supplemental(real)
    work=HERE/("independent-comparison-source-fixture-"+uuid.uuid4().hex[:10]);work.mkdir()
    fixture=work/"experiments/m194c-probe-layout";fixture.mkdir(parents=True)
    gate=work/"crates/strehl-cli/src/merge_cmd/gatefloor.rs";gate.parent.mkdir(parents=True)
    gate.write_text('mod tests { include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/m194c-probe-layout/author-tests.rs")); }\n')
    author=fixture/"author-tests.rs";legacy=fixture/"legacy-fill-noise.rs"
    author.write_text('mod legacy { include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/m194c-probe-layout/legacy-fill-noise.rs")); }\n')
    legacy.write_text("fn legacy_marker() {}\n")
    for name in ["run-candidate.py","compare-candidate.py","comparison-preregister.md","preregister.md","legacy-source.json"]:
        (fixture/name).write_text("fixed independent fixture\n")
    subject.ROOT=work;subject.HERE=fixture;subject.GATE=gate
    good=subject.supplemental();subject.check_supplemental(good)
    rows=[]
    def trial(name,expected):
        try:subject.check_supplemental(expected)
        except ValueError as e:rows.append(dict(name=name,rejected=True,error=str(e)))
        else:rows.append(dict(name=name,rejected=False))
    missing=dict(good);missing.pop(next(k for k in missing if k.endswith("legacy-fill-noise.rs")))
    trial("omitted-nested-include-binding",missing)
    changed=dict(good);changed[next(k for k in changed if k.endswith("author-tests.rs"))]="0"*64
    trial("wrong-included-source-hash",changed)
    old=legacy.read_bytes();legacy.write_bytes(old+b"// changed bytes\n")
    trial("actual-nested-source-changed",good);legacy.write_bytes(old)
    extra=fixture/"unreached.rs";extra.write_text("fn added_unreached() {}\n")
    trial("added-source-not-attested",good)
    trial("rehashed-but-unreached-source",subject.supplemental())
    extra.unlink()
    author_old=author.read_bytes();author.write_text("// nested include removed\n")
    trial("coherently-rehashed-missing-nested-declaration",subject.supplemental());author.write_bytes(author_old)
    subject.check_supplemental(good)
    result=dict(schema="m194c-independent-comparison-sources-v1",pass_=all(r["rejected"] for r in rows),
                subject_sha256=source_sha,real_set_checked=real,private_fixture=str(work),cases=rows,
                unchanged_control_before_after=True,scope="read-only real set plus private source-set/closure mutations; no compiler or product execution")
    (HERE/"independent-comparison-sources.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(pass_=result["pass_"],cases=rows)));assert result["pass_"]


if __name__=="__main__":main()
