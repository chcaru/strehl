//! Dump adjacent gathered frame pairs so the ghost can be measured where it lives.
//!
//! BUILD-RENDER saw "pale outline ghosts left of the left legs — a leg edge
//! appearing more than once" on `bee-1-cpl`. An edge appearing twice is not
//! blur and not a rim: it is two frames disagreeing about where that edge is.
//! The merge elects a single frame per pixel in detailed regions, so adjacent
//! output pixels can come from frames `k` and `k+1`; if those two frames are
//! not registered to each other, their shared edge lands in two places.
//!
//! `bs_residual` already answers "how big is the span-1 residual" as one number
//! per pair. This answers a different question that one number cannot:
//! **where** is it, and **which way does it point**.
//!
//! That direction is the whole discriminator. Focus breathing changes
//! magnification, so its residual is *radial* and grows linearly with radius
//! from the scale centre. Estimator jitter is isotropic — its direction is
//! uncorrelated with the radial direction, at any radius. A magnitude-only plot
//! cannot separate them; a signed radial projection can, and it has a null
//! (mean zero) that jitter must satisfy.
//!
//! This binary only *gathers and dumps*. The measurement, its controls and its
//! plant live in `ghost.py`, because the estimator is what needs commissioning.
//!
//! Arms dumped per pair `(i, i+span)`:
//!   `a_warp` frame i   through its own placement   — the treatment
//!   `b_warp` frame i+s through its own placement   — the treatment
//!   `a_none` frame i   through the identity        — unaligned control
//!   `b_none` frame i+s through the identity        — unaligned control
//!
//! `a_warp` doubles as the self-control input: `ghost.py` compares it against
//! itself and must read exactly zero everywhere.
//!
//! ```text
//! cargo run --release -p strehl-cli --example bs_ghost -- <DIR> \
//!     --sidecar <PATH> --pairs 100,150,200 --span 1 --out <DIR>
//! ```

use std::io::Write;
use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use strehl_core::align::{PlaneRef, Resampler, Similarity, gather_into};
use strehl_core::plane::{PlaneGeometry, green_luma};
use strehl_core::warpmap::WarpMap;

struct Frame {
    plane: Vec<f32>,
    geom: PlaneGeometry,
}

fn decode(path: &std::path::Path) -> Result<Frame> {
    let f = strehl_raw::decode(path).with_context(|| format!("decode {}", path.display()))?;
    let geom = PlaneGeometry::from_active(f.active.width, f.active.height);
    let mut plane = vec![0.0f32; geom.pixels()];
    green_luma(&f, f.levels.black, &mut plane);
    Ok(Frame { plane, geom })
}

fn dump(dir: &std::path::Path, name: &str, data: &[f32]) -> Result<()> {
    let p = dir.join(format!("{name}.f32"));
    let mut f = std::io::BufWriter::new(std::fs::File::create(&p)?);
    // Native-endian f32, read back with numpy dtype '<f4' on x86.
    let bytes: &[u8] =
        unsafe { std::slice::from_raw_parts(data.as_ptr() as *const u8, data.len() * 4) };
    f.write_all(bytes)?;
    f.flush()?;
    Ok(())
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let dir = PathBuf::from(args.next().context("usage: bs_ghost <DIR> --sidecar <PATH>")?);
    let mut sidecar: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut pairs: Vec<usize> = vec![];
    let mut span: usize = 1;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--sidecar" => sidecar = Some(PathBuf::from(args.next().context("--sidecar")?)),
            "--out" => out = Some(PathBuf::from(args.next().context("--out")?)),
            "--span" => span = args.next().context("--span")?.parse()?,
            "--pairs" => {
                pairs = args
                    .next()
                    .context("--pairs")?
                    .split(',')
                    .map(|s| s.trim().parse::<usize>())
                    .collect::<std::result::Result<Vec<_>, _>>()?
            }
            other => bail!("unknown argument {other}"),
        }
    }
    let sidecar = sidecar.context("--sidecar is required")?;
    let out = out.context("--out is required")?;
    if pairs.is_empty() {
        bail!("--pairs is required");
    }
    std::fs::create_dir_all(&out)?;

    let map = WarpMap::load(&sidecar).with_context(|| format!("load {}", sidecar.display()))?;
    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    println!("sidecar   : {}", sidecar.display());
    println!("frames    : {} in map, {} on disk", map.len(), paths.len());
    println!("resampler : {:?}", map.resampler());

    // Decode only what is asked for; a 299-frame decode to look at six planes
    // is 20 s of nothing.
    let mut want: Vec<usize> = vec![];
    for &i in &pairs {
        if i + span >= paths.len().min(map.len()) {
            bail!("pair {i} + span {span} is past the end");
        }
        want.push(i);
        want.push(i + span);
    }
    want.sort_unstable();
    want.dedup();

    let decoded: Vec<(usize, Frame)> = want
        .par_iter()
        .map(|&k| decode(&paths[k]).map(|f| (k, f)))
        .collect::<Result<Vec<_>>>()?;
    let geom = decoded[0].1.geom;
    println!("geometry  : {} x {} plane px", geom.width, geom.height);

    // The scale centre the placements are expressed about. gather_into applies
    // the similarity about the plane centre, so that is the origin the radial
    // projection in ghost.py must use. Written down rather than assumed,
    // because a radial statistic taken about the wrong origin manufactures a
    // linear-in-radius term out of a pure translation.
    let cx = geom.width as f64 / 2.0;
    let cy = geom.height as f64 / 2.0;

    let mut manifest = String::new();
    manifest.push_str(&format!(
        "{{\"width\":{},\"height\":{},\"cx\":{cx},\"cy\":{cy},\"span\":{span},\"pairs\":[{}],\n",
        geom.width,
        geom.height,
        pairs
            .iter()
            .map(|p| p.to_string())
            .collect::<Vec<_>>()
            .join(",")
    ));
    manifest.push_str("\"placements\":{");

    let mut first = true;
    for &k in &want {
        let t = map.placement(k).unwrap_or(Similarity::IDENTITY);
        let q = t.to_params();
        if !first {
            manifest.push(',');
        }
        first = false;
        manifest.push_str(&format!(
            "\"{k}\":{{\"g\":{},\"rot\":{},\"ax\":{},\"ay\":{}}}",
            q.g, q.rot, q.ax, q.ay
        ));
    }
    manifest.push_str("}}\n");
    std::fs::write(out.join("manifest.json"), &manifest)?;

    for &k in &want {
        let f = &decoded.iter().find(|(j, _)| *j == k).unwrap().1;
        let src = PlaneRef::new(&f.plane, f.geom.width, f.geom.height).unwrap();
        for (tag, t) in [
            ("warp", map.placement(k).unwrap_or(Similarity::IDENTITY)),
            ("none", Similarity::IDENTITY),
        ] {
            let mut dst = vec![0.0f32; geom.pixels()];
            gather_into(src, t, geom, resampler_of(&map), &mut dst);
            dump(&out, &format!("f{k}_{tag}"), &dst)?;
        }
        let q = map
            .placement(k)
            .unwrap_or(Similarity::IDENTITY)
            .to_params();
        println!(
            "frame {k:>3}: g={:+.6} rot={:+.6} ax={:+8.3} ay={:+8.3}",
            q.g, q.rot, q.ax, q.ay
        );
    }

    println!("\nwrote {} planes to {}", want.len() * 2, out.display());
    Ok(())
}

fn resampler_of(map: &WarpMap) -> Resampler {
    let _ = map;
    Resampler::CatmullRom
}
