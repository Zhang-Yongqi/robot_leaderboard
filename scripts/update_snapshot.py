#!/usr/bin/env python3
"""Build the reviewed four-error v3 staging payload without estimating completion.

Inputs are read only. Only explicit identity and full-window fields are selected.
Each result retains only four frozen provenance hashes; absent hashes are null.
Four frozen errors may be published with honest pending/null completion. New
completion values remain unsupported until their separate contract is reviewed.
"""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile

FULL_SOURCE_SHA = '119d981f07983b060b038e860ac0da9b2d5c10c166fc637b83d179cbf6bda5dd'
IDENTITY_SHA = 'd7c902304aba5ca0588275b4b366f7bb799ee6e5a243c1bc8866ad059fb12aa4'
WINDOW = 'full_replay_50hz_first_substep'
FULL4 = ('full_body_pos_mm', 'full_body_ori_rad', 'full_wrist_pos_mm', 'full_wrist_ori_rad')
JOIN = ('dataset', 'condition', 'mode', 'robot', 'motion_id', 'seed')
IDENTITY_FIELDS = ('id', 'label', 'phase', 'dataset', 'condition', 'mode', 'robot', 'motion_id', 'scope')
PROVENANCE_FIELDS = ('protocol_sha256', 'execution_protocol_sha256', 'config_sha256', 'source_sha256')
PROVENANCE_SHA = '5d30b618a4300469439d2845b51c3dca0b7c18336abf43b0940d9b9484a6e7ad'
COUNTS = {'episode_records': 180, 'paired_cases': 90, 'unique_motions': 45,
          'comparison_groups': 5, 'aggregate_rows': 10, 'result_rows': 190}
PREVIEW_STATE = 'internal_preview_completion_pending'
PUBLIC_STATE = 'fullwindow_published_completion_pending'
PENDING = {'status': 'pending', 'completed': None, 'rate_pct': None, 'ci95': None,
           'reason': '等待正式完成判据和标签冻结'}
COMPLETION_CONTRACT = {'status': 'pending', 'rule_version': None, 'source_sha256': None}
EPISODE_COLUMNS = ['id', 'label', 'phase', 'dataset', 'condition', 'mode', 'robot', 'motion_id',
    'seed', 'scope', *PROVENANCE_FIELDS, 'comparison_id', 'sample_set_sha256', 'run_id', 'case_id', 'metric_window',
    'full_recorded_frames', 'reference_common_frames', 'reference_start_s', 'reference_end_s',
    *FULL4, 'completion_status', 'motion_completed', 'motion_completion_pct',
    'completion_ci95_low', 'completion_ci95_high', 'completion_reason']
COMPARISON_COLUMNS = ['id', 'label', 'comparison_id', 'phase', 'dataset', 'condition', 'mode',
    'robot', 'scope', *PROVENANCE_FIELDS, 'matched_seed_set', 'n_unique_motions', 'paired_cases', 'sample_set_sha256',
    'metric_window', *[field for metric in FULL4 for field in
    (metric, metric + '_ci95_low', metric + '_ci95_high')],
    'completion_status', 'motion_completed', 'motion_completion_pct',
    'completion_ci95_low', 'completion_ci95_high', 'completion_reason']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, 'Duplicate JSON key')
            obj[key] = value
        return obj
    def invalid(value):
        raise ValueError('Non-finite JSON number')
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=invalid)


def seed(value):
    if type(value) is int and value >= 0:
        return value
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]*', value) is not None,
            'Seed must be a strict decimal integer')
    return int(value)


def episode_key(row):
    require(row['phase'] == 'A', 'Episode phase differs')
    require(all(type(row[key]) is str and row[key] for key in JOIN[:-1]), 'Missing semantic identity')
    return tuple(row[key] for key in JOIN[:-1]) + (seed(row['seed']),)


def group_key(row):
    return tuple(row[key] for key in ('dataset', 'condition', 'mode'))


def provenance(identity):
    """Select frozen scientific hashes; an absent source field stays null."""
    original = identity.get('provenance', {})
    require(type(original) is dict, 'Invalid frozen provenance')
    selected = {name: deepcopy(original.get(name)) for name in PROVENANCE_FIELDS}
    require(all(value is None or (type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value))
                for value in selected.values()), 'Scientific provenance must be SHA256 or null')
    return selected


def provenance_digest(rows):
    records = [{'id': row['id'], 'provenance': row['provenance']}
               for row in sorted(rows, key=lambda row: row['id'])]
    return sha(json.dumps(records, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode())


def metric_cell(value, unit, ci, n):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            'Full-window error must be finite and nonnegative')
    if ci is not None:
        require(type(ci) is list and len(ci) == 2 and all(type(x) in (int, float)
                and math.isfinite(x) for x in ci) and ci[0] <= ci[1], 'Invalid full-window interval')
    return {'value': value, 'unit': unit, 'ci95': deepcopy(ci), 'n_motions': n}


