//! Binary raster operations on the cell grid, row-major `Vec<bool>`.
//!
//! The structuring element is the 4-neighbour cross throughout, and cells
//! outside the grid count as empty for both dilation and erosion (so an
//! erosion eats a part that touches the frame edge, as the prototype's
//! `scipy.ndimage` calls did). Components are 4-connected.

use rayon::prelude::*;

#[derive(Clone, Copy, Debug)]
pub(crate) struct Grid {
    pub cols: usize,
    pub rows: usize,
}

impl Grid {
    pub fn len(self) -> usize {
        self.cols * self.rows
    }
}

fn cross(m: &[bool], g: Grid, dilate: bool) -> Vec<bool> {
    let (w, h) = (g.cols, g.rows);
    let mut out = vec![false; m.len()];
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let at = |xx: isize, yy: isize| -> bool {
                xx >= 0
                    && yy >= 0
                    && (xx as usize) < w
                    && (yy as usize) < h
                    && m[yy as usize * w + xx as usize]
            };
            let (xi, yi) = (x as isize, y as isize);
            let n = [
                at(xi, yi),
                at(xi - 1, yi),
                at(xi + 1, yi),
                at(xi, yi - 1),
                at(xi, yi + 1),
            ];
            *o = if dilate {
                n.iter().any(|&v| v)
            } else {
                n.iter().all(|&v| v)
            };
        }
    });
    out
}

pub(crate) fn dilate(m: &[bool], g: Grid, iterations: usize) -> Vec<bool> {
    let mut cur = m.to_vec();
    for _ in 0..iterations {
        cur = cross(&cur, g, true);
    }
    cur
}

pub(crate) fn erode(m: &[bool], g: Grid, iterations: usize) -> Vec<bool> {
    let mut cur = m.to_vec();
    for _ in 0..iterations {
        cur = cross(&cur, g, false);
    }
    cur
}

pub(crate) fn close(m: &[bool], g: Grid, iterations: usize) -> Vec<bool> {
    erode(&dilate(m, g, iterations), g, iterations)
}

pub(crate) fn open(m: &[bool], g: Grid, iterations: usize) -> Vec<bool> {
    dilate(&erode(m, g, iterations), g, iterations)
}

/// 4-connected labels of the set cells (0 = unset), and each label's size
/// (index 0 unused).
pub(crate) fn label(m: &[bool], g: Grid) -> (Vec<u32>, Vec<usize>) {
    let (w, h) = (g.cols, g.rows);
    let mut lab = vec![0u32; m.len()];
    let mut sizes = vec![0usize];
    let mut stack: Vec<usize> = Vec::new();
    for start in 0..m.len() {
        if !m[start] || lab[start] != 0 {
            continue;
        }
        let id = sizes.len() as u32;
        let mut size = 0usize;
        lab[start] = id;
        stack.push(start);
        while let Some(i) = stack.pop() {
            size += 1;
            let (x, y) = (i % w, i / w);
            let mut visit = |j: usize| {
                if m[j] && lab[j] == 0 {
                    lab[j] = id;
                    stack.push(j);
                }
            };
            if x > 0 {
                visit(i - 1);
            }
            if x + 1 < w {
                visit(i + 1);
            }
            if y > 0 {
                visit(i - w);
            }
            if y + 1 < h {
                visit(i + w);
            }
        }
        sizes.push(size);
    }
    (lab, sizes)
}

/// Keeps the components of `m` that contain at least one cell of `seed`.
pub(crate) fn reconstruct(m: &[bool], seed: &[bool], g: Grid) -> Vec<bool> {
    let (lab, sizes) = label(m, g);
    let mut keep = vec![false; sizes.len()];
    for (l, &s) in lab.iter().zip(seed) {
        if s && *l != 0 {
            keep[*l as usize] = true;
        }
    }
    lab.iter().map(|&l| l != 0 && keep[l as usize]).collect()
}

/// Keeps the components of `m` with at least `min_cells` cells.
pub(crate) fn drop_small(m: &[bool], g: Grid, min_cells: usize) -> (Vec<bool>, usize, usize) {
    let (lab, sizes) = label(m, g);
    let keep: Vec<bool> = sizes.iter().map(|&s| s >= min_cells).collect();
    let kept = keep.iter().skip(1).filter(|&&k| k).count();
    let dropped = sizes.len() - 1 - kept;
    (
        lab.iter().map(|&l| l != 0 && keep[l as usize]).collect(),
        kept,
        dropped,
    )
}

/// Enclosed background: 4-connected components of the unset cells that do
/// not touch the grid's edge.
pub(crate) fn holes(m: &[bool], g: Grid) -> Vec<bool> {
    let bg: Vec<bool> = m.iter().map(|&v| !v).collect();
    let (lab, sizes) = label(&bg, g);
    let mut touches = vec![false; sizes.len()];
    let (w, h) = (g.cols, g.rows);
    for x in 0..w {
        touches[lab[x] as usize] = true;
        touches[lab[(h - 1) * w + x] as usize] = true;
    }
    for y in 0..h {
        touches[lab[y * w] as usize] = true;
        touches[lab[y * w + w - 1] as usize] = true;
    }
    lab.iter()
        .map(|&l| l != 0 && !touches[l as usize])
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grid(rows: &[&str]) -> (Vec<bool>, Grid) {
        let g = Grid {
            cols: rows[0].len(),
            rows: rows.len(),
        };
        let m = rows
            .iter()
            .flat_map(|r| r.bytes().map(|b| b == b'#'))
            .collect();
        (m, g)
    }

    #[test]
    fn labels_are_four_connected() {
        let (m, g) = grid(&["#..", ".#.", "..#"]);
        let (_, sizes) = label(&m, g);
        assert_eq!(sizes.len() - 1, 3);
    }

    #[test]
    fn holes_exclude_the_edge_connected_background() {
        let (m, g) = grid(&["#####.", "#...#.", "#####.", "......"]);
        let h = holes(&m, g);
        assert_eq!(h.iter().filter(|&&v| v).count(), 3);
    }

    #[test]
    fn erosion_eats_the_frame_edge() {
        let (m, g) = grid(&["###", "###", "###"]);
        let e = erode(&m, g, 1);
        assert_eq!(e.iter().filter(|&&v| v).count(), 1);
    }
}
