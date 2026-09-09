"""Native live-publication census only; completed/retained scans stay strict."""
from pathlib import Path, PureWindowsPath
from types import FunctionType
import os,re,stat
COUNTS=(5,22,5,5,2,2,2,5,2)
def need(value,message):
    if not value:raise ValueError(message)
def local_path(path):
    value=str(path)
    if value.startswith("\\\\?\\"):value=value[4:]
    need(len(value)>=3 and value[0].isascii() and value[0].isalpha() and value[1:3]==":\\","local drive path")
    return PureWindowsPath(value)
def published_stat(stage,directory):
    """Only an exact same-directory, named publication target may replace a lost stage stat."""
    stage=Path(stage);directory=Path(directory)
    need(stage.parent==directory and stage.name.endswith(".stage"),"same-directory publication stage")
    name=stage.name[:-6];match=re.fullmatch(r"native-run-([0-8])",directory.name)
    need(match is not None,"fixed native publication directory")
    count=COUNTS[int(match[1])]
    frame=re.fullmatch(r"frame-(\d{2})-(?:original\.u16|route-[01](?:-prepared\.u16|\.trace|\.json))",name)
    allowed=(name in ("incomplete.json","result.json","failure.json")
             or re.fullmatch(r"route-[01]-(?:collapsed\.f32|native\.tiff)",name) is not None
             or frame is not None and int(frame[1])<count)
    need(allowed,"fixed native publication filename")
    target=directory/name
    # lstat sees dangling reparse entries; only the vanished stage itself may be absent.
    for p in (stage,*stage.parents):
        try:s=p.lstat()
        except FileNotFoundError:
            need(p==stage,"publication ancestor disappeared")
            continue
        need(not getattr(s,"st_file_attributes",0)&0x400 and not stat.S_ISLNK(s.st_mode),"publication reparse/symlink path")
    for p in (target,*target.parents):
        s=p.lstat()
        need(not getattr(s,"st_file_attributes",0)&0x400 and not stat.S_ISLNK(s.st_mode),"publication reparse/symlink path")
    need(local_path(target.resolve(strict=True))==local_path(target),"canonical publication target")
    s=target.stat();need(stat.S_ISREG(s.st_mode),"plain publication target")
    return target,s
def make_scanner(held,active,native_root):
    original=held.scan;owned=original.__globals__["owned"]
    HPath=original.__globals__["Path"];native_root=HPath(native_root)
    need(type(original) is FunctionType and original.__closure__ is None,"held scanner closure")
    transitions=[0];samples=[]
    class Stage:
        def __init__(self,path,directory,missing_owned=False):self.path=path;self.directory=directory;self.missing_owned=missing_owned
        def stat(self):
            try:
                if self.missing_owned:raise FileNotFoundError(str(self.path))
                return self.path.stat()
            except FileNotFoundError:
                target,s=published_stat(self.path,self.directory)
                transitions[0]+=1
                if len(samples)<8:samples.append(dict(stage=str(self.path),final=str(target),bytes=s.st_size))
                return s
    def scan(root,limit,*,tolerate_disappearance=False):
        invocation=active[0]
        if invocation is None or HPath(root)!=native_root/f"native-run-{invocation}" or tolerate_disappearance:
            return original(root,limit,tolerate_disappearance=tolerate_disappearance)
        need(type(invocation) is int and 0<=invocation<9,"fixed active native invocation")
        directory=HPath(root);transitions[0]=0;samples.clear()
        def live_owned(path):
            declared=HPath(path)
            eligible=declared.parent==directory and declared.name.endswith(".stage")
            try:path=owned(path)
            except FileNotFoundError:
                if not eligible:raise
                return Stage(declared,directory,missing_owned=True)
            return Stage(path,directory) if eligible else path
        namespace=dict(original.__globals__);namespace["owned"]=live_owned
        current=FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)
        current.__kwdefaults__=None if original.__kwdefaults__ is None else dict(original.__kwdefaults__)
        result=current(root,limit,tolerate_disappearance=False)
        result.update(publication_transitions=transitions[0],publication_samples=list(samples),
                      publication_scope="Active native directory only. A lost named stage charges its validated final extent; a separately enumerated final is also charged. Non-atomic conservative observed sum, not a peak or same-inode proof.")
        return result
    return scan
