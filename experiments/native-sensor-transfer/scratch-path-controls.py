"""Twelve fixed pure-path controls. No filesystem scanner or numerical execution."""
from pathlib import Path, PureWindowsPath
import argparse,ast,hashlib,json,sys,time
START=time.monotonic()
HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument("--shim-sha256",required=True);p.add_argument("--output",required=True);a=p.parse_args()
    source=HERE/"scratch-scan.py";before=source.stat()
    assert 0<before.st_size<=16384
    with source.open("rb") as f:raw=f.read(before.st_size+1)
    identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
    assert len(raw)==before.st_size and identity(source.stat())==identity(before) and hashlib.sha256(raw).hexdigest()==a.shim_sha256
    tree=ast.parse(raw);selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="comparison_path"]
    assert len(selected)==1
    namespace={"PureWindowsPath":PureWindowsPath}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(source),"exec"),namespace)
    compare=namespace["comparison_path"]
    ordinary=r"C:\dev\strehl\target\probe\lib.rmeta";verbatim="\\\\?\\"+ordinary
    expected=PureWindowsPath(r"C:\dev\strehl\target\probe\lib.rmeta")
    pairs=[(ordinary,verbatim,True),(verbatim,ordinary,True),
           (ordinary,r"C:\dev\strehl\target\probe\lib2.rmeta",False),
           (ordinary,r"C:\dev\strehl\target\probe2\lib.rmeta",False),
           (ordinary,r"D:\dev\strehl\target\probe\lib.rmeta",False)]
    rejects=[r"\\server\share\lib.rmeta",r"\\?\UNC\server\share\lib.rmeta",
             r"\\.\C:\dev\strehl\target\probe\lib.rmeta",r"\\?\GLOBALROOT\Device\HarddiskVolume1\lib.rmeta",
             r"target\probe\lib.rmeta",r"C:target\probe\lib.rmeta",r"\target\probe\lib.rmeta"]
    rows=[]
    for left,right,equal in pairs:
        try:
            l=compare(left);r=compare(right);actual=l==r
            passed=l==expected and actual is equal and (not equal or r==expected)
            detail=dict(left=str(l),right=str(r),actual_equal=actual,expected_equal=equal,actual_type=type(l).__name__)
        except Exception as error:passed=False;detail=dict(unexpected_error=repr(error))
        rows.append(dict(id=len(rows)+1,passed=passed,details=detail))
    for value in rejects:
        try:actual=compare(value);passed=False;detail=dict(unexpected_value=str(actual),actual_type=type(actual).__name__)
        except ValueError as error:passed=str(error)=="absolute local drive path required";detail=dict(error_type=type(error).__name__,error=str(error))
        except Exception as error:passed=False;detail=dict(unexpected_error=repr(error))
        rows.append(dict(id=len(rows)+1,passed=passed,details=detail))
    assert len(rows)==12 and [r["id"] for r in rows]==list(range(1,13))
    ok=all(r["passed"] for r in rows)
    result=dict(schema="native-sensor-transfer-scratch-path-controls-v1",status="PASS_FIXED_PATH_CONTROLS" if ok else "REFUSED",
                source=dict(path=str(source),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),invocation=sys.orig_argv,
                rows=rows,groups=12,complete=ok,cpu_sample=time.process_time(),wall_sample=time.monotonic()-START,
                scope="Pure path comparison only; no scanner, filesystem-race, compiler or numerical commissioning.")
    out=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    assert len(out)<=16384 and time.process_time()<5 and time.monotonic()-START<10
    output=Path(a.output);assert output==HERE/"work/scratch-path-controls-1.json"
    with output.open("xb") as f:assert f.write(out)==len(out)
    assert sys.stdout.buffer.write(out)==len(out);sys.stdout.buffer.flush()
    return 0 if ok else 1
if __name__=="__main__":raise SystemExit(main())
