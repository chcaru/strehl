"""Bounded owned publication slots. Stdlib only; no I/O on import."""
import hashlib
import json
import os
from pathlib import Path

KIB=1024
NAMES=("result.json","first-publication.json","publication-stage.json","emergency-refusal.json")

def need(ok,message):
    if not ok:raise ValueError(message)

def sha(data):return hashlib.sha256(data).hexdigest()

def encoded(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()

def ref(path,data):return dict(path=str(Path(path).resolve()),bytes=len(data),sha256=sha(data))

class Writer:
    """The enclosing Budget owns actual I/O, monotone extents and hard limits."""
    def __init__(self,budget,root,family):
        self.budget=budget;self.root=Path(root).resolve();self.family=family
        need(self.root.is_relative_to(budget.output.resolve()),"owned writer root")
    def path(self,path):
        path=Path(path).resolve()
        need(path.is_relative_to(self.root) and path.parent.is_dir(),"owned existing parent")
        return path
    def write(self,path,data,*,replace=False,terminal=False):
        path=self.path(path);need(type(data) is bytes and len(data)>0,"positive bounded payload")
        self.budget.reserve(path,len(data),self.family,terminal)
        need(replace or not path.exists(),"fresh ordinary payload")
        with path.open("wb" if replace else "xb") as stream:
            need(stream.write(data)==len(data),"complete payload write")
            stream.flush();os.fsync(stream.fileno())
        need(path.read_bytes()==data,"actual payload readback")
        self.budget.check(True,terminal=terminal)
        return ref(path,data)
    def replace(self,source,target):
        source=self.path(source);target=self.path(target)
        need(source.parent==target.parent and source!=target and source.is_file() and target.is_file(),"same-directory owned atomic slots")
        os.replace(source,target)
        self.budget.check(True,terminal=True)

class Publisher:
    """Four precharged fixed slots; emergency bytes exist before scientific work."""
    def __init__(self,writer,base,size=64*KIB):
        self.writer=writer;self.size=size
        need(type(size) is int and 512<=size<=64*KIB,"declared slot size")
        self.paths={name:writer.root/name for name in NAMES}
        self.default=dict(base,status="REFUSED",publication_phase="INITIAL_INCOMPLETE",error=None)
        raw=self.pack(self.default)
        for path in self.paths.values():writer.write(path,raw,terminal=True)
        self.default_raw=raw
    def pack(self,value):
        raw=encoded(value);need(len(raw)<=self.size,"terminal slot capacity")
        return raw+b" "*(self.size-len(raw))
    def actual(self):
        data=self.paths["result.json"].read_bytes()
        need(len(data)==self.size,"fixed canonical slot extent")
        value=json.loads(data);need(type(value) is dict,"canonical JSON object")
        return value,ref(self.paths["result.json"],data)
    def publish(self,value,late=lambda:None,emit=lambda receipt:None,after=lambda:None):
        first=None;failure=None;phase="ENCODING";revocation_errors=[]
        try:
            raw=self.pack(value)
            if value["status"]!="REFUSED":
                phase="RETAIN_FIRST_POSITIVE"
                self.writer.write(self.paths["first-publication.json"],raw,replace=True,terminal=True)
                first=ref(self.paths["first-publication.json"],raw)
            phase="CANONICAL_REPLACEMENT"
            self.writer.write(self.paths["publication-stage.json"],raw,replace=True,terminal=True)
            self.writer.replace(self.paths["publication-stage.json"],self.paths["result.json"])
            phase="LATE_CHECK_BEFORE_STDOUT";late()
            actual,receipt=self.actual()
            need(actual==value,"exact canonical publication object")
            phase="STDOUT";emit(receipt)
            phase="AFTER_STDOUT";after()
            return dict(passed=value["status"]!="REFUSED",canonical=receipt,first_positive=first,error=None,canonical_refusal_verified=value["status"]=="REFUSED",phase="TERMINAL")
        except BaseException as exc:
            failure=dict(type=type(exc).__name__,message=str(exc),phase=phase)
            try:
                refused=dict(self.default if phase=="ENCODING" else value,status="REFUSED",publication_phase="TERMINAL_REFUSAL",error=failure,first_positive=first)
                raw=self.pack(refused)
                self.writer.write(self.paths["publication-stage.json"],raw,replace=True,terminal=True)
                self.writer.replace(self.paths["publication-stage.json"],self.paths["result.json"])
            except BaseException as detailed:
                revocation_errors.append(dict(stage="detailed",type=type(detailed).__name__,message=str(detailed)))
                # Never overwrite the prewritten fallback while formatting a detailed error.
                try:self.writer.replace(self.paths["emergency-refusal.json"],self.paths["result.json"])
                except BaseException as emergency:
                    revocation_errors.append(dict(stage="emergency",type=type(emergency).__name__,message=str(emergency)))
            try:actual,receipt=self.actual();refused=actual.get("status")=="REFUSED"
            except BaseException as read_error:
                receipt=None;refused=False
                revocation_errors.append(dict(stage="readback",type=type(read_error).__name__,message=str(read_error)))
            return dict(passed=False,canonical=receipt,canonical_refusal_verified=refused,first_positive=first,error=failure,
                        revocation_errors=revocation_errors,phase="TERMINAL_REFUSAL")

def commission(budget,root,observations,progress):
    """Same real writer and publisher, fixed miniature capacities; no fits/models."""
    root=Path(root);root.mkdir()
    need(type(observations) is list and not observations,"fresh caller-owned control progress")
    def test(name,action):
        directory=root/name;row=dict(id=name,passed=False,before={})
        observations.append(row)
        try:
            directory.mkdir();writer=Writer(budget,directory,"publication")
            publisher=Publisher(writer,dict(schema="m193c-publication-control-slot-v1",control=name),4096)
            row["before"]={p.name:sha(p.read_bytes()) for p in directory.iterdir()}
            action(writer,publisher,row);row["passed"]=True
        except BaseException as exc:
            row["error"]=dict(type=type(exc).__name__,message=str(exc));raise
        finally:
            row["after"]={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in directory.iterdir()} if directory.exists() else {}
            progress(observations)
    success=dict(schema="m193c-publication-control-result-v1",status="COMPLETE",answer=41)
    intrinsic=sha(encoded(success))
    def normal(writer,pub,row):
        emitted=[];result=pub.publish(success,emit=emitted.append)
        value,actual=pub.actual()
        need(result["passed"] and value==success and len(emitted)==1 and emitted[0]==actual,"actual normal terminal publication")
        need(pub.paths["first-publication.json"].read_bytes()==pub.paths["result.json"].read_bytes(),"retained positive before canonical")
        row.update(result=result,intrinsic_sha256=sha(encoded(value)))
    test("normal",normal)
    def capacity(writer,pub,row):
        # An actual local ordinary quota uses the same Budget.reserve branch as science.
        directory=writer.root;payload=b"x"*4096
        with budget.quota(directory,4096):
            writer.write(directory/"filled.txt",payload)
            error=None
            try:writer.write(directory/"one-extra-byte.txt",b"x")
            except ValueError as exc:error=str(exc)
            need(error=="ordinary quota capacity" and not (directory/"one-extra-byte.txt").exists(),"one-byte overflow rejected before write")
            value,_=pub.actual()
            need(value["status"]=="REFUSED" and all(json.loads(p.read_bytes())["status"]=="REFUSED" for p in pub.paths.values()),"overflow preserves all durable refusal slots")
            refused=dict(pub.default,publication_phase="CAPACITY_FAULT")
            result=pub.publish(refused);value,_=pub.actual()
            need(value==refused and result["canonical_refusal_verified"] is True and result["passed"] is False,"terminal lane survives saturated ordinary quota with verified refusal")
        row.update(error=error,result=result,payload_sha256=sha(payload))
    test("capacity",capacity)
    def oversized(writer,pub,row):
        value=dict(status="COMPLETE",padding="")
        extra=pub.size+1-len(encoded(value));need(extra>0,"actual oversized-control range")
        value["padding"]="x"*extra;need(len(encoded(value))==pub.size+1,"one-byte oversized terminal record")
        result=pub.publish(value);actual,_=pub.actual()
        need(not result["passed"] and result["error"]["phase"]=="ENCODING" and actual["status"]=="REFUSED","oversized terminal remains refusal")
        need(pub.paths["first-publication.json"].read_bytes()==pub.default_raw,"oversized positive never retained")
        row["result"]=result
    test("oversized",oversized)
    def late(writer,pub,row):
        emitted=[]
        def fault():raise ValueError("DECLARED_POST_PUBLICATION_FAULT")
        result=pub.publish(success,late=fault,emit=emitted.append);value,_=pub.actual()
        need(not result["passed"] and value["status"]=="REFUSED" and not emitted,"pre-stdout late failure cannot emit complete")
        need(json.loads(pub.paths["first-publication.json"].read_bytes())==success,"first positive survives revocation")
        row["result"]=result
    test("late-before-stdout",late)
    def restored(writer,pub,row):
        payload=b"ACTUAL_ORDINARY_PAYLOAD";writer.write(writer.root/"unchanged.txt",payload)
        before=sha((writer.root/"unchanged.txt").read_bytes())
        def fault():raise ValueError("DECLARED_RESTORATION_PRECEDING_FAULT")
        failed=pub.publish(success,late=fault)
        need(not failed["passed"] and failed["canonical_refusal_verified"],"same-instance fault precedes restoration")
        calls=[];result=pub.publish(success,late=lambda:calls.append("placebo"))
        value,_=pub.actual()
        need(result["passed"] and calls==["placebo"] and sha(encoded(value))==intrinsic,"restored placebo exact intrinsic output")
        row.update(result=result,preceding_fault=failed,placebo_calls=calls,intrinsic_sha256=sha(encoded(value)),
                   ordinary_before=before,ordinary_after=sha((writer.root/"unchanged.txt").read_bytes()))
        need(row["ordinary_before"]==row["ordinary_after"],"actual ordinary payload unchanged across fault/restoration/placebo")
    test("restored-placebo",restored)
    def stdout_fault(writer,pub,row):
        escaped=[]
        def partial(receipt):
            escaped.append(dict(status="COMPLETE",receipt=receipt))
            raise OSError("DECLARED_STDOUT_FAILURE_AFTER_ESCAPE")
        result=pub.publish(success,emit=partial);value,_=pub.actual()
        need(len(escaped)==1 and not result["passed"] and result["error"]["phase"]=="STDOUT" and value["status"]=="REFUSED","canonical refusal governs after escaped stdout")
        row.update(result=result,escaped_stdout_witness=escaped,scope="injected emit failure; no claim of retracting bytes")
    test("stdout-after-escape",stdout_fault)
    def emergency(writer,pub,row):
        def fault():raise ValueError("x"*(pub.size*2))
        result=pub.publish(success,late=fault);value,_=pub.actual()
        need(not result["passed"] and result["canonical_refusal_verified"] and value==pub.default,"actual prewritten emergency fallback")
        need(result["revocation_errors"] and result["revocation_errors"][0]["stage"]=="detailed","detailed error overflow actually occurred")
        need(json.loads(pub.paths["first-publication.json"].read_bytes())==success,"positive retained through emergency fallback")
        row["result"]=result
    test("emergency-fallback",emergency)
    need(all(row["passed"] for row in observations),"all actual publication controls")
    return dict(schema="m193c-durable-publication-controls-v1",passed=True,rows=observations,
                scope="same writer/reservation/publisher; miniature slots; zero image/model/fit calls")
