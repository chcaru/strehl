// Fixed reconstruction-order counterfactual, not automatic source assignment.
// Mask ORIGINAL-domain reconstructed AC, not individual pyramid coefficients.
pub struct SpatialDonor {
    sizes: Vec<LevelSize>,
    planes: usize,
    masks: Vec<Vec<f32>>,
    coverage: Vec<f32>,
    sums: Vec<Vec<f32>>,
    seen: Vec<bool>,
    normalized: usize,
}

impl SpatialDonor {
    pub fn new(sizes: &[LevelSize], planes: usize, masks0: &[Vec<f32>]) -> Self {
        assert!(sizes.len() >= 2 && planes == 4 && masks0.len() <= 8);
        let pixels = sizes[0].pixels();
        let mut masks = masks0.to_vec();
        for mask in &masks {
            assert_eq!(mask.len(), pixels);
            assert!(mask.iter().all(|v| v.is_finite() && (0.0..=1.0).contains(v)));
        }
        let mut coverage = vec![0.0; pixels];
        let mut normalized = 0;
        for (j, coverage) in coverage.iter_mut().enumerate() {
            let total = masks.iter().map(|m| m[j]).sum::<f32>();
            if total > 1.0 {
                normalized += 1;
                for mask in &mut masks { mask[j] /= total; }
                *coverage = 1.0;
            } else { *coverage = total; }
        }
        Self { sizes: sizes.to_vec(), planes, masks, coverage,
            sums: vec![vec![0.0; pixels]; planes], seen: vec![false; masks0.len()], normalized }
    }

    pub fn masks(&self) -> &[Vec<f32>] { &self.masks }
    pub fn coverage(&self) -> &[f32] { &self.coverage }
    pub fn normalized_count(&self) -> usize { self.normalized }
    pub fn detail_sums(&self) -> &[Vec<f32>] { &self.sums }

    /// Source-call order, then mask_indices order, defines the f32 accumulation.
    /// Only current source and a fixed four-plane masked AC sum are retained.
    pub fn add_source(&mut self, mask_indices: &[usize], planes: &[Vec<f32>]) {
        assert_eq!(planes.len(), self.planes);
        assert!(!mask_indices.is_empty());
        for (i, &r) in mask_indices.iter().enumerate() {
            assert!(r < self.masks.len() && !self.seen[r] && !mask_indices[..i].contains(&r),
                "duplicate or invalid prescribed spatial donor region");
        }
        let mut ws = Workspace::new(&self.sizes);
        let mut donor = Pyramid::zeros(&self.sizes);
        let last = self.sizes.len() - 1;
        for (c, source) in planes.iter().enumerate() {
            assert_eq!(source.len(), self.sizes[0].pixels());
            assert!(source.iter().all(|v| v.is_finite()));
            donor.build(source, &mut ws);
            donor.level_mut(last).fill(0.0);
            let ac = donor.collapse(&mut ws);
            for &r in mask_indices {
                for ((sum, &m), &v) in self.sums[c].iter_mut().zip(&self.masks[r]).zip(&ac) {
                    if m > 0.0 { *sum += m * v; }
                }
            }
        }
        for &r in mask_indices { self.seen[r] = true; }
    }

    pub fn finish(&self, merge: &BandMerge, ws: &mut Workspace) -> Vec<Vec<f32>> {
        supported(merge);
        assert_eq!(merge.sizes, self.sizes);
        assert_eq!(merge.planes, self.planes);
        for (r, mask) in self.masks.iter().enumerate() {
            assert!(self.seen[r] || mask.iter().all(|&m| m == 0.0),
                "prescribed spatial region has no actual donor");
        }
        if self.coverage.iter().all(|&m| m == 0.0) { return merge.finish(ws); }
        let last = self.sizes.len() - 1;
        resolved_coefficients(merge).into_iter().enumerate().map(|(c, mut p)| {
            let mut output = p.collapse(ws);
            p.level_mut(last).fill(0.0);
            let baseline_ac = p.collapse(ws);
            for j in 0..output.len() {
                // Literal shortcut retains the original baseline post-hull bits.
                if self.coverage[j] != 0.0 {
                    output[j] = output[j] + (self.sums[c][j] - self.coverage[j] * baseline_ac[j]);
                }
                output[j] = output[j].clamp(merge.lo[c][j], merge.hi[c][j]);
            }
            assert!(output.iter().all(|v| v.is_finite()));
            output
        }).collect()
    }
}
