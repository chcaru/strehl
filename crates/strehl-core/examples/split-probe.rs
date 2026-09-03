//! Fixed-input probe used by M-PHASE0-SPLIT's independent Python DFT check.

use std::f64::consts::PI;

use strehl_core::split;

fn main() -> anyhow::Result<()> {
    const N: usize = 8;
    let mut a = vec![0.0f32; N * N];
    let mut b = vec![0.0f32; N * N];
    for y in 0..N {
        for x in 0..N {
            let xf = x as f64;
            let yf = y as f64;
            let shared = (2.0 * PI * xf / N as f64).sin()
                + 0.35 * (2.0 * PI * (xf + 2.0 * yf) / N as f64).cos()
                + 0.03 * xf * yf;
            let independent = 0.17 * (2.0 * PI * (3.0 * xf + yf) / N as f64).sin();
            a[y * N + x] = shared as f32;
            b[y * N + x] = (0.8 * shared + independent) as f32;
        }
    }

    let result = split::analyse_pair(&a, &b, N, N, N)?;
    println!("radius,count,cross,power_a,power_b");
    for ring in result.aggregate.iter().skip(1) {
        println!(
            "{},{},{:.17e},{:.17e},{:.17e}",
            ring.radius, ring.count, ring.cross, ring.power_a, ring.power_b
        );
    }
    Ok(())
}
