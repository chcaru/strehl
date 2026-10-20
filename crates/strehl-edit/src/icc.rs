//! ICC matrix/TRC profiles derived from published colorimetry.
//! Shared editing exports use the same construction as the legacy TIFF writer.

/// The ICC PCS illuminant, D50. ICC.1:2010 §7.2.16.
///
/// These exact values are chosen so the s15Fixed16 encoding lands on the
/// canonical `0000F6D6 00010000 0000D32D` that every reader expects to see.
const PCS_D50: [f64; 3] = [0.964_203, 1.0, 0.824_905];

/// D65, the sRGB white point (IEC 61966-2-1).
const WHITE_D65: [f64; 3] = [0.950_47, 1.0, 1.088_83];

/// sRGB primaries as CIE xy chromaticities (IEC 61966-2-1).
const SRGB_PRIMARIES_XY: [[f64; 2]; 3] = [[0.6400, 0.3300], [0.3000, 0.6000], [0.1500, 0.0600]];

/// Bradford cone response matrix, and its inverse.
const BRADFORD: [[f64; 3]; 3] = [
    [0.8951, 0.2664, -0.1614],
    [-0.7502, 1.7135, 0.0367],
    [0.0389, -0.0685, 1.0296],
];

fn mat3_mul(a: [[f64; 3]; 3], b: [[f64; 3]; 3]) -> [[f64; 3]; 3] {
    let mut o = [[0.0; 3]; 3];
    for (i, row) in o.iter_mut().enumerate() {
        for (j, cell) in row.iter_mut().enumerate() {
            *cell = (0..3).map(|k| a[i][k] * b[k][j]).sum();
        }
    }
    o
}

fn mat3_vec(a: [[f64; 3]; 3], v: [f64; 3]) -> [f64; 3] {
    let mut o = [0.0; 3];
    for (i, cell) in o.iter_mut().enumerate() {
        *cell = (0..3).map(|k| a[i][k] * v[k]).sum();
    }
    o
}

fn mat3_inv(m: [[f64; 3]; 3]) -> [[f64; 3]; 3] {
    let det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
    assert!(det.abs() > 1e-12, "singular matrix in ICC construction");
    let c = |r: usize, col: usize| -> f64 {
        let (r0, r1) = ((r + 1) % 3, (r + 2) % 3);
        let (c0, c1) = ((col + 1) % 3, (col + 2) % 3);
        m[r0][c0] * m[r1][c1] - m[r0][c1] * m[r1][c0]
    };
    let mut o = [[0.0; 3]; 3];
    for (i, row) in o.iter_mut().enumerate() {
        for (j, cell) in row.iter_mut().enumerate() {
            // transpose of the cofactor matrix, divided by the determinant
            *cell = c(j, i) / det;
        }
    }
    o
}

/// The RGB-to-XYZ matrix for the sRGB primaries under their own white point,
/// then Bradford-adapted to the D50 PCS. Columns are the `rXYZ`/`gXYZ`/`bXYZ`
/// tag values.
fn srgb_to_xyz_d50() -> [[f64; 3]; 3] {
    // Each primary's XYZ at unit luminance, from its xy chromaticity.
    let mut p = [[0.0; 3]; 3];
    for (i, [x, y]) in SRGB_PRIMARIES_XY.iter().enumerate() {
        p[0][i] = x / y;
        p[1][i] = 1.0;
        p[2][i] = (1.0 - x - y) / y;
    }
    // Scale the columns so the primaries sum to the white point.
    let s = mat3_vec(mat3_inv(p), WHITE_D65);
    let mut m = [[0.0; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            m[i][j] = p[i][j] * s[j];
        }
    }
    // Bradford: convert both whites to cone space, scale, convert back.
    let src = mat3_vec(BRADFORD, WHITE_D65);
    let dst = mat3_vec(BRADFORD, PCS_D50);
    let mut scale = [[0.0; 3]; 3];
    for i in 0..3 {
        scale[i][i] = dst[i] / src[i];
    }
    let adapt = mat3_mul(mat3_inv(BRADFORD), mat3_mul(scale, BRADFORD));
    mat3_mul(adapt, m)
}

