use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail, ensure};
use strehl_core::align::{Cx, PlaneRef, Resampler, Similarity};

#[cfg(not(target_endian = "little"))]
compile_error!("M8 trace protocol requires a little-endian target");

const MAGIC: &[u8; 8] = b"M8SITE01";
const VERSION: u32 = 2;

#[derive(Clone, Copy)]
enum Kernel {
    CatmullRom = 0,
    Bilinear = 1,
}

impl Kernel {
    fn resampler(self) -> Resampler {
        match self {
            Self::CatmullRom => Resampler::CatmullRom,
            Self::Bilinear => Resampler::Bilinear,
        }
    }
}

struct Site<'a> {
    kernel: Kernel,
    src_w: usize,
    src_h: usize,
    dst_w: usize,
    dst_h: usize,
    site_x: usize,
    site_y: usize,
    channel: usize,
    transform: Similarity,
    cx: f64,
    cy: f64,
    range: f32,
    site_gain: f32,
    frame: &'a str,
    source: &'a [f32],
    trace: &'a [f32],
}

fn write_u32(w: &mut impl Write, v: usize) -> Result<()> {
    w.write_all(
        &u32::try_from(v)
            .context("fixture dimension exceeds u32")?
            .to_le_bytes(),
    )?;
    Ok(())
}

fn f32_bytes(values: &[f32]) -> &[u8] {
    // SAFETY: f32 has no invalid bit patterns, the byte length is exact, and
    // the returned slice cannot outlive `values`.
    unsafe {
        std::slice::from_raw_parts(values.as_ptr().cast::<u8>(), std::mem::size_of_val(values))
    }
}

