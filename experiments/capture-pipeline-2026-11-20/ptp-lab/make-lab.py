"""Write an experimental copy of the product's PTP bridge source with timing primitives added.

  python make-lab.py <repo>/crates/strehl-capture/src/ptp.rs <out>/ptp.rs

The product file is only read. The copy gains the `lab-*` commands of `lab-fragment.rs`
(inside `impl Camera`) and one dispatch arm in `serve`. Build the copy in a scratch source
tree; never install it as the controller's bridge.
"""
import pathlib
import sys

src = pathlib.Path(sys.argv[1]).read_bytes().decode().replace('\r\n', '\n')
fragment = pathlib.Path(__file__).with_name('lab-fragment.rs').read_bytes().decode().replace('\r\n', '\n')

anchor = '    fn restore_settings(&mut self) -> Vec<String> {\n'
assert src.count(anchor) == 1
src = src.replace(anchor, fragment + anchor)

anchor = '            let result = (|| -> Result<Value> {\n                match a.as_slice() {\n'
assert src.count(anchor) == 1
src = src.replace(anchor, anchor + '                    lab if lab[0].starts_with("lab-") => camera.lab(lab, lab_t0, &mut emit),\n')

anchor = '        for line in std::io::stdin().lock().lines() {\n'
assert src.count(anchor) == 1
src = src.replace(anchor, '        let lab_t0 = Instant::now();\n' + anchor)

pathlib.Path(sys.argv[2]).write_bytes(src.encode())
print('wrote', sys.argv[2], len(src), 'bytes')
