//! Experimental reversible CFA prediction. No denoising of the encoded signal.
//! All samples, including inactive borders, are reconstructed exactly.
use std::slice;

fn med(a: i32, b: i32, c: i32) -> i32 {
    if c >= a.max(b) { a.min(b) } else if c <= a.min(b) { a.max(b) } else { a + b - c }
}
#[inline(always)]
fn prediction(a: &[u16], r: &[u16], i: usize, x: usize, y: usize, w: usize, mode: u32) -> u16 {
    let l = if x >= 2 { a[i-2] as i32 } else { 0 };
    let u = if y >= 2 { a[i-2*w] as i32 } else { l };
    let c = if x >= 2 && y >= 2 { a[i-2*w-2] as i32 } else { u };
    let spatial = if y < 2 { l } else if x < 2 { u } else { med(l,u,c) };
    let p = match mode {
        0 => 0,
        1 => l,
        2 => spatial,
        3 => if x >= 2 && y >= 2 { (l+u)/2 } else { spatial },
        4 => r[i] as i32,
        8 => if x >= 2 && x+2 < w && y >= 2 {
            (l+u+c+a[i-2*w+2] as i32)/4
        } else { spatial },
        9 => if x >= 4 && x+2 < w && y >= 4 {
            (2*l+2*u+c+a[i-2*w+2] as i32+a[i-4] as i32+a[i-4*w] as i32)/8
        } else { spatial },
        5 | 6 | 7 => {
            if x < 2 || y < 2 { r[i] as i32 } else {
                let rl = r[i-2] as i32;
                let ru = r[i-2*w] as i32;
                let rc = r[i-2*w-2] as i32;
                let temporal = r[i] as i32 + med(l-rl,u-ru,c-rc);
                match mode { 6 => (spatial+temporal)/2, 7 => (3*spatial+temporal)/4, _ => temporal }
            }
        },
        _ => 0,
    };
    p.clamp(0,65535) as u16
}

/// Caller supplies aligned u16 arrays of width*height; reference is mandatory
/// for modes 4..7. This C ABI is only for the bounded local research harness.
#[no_mangle]
pub unsafe extern "C" fn strehl_predict(
    source: *const u16, reference: *const u16, output: *mut u8,
    width: usize, height: usize, mode: u32, inverse: bool,
) -> i32 {
    if source.is_null() || output.is_null() || width < 2 || height < 2 ||
        width.checked_mul(height).is_none() || mode > 9 || ((4..=7).contains(&mode) && reference.is_null()) { return -1; }
    let n = width*height;
    let r = if (4..=7).contains(&mode) { slice::from_raw_parts(reference,n) } else { &[] };
    if inverse {
        let bytes = slice::from_raw_parts(source as *const u8,2*n);
        let a = slice::from_raw_parts_mut(output as *mut u16,n);
        for y in 0..height { for x in 0..width {
            let i=y*width+x;
            let z = (bytes[i] as u16) | ((bytes[n+i] as u16)<<8);
            let d = (z >> 1) as i16 ^ -((z & 1) as i16);
            a[i] = prediction(a,r,i,x,y,width,mode).wrapping_add(d as u16);
        }}
    } else {
        let a = slice::from_raw_parts(source,n);
        let bytes = slice::from_raw_parts_mut(output,2*n);
        for y in 0..height { for x in 0..width {
            let i=y*width+x;
            let d = a[i].wrapping_sub(prediction(a,r,i,x,y,width,mode)) as i16;
            let z = ((d as u16)<<1) ^ ((d >> 15) as u16);
            bytes[i] = z as u8; bytes[n+i] = (z >> 8) as u8;
        }}
    }
    0
}

/// Separate the noisy low bits from the compressible quotient. The quotient
/// retains both bytes, so this is reversible even for arbitrary full u16 input.
#[no_mangle]
pub unsafe extern "C" fn strehl_splitbits(
    source: *const u8, output: *mut u8, n: usize, bits: u32, inverse: bool,
) -> usize {
    if source.is_null() || output.is_null() || !(1..=8).contains(&bits) || n > 128*1024*1024 {return 0;}
    let low=(n*bits as usize+7)/8;
    let total=low+2*n;
    let mask=(1u16<<bits)-1;
    if inverse {
        let src=slice::from_raw_parts(source,total);
        let dst=slice::from_raw_parts_mut(output,2*n);
        let mut acc=0u64;let mut used=0u32;let mut at=0usize;
        for i in 0..n {
            while used<bits {acc|=(src[at] as u64)<<used;used+=8;at+=1;}
            let v=((acc as u16)&mask) | (((src[low+i] as u16)|((src[low+n+i] as u16)<<8))<<bits);
            acc>>=bits;used-=bits;dst[i]=v as u8;dst[n+i]=(v>>8) as u8;
        }
    } else {
        let src=slice::from_raw_parts(source,2*n);
        let dst=slice::from_raw_parts_mut(output,total);
        let mut acc=0u64;let mut used=0u32;let mut at=0usize;
        for i in 0..n {
            let v=(src[i] as u16)|((src[n+i] as u16)<<8);
            acc|=((v&mask) as u64)<<used;used+=bits;
            while used>=8 {dst[at]=acc as u8;acc>>=8;used-=8;at+=1;}
            let high=v>>bits;dst[low+i]=high as u8;dst[low+n+i]=(high>>8) as u8;
        }
        if used!=0 {dst[at]=acc as u8;}
    }
    total
}
