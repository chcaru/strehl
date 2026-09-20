"""Root one-time adaptation of the retained bounded photographic runner."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
text = (ROOT / 'experiments/parallel-cfa-wavelet/full-run.py').read_text()
text = text.replace('parallel_full_common', 'rb_residual_full_common')
text = text.replace("assert screen_data['bounded_photographic_prototype_admitted'] is False", "assert screen_data['photographic_replay_admitted'] is False\n    assert c.ref(screen)['sha256'] == '9f064df49645fafc45b5c2cd16d379a5c1fe048a3b47549f7af8062783aea8ae'")
text = text.replace("    sb = json.loads((screen_dir / 'bindings.json').read_text())\n    assert sb['sources'] == sources and sb['executable'] == c.ref(exe)\n", '')
text = text.replace("    assert screen_completion['mechanical_passed'] and screen_completion['preservation']['passed']\n", '')
text = text.replace("independent_plan=c.ref(HERE / 'independent-plan.md'),", "independent_review=c.ref(HERE / 'source-review.md'),")
text = text.replace("HERE / 'charter.md'", "HERE / 'observational-plan.md'")
text = text.replace('STREHL_BOUNDARY_CFA_WAVELET_OUT', 'STREHL_RB_RESIDUAL_GUARD_OUT')
text = text.replace('STREHL_PARALLEL_CFA_FULL_CONFIG', 'STREHL_RB_RESIDUAL_FULL_CONFIG')
text = text.replace('STREHL_PARALLEL_CFA_PHASE', 'STREHL_RB_RESIDUAL_PHASE')
text = text.replace('merge_cmd::parallel_cfa_wavelet::', 'merge_cmd::rb_residual_full::')
text = text.replace("    c.save(out / 'mechanical-binding.json', c.ref(screen_dir / 'completion.json'))", "    c.save(out / 'mechanical-binding.json', c.ref(screen_dir / 'completion.json'))\n    controls = build / 'mechanical-1/completion.json'\n    control = json.loads(controls.read_text())\n    assert control['passed'] and control['executable'] == c.ref(exe)\n    c.save(out / 'full-mechanical-binding.json', c.ref(controls))")
with (HERE / 'full-run.py').open('x') as f: f.write(text)
text = (ROOT / 'experiments/parallel-cfa-wavelet/cost-decision.py').read_text()
text = text.replace("[4096, 4096] and measured['candidate_levels'] == 12", "[3460, 2306] and measured['candidate_levels'] == 7\n    assert measured['significance_sources'] == 70")
text = text.replace("HERE / 'charter.md'", "HERE / 'observational-plan.md'")
with (HERE / 'cost-decision.py').open('x') as f: f.write(text)