def project(full, identities, publication=False):
    require(full['schema'] == 'rp1-g1-public-fullwindow-handoff-v1' and
            full['metric_window'] == WINDOW, 'Unreviewed full-window schema')
    require(len(full['episodes']) == 180 and len(full['comparisons']) == 5,
            'Full-window source counts differ')
    original_rows = identities['results']
    require(len(original_rows) == 190 and len({r['id'] for r in original_rows}) == 190,
            'Identity baseline must contain 190 original IDs')
    require(Counter(r['scope'] for r in original_rows) == {'per_motion': 180, 'aggregate': 10},
            'Identity scope counts differ')
    episodes = {episode_key(r): r for r in full['episodes']}
    originals = {episode_key(r): r for r in original_rows if r['scope'] == 'per_motion'}
    require(len(episodes) == len(originals) == 180 and set(episodes) == set(originals),
            'Full-window and original episodes do not have the same unique semantic identities')
    groups = {group_key(c): c for c in full['comparisons']}
    require(len(groups) == 5, 'Duplicate comparison group')
    original_by_id = {r['id']: r for r in original_rows}
    group_ids = {}
    for c in identities['comparisons']:
        members = [original_by_id[x] for x in c['expected_participants']]
        require(len(members) == 2 and {r['robot'] for r in members} == {'rp1', 'g1'}
                and all(r['scope'] == 'aggregate' for r in members), 'Invalid original aggregate participants')
        g = group_key(members[0])
        require(g == group_key(members[1]) and g not in group_ids and g in groups,
                'Original aggregate group cannot be joined')
        group_ids[g] = c
    require(set(group_ids) == set(groups), 'Missing original comparison identity')
    units = {name: full['metric_definitions'][name]['unit'] for name in FULL4}
    require(units == {name: 'mm' if name.endswith('_mm') else 'rad' for name in FULL4},
            'Full-window units differ')
    results = []
    for identity in original_rows:
        row = {name: deepcopy(identity[name]) for name in IDENTITY_FIELDS}
        row['provenance'] = provenance(identity)
        g = group_key(identity)
        source_group = groups[g]
        n = source_group['n_unique_motions']
        row['completion'] = deepcopy(PENDING)
        row['pairing'] = {'comparison_id': group_ids[g]['id'],
                          'sample_set_sha256': source_group['sample_set_sha256'], 'case_id': None}
        if identity['scope'] == 'per_motion':
            source = episodes[episode_key(identity)]
            row['seed'] = seed(identity['seed'])
            row['matched_seed_set'] = [row['seed']]
            row['coverage'] = {'numerator': 1, 'denominator': 1, 'unit': 'episodes'}
            row['metrics'] = {name: metric_cell(source[name], units[name], None, 1) for name in FULL4}
            row['fullwindow'] = {'run_id': source['run_id'],
                'case_id': source['scientific_selected_case_id'], 'metric_window': WINDOW,
                'full_recorded_frames': source['full_recorded_frames'],
                'reference_common_frames': source['reference_common_frames'],
                'reference_start_s': source['full_reference_start_s'],
                'reference_end_s': source['full_reference_end_s']}
            row['pairing']['case_id'] = source['scientific_selected_case_id']
        else:
            row['seed'] = None
            row['matched_seed_set'] = deepcopy(source_group['matched_seed_set'])
            row['coverage'] = {'numerator': n, 'denominator': n, 'unit': 'motions'}
            row['metrics'] = {name: metric_cell(source_group['robot_means'][name][row['robot']]['value'],
                units[name], source_group['robot_means'][name][row['robot']]['ci95'], n) for name in FULL4}
        results.append(row)
    require(provenance_digest(results) == PROVENANCE_SHA, 'Frozen scientific provenance differs')
    comparisons = []
    for source_group in full['comparisons']:
        g = group_key(source_group)
        identity = group_ids[g]
        comparison = {name: deepcopy(source_group[name]) for name in
            ('phase', 'dataset', 'condition', 'mode', 'role', 'metric_window', 'n_unique_motions',
             'paired_cases', 'episode_records', 'matched_seed_set', 'expected_paired_motions',
             'sample_set', 'sample_set_sha256', 'paired_deltas', 'paired_motion_values')}
        comparison.update(id=identity['id'], label=identity['label'],
                          expected_participants=deepcopy(identity['expected_participants']),
                          fullwindow_comparison_id=source_group['id'], completion=deepcopy(PENDING))
        require(set(comparison['paired_deltas']) == set(comparison['paired_motion_values']) == set(FULL4),
                'Unreviewed comparison metric')
        comparisons.append(comparison)
    return {'schema_version': 3, 'publication_state': PUBLIC_STATE if publication else PREVIEW_STATE,
        'fullwindow_source_sha256': FULL_SOURCE_SHA, 'identity_map_sha256': IDENTITY_SHA,
        'counts': deepcopy(COUNTS),
        'metrics': {name: {'unit': units[name], 'label': full['metric_definitions'][name]['label'],
                           'higher_is_better': False} for name in FULL4},
        'results': results, 'comparisons': comparisons,
        'datasets': [{'id': 'lafan40', 'label': 'LAFAN40', 'expected_motions': 40},
                     {'id': 'extreme5', 'label': 'Extreme5', 'expected_motions': 5}],
        'phase': 'A',
        'primary_comparison_ids': [c['id'] for c in comparisons if c['role'] == 'primary'],
        'secondary_comparison_ids': [c['id'] for c in comparisons if c['role'] == 'secondary'],
        'methods': {'fullwindow': '全部50 Hz首次物理子步误差样本，motion_t=1..Ncommon−1；frame0为初始化，200 Hz末端hold不额外评分。',
                    'units': '位置误差已为mm，姿态误差为rad；数值直接显示。',
                    'weighting': full['methods']['weighting'], 'bootstrap': deepcopy(full['methods']['bootstrap'])},
        'completion_contract': deepcopy(COMPLETION_CONTRACT),
        'report_downloads': [], 'fairness': [], 'stats': {}}


