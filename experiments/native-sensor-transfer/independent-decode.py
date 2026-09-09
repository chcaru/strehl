"""Independent owned RAW ROI and native trace reader. No decoder import at module load.
The real caller pins full source bytes and runtime before supplying rawpy/NumPy.
This source never imports or executes a producer/helper as a numerical oracle.
"""
import hashlib
import io
import math
import struct

NONE = 2**32-1
SIDES = (128, 64, 32, 16, 8)
ROI = (3388, 2216, 256, 256)
BUFFER = (5120, 7168)


def need(test, reason):
    if not test:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(value, reason):
    need(type(value) in (int, float) and math.isfinite(value), reason)
    return float(value)


def owned_roi(raw, np, roi, expected_shape, *, copy=True):
    """Generic copy primitive; real caller separately fixes metadata and ROI constants.

    Private small lifetime/address controls supply their literal shape/rectangle,
    never a relaxed real-data authority. All inspection/copy must happen in context.
    """
    need(type(roi) in (tuple, list) and len(roi) == 4 and
         all(type(v) is int and v >= 0 for v in roi), 'sensor ROI integer rectangle')
    x, y, width, height = roi
    need(width > 0 and height > 0 and all(v%2 == 0 for v in roi), 'sensor ROI even domain')
    full = raw.raw_image
    need(isinstance(full, np.ndarray) and full.ndim == 2 and full.dtype == np.dtype('uint16'), 'raw buffer uint16 shape')
    need(tuple(full.shape) == tuple(expected_shape), 'raw buffer exact expected shape')
    need((raw.sizes.raw_height, raw.sizes.raw_width) == full.shape, 'raw declared buffer shape')
    need(x+width <= full.shape[1] and y+height <= full.shape[0], 'sensor ROI outside decoded buffer')
    view = full[y:y+height, x:x+width]
    owned = view.copy(order='C') if copy else view
    need(owned.flags.owndata and owned.flags.c_contiguous and not np.shares_memory(owned, full),
         'owned sensor copy inside lifetime')
    desc = bytes(raw.color_desc)
    indices = [int(raw.raw_color(y+dy, x+dx)) for dy, dx in ((0,0),(0,1),(1,0),(1,1))]
    need(all(0 <= i < len(desc) for i in indices), 'CFA descriptor index')
    letters = [chr(desc[i]) for i in indices]
    return owned, {'indices': indices, 'letters': letters, 'color_desc': desc.decode('ascii'),
                   'roi_raw_xywh': list(roi), 'raw_shape': list(full.shape),
                   'owned': bool(owned.flags.owndata), 'contiguous': bool(owned.flags.c_contiguous)}


def roi_hashes(owned, np):
    need(owned.dtype == np.dtype('uint16') and owned.ndim == 2 and owned.flags.owndata and
         owned.flags.c_contiguous, 'owned ROI after context')
    raw = owned.astype('<u2', copy=False).tobytes(order='C')
    width_bytes = owned.shape[1]*2
    return sha(raw), [sha(raw[i:i+width_bytes]) for i in range(0, len(raw), width_bytes)]


def compare_roi(owned, expected_bytes, expected_rows, np):
    whole, rows = roi_hashes(owned, np)
    need(whole == sha(expected_bytes), 'whole sensor ROI u16 disagreement')
    need(rows == expected_rows, 'sensor ROI row hashes disagreement')
    return {'whole_sha256': whole, 'row_sha256': rows, 'all_rows_equal': True}


def white_authority(metadata, primary):
    indices = metadata['indices']
    need(type(indices) is list and len(indices) == 4 and
         all(type(i) is int and 0 <= i < 4 for i in indices), 'camera white CFA indices')
    used = sorted(set(indices))
    generic, camera = metadata['generic_white'], metadata['camera_white']
    need(type(generic) is int and 0 < generic <= 65535, 'generic white integer range')
    need(camera is not None, 'camera white metadata required; no generic fallback')
    need(type(camera) is list and len(camera) == 4, 'camera white four-entry list')
    need(all(type(camera[i]) is int and 0 < camera[i] <= 65535 for i in used), 'camera white positive integer entries')
    selected = camera[used[0]]
    need(all(camera[i] == selected for i in used), 'mixed used-channel camera white')
    need(selected == primary['white'], 'selected camera white disagrees with primary')
    need(metadata['letters'] == ['R','G','G','B'], 'independent local RGGB')
    black = metadata['black']
    need(type(black) is list and len(black) == 4, 'independent black four-entry list')
    need(all(finite(black[i], 'independent black finite') == primary['black'] for i in used), 'used-channel black disagrees')
    return {'method': 'equal-positive-used-camera-channels', 'generic_white': generic,
            'camera_white': list(camera), 'selected_white': selected,
            'generic_matches_selected': generic == selected, 'used_cfa_indices': used,
            'physical_calibration_claim': False}


