//! Offline inspection of the Sony focus audit, without interpreting it as depth.

use serde_json::Value;

/// JSON escaping alone cannot prevent the HTML parser ending a script element.
/// Keep every report string as data, including hostile filenames and errors.
pub(crate) fn render(report: &Value) -> String {
    let json = report
        .to_string()
        .replace('&', "\\u0026")
        .replace('<', "\\u003c")
        .replace('>', "\\u003e")
        .replace('\u{2028}', "\\u2028")
        .replace('\u{2029}', "\\u2029");
    let mut html = String::with_capacity(HTML_START.len() + json.len() + HTML_END.len());
    html.push_str(HTML_START);
    html.push_str(&json);
    html.push_str(HTML_END);
    html
}

const HTML_START: &str = r##"<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Strehl · Focus metadata</title>
<style>
:root{color-scheme:light dark;--bg:#f4f5f7;--panel:#fff;--ink:#202631;--muted:#626c7b;--line:#d9dee5;--accent:#245fa7;--soft:#eaf1f9;--warn:#8a5011;--warn-bg:#fff3df}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1320px;margin:auto;padding:24px}header{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:14px}.brand{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:700}h1{font-size:26px;letter-spacing:-.025em;margin:0;font-weight:650}h2{font-size:17px;margin:0}p{margin:8px 0}.muted{color:var(--muted)}.small{font-size:13px}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-numeric:tabular-nums}.notice{border-left:3px solid var(--accent);padding:9px 14px;background:var(--soft);margin:12px 0 18px}.counts{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 20px}.pill{border:1px solid var(--line);border-radius:20px;padding:3px 10px;font-size:13px;background:var(--panel)}.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px;margin-bottom:18px;min-width:0}.card-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:12px}.controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap}button,select,input{font:inherit;color:var(--ink)}button,select{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:7px 10px}button{cursor:pointer}button:hover{background:var(--soft)}button:disabled{opacity:.45;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px}input[type=range]{accent-color:var(--accent);min-width:120px;cursor:pointer}#frame-slider{flex:1}#frame-choice{max-width:100%;flex:1;min-width:180px}#frame-counter{min-width:100px;text-align:right}.frame-path{font-weight:600;overflow-wrap:anywhere;margin:14px 0 6px}.status{font-size:12px;text-transform:uppercase;letter-spacing:.055em;color:var(--accent)}.error{padding:10px 14px;background:var(--warn-bg);color:var(--warn);border-radius:6px;margin:10px 0;overflow-wrap:anywhere}.layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr);gap:18px}.metadata{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:16px 0 4px}.metadata dt{font-size:12px;color:var(--muted)}.metadata dd{margin:2px 0;font-size:16px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.metadata .wide{grid-column:1/-1}canvas{display:block;width:100%;height:auto;background:var(--bg);border:1px solid var(--line);image-rendering:pixelated;cursor:crosshair}.legend{display:flex;gap:10px;align-items:center;font-size:12px;margin:12px 0}.ramp{height:10px;flex:1;background:linear-gradient(90deg,#3268b6,#f0f0ef,#c76a32);border-radius:2px}.ramp.flag{background:linear-gradient(90deg,#f0f0ef,#7656a4)}.ramp.byte{background:linear-gradient(90deg,#f0f0ef,#245fa7)}#cell-info{min-height:70px;border-top:1px solid var(--line);padding-top:10px;overflow-wrap:anywhere;white-space:pre-wrap}.cell-controls{display:flex;align-items:center;gap:12px;margin:8px 0}.cell-controls input{flex:1}#grid-empty{padding:34px 12px;text-align:center;border:1px dashed var(--line);color:var(--muted)}#trace{display:block;width:100%;height:auto;min-height:160px;touch-action:manipulation;cursor:crosshair}#trace .axis{stroke:var(--line);stroke-width:1}#trace .label{fill:var(--muted);font-size:11px}#trace .series{fill:none;stroke:var(--accent);stroke-width:1.7}#trace .point{fill:var(--accent)}#trace .selection{stroke:var(--warn);stroke-width:1.5;stroke-dasharray:4 3}#trace .selected-point{fill:var(--warn)}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:7px 9px;white-space:nowrap}th{font-weight:600;color:var(--muted)}td.numeric{text-align:right;font-variant-numeric:tabular-nums}details{margin-top:12px}summary{cursor:pointer;font-size:13px;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:320px;overflow:auto;padding:12px;background:var(--bg);border-radius:6px}ul{padding-left:20px}.break-list{max-height:180px;overflow:auto}.footer{font-size:12px;color:var(--muted);overflow-wrap:anywhere;margin:18px 0}noscript{display:block;padding:20px;background:var(--warn-bg)}[hidden]{display:none!important}
@media(max-width:850px){main{padding:14px}.layout{grid-template-columns:1fr}.card{padding:16px}.metadata{grid-template-columns:repeat(2,minmax(0,1fr))}h1{font-size:23px}#frame-counter{min-width:70px}}
@media(prefers-color-scheme:dark){:root{--bg:#171c23;--panel:#202731;--ink:#e7ebf1;--muted:#a8b1bf;--line:#3b4655;--accent:#82b3ed;--soft:#25364a;--warn:#efbd80;--warn-bg:#3c3021}canvas{background:#f0f0ef}}
</style>
</head>
<body>
<main>
<header><span class="brand">Strehl</span><h1>Focus metadata</h1><span class="muted small">Offline inspection</span></header>
<p class="notice">Uncalibrated camera values. The record grid follows the firmware row-major layout; its mapping onto the decoded photograph and physical units are not calibrated. This report does not establish a depth map or measurement freshness.</p>
<noscript>JavaScript is needed to inspect this report. The complete audit JSON is embedded in the file.</noscript>
<div class="counts" id="counts" aria-label="File status counts"></div>
<section class="card" aria-labelledby="frame-heading">
<div class="card-head"><h2 id="frame-heading">Frame</h2><span id="frame-counter" class="mono small"></span></div>
<div class="controls"><button id="previous" type="button" aria-label="Previous frame">← Previous</button><input id="frame-slider" type="range" min="0" max="0" value="0" aria-label="Frame in filename order"><button id="next" type="button" aria-label="Next frame">Next →</button></div>
<div class="controls" style="margin-top:12px"><label for="frame-choice" class="small">Filename order</label><select id="frame-choice" aria-label="Choose frame"></select></div>
<div id="frame-path" class="frame-path"></div><div id="frame-status" class="status"></div>
<div id="frame-error" class="error" role="status" hidden></div>
<dl class="metadata" id="metadata"></dl>
</section>
<div class="layout">
<section class="card" aria-labelledby="grid-heading">
<div class="card-head"><h2 id="grid-heading">Record grid</h2><select id="grid-mode" aria-label="Grid display"><option value="signed">Signed value display</option><option value="flag">Last flag byte · bit 0x20</option><option value="flag0">First flag byte</option><option value="flag1">Last flag byte</option></select></div>
<p id="grid-caption" class="muted small"></p>
<canvas id="grid" width="660" height="460" role="img" aria-label="Stored focus record grid, not mapped onto the photograph"></canvas>
<div id="grid-empty" hidden></div>
<div class="legend" id="legend"><span id="legend-low" class="mono">−32000</span><span class="ramp" id="ramp"></span><span id="legend-high" class="mono">+32000</span></div>
<p id="legend-note" class="muted small">Fixed color scale, centered at zero. Signed int16 is a display interpretation of the stored bits; no records are discarded.</p>
<div class="cell-controls"><label for="cell-slider" class="small">Record</label><input id="cell-slider" type="range" min="0" max="0" value="0" aria-label="Inspect grid record"><span id="cell-counter" class="small mono"></span></div>
<div id="cell-info" class="small mono" aria-live="polite"></div>
<details><summary>Flag pairs in this frame</summary><div class="scroll"><table><thead><tr><th>First byte</th><th>Last byte</th><th>Records</th></tr></thead><tbody id="flags-body"></tbody></table></div><p class="muted small">Raw flag bytes are retained. Their meanings are not established.</p></details>
</section>
<section class="card" aria-labelledby="trend-heading">
<div class="card-head"><h2 id="trend-heading">Focus state through the bracket</h2><select id="trace-mode" aria-label="Scalar to plot"><option value="b">Fine scalar B</option><option value="a">Scalar A</option><option value="coarse">Coarse focus position</option></select></div>
<p class="muted small">Filename order, raw camera units. Lines connect only comparable adjacent frames. Select a point to inspect its frame.</p>
<svg id="trace" viewBox="0 0 620 240" role="img" aria-label="Raw focus scalar through frames in filename order"></svg>
<p id="trace-caption" class="mono small"></p>
<p class="muted small">Fine scalar B can distinguish frames with the same coarse position. Neither scale is calibrated to distance or equal physical focus steps.</p>
<details open><summary>Comparable segments · scalar B</summary><div class="scroll"><table><thead><tr><th>Frames</th><th>Direction</th><th>Repeated</th><th>Reversals</th><th>Large deltas</th></tr></thead><tbody id="segments-body"></tbody></table></div><p class="muted small">Large means greater than three times the segment's median nonzero absolute delta. These are descriptive changes, not proof of missing frames.</p></details>
<details id="breaks-details"><summary id="breaks-heading">Comparison breaks</summary><ul id="breaks" class="break-list small"></ul></details>
</section>
</div>
<section class="card" id="optical-card" aria-labelledby="optical-heading" hidden><h2 id="optical-heading">Optical header facts</h2><p id="optical-status" class="small"></p><p class="muted small">Camera settings and signed tables are stored separately. A zero setting does not erase a table. Values do not establish a calibrated correction; this report activates none.</p><pre id="optical-facts"></pre></section>
<section class="card" aria-labelledby="provenance-heading"><h2 id="provenance-heading">Interpretation and provenance</h2><ul id="limits" class="small"></ul><details><summary>Selected frame · stored fields and hashes</summary><pre id="provenance"></pre></details><p class="muted small">This file embeds audit metadata only. It has no external resources and does not alter source files, frame order, alignment, or merge decisions.</p></section>
<div class="footer" id="footer"></div>
</main>
<script id="report-data" type="application/json">"##;

const HTML_END: &str = r##"</script>
<script>
'use strict';
(() => {
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const array = value => Array.isArray(value) ? value : [];
  const number = value => typeof value === 'number' && Number.isFinite(value) ? value : null;
  const integer = value => Number.isInteger(value) ? value : null;
  const display = value => value === null || value === undefined ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  const el = id => document.getElementById(id);
  const text = (id, value) => { el(id).textContent = display(value); };
  const filename = value => typeof value === 'string' ? value.split(/[\\/]/).pop() : 'Unnamed frame';
  const hex = value => integer(value) !== null && value >= 0 && value <= 255 ? '0x' + value.toString(16).padStart(2, '0').toUpperCase() : '—';
  const report = object(JSON.parse(el('report-data').textContent));
  const frames = array(report.frames).map(object);
  const segments = array(report.scalar_b_segments).map(object);
  const breaks = array(report.comparison_breaks).map(object);
  const byIndex = new Map();
  frames.forEach((frame, position) => { if (integer(frame.index) !== null) byIndex.set(frame.index, position); });
  const frameNumber = index => byIndex.has(index) ? byIndex.get(index) + 1 : '?';
  const edges = new Set();
  segments.forEach(segment => array(segment.deltas).forEach(deltaValue => {
    const delta = object(deltaValue), from = byIndex.get(delta.from_index), to = byIndex.get(delta.to_index);
    if (from !== undefined && to === from + 1) edges.add(from);
  }));
  let selected = 0, cell = 0, grid = {}, records = [], gridWidth = 0, gridHeight = 0;
  const counts = object(report.counts);
  [['Files',frames.length],['Present',counts.present],['Absent',counts.absent],['Unsupported',counts.unsupported],['Malformed',counts.malformed],['I/O errors',counts.io_error]].forEach(([label,value]) => {
    const span = document.createElement('span'); span.className = 'pill'; span.textContent = label + ' ' + display(value); el('counts').appendChild(span);
  });
  frames.forEach((frame, position) => {
    const option = document.createElement('option'); option.value = String(position);
    option.textContent = (position + 1) + ' · ' + filename(frame.path) + (frame.status === 'present' ? '' : ' · ' + display(frame.status));
    el('frame-choice').appendChild(option);
  });
  el('frame-slider').max = String(Math.max(0, frames.length - 1));
  el('frame-slider').disabled = frames.length === 0;
  el('frame-choice').disabled = frames.length === 0;
  const fallbackLimits = [
    'Raw scalar differences are not calibrated physical focus steps or distance.',
    'Grid values and flags do not establish sharpness, valid depth, registration to the photograph, or spatial coverage.',
    'Matching section sequences do not prove fresh measurements; firmware can reuse a prior buffer.'
  ];
  (array(report.limits).length ? report.limits : fallbackLimits).forEach(value => {
    const li = document.createElement('li'); li.textContent = display(value); el('limits').appendChild(li);
  });
  segments.forEach(segment => {
    const tr = document.createElement('tr');
    [frameNumber(segment.first_index) + '–' + frameNumber(segment.last_index),segment.direction,segment.repeated_pairs,segment.direction_changes,segment.large_delta_pairs].forEach((value,index) => {
      const td = document.createElement('td'); td.textContent = display(value); if (index > 1) td.className = 'numeric'; tr.appendChild(td);
    }); el('segments-body').appendChild(tr);
  });
  if (!segments.length) {
    const tr = document.createElement('tr'), td = document.createElement('td'); td.colSpan = 5; td.textContent = 'No comparable segments.'; tr.appendChild(td); el('segments-body').appendChild(tr);
  }
  breaks.forEach(item => {
    const li = document.createElement('li'); li.textContent = 'Frames ' + frameNumber(item.from_index) + ' → ' + frameNumber(item.to_index) + ': ' + display(item.reason); el('breaks').appendChild(li);
  });
  text('breaks-heading', 'Comparison breaks · ' + breaks.length);
  if (!breaks.length) { const li = document.createElement('li'); li.textContent = 'None reported.'; el('breaks').appendChild(li); }
  text('footer', 'Strehl ' + display(report.strehl_version) + ' · ' + display(report.schema) + ' · Order: ' + display(report.input_order));

  function property(label, value, wide = false) {
    const div = document.createElement('div'); if (wide) div.className = 'wide';
    const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = label; dd.textContent = display(value); div.append(dt,dd); el('metadata').appendChild(div);
  }

  function selectFrame(position) {
    selected = Math.max(0,Math.min(frames.length - 1,Number.isFinite(position) ? Math.round(position) : 0));
    if (!frames.length) selected = 0;
    el('frame-slider').value = String(selected); el('frame-choice').value = String(selected);
    el('previous').disabled = selected === 0 || !frames.length; el('next').disabled = selected >= frames.length - 1;
    const frame = frames[selected] || {}, meta = object(frame.metadata), scalars = array(meta.scalars_raw), optics = object(meta.optical_identity);
    text('frame-counter', frames.length ? (selected + 1) + ' / ' + frames.length : '0 / 0');
    text('frame-path', frames.length ? display(frame.path) : 'No frames in this report');
    text('frame-status', frames.length ? frame.status : 'Empty report');
    el('frame-error').hidden = !frame.reason; text('frame-error', frame.reason || '');
    el('metadata').replaceChildren();
    property('Coarse focus position',meta.coarse_focus_position);
    property('Fine scalar B',scalars[1]);
    property('Scalar A',scalars[0]);
    property('Camera / firmware',meta.model ? display(meta.model) + ' / ' + display(meta.software) : null);
    property('Focal length / aperture',optics.focal_length_mm != null || optics.f_number != null ? display(optics.focal_length_mm) + ' mm / f/' + display(optics.f_number) : null);
    property('Section sequences',array(meta.section_sequences).length ? meta.section_sequences.map(display).join(' / ') + (meta.section_sequences_agree === false ? ' · disagree' : '') : null);
    property('Lens',optics.lens_model, true);
    grid = object(meta.grid); records = array(grid.records).map(object);
    gridWidth = integer(grid.width) || 0; gridHeight = integer(grid.height) || 0;
    const shapeOkay = gridWidth > 0 && gridHeight > 0 && gridWidth <= 512 && gridHeight <= 512 && gridWidth * gridHeight === records.length;
    el('grid').hidden = !shapeOkay; el('grid-empty').hidden = shapeOkay;
    el('legend').hidden = !shapeOkay; el('cell-slider').disabled = !shapeOkay;
    el('cell-slider').max = String(Math.max(0,records.length - 1));
    text('grid-caption', shapeOkay ? gridWidth + ' × ' + gridHeight + ' · ' + records.length + ' records · top left is stored record 0' : 'No grid available for this frame.');
    text('grid-empty', frame.status !== 'present' ? 'Focus metadata ' + display(frame.status || 'unavailable') + '.' : !Array.isArray(grid.records) ? 'Grid records were not included in this report. Export with --html to include them.' : 'The stored grid dimensions and record count do not agree.');
    el('flags-body').replaceChildren();
    array(grid.flag_pairs).forEach(value => {
      const pair = object(value), bytes = array(pair.bytes), tr = document.createElement('tr');
      [hex(bytes[0]),hex(bytes[1]),display(pair.count)].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.appendChild(td); }); el('flags-body').appendChild(tr);
    });
    const optical = object(frame.optical);
    el('optical-card').hidden = !frame.optical;
    text('optical-status', frame.optical ? 'Optical metadata: ' + display(optical.status) + (optical.reason ? ' - ' + display(optical.reason) : '') : '');
    text('optical-facts', optical.facts ? JSON.stringify(optical.facts,null,2) : 'No optical facts available for this frame.');
    const provenance = {...frame};
    if (frame.metadata && typeof frame.metadata === 'object') provenance.metadata = {...meta,grid:{...grid,records:undefined}};
    text('provenance',JSON.stringify(provenance,null,2));
    if (!shapeOkay) { records = []; gridWidth = 0; gridHeight = 0; }
    cell = Math.min(cell,Math.max(0,records.length - 1));
    drawGrid(); inspectCell(cell); drawTrace();
  }

  function mix(a,b,t) { return 'rgb(' + a.map((value,index) => Math.round(value + (b[index] - value) * t)).join(',') + ')'; }
  function recordColor(record, mode) {
    const neutral = [240,240,239], flags = array(record.flags);
    if (mode === 'signed') {
      const value = number(record.signed_display); if (value === null) return '#999999';
      return mix(neutral,value < 0 ? [50,104,182] : [199,106,50],Math.min(1,Math.abs(value) / 32000));
    }
    const byte = number(flags[mode === 'flag0' ? 0 : 1]);
    if (byte === null || !Number.isInteger(byte) || byte < 0 || byte > 255) return '#999999';
    return mode === 'flag' ? (byte & 0x20 ? '#7656a4' : '#f0f0ef') : mix(neutral,[36,95,167],byte / 255);
  }

  function drawGrid() {
    const mode = el('grid-mode').value;
    text('legend-low',mode === 'signed' ? '−32000' : mode === 'flag' ? 'Clear' : '0x00');
    text('legend-high',mode === 'signed' ? '+32000' : mode === 'flag' ? 'Set' : '0xFF');
    el('ramp').className = 'ramp' + (mode === 'flag' ? ' flag' : mode !== 'signed' ? ' byte' : '');
    text('legend-note',mode === 'signed' ? 'Fixed color scale, centered at zero. Signed int16 is a display interpretation of the stored bits; no records are discarded.' : 'Raw flags, with no validity or confidence interpretation. Gray cells have unavailable or malformed values.');
    if (!records.length) return;
    const canvas = el('grid'), context = canvas.getContext('2d');
    if (!context) { text('grid-empty','Canvas is unavailable in this browser. Use the Record slider to inspect exact values.'); el('grid-empty').hidden = false; return; }
    const size = 20; canvas.width = gridWidth * size; canvas.height = gridHeight * size;
    records.forEach((record,index) => { context.fillStyle = recordColor(record,mode); context.fillRect((index % gridWidth) * size,Math.floor(index / gridWidth) * size,size,size); });
    context.strokeStyle = '#202631'; context.lineWidth = 1; context.strokeRect((cell % gridWidth) * size + 1.5,Math.floor(cell / gridWidth) * size + 1.5,size - 3,size - 3);
    context.strokeStyle = '#ffffff'; context.strokeRect((cell % gridWidth) * size + 2.5,Math.floor(cell / gridWidth) * size + 2.5,size - 5,size - 5);
    canvas.setAttribute('aria-label',gridWidth + ' by ' + gridHeight + ' stored records. ' + el('grid-mode').selectedOptions[0].textContent + '. Use the Record slider below for exact values.');
  }

  function inspectCell(index) {
    cell = Math.max(0,Math.min(records.length - 1,Math.round(index))); if (!records.length) cell = 0;
    el('cell-slider').value = String(cell);
    text('cell-counter',records.length ? cell + ' / ' + (records.length - 1) : '—');
    if (!records.length) { text('cell-info','No record selected.'); return; }
    const record = records[cell], flags = array(record.flags), bits = integer(record.value_bits);
    text('cell-info','Record ' + cell + ' · row ' + Math.floor(cell / gridWidth) + ', column ' + (cell % gridWidth) + ' (zero based)\nSigned display: ' + display(record.signed_display) + ' · stored bits: ' + display(record.value_bits) + (bits !== null && bits >= 0 && bits <= 65535 ? ' (0x' + bits.toString(16).padStart(4,'0').toUpperCase() + ')' : '') + '\nFlags: ' + hex(flags[0]) + ' ' + hex(flags[1]));
    drawGrid();
  }

  function svgNode(tag, attributes, content) {
    const node = document.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attributes || {}).forEach(([key,value]) => node.setAttribute(key,String(value)));
    if (content !== undefined) node.textContent = content;
    el('trace').appendChild(node); return node;
  }

  function traceValue(frame, mode) {
    if (frame.status !== 'present') return null;
    const meta = object(frame.metadata);
    return number(mode === 'coarse' ? meta.coarse_focus_position : array(meta.scalars_raw)[mode === 'a' ? 0 : 1]);
  }

  function drawTrace() {
    const mode = el('trace-mode').value, values = frames.map(frame => traceValue(frame,mode));
    const finite = values.filter(value => value !== null), svg = el('trace'); svg.replaceChildren();
    const title = el('trace-mode').selectedOptions[0].textContent;
    svgNode('title',{},title + ' in filename order, raw camera units.');
    if (!finite.length) { svgNode('text',{x:310,y:110,'text-anchor':'middle',class:'label'},'No numeric values to plot.'); text('trace-caption','No scalar data.'); return; }
    let low = Infinity, high = -Infinity; finite.forEach(value => { low = Math.min(low,value); high = Math.max(high,value); });
    const lowLabel = low, highLabel = high; if (low === high) { low -= 1; high += 1; }
    const left = 70, right = 605, top = 22, bottom = 200;
    const x = position => frames.length < 2 ? (left + right) / 2 : left + position / (frames.length - 1) * (right - left);
    const y = value => bottom - (value - low) / (high - low) * (bottom - top);
    [top,bottom].forEach(position => svgNode('line',{x1:left,x2:right,y1:position,y2:position,class:'axis'}));
    svgNode('text',{x:left - 8,y:top + 4,'text-anchor':'end',class:'label'},String(highLabel));
    svgNode('text',{x:left - 8,y:bottom + 4,'text-anchor':'end',class:'label'},String(lowLabel));
    svgNode('text',{x:left,y:224,class:'label'},'Frame 1');
    svgNode('text',{x:right,y:224,'text-anchor':'end',class:'label'},'Frame ' + frames.length);
    let path = '';
    values.forEach((value,index) => { if (value !== null && index > 0 && values[index - 1] !== null && edges.has(index - 1)) path += 'M' + x(index - 1) + ',' + y(values[index - 1]) + 'L' + x(index) + ',' + y(value); });
    if (path) svgNode('path',{d:path,class:'series'});
    values.forEach((value,index) => { if (value !== null) svgNode('circle',{cx:x(index),cy:y(value),r:index === selected ? 4 : 2,class:index === selected ? 'selected-point' : 'point'}); });
    svgNode('line',{x1:x(selected),x2:x(selected),y1:top,y2:bottom,class:'selection'});
    text('trace-caption',title + ': ' + display(values[selected]) + ' · range ' + lowLabel + '–' + highLabel);
  }

  el('frame-slider').addEventListener('input',event => selectFrame(Number(event.target.value)));
  el('frame-choice').addEventListener('change',event => selectFrame(Number(event.target.value)));
  el('previous').addEventListener('click',() => selectFrame(selected - 1));
  el('next').addEventListener('click',() => selectFrame(selected + 1));
  el('grid-mode').addEventListener('change',drawGrid);
  el('trace-mode').addEventListener('change',drawTrace);
  el('cell-slider').addEventListener('input',event => inspectCell(Number(event.target.value)));
  el('grid').addEventListener('pointerdown',event => {
    if (!records.length) return;
    const rect = el('grid').getBoundingClientRect();
    const column = Math.max(0,Math.min(gridWidth - 1,Math.floor((event.clientX - rect.left) / rect.width * gridWidth)));
    const row = Math.max(0,Math.min(gridHeight - 1,Math.floor((event.clientY - rect.top) / rect.height * gridHeight)));
    inspectCell(row * gridWidth + column);
  });
  el('trace').addEventListener('pointerdown',event => {
    const rect = el('trace').getBoundingClientRect();
    selectFrame(((event.clientX - rect.left) / rect.width * 620 - 70) / (605 - 70) * (frames.length - 1));
  });
  selectFrame(0);
})();
</script>
</body>
</html>
"##;

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn embedded_report(html: &str) -> Value {
        let (_, data) = html
            .split_once("<script id=\"report-data\" type=\"application/json\">")
            .unwrap();
        let (data, _) = data.split_once("</script>").unwrap();
        serde_json::from_str(data).unwrap()
    }

    #[test]
    fn untrusted_paths_cannot_end_the_data_script() {
        let report = json!({
            "frames": [{"path": "</script><script>alert('x')</script>&<>\u{2028}\u{2029}",
                "reason": "<!-- </ScRiPt> <img src=x onerror=alert(1)>",
                "status": "malformed"}],
            "limits": ["Do not interpolate \" or ' into script source."]
        });
        let html = render(&report);
        assert_eq!(embedded_report(&html), report);
        assert_eq!(html.matches("<script").count(), 2);
        assert_eq!(html.matches("</script>").count(), 2);
        assert!(!html.contains("<img src=x"));
        assert!(!html.contains("</ScRiPt>"));
        assert!(!html.contains('\u{2028}'));
        assert!(!html.contains('\u{2029}'));
    }

    #[test]
    fn missing_and_malformed_report_values_remain_data() {
        for report in [
            Value::Null,
            json!({}),
            json!({"frames": [], "scalar_b_segments": []}),
            json!({"frames": [null, {"metadata": {"grid": {"width": 33, "height": 23,
                "records": [{"signed_display": "<b>unknown</b>", "flags": null}]}}}],
                "limits": [null, 42], "counts": "not an object"}),
        ] {
            let html = render(&report);
            assert_eq!(embedded_report(&html), report);
            assert!(html.ends_with("</html>\n"));
        }
    }

    #[test]
    fn report_is_offline_and_retains_unknown_flag_bits() {
        let report = json!({"frames": [{"metadata": {"grid": {
            "records": [{"value_bits": 65535, "signed_display": -1, "flags": [255, 173]}]
        }}}]});
        let html = render(&report);
        assert_eq!(embedded_report(&html), report);
        assert!(html.contains("default-src 'none'"));
        assert!(!html.contains("<script src="));
        assert!(!html.contains("<link "));
        assert!(!html.contains("innerHTML"));
    }
}
