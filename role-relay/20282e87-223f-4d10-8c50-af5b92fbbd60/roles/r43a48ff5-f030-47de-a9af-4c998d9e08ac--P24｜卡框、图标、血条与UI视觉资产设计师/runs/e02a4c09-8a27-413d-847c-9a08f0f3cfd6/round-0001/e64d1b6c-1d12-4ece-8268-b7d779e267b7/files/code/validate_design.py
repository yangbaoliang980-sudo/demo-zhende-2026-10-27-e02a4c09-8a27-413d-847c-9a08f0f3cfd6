#!/usr/bin/env python3
"""P23 design-file validator. Standard library only; never executes upstream UI.

This validates the delivered design contract and archive integrity, not a game.
All reports are written to a new directory outside the package.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
UX = ROOT / "design/ux"
A11Y = ROOT / "design/accessibility"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def read_tsv(path: Path):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"empty/malformed TSV: {path.name}")
    return rows


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def unique_ids(items, key):
    values = [x[key] for x in items]
    ensure(len(values) == len(set(values)), f"duplicate {key}")
    ensure(all(isinstance(x, str) and x for x in values), f"empty/non-string {key}")


def safe_path(relative: str) -> Path:
    p = PurePosixPath(relative)
    ensure(not p.is_absolute() and '..' not in p.parts and '\\' not in relative, f"unsafe path: {relative}")
    target = ROOT.joinpath(*p.parts)
    ensure(not target.is_symlink() and target.resolve().is_relative_to(ROOT), f"path escape: {relative}")
    return target


def anchor_check(contract):
    unique_ids(contract['anchors'], 'anchor_id')
    ensure(contract['owner'] == 'P23', 'wrong contract owner')
    ensure(contract['related_contracts'] == ['IC-21', 'IC-23'], 'wrong IC relation')
    for a in contract['anchors']:
        ensure(a['anchor_id'].startswith('ux.'), 'bad UX namespace')
        ensure(a['screen_id'] in contract['screens'], 'unknown anchor screen')
        ensure(a['writes_business_state'] is False, 'UX may not write business state')
        ensure(a['production_accepted'] is False, 'unaccepted production claim')
        ensure(bool(a['source_input_hashes']), 'anchor missing source hashes')
        ensure(('{' in a['anchor_id']) == bool(a['instance_key']), 'dynamic identity mismatch')
    ensure(contract['compatibility']['preserve_existing_payload'] is True, 'P19 payload must be preserved')
    ensure(contract['compatibility']['current_fields'] == ['id', 'x', 'y', 'width', 'height'], 'closed payload changed')
    ensure(contract['compatibility']['legacy_units_id'] == 'original unit_id unchanged', 'unit id rewritten')
    ensure(contract['compatibility']['legacy_cards_id'] == 'original card_instance_id unchanged', 'card id rewritten')


def learning_check(mapping):
    ensure(mapping['axes'] == ['connection', 'ledger_record', 'wallet_proof'], 'learning axes merged')
    unique_ids(mapping['entries'], 'ui_state_id')
    required = {'L_DISCONNECTED', 'L_TRANSPORT_ONLY', 'L_QUARANTINED', 'L_APPLIED_SIMULATED', 'L_APPLIED_UNPROVEN', 'L_APPLIED_VERIFIED', 'L_REVERTED', 'L_LOOKUP_UNKNOWN'}
    ensure(required.issubset({e['ui_state_id'] for e in mapping['entries']}), 'missing learning exception')
    for entry in mapping['entries']:
        ensure(entry['wallet_calculation'] == 'NONE', 'UI calculates wallet')
        ensure(entry['ledger_enum_added'] is False, 'UX invented ledger enum')
        ensure(entry['action'] == 'read_only_query', 'learning UX mutates ledger')
        if entry['formal_credit_label_allowed']:
            ensure(entry['ui_state_id'] == 'L_APPLIED_VERIFIED', 'false formal credit label')
            ensure(entry['current_execution_enabled'] is False, 'unproven production gate enabled')
            ensure(entry['formal_label_gate'] != 'NOT_APPLICABLE', 'credit proof gate missing')


def battle_retry_check(contract, ui_map):
    ensure('recovery' in contract, 'recovery distinction missing')
    battle = contract['recovery']['battle']
    ensure(battle['current_mode'] == 'RESEND_ORIGINAL_COMMAND_IDEMPOTENT', 'P19 recovery mode changed without acceptance')
    ensure(battle['read_only'] is False, 'P19 same-ID command resend incorrectly marked read-only')
    ensure(battle['preserve_fields'] == ['command_id','expected_revision','payload'], 'original command fields not preserved')
    ensure(battle['pending_storage'] == 'MEMORY_ONLY', 'prototype pending persistence overstated')
    ensure(battle['full_page_reload_recovery'] == 'BLOCKED_PENDING_PRODUCTION_CONTRACT', 'unaccepted reload recovery')
    ensure(contract['recovery']['meta']['read_only'] is True and contract['recovery']['learning']['read_only'] is True, 'read-only nonbattle queries changed')
    widget = next(w for w in ui_map['widgets'] if w['anchor_id']=='ux.battle.command.lookup')
    ensure(widget.get('transport_effect') == battle['current_mode'], 'battle widget retry binding mismatch')


def focus_check(rows, graph, anchor_ids):
    seen = set()
    for scope, ids in graph['groups'].items():
        subset = [r for r in rows if r['scope_id'] == scope]
        ensure([r['anchor_id'] for r in subset] == ids, f'focus order mismatch: {scope}')
        ensure([int(r['tab_order']) for r in subset] == list(range(1, len(ids)+1)), 'non-contiguous focus order')
        for i, row in enumerate(subset):
            ensure(row['anchor_id'] in anchor_ids, 'unregistered focus anchor')
            ensure(row['next_anchor'] == ids[(i+1) % len(ids)], 'broken next focus edge')
            ensure(row['previous_anchor'] == ids[(i-1) % len(ids)], 'broken previous focus edge')
            ensure((scope, row['anchor_id']) not in seen, 'duplicate focus row')
            seen.add((scope, row['anchor_id']))
            ensure(row['device_test_status'] == 'NOT_RUN', 'unrun device test claimed')
            ensure(row['disabled_behavior'] and row['removed_behavior'], 'missing focus fallback')
    ensure(len(seen) == len(rows), 'focus rows outside declared groups')
    ensure(graph['modal_scopes'] == ['growth_dialog'], 'unexpected modal trap')


def state_check(rows):
    unique_ids(rows, 'state_id')
    required = {'B_LOADING', 'B_READY', 'B_CARD_SELECTED', 'B_TARGET_COMPLETE', 'B_DISABLED_CARD', 'B_END_REVIEW', 'B_SENDING', 'B_UNKNOWN', 'B_INTENT_MISSING', 'B_CARD_CONTEXT_MISSING', 'B_STALE_SELECTION', 'B_WIN', 'B_LOSS', 'B_DRAW', 'B_ABORTED', 'B_FAULTED', 'P_DIRTY', 'G_CONFIRM', 'M_RESTART_PENDING', 'M_SAVE_RECOVERY_REQUIRED', 'R_UNKNOWN', 'L_QUARANTINED'}
    ensure(required.issubset({r['state_id'] for r in rows}), 'required exception state missing')
    ensure(all(r['runtime_result'] == 'NOT_RUN' for r in rows), 'design state claimed runtime PASS')


def svg_check(path, allowed_anchors):
    text = path.read_text(encoding='utf-8')
    ensure('<!DOCTYPE' not in text and '<!ENTITY' not in text, 'SVG external entity forbidden')
    root = ET.fromstring(text)
    ensure(root.tag.endswith('svg'), 'not SVG')
    width, height = float(root.attrib['width']), float(root.attrib['height'])
    control_ids = []
    focus_indicators = []
    for element in root.iter():
        tag = element.tag.rsplit('}', 1)[-1]
        ensure(tag not in ('script', 'foreignObject', 'animate', 'animateTransform', 'set', 'image'), 'active or raster content in editable low-fi SVG')
        for key, value in element.attrib.items():
            ensure(not key.lower().startswith('on'), 'SVG event handler')
            if key.rsplit('}', 1)[-1] == 'href':
                ensure(not value.startswith(('http:', 'https:', '//', 'javascript:')), 'external SVG resource')
        if tag == 'style':
            ensure(not re.search(r'url\([\s\"\']*(https?:|//)', element.text or ''), 'external font URL')
        if element.attrib.get('data-region') == 'focus_indicator':
            focus_indicators.append(element)
        aid = element.attrib.get('data-anchor-id')
        if aid:
            ensure(aid in allowed_anchors, f'unregistered SVG anchor: {aid}')
        if element.attrib.get('data-control'):
            x, y, w, h = [float(element.attrib[k]) for k in ('x', 'y', 'width', 'height')]
            ensure(all(math.isfinite(v) for v in (x, y, w, h)), 'non-finite geometry')
            ensure(w >= 44 and h >= 44, 'control smaller than project target 44')
            ensure(x >= 0 and y >= 48 and x+w <= width and y+h <= 768, 'control outside candidate screen rect')
            if aid and '{' not in aid:
                control_ids.append(aid)
        if tag == 'text':
            ensure(float(element.attrib['font-size']) >= 16, 'preview below support minimum')
    ensure(len(control_ids) == len(set(control_ids)), 'two fixed controls share one anchor')
    ensure(len(focus_indicators) <= 1, 'multiple focus indicators in one static state')
    ensure(root.find('{http://www.w3.org/2000/svg}title') is not None, 'SVG missing title')
    return {'width': width, 'height': height}


def contrast(hex1, hex2):
    def lum(hexcolor):
        values = [int(hexcolor[i:i+2], 16)/255 for i in (1, 3, 5)]
        values = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in values]
        return sum(x*y for x, y in zip(values, (.2126, .7152, .0722)))
    a, b = sorted((lum(hex1), lum(hex2)), reverse=True)
    return (a+.05)/(b+.05)


def manifest_check(manifest):
    records = manifest['files']
    unique_ids(records, 'relative_path')
    expected = {r['relative_path'] for r in records}
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()}
    ensure(actual == expected | {'delivery_manifest.json'}, 'manifest missing or unexpected file')
    for item in records:
        p = safe_path(item['relative_path'])
        ensure(p.stat().st_size == item['size_bytes'], f"size mismatch: {p}")
        ensure(digest(p) == item['sha256'], f"hash mismatch: {p}")
        ensure(item['format'] and item['version'] and item['receivers'], 'incomplete manifest metadata')
        ensure('modification_allowlist' in item and 'source_input_hashes' in item, 'missing ownership/provenance')
    return len(records)


def run(args):
    output = Path(args.output).resolve()
    ensure(not output.exists(), 'output must be a new directory')
    ensure(not output.is_relative_to(ROOT), 'output must be outside the package')
    output.mkdir(parents=True)
    report = {'layer': 'AUTHOR_STATIC_DESIGN_VALIDATION', 'game_ui_executed': False,
              'independent_review': False, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'command': sys.argv, 'validator_sha256': digest(Path(__file__)), 'checks': [], 'negative_probes': [], 'contrast': []}
    def check(name, fn, negative=False):
        try:
            detail = fn()
            result = 'FAIL' if negative else 'PASS'
            note = 'invalid mutation was accepted' if negative else detail
        except Exception as exc:
            result = 'PASS' if negative and isinstance(exc, ValueError) else 'FAIL'
            note = f'{type(exc).__name__}: {exc}'
        row = {'id': name, 'result': result, 'detail': note}
        report['negative_probes' if negative else 'checks'].append(row)
        print(f'{name}: {result}' + (f' [{note}]' if result == 'FAIL' else ''))

    if args.preflight:
        gates = read_json(UX/'blocker_register.json')
        paths = read_json(ROOT/'actual_path_request.json')
        report['layer'] = 'PRODUCTION_READINESS_PREFLIGHT'
        report['blockers'] = gates['items']
        report['production_write_authorized'] = paths['production_write_authorized']
        report['result'] = 'BLOCKED'
        report['exit_code'] = 3
        report['explanation'] = 'This isolated package never grants production authorization; resolve the named owner evidence before integration.'
        (output/'preflight.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print('PRODUCTION_READINESS: BLOCKED (exit 3)')
        return 3

    contract = read_json(UX/'ux_anchor_contract.json')
    anchor_ids = {a['anchor_id'] for a in contract['anchors']}
    mapping = read_json(UX/'learning_status_mapping.json')
    focus = read_tsv(UX/'keyboard_focus_matrix.tsv')
    graph = read_json(UX/'focus_graph.json')
    states = read_tsv(UX/'interaction_state_matrix.tsv')
    state_ids = {s['state_id'] for s in states}
    source = read_json(ROOT/'source_input_receipt.json')
    sources = {s['source_id']: s for s in source['sources']}
    catalog = read_json(UX/'wireframe_catalog.json')
    tasks = read_tsv(A11Y/'ux_acceptance_tasks.tsv')
    tokens = read_json(A11Y/'accessibility_tokens.json')

    def source_integrity():
        for item in source['sources']:
            p = safe_path(item['package_relative_path'])
            ensure(p.stat().st_size == item['size_bytes'] and digest(p) == item['sha256'], f"source changed: {item['source_id']}")
            ensure(item['modification_allowlist'] == [], 'upstream copy made editable')
        return len(sources)
    check('D01_SOURCE_BYTE_INTEGRITY', source_integrity)
    check('D02_ANCHOR_ID_AUTHORITY_AND_LEGACY', lambda: anchor_check(contract))
    check('D03_FOCUS_GRAPH_AND_FALLBACKS', lambda: focus_check(focus, graph, anchor_ids))
    check('D04_STATE_COMPLETENESS_AND_NOT_RUN', lambda: state_check(states))
    check('D05_LEARNING_PROOF_SEPARATION', lambda: learning_check(mapping))

    def input_hashes():
        records = contract['source_input_hashes'] + [r for a in contract['anchors'] for r in a['source_input_hashes']]
        for item in records:
            ensure(item['source_id'] in sources, 'unreceived source id')
            ensure(item['sha256'] == sources[item['source_id']]['sha256'], 'wrong source input hash')
        return len(records)
    check('D06_SOURCE_BINDINGS', input_hashes)

    def state_map():
        data = read_json(UX/'ui_state_map.json')
        unique_ids(data['widgets'], 'widget_id')
        ensure({x['anchor_id'] for x in data['widgets']} == anchor_ids, 'widget map incomplete')
        for widget in data['widgets']:
            ensure(set(widget['states']).issubset(state_ids), 'unregistered widget state')
            ensure(widget['states'], 'widget has no state family')
            ensure(set(widget['focus_scope']).issubset(graph['groups']), 'unknown focus scope')
            ensure(widget['runtime_status'] == 'NOT_RUN', 'widget runtime claim')
        return len(data['widgets'])
    check('D07_SCREEN_WIDGET_STATE_ANCHOR_MAP', state_map)

    def ia():
        data = read_json(UX/'information_architecture.json')
        ids = {s['screen_id'] for s in data['screens']}
        ensure(ids == set(contract['screens']) and len(ids) == 9, 'unexpected screen scope')
        ensure(all(s['new_screen'] is False for s in data['screens']), 'new unapproved screen')
        ensure(all(e['from'] in ids and e['to'] in ids for e in data['edges']), 'dangling IA edge')
        expected = {('home','learning'), ('home','party'), ('characters','growth'), ('chapters','handoff'), ('handoff','battle'), ('battle','settlement')}
        ensure(expected.issubset({(e['from'],e['to']) for e in data['edges']}), 'missing core IA path')
    check('D08_IA_EXISTING_SCOPE_AND_PATH', ia)

    def svg_all():
        for item in catalog['items']:
            ensure(set(item['state_ids']).issubset(state_ids), 'unknown wireframe state')
            ensure(item['runtime_binding'] == 'DESIGN_FIXTURE_ONLY', 'fixture scope not explicit')
            svg_check(safe_path(item['svg_relative_path']), anchor_ids)
            png = safe_path(item['png_relative_path']).read_bytes()
            ensure(png[:8] == b'\x89PNG\r\n\x1a\n', 'invalid PNG signature')
            ensure(int.from_bytes(png[16:20], 'big') == item['board_size'][0], 'PNG width mismatch')
            ensure(int.from_bytes(png[20:24], 'big') == item['board_size'][1], 'PNG height mismatch')
        return len(catalog['items'])
    check('D09_SVG_ANCHORS_HIT_AREAS_AND_PNGS', svg_all)

    def render_evidence():
        rendered = read_json(UX/'evidence/render_final/render_results.json')
        ensure(rendered['result'] == 'PASS' and rendered['game_ui_executed'] is False, 'render evidence failed/wrong layer')
        ensure({i['wireframe_id'] for i in rendered['cases']} == {i['wireframe_id'] for i in catalog['items']}, 'render coverage incomplete')
        by_id = {i['wireframe_id']: i for i in catalog['items']}
        for result in rendered['cases']:
            ensure(result['result'] == 'PASS' and not result['out_of_board'], 'render overflow or font error')
            ensure(result['input_svg_sha256'] == digest(safe_path(by_id[result['wireframe_id']]['svg_relative_path'])), 'stale render evidence')
            ensure(result['output_png_sha256'] == digest(safe_path(by_id[result['wireframe_id']]['png_relative_path'])), 'preview bytes differ from render')
        return {'browser':rendered['browser'], 'boards':len(rendered['cases'])}
    check('D10_RENDER_PROVENANCE_AND_BOUNDS', render_evidence)

    def contrast_check():
        for pair in tokens['contrast_pairs']:
            ratio = contrast(tokens['colors'][pair['fg']], tokens['colors'][pair['bg']])
            report['contrast'].append({'id':pair['id'], 'ratio':round(ratio,6), 'minimum':pair['min_ratio']})
            ensure(ratio >= pair['min_ratio'], 'contrast below proposed threshold')
        return len(report['contrast'])
    check('D11_LOW_FIDELITY_TOKEN_CONTRAST', contrast_check)

    def task_check():
        unique_ids(tasks, 'task_id')
        for t in tasks:
            ensure(t['status'] == 'NOT_RUN', 'unperformed UX acceptance claimed')
            ensure(t['executor'] and t['fix_owner'] and t['measurement'] and t['evidence_required'], 'acceptance task incomplete')
        return len(tasks)
    check('D12_MEASURABLE_UNRUN_ACCEPTANCE_TASKS', task_check)

    def trace_check():
        rows = read_tsv(UX/'requirements_traceability.tsv')
        requirements = {r['requirement_id'] for r in read_tsv(safe_path(sources['SRC-P01-REQ']['package_relative_path']))}
        test_ids = {t['task_id'] for t in tasks}
        for row in rows:
            ensure(row['requirement_id'] in requirements, 'invented upstream requirement id')
            ensure(set(row['candidate_test_ids'].split(';')).issubset(test_ids), 'nonexistent acceptance test')
            for art in row['artifacts'].split(';'):
                ensure(safe_path(art).exists() or (args.skip_manifest and art=='delivery_manifest.json'), 'missing trace artifact')
        return len(rows)
    check('D13_REQUIREMENT_TRACEABILITY', trace_check)

    def path_gate():
        data = read_json(ROOT/'actual_path_request.json')
        ensure(data['production_write_authorized'] is False and data['actual_game_commit'] is None, 'false production authority')
        ensure(all(x['write_allowed'] is False and x['actual_production_path'] is None for x in data['requested']), 'unmapped production write')
        ensure(data['upstream_files_read_only'] is True, 'upstream write allowed')
    check('D14_ISOLATED_WRITE_BOUNDARY', path_gate)

    def rfcs():
        items = read_json(ROOT/'interface_rfcs.json')['rfcs']
        unique_ids(items, 'rfc_id')
        for item in items:
            ensure(item['status'] == 'PREPARED_NOT_SUBMITTED', 'RFC incorrectly marked submitted')
            ensure(item['change_request']['overwrite_allowed'] is False, 'overwrite conflict allowed')
            for ref in item['base_source_hashes']:
                ensure(ref['sha256'] == sources[ref['source_id']]['sha256'], 'RFC wrong base hash')
        return len(items)
    check('D15_RFC_BASES_AND_NO_OVERWRITE', rfcs)

    def docs():
        required = ['README.md','P23_delivery_report.md','design/ux/information_architecture.md','design/ux/interaction_spec.md','design/ux/integration_handoff.md','design/ux/author_walkthrough.md','design/accessibility/typography_accessibility_spec.md','design/accessibility/reduced_motion_cases.md']
        for name in required:
            ensure(safe_path(name).stat().st_size > 500, f'incomplete required document: {name}')
        return len(required)
    check('D16_REQUIRED_ENTITY_DELIVERABLES', docs)

    def fonts():
        data = read_json(A11Y/'font_provenance.json')
        for item in data['fonts']:
            ensure(digest(safe_path(item['font_path'])) == item['sha256'], 'font byte mismatch')
            ensure(digest(safe_path(item['license_path'])) == item['license_sha256'], 'license byte mismatch')
        glyph = read_json(UX/'evidence/glyph_coverage.json')
        ensure(glyph['result'] == 'PASS_EXPECTED_MISSING_FIXTURE_ONLY', 'unexpected font coverage failure')
        ensure(glyph['missing_fixture_codepoints'] == ['U+20BB7','U+F0000'], 'missing fixture coverage changed')
    check('D17_FONT_PROVENANCE_AND_EXPECTED_FALLBACK', fonts)

    def independent_claims():
        data = read_json(ROOT/'verification_status.json')
        for key in ['game_unit_tests','runtime_contract_acceptance','target_engine_windows','physical_gamepad','screen_reader','P32_independent','P33_player_usability','P25_style','P37_license_review','P35_independent_gate','real_anki_e2e']:
            ensure(data['layers'][key] == 'NOT_RUN', f'unrun layer claimed: {key}')
        ensure(data['layers']['production_integration'] == 'BLOCKED', 'integration incorrectly claimed')
    check('D18_LAYERED_CLAIM_BOUNDARY', independent_claims)

    ui_map = read_json(UX/'ui_state_map.json')
    check('D20_BATTLE_RETRY_VERSUS_READ_ONLY_QUERY', lambda: battle_retry_check(contract, ui_map))

    mutation = copy.deepcopy(contract)
    mutation['anchors'].append(copy.deepcopy(mutation['anchors'][0]))
    check('N01_DUPLICATE_ANCHOR_REJECTED', lambda: anchor_check(mutation), True)
    mutation = copy.deepcopy(contract)
    mutation['anchors'][0]['writes_business_state'] = True
    check('N02_BUSINESS_WRITE_REJECTED', lambda: anchor_check(mutation), True)
    mutation = copy.deepcopy(contract)
    mutation['compatibility']['legacy_cards_id'] = 'localized_card_name'
    check('N03_LEGACY_ID_REWRITE_REJECTED', lambda: anchor_check(mutation), True)
    mutation = copy.deepcopy(mapping)
    next(e for e in mutation['entries'] if e['ui_state_id']=='L_QUARANTINED')['formal_credit_label_allowed'] = True
    check('N04_QUARANTINE_CREDIT_REJECTED', lambda: learning_check(mutation), True)
    mutation = copy.deepcopy(mapping)
    next(e for e in mutation['entries'] if e['ui_state_id']=='L_APPLIED_VERIFIED')['current_execution_enabled'] = True
    check('N05_UNACCEPTED_FORMAL_GATE_REJECTED', lambda: learning_check(mutation), True)
    mutation = copy.deepcopy(focus)
    mutation[0]['next_anchor'] = 'ux.invalid'
    check('N06_BROKEN_FOCUS_EDGE_REJECTED', lambda: focus_check(mutation, graph, anchor_ids), True)
    mutation = [r for r in states if r['state_id'] != 'B_UNKNOWN']
    check('N07_MISSING_UNKNOWN_STATE_REJECTED', lambda: state_check(mutation), True)
    check('N08_PATH_ESCAPE_REJECTED', lambda: safe_path('../elsewhere'), True)
    mutation = copy.deepcopy(contract)
    mutation['recovery']['battle']['read_only'] = True
    check('N09_BATTLE_RETRY_FALSE_READ_ONLY_REJECTED', lambda: battle_retry_check(mutation, ui_map), True)

    if args.skip_manifest:
        report['manifest_check'] = 'NOT_RUN_BUILD_STAGE_ONLY'
    else:
        check('D19_MANIFEST_ALL_FILES', lambda: manifest_check(read_json(ROOT/'delivery_manifest.json')))
        report['manifest_check'] = 'EXECUTED'
    all_checks = report['checks'] + report['negative_probes']
    report['summary'] = {'checks':len(report['checks']), 'negative_probes':len(report['negative_probes']), 'passed':sum(r['result']=='PASS' for r in all_checks), 'failed':sum(r['result']=='FAIL' for r in all_checks)}
    report['counts'] = {'anchors':len(anchor_ids), 'ui_states':len(states), 'focus_rows':len(focus), 'wireframes':len(catalog['items']), 'acceptance_tasks':len(tasks), 'fixed_sources':len(sources)}
    report['result'] = 'PASS' if not report['summary']['failed'] else 'FAIL'
    report['ended_utc'] = datetime.now(timezone.utc).isoformat()
    (output/'validation_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result':report['result'], **report['summary'], 'layer':report['layer']}, ensure_ascii=False))
    return 0 if report['result'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='new report directory outside the package')
    parser.add_argument('--preflight', action='store_true', help='production readiness, expected BLOCKED/exit 3')
    parser.add_argument('--skip-manifest', action='store_true', help='author build stage only; not final package verification')
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f'VALIDATOR_ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
