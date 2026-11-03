p = r'C:\dev\blog\death-of-software\projects\strehl\crates\strehl-core\src\pyramid.rs'
s = open(p, encoding='utf-8').read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:80], n)
    s = s.replace(old, new)


# A consistency factor per frame, computed after the guide fields are built,
# applied to the weights of the finest levels.
rep('''        self.build_guide_fields(luma, variance, ws);''', '''        self.build_guide_fields(luma, variance, ws);
        let consistency = coarse_reference().and_then(|r| r.factor(luma, &self.sizes));''')

rep('''                let sel: &[f32] = if pooled { &ws.eff[..px] } else { sq };''', '''                let sel: &[f32] = if pooled { &ws.eff[..px] } else { sq };
                let gate_here = consistency
                    .as_ref()
                    .filter(|_| k < coarse_gate_levels())
                    .map(|(f, fsz)| (f, *fsz));''')

# multiply weights after they are computed: find the end of the weight par_iter (HardFloor/Pedestal match) -> first occurrence after 'let sel'
anchor = '''                if !self.zmax.is_empty() {
                    // Energy in units of this frame's own expected noise energy
                    // (the floor without the gate multiplier).'''
rep(anchor, '''                if let Some((f, fsz)) = gate_here {
                    // Experiment: nearest-neighbour from the reference grid.
                    let shift = coarse_gate_grid() - k;
                    let sz = self.sizes[k];
                    for (j, wv) in w.iter_mut().enumerate() {
                        let (x, y) = ((j % sz.width) >> shift, (j / sz.width) >> shift);
                        let i = y.min(fsz.height - 1) * fsz.width + x.min(fsz.width - 1);
                        *wv *= f[i];
                    }
                }
''' + anchor)

rep('''/// Environment override for the ensemble gate's default (`0`/`off` disables).''', '''/// EXPERIMENT ONLY: a reference coarse luma image (raw f32, little-endian, at
/// pyramid level `coarse_gate_grid()` of the analysis plane) read from
/// `STREHL_COARSE_REFERENCE=path,width,height`. Frames whose own coarse luma
/// deviates from it (after removing a per-frame scale) lose weight at the
/// finest `STREHL_COARSE_GATE_LEVELS` levels, with tolerance
/// `STREHL_COARSE_GATE_C0` (natural-log units).
pub struct CoarseReference {
    data: Vec<f32>,
    size: LevelSize,
}

fn coarse_gate_grid() -> usize {
    static V: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *V.get_or_init(|| std::env::var("STREHL_COARSE_GATE_GRID").ok().and_then(|v| v.parse().ok()).unwrap_or(2))
}

fn coarse_gate_levels() -> usize {
    static V: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *V.get_or_init(|| std::env::var("STREHL_COARSE_GATE_LEVELS").ok().and_then(|v| v.parse().ok()).unwrap_or(2))
}

fn coarse_gate_c0() -> f32 {
    static V: std::sync::OnceLock<f32> = std::sync::OnceLock::new();
    *V.get_or_init(|| std::env::var("STREHL_COARSE_GATE_C0").ok().and_then(|v| v.parse().ok()).unwrap_or(0.3))
}

fn coarse_reference() -> Option<&'static CoarseReference> {
    static R: std::sync::OnceLock<Option<CoarseReference>> = std::sync::OnceLock::new();
    R.get_or_init(|| {
        let raw = std::env::var("STREHL_COARSE_REFERENCE").ok()?;
        let mut it = raw.split(',');
        let path = it.next()?;
        let width: usize = it.next()?.parse().ok()?;
        let height: usize = it.next()?.parse().ok()?;
        let bytes = std::fs::read(path).expect("STREHL_COARSE_REFERENCE unreadable");
        assert_eq!(bytes.len(), width * height * 4, "coarse reference size");
        let data = bytes.chunks_exact(4).map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]])).collect();
        Some(CoarseReference { data, size: LevelSize { width, height } })
    })
    .as_ref()
}

impl CoarseReference {
    /// Per-pixel weight factor for one frame at the reference grid, or `None`
    /// when the grids disagree.
    fn factor(&self, luma: &[f32], sizes: &[LevelSize]) -> Option<(Vec<f32>, LevelSize)> {
        let g = coarse_gate_grid();
        if sizes.len() <= g || sizes[g] != self.size {
            return None;
        }
        let mut cur = luma.to_vec();
        for k in 0..g {
            let mut next = vec![0.0f32; sizes[k + 1].pixels()];
            let mut scratch = vec![0.0f32; sizes[k].pixels() + sizes[k].width];
            reduce(&cur, sizes[k], &mut next, &mut scratch);
            cur = next;
        }
        let mut logs: Vec<f32> = cur
            .iter()
            .zip(&self.data)
            .filter(|(a, b)| **a > 20.0 && **b > 20.0)
            .map(|(a, b)| (a / b).ln())
            .collect();
        if logs.len() < 100 {
            return None;
        }
        let mid = logs.len() / 2;
        let med = *logs.select_nth_unstable_by(mid, |a, b| a.total_cmp(b)).1;
        let c0 = coarse_gate_c0();
        let f = cur
            .iter()
            .zip(&self.data)
            .map(|(a, b)| {
                let c = ((a.max(1.0) / b.max(1.0)).ln() - med) / c0;
                (-c * c).exp()
            })
            .collect();
        Some((f, self.size))
    }
}

/// Environment override for the ensemble gate's default (`0`/`off` disables).''')
open(p, 'w', encoding='utf-8').write(s)
print('ok')
