"""M192e bounded persistence adapter. No imports of product/observer code."""
from __future__ import annotations
import hashlib
import json
import math
import re
import stat
import os
from pathlib import Path
import time

MIB = 1 << 20
FAMILIES = dict(terminal=MIB, trace=61*MIB, metadata=12*MIB,
                logs=16*MIB, raster=672*MIB, scratch=128*MIB)
TOTAL = 1 << 30
assert sum(FAMILIES.values()) <= TOTAL
SLOT_BYTES = 4*MIB
RECORD_BYTES = 8*MIB

def need(ok, message):
    if not ok: raise ValueError(message)

def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()

def sha(raw): return hashlib.sha256(raw).hexdigest().upper()

def parse_json(raw):
    def pairs(items):
        answer = {}
        for k, value in items:
            need(k not in answer, "duplicate JSON key")
            answer[k] = value
        return answer
    def bad(value): raise ValueError("nonfinite JSON")
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    def finite(item):
        if type(item) is float: need(math.isfinite(item), "overflow JSON float")
        elif type(item) is dict:
            for child in item.values(): finite(child)
        elif type(item) is list:
            for child in item: finite(child)
    finite(value)
    return value

def bytes_binding(path, cap=RECORD_BYTES, *, expected=None, expected_sha256=None):
    """Authenticate the same bounded buffer that the caller will consume."""
    path = lexical_path(path)
    before = path.stat(follow_symlinks=False)
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
                        getattr(s, "st_file_attributes", 0), s.st_nlink)
    need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "bounded regular metadata")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need(fields(opened) == fields(before), "metadata opened identity")
        raw = stream.read(cap+1)
        after_handle = os.fstat(stream.fileno())
    after = path.stat(follow_symlinks=False)
    need(fields(before) == fields(opened) == fields(after_handle) == fields(after)
         and len(raw) == before.st_size <= cap, "stable complete metadata buffer")
    actual = dict(path=str(path), bytes=len(raw), sha256=sha(raw))
    if expected is not None:
        ref_shape(expected)
        need(lexical_path(expected["path"]) == path
             and actual["bytes"] == expected["bytes"]
             and actual["sha256"] == expected["sha256"].upper(), "same-byte FileRef")
    if expected_sha256 is not None:
        need(type(expected_sha256) is str and actual["sha256"] == expected_sha256.upper(),
             "same-byte released digest")
    return raw, actual

def json_binding(path, cap=RECORD_BYTES, **expected):
    raw, actual = bytes_binding(path, cap, **expected)
    return parse_json(raw), actual

def read_json(path, cap=RECORD_BYTES):
    return json_binding(path, cap)[0]

def read_ref(ref, cap=RECORD_BYTES):
    ref_shape(ref)
    return json_binding(ref["path"], cap, expected=ref)[0]

def environment_domain(defaults_ref, binding_reader):
    # Same normalized source pinned by M192b at4e6b4572, without child Git commands.
    raw, _ = bytes_binding(defaults_ref["path"], expected=defaults_ref)
    need(sha(raw.replace(b"\r\n", b"\n")) ==
         "2C1763DF47FC04B082D7969470F347D2A5D8960BB0EADB16F4587B52CB5D013F",
         "frozen declared-environment source")
    declared = set(re.findall(r'"(STREHL_[A-Z0-9_]+)"\s*:\s*Declared\(', raw.decode("utf-8")))
    need(declared, "exercised declared STREHL environment domain")
    return declared | binding_reader.THREAD_ENV | binding_reader.ACTIVE_ENV


def lexical_path(path, *, missing=False):
    """Reject supplied lexical reparse components before resolving the target."""
    path=Path(os.path.abspath(path))
    for component in (path,*path.parents):
        try:info=component.lstat()
        except FileNotFoundError:
            need(missing,"missing lexical component");continue
        need(not component.is_symlink() and not (getattr(info,"st_file_attributes",0)&0x400),
             "lexical reparse component")
    return path.resolve()

