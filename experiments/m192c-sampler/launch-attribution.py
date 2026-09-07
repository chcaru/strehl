import json
from pathlib import Path
import subprocess
import sys
import time
import sampler

rows=[]
for outer in (0,subprocess.CREATE_NO_WINDOW):
    for inner in (0,subprocess.CREATE_NO_WINDOW):
        job=sampler.k32.CreateJobObjectW(None,None)
        script=("import subprocess,sys; "
                "p=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(.15)'],"
                f"creationflags={inner}); p.wait()")
        p=subprocess.Popen([sys.executable,"-B","-c",script],
                           creationflags=sampler.h.CREATE_SUSPENDED|outer)
        sampler.h.assign_process_to_job(job,p)
        known={}
        while True:
            pids=sampler.h.job_process_ids(job)
            table=sampler.h.process_table()
            for pid in pids:
                counters=sampler.h.process_counters(pid)
                if counters:
                    known[pid]={"pid":pid,**table.get(pid,{}),"created":counters["created"]}
            accounting=sampler.h.job_accounting(job)
            if p.poll() is not None and accounting["active_processes"]==0:
                break
            time.sleep(.005)
        p.wait()
        sampler.k32.CloseHandle(job)
        rows.append({"outer_create_no_window":bool(outer),"inner_create_no_window":bool(inner),
                     "accounting":accounting,"observed":list(known.values())})
output=sampler.HERE/"launch-attribution.json"
output.write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
print(json.dumps(rows,indent=2))
