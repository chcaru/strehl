"""Read PE import names only; never loads or modifies a DLL."""
from pathlib import Path
import json
import struct

PROGRAM = Path(r'C:\dev\strehl-out\V-LINEAR2\fs15\focus-stack')
SYSTEM = Path(r'C:\Windows\System32')


def imports(path):
    data = path.read_bytes()
    pe = struct.unpack_from('<I', data, 60)[0]
    assert data[pe:pe+4] == b'PE\0\0'
    sections = struct.unpack_from('<H', data, pe+6)[0]
    optional_size = struct.unpack_from('<H', data, pe+20)[0]
    optional = pe+24
    magic = struct.unpack_from('<H', data, optional)[0]
    directories = optional+(112 if magic == 0x20b else 96)
    import_rva = struct.unpack_from('<I', data, directories+8)[0]
    table = optional+optional_size
    def offset(rva):
        for index in range(sections):
            size, address, raw_size, raw = struct.unpack_from('<IIII', data, table+40*index+8)
            if address <= rva < address+max(size, raw_size):
                return raw+rva-address
        raise ValueError(f'Unmapped RVA {rva}')
    if not import_rva:
        return []
    pos = offset(import_rva)
    names = []
    while any(data[pos:pos+20]):
        name = offset(struct.unpack_from('<I', data, pos+12)[0])
        names.append(data[name:data.index(0, name)].decode('ascii'))
        pos += 20
    return names


rows = []
for path in sorted(PROGRAM.iterdir()):
    if path.suffix.lower() not in ('.exe', '.dll'):
        continue
    names = imports(path)
    missing = [name for name in names if not name.lower().startswith(('api-ms-', 'ext-ms-'))
               and not (PROGRAM/name).exists() and not (SYSTEM/name).exists()]
    rows.append(dict(file=str(path), imports=names, not_found_in_program_or_system32=missing))
print(json.dumps(rows, indent=2))