def binding(path):
    path = lexical_path(path)
    before = path.stat()
    need(path.is_file(), "regular file")
    h = hashlib.sha256(); size = 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need((before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
             "opened file identity")
        while raw := stream.read(MIB): h.update(raw); size += len(raw)
        after_handle = os.fstat(stream.fileno())
    after = path.stat()
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    need(fields(before) == fields(opened) == fields(after_handle) == fields(after)
         and size == before.st_size, "file changed during binding")
    return dict(path=str(path), bytes=size, sha256=h.hexdigest().upper())

def ref_shape(ref):
    need(type(ref) is dict and set(ref) == {"path", "bytes", "sha256"}, "FileRef fields")
    need(type(ref["path"]) is str and Path(ref["path"]).is_absolute()
         and type(ref["bytes"]) is int and ref["bytes"] >= 0
         and type(ref["sha256"]) is str and len(ref["sha256"]) == 64
         and all(c in "0123456789abcdefABCDEF" for c in ref["sha256"]),
         "FileRef types")
def check_ref(ref):
    ref_shape(ref)
    actual = binding(ref["path"])
    need(actual["bytes"] == ref["bytes"] and actual["sha256"] == ref["sha256"].upper(),
         "FileRef bytes/digest")
    return actual

class Budget:
    """Fixed durable-slot reservation plus observed native output limits.

    Reservations are peak extents per path, never cumulative write traffic.
    Directory checks include hidden/system entries through os.walk. Native file
    growth is observed, not a filesystem quota or a zero-overshoot promise.
    """
    def __init__(self, output, seconds, cpu_seconds=None, *, started=None):
        self.output = lexical_path(output,missing=True)
        self.deadline = (time.monotonic() if started is None else started) + seconds
        self.cpu_limit=cpu_seconds;self.child_cpu=0.;self.accounting_error=None;self.job_queries=0
        self.extents = {}
        self.last_scan = 0
        self.bytes_written = 0
        self.observed = {}
        self.vanished_during_scan = 0

    def family(self, path):
        rel = path.relative_to(self.output).as_posix()
        if rel.endswith(".tiff"): return "raster"
        if rel.endswith(".log"): return "logs"
        if "/trace/" in "/" + rel or rel.endswith("/monitor.json"): return "trace"
        if rel.startswith("work/cache/") or rel.startswith("work/monitor/"): return "scratch"
        if rel == "child.json": return "terminal"
        if any(rel==name or rel.endswith("/"+name) for name in
               ("result.json", "first-publication.json", "publication-stage.json",
                "emergency-refusal.json", "terminal-tail.json", "terminal-tail-stage.json")): return "terminal"
        return "metadata"

    def observe_job(self,value):
        self.job_queries+=1
        if type(value) is dict and type(value.get("total_cpu_100ns")) is int and value["total_cpu_100ns"]>=0:
            cpu=value["total_cpu_100ns"]/1e7
            if cpu>=self.child_cpu:self.child_cpu=cpu
            else:self.accounting_error="decreasing observed Job CPU"
        else:self.accounting_error="missing typed observed Job CPU"

    def reserve(self, path, size, family, terminal=False):
        path = Path(path).resolve()
        need(path.is_relative_to(self.output) and family in FAMILIES
             and type(size) is int and size >= 0, "owned reservation")
        key = str(path)
        old = self.extents.get(key)
        need(old is None or old[0] == family, "reservation family changed")
        candidate = dict(self.extents)
        candidate[key] = (family, max(size, 0 if old is None else old[1]))
        totals = {k: sum(n for f,n in candidate.values() if f == k) for k in FAMILIES}
        need(all(totals[k] <= FAMILIES[k] for k in FAMILIES)
             and sum(totals.values()) <= TOTAL, "reservation capacity")
        self.extents = candidate
        self.check(False, terminal=terminal)

    def check(self, force=False, terminal=False):
        now = time.monotonic()
        need(terminal or now <= self.deadline, "ordinary deadline")
        if not terminal:
            need(self.accounting_error is None,"invalid observed Job accounting")
            need(self.cpu_limit is None or time.process_time()+self.child_cpu<=self.cpu_limit,"combined CPU bound")
        if force or now-self.last_scan >= .1:
            self.last_scan = now
            totals = {k: 0 for k in FAMILIES}
            for base, dirs, names in os.walk(self.output, followlinks=False):
                for name in dirs + names:
                    p = Path(base)/name
                    try: stat = p.lstat()
                    except FileNotFoundError:
                        self.vanished_during_scan += 1
                        continue
                    need(not p.is_symlink() and
                         not (getattr(stat, "st_file_attributes", 0) & 0x400),
                         "owned tree reparse point")
                for name in names:
                    p = Path(base)/name
                    try: totals[self.family(p)] += p.stat().st_size
                    except FileNotFoundError: self.vanished_during_scan += 1
            self.observed = totals
            # Terminal publication remains possible after an ordinary overflow.
            if not terminal:
                need(all(totals[k] <= FAMILIES[k] for k in FAMILIES)
                     and sum(totals.values()) <= TOTAL, "observed output capacity")

    def write(self, path, raw, family="metadata", cap=RECORD_BYTES, replace=False):
        need(type(raw) is bytes and 0 < len(raw) <= cap, "ordinary payload capacity")
        path = Path(path)
        self.reserve(path, len(raw), family)
        need(replace or not path.exists(), "fresh evidence")
        with path.open("wb" if replace else "xb") as stream:
            need(stream.write(raw) == len(raw), "complete write")
            stream.flush(); os.fsync(stream.fileno())
        self.bytes_written += len(raw)
        actual = binding(path)
        need(actual["sha256"] == sha(raw), "evidence readback")
        self.check(True)
        return actual

class Checkpoint:
    """Two committed generations and one precharged staging extent."""
    def __init__(self, budget, directory, identity, size=SLOT_BYTES):
        self.budget = budget
        self.directory = Path(directory)
        self.directory.mkdir(parents=True)
        self.identity = identity
        self.size = size
        need(type(size) is int and 512<=size<=SLOT_BYTES,"fixed checkpoint size")
        self.sequence = 0
        self.previous = "0"*64
        self.paths = [self.directory/f"slot-{i}.json" for i in range(2)]
        self.stage = self.directory/"stage.json"
        self.history = []
        for p in self.paths+[self.stage]:
            budget.reserve(p, size, "trace")
            self._write(p, self.pack(dict(schema="m192e-checkpoint-v1",
                        identity=identity, sequence=-1, status="INCOMPLETE",
                        previous_sha256="0"*64, payload_sha256=sha(encode(None)), payload=None)))

    def pack(self, value):
        raw = encode(value)
        need(len(raw) <= self.size, "trace checkpoint capacity")
        return raw + b" "*(self.size-len(raw))

    def _write(self, path, raw):
        with path.open("wb") as stream:
            need(stream.write(raw) == len(raw), "checkpoint full write")
            stream.flush(); os.fsync(stream.fileno())
        self.budget.bytes_written += len(raw)

    def save(self, payload, *, fault=None):
        value = dict(schema="m192e-checkpoint-v1", identity=self.identity,
                     sequence=self.sequence, status="INCOMPLETE",
                     previous_sha256=self.previous, payload_sha256=sha(encode(payload)), payload=payload)
        raw = self.pack(value)  # overflow occurs before altering either generation
        self.budget.check(True)
        if fault == "partial-stage":
            self._write(self.stage, raw[:len(raw)//2])
            raise OSError("DECLARED_PARTIAL_STAGE")
        self._write(self.stage, raw)
        if fault == "before-replace":
            raise OSError("DECLARED_BEFORE_REPLACE")
        target = self.paths[self.sequence % 2]
        os.replace(self.stage, target)
        actual = binding(target)
        need(actual["bytes"] == self.size and actual["sha256"] == sha(raw),
             "checkpoint exact readback")
        self.previous = actual["sha256"]
        self.sequence += 1
        self.history.append(dict(sequence=self.sequence-1, **actual))
        # Only two latest checkpoint witnesses; publication count is separate.
        self.history = self.history[-2:]
        return actual

    def recover(self):
        rows, errors = [], []
        for p in self.paths:
            try:
                v, actual = json_binding(p, self.size)
                need(actual["bytes"] == self.size and
                     v["schema"] == "m192e-checkpoint-v1"
                     and set(v)=={"schema","identity","sequence","status","previous_sha256","payload_sha256","payload"}
                     and v["identity"] == self.identity and v["status"]=="INCOMPLETE"
                     and type(v["sequence"]) is int and v["sequence"]>=-1
                     and type(v["previous_sha256"]) is str and len(v["previous_sha256"])==64
                     and all(c in "0123456789ABCDEF" for c in v["previous_sha256"])
                     and (v["sequence"]!=-1 or (v["payload"] is None and v["previous_sha256"]=="0"*64))
                     and (v["sequence"]!=0 or v["previous_sha256"]=="0"*64)
                     and v["payload_sha256"] == sha(encode(v["payload"])), "checkpoint identity")
                rows.append((v, actual))
            except Exception as e:
                errors.append(dict(path=str(p), error=repr(e)))
        need(rows, "no readable checkpoint generation")
        rows.sort(key=lambda x: x[0]["sequence"])
        if len(rows) == 2 and rows[-2][0]["sequence"] >= 0:
            need(rows[-1][0]["sequence"] == rows[-2][0]["sequence"]+1
                 and rows[-1][0]["previous_sha256"] == rows[-2][1]["sha256"],
                 "checkpoint generation chain")
        return dict(status="RECOVERABLE_INCOMPLETE",
                    latest=rows[-1][1], sequence=rows[-1][0]["sequence"],
                    generations=[r for _,r in rows], errors=errors,
                    may_resume=False, may_certify=False)


