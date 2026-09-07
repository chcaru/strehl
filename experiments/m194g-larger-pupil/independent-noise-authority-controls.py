"""Prospective controls of the actual FloatAuthority; no sampler/encoder calls."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import copy
import gc
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUPPORT = HERE / "independent-noise-verifier-support.py"
spec = importlib.util.spec_from_file_location("m194g_noise_verifier_support", SUPPORT)
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

CONTROL_IDS = (
    "genuine-authority-five-scalars", "incomplete-authority", "bool-width", "wrong-reference",
    "bool-index", "swapped-primary-scalar", "refined-primary-receipt", "duplicate-primary-row", "actual-hardlink-primary-identity",
    "projection-mismatch", "component-command-failed", "component-child-failed",
    "component-error", "comparison-incomplete", "comparison-error", "comparison-finalization-error",
    "missing-render-role", "author-render-incomplete", "author-render-error", "reference-render-error",
    "scalar-traversal", "scalar-absolute-path", "restored-genuine-authority",
    "scalar-valid-private", "npy-duplicate-descr", "npy-huge-shape", "npy-object",
    "npy-fortran", "npy-short", "npy-appended", "npy-nan", "npy-negative",
    "changed-input-at-finish", "restored-input-at-finish", "live-owner-alias",
    "expired-owner-reuse", "live-cumulative-allocation", "genuine-final-restored",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--float-commission", type=Path, required=True)
    parser.add_argument("--float-commission-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prefix = HERE.relative_to(ROOT).as_posix()+"/"
    required = [prefix+x for x in (Path(__file__).name, SUPPORT.name, "software-noise.py",
                "software-noise-authority.py", "next-noise-contract.md",
                "independent-full-float-authority-schema.md", "next-noise-files-verifier-design.md")]
    session = S.Session(args, "noise-authority-controls", ENTRY_CPU, ENTRY_WALL, required)
    result = dict(schema="m194g-independent-noise-authority-controls-v1",
                  status="UNCOMMISSIONED_AUTHORITY_CONTROLS", ref_root="repository",
                  float_commission=S.file_ref(args.float_commission), execution_release=session.release_ref,
                  invocation=list(sys.orig_argv), sources_before=session.release["source_bindings"],
                  sources_after=None, inputs_before=None, inputs_after=None,
                  runtime=None, check_count=0, checks=[], work=None, error=None, finalization_errors=[])
    need = S.need
    try:
        need(result["float_commission"]["sha256"] == args.float_commission_sha256,
             "external genuine float pin mismatch")
        need(result["float_commission"] in session.release["inputs"], "genuine float input not released")
        core = session.load("software-noise.py", "m194g_authority_core")
        A = session.load("software-noise-authority.py", "m194g_actual_authority")
        budget, np = session.budget, core.np
        budget.np = np
        runtime = core.runtime_manifest()
        result["runtime"] = session.json("runtime.json",runtime)
        session.final_checks.append(lambda:need(core.runtime_manifest() == runtime,"authority runtime changed"))
        # Any inadvertent producer call is a failing control, even if caught later.
        def forbidden(*_args, **_kwargs):
            budget.forbidden_calls += 1
            raise RuntimeError("sampling/encoding is forbidden in authority controls")
        for name in ("sample_frame", "encode_dn", "_new_generator", "Generator", "PCG64DXSM", "SeedSequence"):
            setattr(core, name, forbidden)
        gate, _ = session.reads.json(result["float_commission"])
        comparison, _ = session.reads.json(gate["comparison"])
        component, _ = session.reads.json(gate["component_verification"])
        def add(name, passed, evidence):
            result["checks"].append(dict(name=name, **{"pass": bool(passed)}, evidence=evidence))
            result["check_count"] = len(result["checks"])
            need(passed, "authority control failed: "+name)
            budget.check()
        def authority(ref):
            return A.FloatAuthority(ROOT/ref["path"], ref["sha256"], core, budget)
        def valid(name):
            actual = authority(result["float_commission"])
            rows = []
            for index in range(5):
                arr = actual.scalar(index)
                rows.append(dict(index=index, shape=list(arr.shape), dtype=arr.dtype.str,
                                 scalar_sha256=hashlib.sha256(arr.tobytes()).hexdigest()))
                del arr
            observed = actual.finish()
            for path, value in observed.items():
                key = Path(path).relative_to(ROOT).as_posix()
                need(key not in session.reads.observed or session.reads.observed[key] == value,
                     "genuine authority binding conflicts")
                session.reads.observed[key] = value
            add(name, True, rows)
        def reject(name, call, expected):
            try:
                call()
            except ValueError as exc:
                add(name, expected in str(exc), {"exception": type(exc).__name__, "message": str(exc),
                                              "expected_message_fragment": expected})
            else:
                add(name, False, {"expected_message_fragment": expected, "accepted": True})
        def mutation(name, change, expected, *, project=True):
            g, c, comp = copy.deepcopy(gate), copy.deepcopy(comparison), copy.deepcopy(component)
            change(g, c, comp)
            if comp != component:
                g["component_verification"] = session.json("controls/"+name+"-component.json", comp)
            if project:
                c["admitted_inputs"] = {key: g[key] for key in A.PROJECTION}
            # Re-seal actual changed ancestor bytes to reach its semantic consumer.
            g["comparison"] = session.json("controls/"+name+"-comparison.json", c)
            ref = session.json("controls/"+name+"-authority.json", g)
            reject(name, lambda: authority(ref), expected)

        valid("genuine-authority-five-scalars")
        mutation("incomplete-authority", lambda g,c,p: g.update(status="PARTIAL"), "complete genuine")
        mutation("bool-width", lambda g,c,p: g.update(width=True), "authority integer")
        mutation("wrong-reference", lambda g,c,p: g.update(reference_index=0), "authority integer")
        mutation("bool-index", lambda g,c,p: g["primary_frames"][0].update(index=False), "primary frame order/type")
        mutation("swapped-primary-scalar", lambda g,c,p: g["primary_frames"][0].update(scalar=g["primary_frames"][1]["scalar"]),
                 "scalar/receipt association")
        refined, refined_path = session.reads.json(comparison["render_results"]["author-cell-refined"])
        def refined_swap(g,c,p):
            ref = refined["frames"][0]["receipt"]
            g["primary_frames"][0]["author_receipt"] = S.file_ref(S.relative(refined_path.parent, ref["path"]))
        mutation("refined-primary-receipt", refined_swap, "not the primary result")
        mutation("duplicate-primary-row", lambda g,c,p: g["primary_frames"].__setitem__(1, g["primary_frames"][0]),
                 "primary frame order/type")
        # Two real paths with one backing file identity, reached after all
        # first-two receipt/index/scalar associations have been resealed.
        g, c = copy.deepcopy(gate), copy.deepcopy(comparison)
        primary,_ = session.reads.json(comparison["render_results"]["author-primary"])
        primary = copy.deepcopy(primary)
        original_scalar = S.relative(ROOT,gate["primary_frames"][0]["scalar"]["path"])
        links=[]
        for index in range(2):
            leaf=session.output/"controls/hardlink"/f"frame-{index}"
            leaf.mkdir(parents=True,exist_ok=False)
            link=leaf/"scalar.npy"
            logical=original_scalar.stat().st_size
            need(budget.output_bytes+logical <= 16<<20,"hardlink logical output reservation")
            os.link(original_scalar,link)
            budget.output_bytes += logical
            budget.check()
            ref=S.file_ref(link)
            session.written[ref["path"]]={k:ref[k] for k in ("sha256","bytes")}
            scalar_ref={**ref,"dtype":"<f8","shape":[240,320]}
            receipt,_=session.reads.json(gate["primary_frames"][index]["author_receipt"])
            receipt=copy.deepcopy(receipt)
            receipt["arrays"]["scalar"]={**scalar_ref,"path":"scalar.npy"}
            receipt_ref=session.json(f"controls/hardlink/frame-{index}/receipt.json",receipt)
            primary["frames"][index]["receipt"]={**receipt_ref,"path":f"frame-{index}/receipt.json"}
            g["primary_frames"][index]["author_receipt"]=receipt_ref
            g["primary_frames"][index]["scalar"]=scalar_ref
            links.append(link)
        info=[path.stat() for path in links]
        need(links[0] != links[1] and info[0].st_ino != 0
             and (info[0].st_dev,info[0].st_ino) == (info[1].st_dev,info[1].st_ino),
             "private hardlink fault did not create distinct paths with equal identity")
        c["render_results"]["author-primary"]=session.json("controls/hardlink/primary.json",primary)
        c["admitted_inputs"]={key:g[key] for key in A.PROJECTION}
        g["comparison"]=session.json("controls/hardlink/comparison.json",c)
        ref=session.json("controls/hardlink/authority.json",g)
        reject("actual-hardlink-primary-identity",lambda:authority(ref),"aliased primary file identity")
        result["checks"][-1]["evidence"].update(paths=[S.file_ref(p) for p in links],
                                               same_device=int(info[0].st_dev),same_inode=int(info[0].st_ino),
                                               logical_output_bytes=sum(p.stat().st_size for p in links))
        mutation("projection-mismatch", lambda g,c,p: c["admitted_inputs"].update(reference_index=0),
                 "projection differs", project=False)
        mutation("component-command-failed", lambda g,c,p: p.update(status="PARTIAL"), "component command failed")
        mutation("component-child-failed", lambda g,c,p: p["result"].update(status="PARTIAL"), "component child failed")
        mutation("component-error", lambda g,c,p: p.update(exception="planted error"), "component command failed")
        mutation("comparison-incomplete", lambda g,c,p: c.update(status="PARTIAL"), "full comparison child failed")
        mutation("comparison-error", lambda g,c,p: c.update(error="planted error"), "full comparison child failed")
        mutation("comparison-finalization-error", lambda g,c,p: c.update(finalization_errors=["planted"]), "full comparison child failed")
        mutation("missing-render-role", lambda g,c,p: c["render_results"].pop("reference-refined"), "five complete render roles")
        def render_fault(role, field, value, name, expected):
            child, _ = session.reads.json(comparison["render_results"][role])
            child[field] = value
            ref = session.json("controls/"+name+"-render.json", child)
            mutation(name, lambda g,c,p: c["render_results"].__setitem__(role, ref), expected)
        render_fault("author-primary", "status", "PARTIAL", "author-render-incomplete", "render role incomplete")
        render_fault("author-primary", "error", "planted", "author-render-error", "failed terminal render")
        render_fault("reference-primary", "exception", "planted", "reference-render-error", "failed terminal render")
        # Direct reference boundary avoids an earlier primary-association rejection.
        original_ref = gate["primary_frames"][0]["scalar"]
        reject("scalar-traversal", lambda: A.Reads(core,budget).scalar({**original_ref,"path":"../escape.npy"}),
               "noncanonical relative")
        reject("scalar-absolute-path", lambda: A.Reads(core,budget).scalar({**original_ref,"path":str(ROOT/"x.npy")}),
               "invalid relative")
        valid("restored-genuine-authority")

        original, _ = session.reads.raw(original_ref, array=True, maximum=700000)
        def npy(header, payload):
            raw = header.encode("latin1")
            raw += b" " * ((64-(10+len(raw)+1)%64)%64) + b"\n"
            return b"\x93NUMPY\x01\x00"+struct.pack("<H",len(raw))+raw+payload
        prefix = 10 + struct.unpack("<H",original[8:10])[0]
        payload = original[prefix:]
        default_header = "{'descr': '<f8', 'fortran_order': False, 'shape': (240, 320), }"
        private = session.write("controls/scalar-valid.npy", original)
        private_array = {**private,"dtype":"<f8","shape":[240,320]}
        arr = A.Reads(core,budget).scalar(private_array)
        add("scalar-valid-private", arr.shape == (240,320), {"file": private})
        del arr
        malformed = [
            ("npy-duplicate-descr", npy(default_header.replace("'descr': '<f8',", "'descr': '<f8', 'descr': '<f8',"), payload), "duplicate/nonstring"),
            ("npy-huge-shape", npy(default_header.replace("(240, 320)","(240000000, 320000000)"), b""), "header mismatch"),
            ("npy-object", npy(default_header.replace("'<f8'","'|O'"), b""), "header mismatch"),
            ("npy-fortran", npy(default_header.replace("False","True"), payload), "header mismatch"),
            ("npy-short", original[:-8], "payload extent"),
            ("npy-appended", original+b"x", "payload extent"),
            ("npy-nan", original[:prefix]+struct.pack("<d",float("nan"))+payload[8:], "nonfinite"),
            ("npy-negative", original[:prefix]+struct.pack("<d",-1.)+payload[8:], "negative"),
        ]
        for name, raw, message in malformed:
            ref = {**session.write("controls/"+name+".npy", raw),"dtype":"<f8","shape":[240,320]}
            reject(name, lambda ref=ref: A.Reads(core,budget).scalar(ref), message)
        del malformed, original, payload
        tracked = A.Reads(core,budget)
        arr = tracked.scalar(private_array)
        del arr
        changed = ROOT/private["path"]
        old = changed.read_bytes()
        try:
            budget.output_bytes += len(old)
            budget.check()
            changed.write_bytes(old[:-1]+bytes([old[-1]^1]))
            reject("changed-input-at-finish", tracked.finish, "changed before completion")
        finally:
            budget.output_bytes += len(old)
            changed.write_bytes(old)
        add("restored-input-at-finish", bool(tracked.finish()), {"restored_file": private})
        a = budget.empty((5,8),"<f8","owner control")
        before = budget.live()
        budget.watch(a[:,1:],"alias control")
        add("live-owner-alias", budget.live() == before, {"delta_bytes":budget.live()-before})
        token = id(a)
        del a
        gc.collect()
        b = budget.empty((5,8),"<f8","new live owner")
        # Deterministically plant a dead weak entry at the new owner's id.
        dead = budget.np.empty((1,),dtype="<f8")
        import weakref
        stale = weakref.ref(dead)
        del dead
        budget.owners[id(b)] = (stale,8,{"expired control"})
        budget.watch(b,"restored actual owner")
        add("expired-owner-reuse", budget.owners[id(b)][0]() is b and budget.owners[id(b)][1] == 320,
            {"prior_token":token,"dead_weakref":stale() is None,"actual_live_bytes":320})
        del b
        a = budget.empty((18<<20,),"|u1","retained allocation A")
        reject("live-cumulative-allocation", lambda: budget.empty((18<<20,),"|u1","allocation B"),
               "allocation would exceed")
        del a
        valid("genuine-final-restored")
        need(tuple(row["name"] for row in result["checks"]) == CONTROL_IDS, "authority controls population/order")
        need(budget.forbidden_calls == 0 and budget.generators == 0 and sum(budget.requested.values()) == 0,
             "authority controls performed forbidden work")
        result["status"] = "PASS_ACTUAL_FLOAT_AUTHORITY_CONTROLS"
    except Exception:
        result["error"] = traceback.format_exc()
    result["inputs_before"] = dict(session.reads.observed)
    session.terminal(result)
    print(S.canonical({"status":result["status"],"check_count":result["check_count"],
                       "result":S.file_ref(args.output/"result.json")}).decode(),flush=True)
    return 0 if result["status"] == "PASS_ACTUAL_FLOAT_AUTHORITY_CONTROLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
