"""One resource-only rerun after the comparator exceeded our 12 GiB cap."""
from pathlib import Path
import ctypes
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=HERE/'vitamin-c-comparator-2'
OUT=HERE/'vitamin-c-fork-40g-1'
spec=importlib.util.spec_from_file_location('vitamin_retry', HERE/'vitamin-c-comparator.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in
        ('total_physical','available_physical','total_page','available_page','total_virtual','available_virtual','extended')]

def main():
    failure=json.loads((BASE/'fork-process.json').read_text())
    assert failure['error']=="ValueError('child committed-memory bound')"
    memory=Memory();memory.length=ctypes.sizeof(Memory)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    assert memory.available_physical>=48<<30
    freeze=json.loads((BASE/'fork-freeze.json').read_text())
    assert m.ref(m.FORK)==freeze['executable']
    assert m.ref(BASE/'developed/receipt.json')==freeze['development_receipt']
    receipt=json.loads((BASE/'developed/receipt.json').read_text())
    for row in receipt['frames']:
        assert m.m.binding(Path(row['output']))==dict(sha256=row['output_sha256'],bytes=row['output_bytes'])
    inputs=json.loads((HERE/'vitamin-c-baseline-1/invocation.json').read_text())['inputs']
    m.inputs_unchanged(inputs)
    OUT.mkdir()
    command=freeze['command'].copy()
    assert command[1].startswith('--output=')
    command[1]='--output='+str(OUT/'fork.tiff')
    assert command[2:]==freeze['command'][2:]
    m.save(OUT/'amendment.json',dict(failed_process=m.ref(BASE/'fork-process.json'),frozen_plan=m.ref(BASE/'fork-freeze.json'),
        changed=['output path','job commit cap12GiBto40GiB'],all_quality_settings_unchanged=True,
        available_physical_before=memory.available_physical,total_physical=memory.total_physical,
        runner=m.ref(Path(__file__)),note='Prior coffee comparator required40GiB;12GiB was an insufficient harness cap, not engine failure.'))
    m.job(command,OUT,'fork',dict(wall_seconds=600,cpu_seconds=2400,log_bytes=16<<20,committed_bytes=40<<30))
    m.inputs_unchanged(inputs)
    import tifffile
    with tifffile.TiffFile(OUT/'fork.tiff') as tf:
        shape=list(tf.pages[0].shape);dtype=str(tf.pages[0].dtype)
    assert len(shape)==3 and shape[2]==3 and dtype=='uint16'
    m.save(OUT/'completion.json',dict(status='COMPLETE_UNREVIEWED',image=m.ref(OUT/'fork.tiff'),shape=shape,dtype=dtype,
        baseline=m.ref(HERE/'vitamin-c-baseline-1/vitamin-c.tiff'),original_metadata_unchanged=True))

if __name__=='__main__':main()