def white_balance(metadata, primary_bits, numerics):
    # Ancillary metadata observation. This comparison has no admission tolerance
    # and cannot erase no-map/dark observations when decoder WB conventions differ.
    wb=metadata.get('wb');indices=metadata.get('indices')
    primary=[numerics.from_bits(v) for v in primary_bits[:3]]
    native_ok=len(primary)==3 and all(math.isfinite(v) and v>0 for v in primary)
    native=[numerics.f32(primary[0]/primary[1]),1.,numerics.f32(primary[2]/primary[1])] if native_ok else None
    actual=None
    if type(wb) is list and len(wb)==4 and type(indices) is list and len(indices)==4:
        values=[wb[i] for i in (indices[0],indices[1],indices[3])]
        if all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in values):
            actual=[values[0]/values[1],1.,values[2]/values[1]]
    return {'rawpy_rgb_normalized':actual,'native_rgb_normalized':native,
            'difference':None if actual is None or native is None else [a-b for a,b in zip(actual,native)],
            'rawpy_wb':wb,'native_coeff_bits':list(primary_bits),'agreement_gate':False,
            'scope':'descriptive metadata only; raw codes/black/white and actual green consumption govern relevant eligibility'}


def decode_snapshot(snapshot, rawpy, np, primary, numerics):
    """Exactly one independent decode; caller owns byte/CPU/memory/resource authority."""
    need(type(snapshot) is bytes and 0 < len(snapshot) <= 38825984, 'RAW snapshot extent')
    with rawpy.imread(io.BytesIO(snapshot)) as raw:
        sizes = raw.sizes
        need((sizes.raw_height, sizes.raw_width) == BUFFER, 'fixed raw buffer dimensions')
        need(type(sizes.top_margin) is int and type(sizes.left_margin) is int and
             sizes.top_margin == 0 and sizes.left_margin == 0 and type(sizes.flip) is int and sizes.flip == 0,
             'fixed raw origin orientation')
        need(type(sizes.height) is int and type(sizes.width) is int and
             0 < sizes.height <= BUFFER[0] and 0 < sizes.width <= BUFFER[1], 'visible rectangle bounds')
        owned, domain = owned_roi(raw, np, ROI, BUFFER)
        wb = [float(v) if math.isfinite(float(v)) else None for v in raw.camera_whitebalance]
        metadata = {**domain, 'black': list(raw.black_level_per_channel),
                    'generic_white': raw.white_level, 'camera_white': raw.camera_white_level_per_channel,
                    'wb': wb, 'visible_xywh': [sizes.left_margin, sizes.top_margin, sizes.width, sizes.height],
                    'flip': sizes.flip, 'active_native_xywh': [0,0,7032,4688],
                    'ISO_camera_scope': 'native fields plus inherited capture metadata; rawpy does not independently parse them here'}
        black, white = [numerics.from_bits(v) for v in primary['levels_bits']]
        need(math.isfinite(black) and 0 <= black < white and white == 15360, 'native black white authority')
        authority = white_authority(metadata, {'black': black, 'white': white})
        wb_authority = white_balance(metadata, primary['wb_coeff_bits'], numerics)
    whole, rows = roi_hashes(owned, np)
    return owned, {'metadata': metadata, 'white_authority': authority, 'wb_authority': wb_authority,
                   'whole_sha256': whole, 'row_sha256': rows, 'owned_after_close': True,
                   'postprocess_calls': 0, 'original_decode_count': 1}


def trace_order():
    result = [(1, NONE, NONE, 18), (2, NONE, NONE, None)]
    for k, side in enumerate(SIDES):
        result.append((3,k,NONE,9))
        for tag in ((10,11,12,13) if k < 4 else (10,11,13)):
            result.append((tag,k,NONE,side*side))
        for plane in range(4):
            result.append((20,k,plane,side*side))
    result.extend((tag,0,NONE,16384) for tag in range(100,106))
    need(len(result) == 52, 'source trace population')
    return result


def trace_decode(raw, route, observer, np):
    need(type(raw) is bytes and 12 <= len(raw) <= 2*1024**2, 'trace extent')
    need(raw[:8] == b'NSTRC001' and struct.unpack_from('<I',raw,8)[0] == 52, 'trace magic fieldcount')
    need(type(route) is int and route in (0,1) and observer in ('on','placebo'), 'trace role')
    cursor, values = 12, {}
    for tag, level, plane, count in trace_order():
        need(cursor+16 <= len(raw), 'truncated trace field')
        observed = struct.unpack_from('<4I',raw,cursor); cursor += 16
        expected_count = route*3 if count is None else count
        need(observed == (tag,level,plane,expected_count), 'trace field order/shape')
        end = cursor+4*expected_count
        need(end <= len(raw), 'truncated trace payload')
        words = np.frombuffer(raw[cursor:end], dtype='<u4').copy()
        if observer == 'placebo':
            need(bool((words == 0).all()), 'placebo observed nonzero payload')
        values[tag,level,plane] = words
        cursor = end
    need(cursor == len(raw), 'trace trailing bytes')
    return values


def trace_arrays(fields, np):
    arrays = {}
    for key, words in fields.items():
        tag, level, plane = key
        if tag in (10,11,12,13,20) or 100 <= tag <= 105:
            side = SIDES[level] if tag < 100 else 128
            a = words.view('<f4').reshape(side,side)
            need(bool(np.isfinite(a).all()), 'nonfinite native trace array')
            arrays[key] = a
    return arrays
