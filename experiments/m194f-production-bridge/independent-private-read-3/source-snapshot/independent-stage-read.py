"""Bounded actual build/private-stage preflight; never whole integration authority."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("m194f_independent_verify",HERE/"independent-verify.py")
V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)


def ref(path):
    path=Path(path).resolve()
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=V.sha(path),bytes=path.stat().st_size)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build",type=Path,required=True)
    ap.add_argument("--build-sha256",required=True)
    ap.add_argument("--private-command",type=Path)
    ap.add_argument("--private-command-sha256")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),HERE/"independent-verify.py",HERE/"independent-reader.py"]
    before={p.relative_to(ROOT).as_posix():V.sha(p) for p in sources}
    snap=out/"source-snapshot";snap.mkdir()
    for p in sources:shutil.copyfile(p,snap/p.name)
    result=dict(schema="m194f-independent-stage-read-v1",status="RUNNING",orig_argv=sys.orig_argv,
                executable=sys.executable,python=sys.version,xoptions=sys._xoptions,source_before=before,
                thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
                started_utc=datetime.now(timezone.utc).isoformat(),build=ref(args.build),
                external_build_sha256=args.build_sha256,scope="component preflight only; no whole integration authority")
    start,cpu=time.perf_counter(),time.process_time()
    try:
        build=V.check_build(ref(args.build),args.build_sha256)
        result.update(status="PASS_BUILD_BINDING_ONLY",compiled_executable=build["test_executable"],source_count=len(build["sources_after"]))
        if args.private_command:
            V.R.require(args.private_command_sha256 is not None,"external private command digest required")
            command=V.load(args.private_command,args.private_command_sha256)
            private_ref=ref(command["result"])
            drivers={p.relative_to(ROOT).as_posix():V.sha(p) for p in (HERE/"consumer-run.py",HERE/"run-commission.py")}
            V.check_private_command(command,private_ref,build,args.build_sha256,drivers)
            result.update(private=V.verify_private(V.load(command["result"],command["result_sha256"])),
                          private_command=ref(args.private_command),private_controls=private_ref,
                          status="PASS_FIVE_PRIVATE_TIFFS_ONLY")
        V.check_source_map(build["sources_after"])
    except Exception as error:
        result.update(status="FAIL_STAGE_READ",error=repr(error),traceback=traceback.format_exc())
    result.update(source_after={p.relative_to(ROOT).as_posix():V.sha(p) for p in sources},wall_seconds=time.perf_counter()-start,
                  cpu_seconds=time.process_time()-cpu,ended_utc=datetime.now(timezone.utc).isoformat())
    result["source_unchanged"]=result["source_before"]==result["source_after"]
    if not result["source_unchanged"]:result["status"]="FAIL_STAGE_SOURCE_CHANGED"
    (out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],sha256=V.sha(out/"result.json"))))
    return 0 if result["status"].startswith("PASS") else 1


if __name__=="__main__":raise SystemExit(main())
