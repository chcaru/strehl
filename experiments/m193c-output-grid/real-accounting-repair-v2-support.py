"""V2 grant adapter; exact held operational bodies, fixed cumulative-bound control update."""
import ast,hashlib,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
PIN=dict(bytes=22268,sha256="295e5d5e5289cff1f0657e697016c6c98f657fa14178b20567090ce64d4aaba0")
def need(ok,message):
    if not ok:raise ValueError(message)
path=HERE/"real-accounting-repair-support.py"
with path.open("rb") as stream:raw=stream.read(PIN["bytes"]+1)
need(len(raw)==PIN["bytes"] and hashlib.sha256(raw).hexdigest()==PIN["sha256"],"held v1 operational helper")
base=types.ModuleType("m193c_v2_held_operational_bodies");base.__file__=str(path)
sys.modules[base.__name__]=base
exec(compile(raw,str(path),"exec"),base.__dict__)
# Only the separately authorized cumulative CPU ceilings change. Local science,
# cleanup, transport, reservations, observer wrappers and tests retain their bodies.
base.OLD_GLOBAL=dict(base.OLD_GLOBAL,cpu_seconds=1320)
base.NEW_GLOBAL=dict(base.NEW_GLOBAL,cpu_seconds=1440)
node=next(x for x in ast.parse(raw).body if isinstance(x,ast.FunctionDef) and x.name=="live_controls")
class CeilingControl(ast.NodeTransformer):
    def __init__(self):self.counts={}
    def visit_Constant(self,node):
        changes={1222:1342,1319:1439,1200:1320,1320:1440,
                 "retired1200 replaced only by explicit1320":"retired1320 replaced only by explicit1440"}
        if type(node.value) in (int,str) and node.value in changes:
            self.counts[str(node.value)]=self.counts.get(str(node.value),0)+1
            return ast.copy_location(ast.Constant(changes[node.value]),node)
        return node
update=CeilingControl();node=update.visit(node)
need(update.counts=={"1222":1,"1319":1,"1200":1,"1320":1,
     "retired1200 replaced only by explicit1320":1},"closed cumulative-control edits")
tree=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
exec(compile(tree,str(Path(__file__).resolve()),"exec"),base.__dict__)
for name in ("OLD_GLOBAL","NEW_GLOBAL","ATTEMPT","EXTENSION","make_budget","prepare_transport",
             "write_slot","refresh_recovery","operation_controls","live_controls","live_job_accounting",
             "capture_child","encoded"):
    globals()[name]=getattr(base,name)
