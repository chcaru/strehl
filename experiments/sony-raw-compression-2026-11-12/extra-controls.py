"""Adversarial full-file transport and compression-benefit controls.

Synthetic results are controls, never estimates of real camera compression.
"""
import io
import json
import struct
import numpy as np
import imagecodecs as ic
from bench import transform
from advanced import shifted_reference
import wire


def tiff(a):
    """Minimal uncompressed CFA TIFF, with metadata and trailing bytes."""
    h, w = a.shape
    tags = [(256, 4, w), (257, 4, h), (258, 3, 16), (259, 3, 1),
            (262, 3, 32803), (273, 4, 256), (277, 3, 1), (279, 4, a.nbytes)]
    prefix = bytearray(256)
    prefix[:8] = b'II*\0' + struct.pack('<I', 8)
    struct.pack_into('<H', prefix, 8, len(tags))
    for i, (tag, typ, value) in enumerate(tags):
        struct.pack_into('<HHII', prefix, 10 + i * 12, tag, typ, 1, value)
    prefix[160:176] = bytes(range(16))
    return bytes(prefix) + a.astype('<u2').tobytes() + b'preview-padding\0\xff'


def main():
    rng = np.random.default_rng(240112)
    yy, xx = np.indices((258, 520))
    arrays = [np.zeros((258, 520), 'u2'), np.full((258, 520), 65535, 'u2'),
              ((xx * 17 + yy * 83) % 65536).astype('u2'),
              rng.integers(0, 65536, (258, 520), dtype='u2')]
    successes = refused = 0
    for a in arrays:
        raw = tiff(a)
        assert wire.layout(raw)['body_bytes'] == a.nbytes
        for workers in [1, 4]:
            packet = b''.join(wire.encode_iter(raw, workers=workers, rows=128))
            out = io.BytesIO()
            assert wire.receive(io.BytesIO(packet), out)['exact'] and out.getvalue() == raw
            successes += 1
            hsize = struct.unpack_from('<I', packet, 8)[0]
            first = 12 + hsize
            n, psize, _, _ = struct.unpack_from('<IIBI', packet, first)
            body = first + 13 + psize
            mutations = [packet[:body + 16], packet[:-1], packet + b'!',
                         packet[:body + 8] + b'\xfe' + packet[body + 9:],
                         packet[:body + 9] + struct.pack('<I', 0) + packet[body + 13:],
                         packet[:body] + struct.pack('<I', wire.MAX_CHUNK + 1) + packet[body + 4:]]
            # A literal incompressible chunk ignores width; substitute mode 8
            # as well so a zero width is an invalid CFA command in every arm.
            mutations[4] = packet[:body + 8] + b'\x08' + struct.pack('<I', 0) + packet[body + 13:]
            damaged = bytearray(packet)
            damaged[body + 17] ^= 128
            mutations.append(bytes(damaged))
            for bad in mutations:
                try:
                    wire.receive(io.BytesIO(bad), io.BytesIO())
                except (AssertionError, ValueError, RuntimeError):
                    refused += 1
                else:
                    raise AssertionError('Accepted corrupt CFA transport')
    print(json.dumps({'cfa_wire_exact_roundtrips': successes,
                      'cfa_wire_malformed_refusals': refused}), flush=True)

    # Repeated texture with fresh shot/read noise. No noise is removed from
    # samples: only the optional reference used to predict them is filtered.
    yy, xx = np.indices((512, 512))
    phase = np.array([[1.0, 1.7], [1.5, 0.7]])[yy % 2, xx % 2]
    signal = (1800 + 700 * np.sin(xx / 23) + 500 * np.cos(yy / 31)) * phase
    def exposure():
        return np.clip(np.rint(512 + rng.poisson(signal) + rng.normal(0, 3, signal.shape)), 0, 65535).astype('u2')
    first = exposure()
    second = exposure()
    unrelated = rng.integers(0, 65536, signal.shape, dtype='u2')
    for name, target, reference in [
            ('identical-frame-positive', first, first),
            ('fresh-photon-and-read-noise', second, first),
            ('filtered-reference-fresh-noise', second, shifted_reference(first, 0, 0, True)),
            ('wrong-cfa-phase', second, np.roll(first, 1, axis=1)),
            ('changed-exposure', (second.astype('u4') * 2).clip(0, 65535).astype('u2'), first),
            ('unrelated-random-negative', unrelated, first)]:
        sizes = {}
        for mode in [8, 4]:
            ref = reference if mode == 4 else None
            residual = transform(target, mode, ref)
            packed = ic.zstd_encode(residual, level=1)
            decoded = np.frombuffer(ic.zstd_decode(packed), dtype='u1')
            restored = transform(decoded, mode, ref, True, target.shape)
            assert np.array_equal(restored, target)
            sizes[str(mode)] = len(packed)
        print(json.dumps({'synthetic_control': name, 'raw_cfa_bytes': target.nbytes,
                          'spatial_bytes': sizes['8'], 'temporal_bytes': sizes['4'],
                          'exact': True}), flush=True)


if __name__ == '__main__':
    main()