fn write_site(path: &Path, s: &Site<'_>) -> Result<()> {
    ensure!(
        s.source.len() == s.src_w * s.src_h,
        "source length does not match geometry"
    );
    ensure!(
        s.trace.len() == s.dst_w * s.dst_h,
        "trace length does not match geometry"
    );
    let frame = s.frame.as_bytes();
    let mut w =
        BufWriter::new(File::create(path).with_context(|| format!("creating {}", path.display()))?);
    w.write_all(MAGIC)?;
    w.write_all(&VERSION.to_le_bytes())?;
    w.write_all(&(s.kernel as u32).to_le_bytes())?;
    for v in [
        s.src_w, s.src_h, s.dst_w, s.dst_h, s.site_x, s.site_y, s.channel,
    ] {
        write_u32(&mut w, v)?;
    }
    for v in [
        s.transform.a.re,
        s.transform.a.im,
        s.transform.b.re,
        s.transform.b.im,
        s.cx,
        s.cy,
    ] {
        w.write_all(&v.to_le_bytes())?;
    }
    w.write_all(&s.range.to_le_bytes())?;
    w.write_all(&s.site_gain.to_le_bytes())?;
    write_u32(&mut w, frame.len())?;
    w.write_all(frame)?;
    w.write_all(f32_bytes(s.source))?;
    w.write_all(f32_bytes(s.trace))?;
    w.flush()?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn trace(
    source: &[f32],
    src_w: usize,
    src_h: usize,
    dst_w: usize,
    dst_h: usize,
    site_x: usize,
    site_y: usize,
    transform: Similarity,
    kernel: Kernel,
) -> Vec<f32> {
    let src = PlaneRef::new(source, src_w, src_h).expect("fixture geometry");
    let (cx, cy) = (dst_w as f64 * 0.5, dst_h as f64 * 0.5);
    let (ox, oy) = (site_x as f64 * 0.5, site_y as f64 * 0.5);
    let mut out = vec![f32::NAN; dst_w * dst_h];
    for y in 0..dst_h {
        for x in 0..dst_w {
            let (sxp, syp) = transform.apply_at(x as f64 + ox, y as f64 + oy, cx, cy);
            if let Some(v) = kernel.resampler().sample_checked(src, 2.0 * sxp, 2.0 * syp) {
                out[y * dst_w + x] = v;
            }
        }
    }
    out
}

#[allow(clippy::too_many_arguments)]
fn write_fixture(
    root: &Path,
    name: &str,
    source: &[f32],
    src_w: usize,
    src_h: usize,
    dst_w: usize,
    dst_h: usize,
    transform: Similarity,
    kernel: Kernel,
    trace_values: &[f32],
) -> Result<PathBuf> {
    let path = root.join(format!("{name}.m8site"));
    write_site(
        &path,
        &Site {
            kernel,
            src_w,
            src_h,
            dst_w,
            dst_h,
            site_x: 0,
            site_y: 0,
            channel: 0,
            transform,
            cx: dst_w as f64 * 0.5,
            cy: dst_h as f64 * 0.5,
            range: 1.0,
            site_gain: 1.0,
            frame: name,
            source,
            trace: trace_values,
        },
    )?;
    Ok(path)
}

fn commission(root: &Path) -> Result<()> {
    fs::create_dir_all(root)?;
    let (src_w, src_h) = (40usize, 32usize);
    let (dst_w, dst_h) = (20usize, 16usize);

    let mut step = vec![0.0f32; src_w * src_h];
    for y in 0..src_h {
        for x in 0..src_w {
            step[y * src_w + x] = if x < 18 { 0.0 } else { 1.0 };
        }
    }
    let fractional = Similarity {
        a: Cx::ONE,
        b: Cx::new(0.25, 0.0),
    };
    let catmull = trace(
        &step,
        src_w,
        src_h,
        dst_w,
        dst_h,
        0,
        0,
        fractional,
        Kernel::CatmullRom,
    );
    ensure!(
        catmull
            .iter()
            .any(|v| v.is_finite() && (*v < 0.0 || *v > 1.0)),
        "fractional Catmull-Rom hard step did not overshoot"
    );
    write_fixture(
        root,
        "catmull-hard-step",
        &step,
        src_w,
        src_h,
        dst_w,
        dst_h,
        fractional,
        Kernel::CatmullRom,
        &catmull,
    )?;

    let texture: Vec<f32> = (0..src_h)
        .flat_map(|y| {
            (0..src_w).map(move |x| (17 * x + 29 * y + 7 * ((x * y) % 19)) as f32 / 4096.0)
        })
        .collect();
    let copy = trace(
        &texture,
        src_w,
        src_h,
        dst_w,
        dst_h,
        0,
        0,
        Similarity::IDENTITY,
        Kernel::CatmullRom,
    );
    write_fixture(
        root,
        "copy-null",
        &texture,
        src_w,
        src_h,
        dst_w,
        dst_h,
        Similarity::IDENTITY,
        Kernel::CatmullRom,
        &copy,
    )?;

    let bilinear_t = Similarity {
        a: Cx::ONE,
        b: Cx::new(0.25, 0.125),
    };
    let bilinear = trace(
        &texture,
        src_w,
        src_h,
        dst_w,
        dst_h,
        0,
        0,
        bilinear_t,
        Kernel::Bilinear,
    );
    write_fixture(
        root,
        "bilinear-null",
        &texture,
        src_w,
        src_h,
        dst_w,
        dst_h,
        bilinear_t,
        Kernel::Bilinear,
        &bilinear,
    )?;

    let constant = vec![1.0f32; src_w * src_h];
    let mut planted = trace(
        &constant,
        src_w,
        src_h,
        dst_w,
        dst_h,
        0,
        0,
        Similarity::IDENTITY,
        Kernel::CatmullRom,
    );
    let ulp_one = f32::from_bits(1.0f32.to_bits() + 1) - 1.0;
    let tau = 8.0 * ulp_one;
    let high = 5 * dst_w + 5;
    let low = 5 * dst_w + 6;
    ensure!(
        planted[high] == 1.0 && planted[low] == 1.0,
        "plant anchors are not exact-copy samples"
    );
    planted[high] = 1.0 + 32.0 * tau;
    planted[low] = 1.0 - 32.0 * tau;
    write_fixture(
        root,
        "explicit-hi-lo-plant",
        &constant,
        src_w,
        src_h,
        dst_w,
        dst_h,
        Similarity::IDENTITY,
        Kernel::CatmullRom,
        &planted,
    )?;

    fs::write(
        root.join("manifest.json"),
        format!(
            "{{\n  \"catmull\": \"catmull-hard-step.m8site\",\n  \
             \"copy\": \"copy-null.m8site\",\n  \
             \"bilinear\": \"bilinear-null.m8site\",\n  \
             \"plant\": \"explicit-hi-lo-plant.m8site\",\n  \
             \"plant_high_xy\": [5, 5],\n  \
             \"plant_low_xy\": [6, 5],\n  \
             \"tau_at_one\": {tau:.10e},\n  \
             \"plant_multiple\": 32\n}}\n"
        ),
    )?;
    println!("{}", root.display());
    Ok(())
}

fn main() -> Result<()> {
    let mut args = std::env::args_os();
    let _exe = args.next();
    let Some(command) = args.next() else {
        bail!("usage: m8-overshoot-fixture commission <directory>");
    };
    let Some(root) = args.next() else {
        bail!("usage: m8-overshoot-fixture commission <directory>");
    };
    ensure!(args.next().is_none(), "unexpected extra argument");
    match command.to_string_lossy().as_ref() {
        "commission" => commission(Path::new(&root)),
        other => bail!("unknown command {other:?}"),
    }
}