/// s15Fixed16Number, ICC.1 §4.2.
fn s15(v: f64) -> [u8; 4] {
    ((v * 65536.0).round() as i32).to_be_bytes()
}

/// The sRGB electro-optical transfer function: encoded value to linear light.
///
/// This is the direction an ICC `TRC` tag stores, because a matrix/TRC profile
/// computes `PCS = Matrix * TRC(device)`. Storing the opposite direction is a
/// classic and completely silent error -- the image simply renders with the
/// wrong contrast -- so the direction is named here rather than left implied.
fn srgb_eotf(v: f64) -> f64 {
    if v <= 0.040_45 {
        v / 12.92
    } else {
        ((v + 0.055) / 1.055).powf(2.4)
    }
}

/// Build a v2 display profile for RGB data on sRGB primaries.
///
/// `linear` selects the transfer curve: `false` gives the sRGB curve, `true`
/// gives an identity curve for data that is already linear light.
///
/// Deterministic by construction. The creation date is fixed rather than taken
/// from the clock, because a profile that changes every run would make every
/// output file's hash change every run, and this project's epistemics rest on
/// byte-freezes.
pub(crate) fn icc_srgb_v2(linear: bool) -> Vec<u8> {
    let m = srgb_to_xyz_d50();

    let desc = if linear {
        "strehl linear sRGB (BT.709-6 primaries, D65, gamma 1.0)"
    } else {
        "strehl sRGB (IEC 61966-2-1)"
    };
    let cprt = "Constructed by strehl from published colorimetry \
                (IEC 61966-2-1 primaries and transfer curve, ICC.1 D50 PCS, \
                 Bradford adaptation). No rights reserved.";

    // -- tag payloads ------------------------------------------------------
    let xyz_tag = |c: usize| -> Vec<u8> {
        let mut v = b"XYZ \0\0\0\0".to_vec();
        for row in &m {
            v.extend_from_slice(&s15(row[c]));
        }
        v
    };

    let mut wtpt = b"XYZ \0\0\0\0".to_vec();
    for v in PCS_D50 {
        wtpt.extend_from_slice(&s15(v));
    }

    let trc = {
        let mut v = b"curv\0\0\0\0".to_vec();
        if linear {
            // count 0 is the identity curve.
            v.extend_from_slice(&0u32.to_be_bytes());
        } else {
            const N: usize = 1024;
            v.extend_from_slice(&(N as u32).to_be_bytes());
            for i in 0..N {
                let y = srgb_eotf(i as f64 / (N - 1) as f64);
                v.extend_from_slice(&((y * 65535.0).round() as u16).to_be_bytes());
            }
        }
        v
    };

    // textDescriptionType, the v2 form of `desc`.
    let desc_tag = {
        let mut v = b"desc\0\0\0\0".to_vec();
        v.extend_from_slice(&((desc.len() + 1) as u32).to_be_bytes());
        v.extend_from_slice(desc.as_bytes());
        v.push(0);
        v.extend_from_slice(&[0u8; 4]); // unicode language code
        v.extend_from_slice(&[0u8; 4]); // unicode count
        v.extend_from_slice(&[0u8; 2]); // scriptcode code
        v.push(0); // scriptcode count
        v.extend_from_slice(&[0u8; 67]); // scriptcode description
        v
    };

    let cprt_tag = {
        let mut v = b"text\0\0\0\0".to_vec();
        v.extend_from_slice(cprt.as_bytes());
        v.push(0);
        v
    };

    // The adaptation actually applied, recorded so a reader can undo it.
    let chad_tag = {
        let src = mat3_vec(BRADFORD, WHITE_D65);
        let dst = mat3_vec(BRADFORD, PCS_D50);
        let mut scale = [[0.0; 3]; 3];
        for i in 0..3 {
            scale[i][i] = dst[i] / src[i];
        }
        let adapt = mat3_mul(mat3_inv(BRADFORD), mat3_mul(scale, BRADFORD));
        let mut v = b"sf32\0\0\0\0".to_vec();
        for row in adapt {
            for cell in row {
                v.extend_from_slice(&s15(cell));
            }
        }
        v
    };

    // `rTRC`, `gTRC` and `bTRC` share one payload: identical curves pointing at
    // one offset is normal ICC practice and is what most shipping profiles do.
    let tags: Vec<(&[u8; 4], Vec<u8>)> = vec![
        (b"desc", desc_tag),
        (b"wtpt", wtpt),
        (b"rXYZ", xyz_tag(0)),
        (b"gXYZ", xyz_tag(1)),
        (b"bXYZ", xyz_tag(2)),
        (b"rTRC", trc),
        (b"cprt", cprt_tag),
        (b"chad", chad_tag),
    ];

    // -- lay out ------------------------------------------------------------
    // Tag count includes the two aliased TRC entries, which carry no payload of
    // their own.
    let n_entries = tags.len() as u32 + 2;
    let table_bytes = 4 + 12 * n_entries as usize;
    let mut offset = 128 + table_bytes;

    let mut entries: Vec<([u8; 4], u32, u32)> = Vec::new();
    let mut payload: Vec<u8> = Vec::new();
    let mut trc_at = (0u32, 0u32);
    for (sig, data) in &tags {
        let at = offset as u32;
        let size = data.len() as u32;
        entries.push((**sig, at, size));
        if *sig == b"rTRC" {
            trc_at = (at, size);
        }
        payload.extend_from_slice(data);
        // Tag data must start on a 4-byte boundary.
        let pad = (4 - (data.len() % 4)) % 4;
        payload.extend(std::iter::repeat_n(0u8, pad));
        offset += data.len() + pad;
    }
    entries.push((*b"gTRC", trc_at.0, trc_at.1));
    entries.push((*b"bTRC", trc_at.0, trc_at.1));

    let total = 128 + table_bytes + payload.len();

    let mut out = Vec::with_capacity(total);
    out.extend_from_slice(&(total as u32).to_be_bytes()); // profile size
    out.extend_from_slice(&[0u8; 4]); // preferred CMM: none
    out.extend_from_slice(&0x0210_0000u32.to_be_bytes()); // v2.1
    out.extend_from_slice(b"mntr");
    out.extend_from_slice(b"RGB ");
    out.extend_from_slice(b"XYZ ");
    // Fixed creation date: 2026-01-01T00:00:00Z. See the determinism note above.
    for v in [2026u16, 1, 1, 0, 0, 0] {
        out.extend_from_slice(&v.to_be_bytes());
    }
    out.extend_from_slice(b"acsp");
    out.extend_from_slice(&[0u8; 4]); // platform
    out.extend_from_slice(&[0u8; 4]); // flags: not embedded, usable independently
    out.extend_from_slice(&[0u8; 4]); // device manufacturer
    out.extend_from_slice(&[0u8; 4]); // device model
    out.extend_from_slice(&[0u8; 8]); // device attributes
    out.extend_from_slice(&0u32.to_be_bytes()); // rendering intent: perceptual
    for v in PCS_D50 {
        out.extend_from_slice(&s15(v));
    }
    out.extend_from_slice(&[0u8; 4]); // profile creator
    out.extend_from_slice(&[0u8; 16]); // profile ID (MD5); zero = not computed
    out.extend_from_slice(&[0u8; 28]); // reserved
    debug_assert_eq!(out.len(), 128);

    out.extend_from_slice(&n_entries.to_be_bytes());
    for (sig, at, size) in &entries {
        out.extend_from_slice(sig);
        out.extend_from_slice(&at.to_be_bytes());
        out.extend_from_slice(&size.to_be_bytes());
    }
    out.extend_from_slice(&payload);
    debug_assert_eq!(out.len(), total);
    out
}