def completion_columns(completion):
    bounds = completion['ci95']
    return {'completion_status': completion['status'], 'motion_completed': completion['completed'],
            'motion_completion_pct': completion['rate_pct'],
            'completion_ci95_low': bounds[0] if bounds else None,
            'completion_ci95_high': bounds[1] if bounds else None, 'completion_reason': completion['reason']}


def csv_records(data, scope):
    comparisons = {c['id']: c for c in data['comparisons']}
    records = []
    for row in data['results']:
        if row['scope'] != scope:
            continue
        record = {k: row[k] for k in ('id', 'label', 'phase', 'dataset', 'condition', 'mode', 'robot', 'scope')}
        record.update(row['provenance'])
        record.update(comparison_id=row['pairing']['comparison_id'], sample_set_sha256=row['pairing']['sample_set_sha256'],
                      metric_window=WINDOW)
        if scope == 'per_motion':
            record.update(motion_id=row['motion_id'], seed=row['seed'])
            record.update({k: row['fullwindow'][k] for k in ('run_id', 'case_id', 'full_recorded_frames',
                          'reference_common_frames', 'reference_start_s', 'reference_end_s')})
            record.update({name: row['metrics'][name]['value'] for name in FULL4})
        else:
            comparison = comparisons[row['pairing']['comparison_id']]
            record.update(matched_seed_set='|'.join(map(str, row['matched_seed_set'])),
                          n_unique_motions=comparison['n_unique_motions'], paired_cases=comparison['paired_cases'])
            for name in FULL4:
                cell = row['metrics'][name]
                record.update({name: cell['value'], name + '_ci95_low': cell['ci95'][0],
                               name + '_ci95_high': cell['ci95'][1]})
        record.update(completion_columns(row['completion']))
        records.append(record)
    return records


def csv_bytes(data, scope):
    handle = io.StringIO(newline='')
    columns = EPISODE_COLUMNS if scope == 'per_motion' else COMPARISON_COLUMNS
    writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\r\n')
    writer.writeheader()
    writer.writerows(csv_records(data, scope))
    return handle.getvalue().encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fullwindow-source', type=Path, required=True)
    parser.add_argument('--identity-map', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--publication', action='store_true',
                        help='stage the publishable four-error contract with completion still pending/null')
    args = parser.parse_args()
    raw = args.fullwindow_source.read_bytes()
    identity_raw = args.identity_map.read_bytes()
    require(sha(raw) == FULL_SOURCE_SHA and sha(identity_raw) == IDENTITY_SHA, 'Unreviewed input identity')
    dest = args.output_dir.resolve()
    require('.private' in dest.parts or dest.is_relative_to(Path(tempfile.gettempdir()).resolve()),
            'Generate only in a private staging or temporary directory')
    data = project(read_json(args.fullwindow_source), read_json(args.identity_map), args.publication)
    outputs = {'data.json': (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode(),
               'episodes.csv': csv_bytes(data, 'per_motion'), 'comparisons.csv': csv_bytes(data, 'aggregate')}
    require(args.fullwindow_source.read_bytes() == raw and args.identity_map.read_bytes() == identity_raw,
            'Input changed during projection')
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (dest / name).write_bytes(content)
    print(json.dumps({'schema_version': 3, 'publication_contract_eligible': args.publication,
        'completion_ready': False, 'publication_state': data['publication_state'], 'counts': COUNTS,
        'files': {name: {'bytes': len(content), 'sha256': sha(content)} for name, content in outputs.items()}},
        ensure_ascii=False))


if __name__ == '__main__':
    main()
