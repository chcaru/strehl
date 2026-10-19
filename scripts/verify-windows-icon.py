"""Verify linked PE icon resources against the checked-in multiresolution ICO.

Missing resources, changed pixels, a wrong size, or a mismatched group fail.
This reads the executable itself; a successful resource-compiler exit is not
the evidence. No Windows API, desktop input, or external dependency is needed.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def verify(data, ico):
    def u16(offset):
        return struct.unpack_from('<H', data, offset)[0]

    def u32(offset):
        return struct.unpack_from('<I', data, offset)[0]

    assert data[:2] == b'MZ', 'Not a Windows executable'
    pe = u32(0x3c)
    assert data[pe:pe + 4] == b'PE\0\0', 'Missing PE header'
    optional = pe + 24
    magic = u16(optional)
    assert magic in (0x10b, 0x20b), 'Unknown PE optional header'
    directories = optional + (112 if magic == 0x20b else 96)
    resource_rva = u32(directories + 16)
    assert resource_rva, 'No resource directory in linked executable'
    section_start = optional + u16(pe + 20)
    sections = []
    for index in range(u16(pe + 6)):
        start = section_start + 40 * index
        sections.append((u32(start + 12), u32(start + 16), u32(start + 20)))

    def offset(rva):
        for virtual, size, raw in sections:
            if virtual <= rva < virtual + size:
                return raw + rva - virtual
        raise AssertionError('Resource points outside section data')

    base = offset(resource_rva)
    leaves = {}

    def directory(relative, path=()):
        assert len(path) < 4, 'Cyclic or unexpected resource hierarchy'
        start = base + relative
        count = u16(start + 12) + u16(start + 14)
        for index in range(count):
            entry = start + 16 + 8 * index
            name, target = u32(entry), u32(entry + 4)
            identity = name if not name & 0x80000000 else ('name', name & 0x7fffffff)
            key = path + (identity,)
            if target & 0x80000000:
                directory(target & 0x7fffffff, key)
            else:
                leaf = base + target
                location, size = offset(u32(leaf)), u32(leaf + 4)
                assert location + size <= len(data), 'Truncated resource payload'
                leaves[key] = (location, data[location:location + size])

    directory(0)
    groups = [(key, payload) for key, payload in leaves.items() if key[:2] == (14, 1)]
    assert len(groups) == 1, 'Expected one Strehl RT_GROUP_ICON with ID1'
    group_key, (_, group) = groups[0]
    assert struct.unpack_from('<HH', ico) == (0, 1), 'Invalid source ICO'
    count = struct.unpack_from('<H', ico, 4)[0]
    assert count == 9 and group[:6] == ico[:6], 'Missing native icon sizes'
    sizes, payload_offsets = [], []
    for index in range(count):
        source = 6 + index * 16
        target = 6 + index * 14
        assert group[target:target + 12] == ico[source:source + 12], 'Icon group metadata differs'
        length, source_offset = struct.unpack_from('<II', ico, source + 8)
        resource_id = struct.unpack_from('<H', group, target + 12)[0]
        key = (3, resource_id, group_key[2])
        assert key in leaves, 'Group references a missing RT_ICON'
        location, payload = leaves[key]
        assert len(payload) == length and payload == ico[source_offset:source_offset + length], 'Linked icon pixels differ'
        sizes.append(ico[source] or 256)
        payload_offsets.append(location)
    assert sizes == [16, 20, 24, 32, 40, 48, 64, 128, 256]
    return sizes, payload_offsets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--ico', type=Path, default=Path('crates/strehl-ui/assets/strehl.ico'))
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    data, ico = args.exe.read_bytes(), args.ico.read_bytes()
    sizes, offsets = verify(data, ico)
    # Independently destroy one embedded pixel/header byte. It must be caught
    # while the original checked-in artwork remains unchanged.
    altered = bytearray(data)
    altered[offsets[0] + 39] ^= 1
    try:
        verify(altered, ico)
    except AssertionError:
        pass
    else:
        raise AssertionError('Changed embedded payload passed verification')
    result = dict(executable=str(args.exe.resolve()), sha256=hashlib.sha256(data).hexdigest(),
                  ico_sha256=hashlib.sha256(ico).hexdigest(), embedded_sizes=sizes,
                  payloads_match=True, changed_payload_rejected=True)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('VERIFIED: nine embedded icon sizes match the source ICO; altered payload rejected')


if __name__ == '__main__':
    main()
