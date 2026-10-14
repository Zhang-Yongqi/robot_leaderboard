#!/usr/bin/env python3
"""Build reviewed full-window staging with semantic completion and optional ROOT2.

Inputs are read only. Only explicit identity and full-window fields are selected.
Each result retains only four frozen provenance hashes; absent hashes are null.
Four frozen errors may be published with honest pending/null completion. New
Frozen completion is selected only from the separately SHA-bound public package.
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
from source_contract import (prepare_schema5, reviewed_root_adapter, framework_status,
    ROOT_METRICS, ROOTWINDOW_FIELDS, ROOT_WINDOW)

FULL_SOURCE_SHA = '119d981f07983b060b038e860ac0da9b2d5c10c166fc637b83d179cbf6bda5dd'
IDENTITY_SHA = 'd7c902304aba5ca0588275b4b366f7bb799ee6e5a243c1bc8866ad059fb12aa4'
COMPLETION_SOURCE_SHA = '8607a1403d9fbc846a741cb141cd65b07ce7805c7fb0df11cf1f22ecb119905f'
COMPLETION_CSV_SHA = '7c818403e107c380e9fdccddaf4214fce789df9a9a92ea49d40d322d102d038b'
CRITERION_ID = 'fall_recovery_terminal_tracking_v2'
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
COMPLETION_PUBLIC_STATE = 'fullwindow_semantic_completion_published'
COMPLETION_PREVIEW_STATE = 'internal_preview_semantic_completion'
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
COMPLETION_ROW_FIELDS = ('status', 'completed', 'rate_pct', 'ci95', 'reason', 'evidence_level',
    'reason_code', 'failure_reference_time_s', 'failure_physics_time_s', 'summary')
COMPLETION_DEFINITION_FIELDS = ('label', 'criterion_id', 'definition', 'statuses', 'evidence_levels',
    'reason_codes', 'recovered_midmotion_falls_can_complete', 'precision_errors_do_not_define_completion',
    'point_rate_when_unknown')
COMPLETION_GROUP_FIELDS = ('aggregation_rule', 'ratio_unit', 'display_unit', 'range_type',
    'completion_CI_created', 'interpretation', 'robots')
COMPLETION_SUMMARY_FIELDS = ('seed_counts', 'motion_completion_equivalents', 'expected_motion_denominator',
    'expected_seeds_per_motion', 'effective_adjudicated_motions', 'n_unknown_motions',
    'integer_completed_motions', 'completion_rate', 'possible_rate_bounds', 'completion_percent',
    'possible_percent_bounds', 'completion_summary_label', 'completion_CI_created', 'per_motion_rates')
COMPLETION_MOTION_FIELDS = ('motion_id', 'seed_counts', 'expected_seed_denominator', 'completion_fraction',
    'possible_fraction_bounds', 'completion_percent', 'possible_percent_bounds')
COMPLETION_EPISODE_FIELDS = ('phase', 'dataset', 'condition', 'mode', 'robot', 'motion_id', 'seed',
    'effective_condition', 'scope', 'run_id', 'scientific_selected_case_id', 'metric_window', *FULL4,
    'completion_status', 'completion_evidence_level', 'completion_reason_code',
    'completion_failure_reference_time_s', 'completion_failure_physics_time_s')
COMPLETION_COLUMNS_V4 = ['completion_status', 'motion_completed', 'motion_completion_pct',
    'completion_reason', 'completion_evidence_level', 'completion_reason_code',
    'completion_failure_reference_time_s', 'completion_failure_physics_time_s']
EPISODE_COLUMNS_V4 = EPISODE_COLUMNS[:-6] + COMPLETION_COLUMNS_V4
COMPARISON_COLUMNS_V4 = COMPARISON_COLUMNS[:-6] + COMPLETION_COLUMNS_V4 + [
    'completion_possible_fraction_low', 'completion_possible_fraction_high',
    'completion_possible_pct_low', 'completion_possible_pct_high', 'completion_summary_json']
ROOTWINDOW_COLUMNS = ['root_' + field for field in ROOTWINDOW_FIELDS]
EPISODE_COLUMNS_V5 = EPISODE_COLUMNS[:-6] + list(ROOT_METRICS) + ROOTWINDOW_COLUMNS + COMPLETION_COLUMNS_V4
COMPARISON_COLUMNS_V5 = COMPARISON_COLUMNS[:-6] + [field for metric in ROOT_METRICS for field in
    (metric, metric + '_ci95_low', metric + '_ci95_high')] + ['root_metric_window'] + COMPLETION_COLUMNS_V4 + [
    'completion_possible_fraction_low', 'completion_possible_fraction_high',
    'completion_possible_pct_low', 'completion_possible_pct_high', 'completion_summary_json']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_json(raw):
    """Parse the bytes whose identity was checked, rejecting ambiguous JSON."""
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, 'Duplicate JSON key')
            obj[key] = value
        return obj
    def invalid(value):
        raise ValueError('Non-finite JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=invalid)


def read_json(path):
    return parse_json(Path(path).read_bytes())


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


def project(full, identities, publication=False, completion=None):
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
    data = {'schema_version': 3, 'publication_state': PUBLIC_STATE if publication else PREVIEW_STATE,
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
        'report_downloads': [
            {'label': 'V7 技术报告正文', 'url': 'https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb', 'access': '需飞书组织权限'},
            {'label': 'V7 全程报告 PDF', 'url': 'https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7', 'access': '需飞书组织权限'},
            {'label': 'V7 全程报告 DOCX', 'url': 'https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce', 'access': '需飞书组织权限'}],
        'fairness': [], 'stats': {'report_status': 'V7 已同步：RP1与G1全程跟踪精度与动作完成率，正文、PDF 和 DOCX 已更新至原地址。'}}
    if completion is not None:
        apply_completion(data, full, completion, publication)
    return data


def exact_keys(obj, fields, location):
    require(type(obj) is dict and set(obj) == set(fields), location + ': fields differ')


def read_completion(path):
    path = Path(path)
    csv_path = path.with_name('public_completion_episodes.csv')
    raw, csv_raw = path.read_bytes(), csv_path.read_bytes()
    require(sha(raw) == COMPLETION_SOURCE_SHA and sha(csv_raw) == COMPLETION_CSV_SHA,
            'Unreviewed public completion JSON/CSV identity')
    obj = parse_json(raw)
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=COMPLETION_EPISODE_FIELDS, lineterminator='\r\n')
    writer.writeheader()
    writer.writerows(obj['episodes'])
    require(csv_raw == handle.getvalue().encode(), 'Completion source CSV is not its exact JSON episode export')
    require(path.read_bytes() == raw and csv_path.read_bytes() == csv_raw, 'Completion input changed during read')
    return obj


def apply_completion(data, full, completion, publication):
    exact_keys(completion, ('schema', 'status', 'metric_window', 'counts', 'episode_semantic_join_key',
        'episodes', 'comparisons', 'primary_comparison_ids', 'secondary_comparison_ids', 'metric_definitions',
        'completion_definition', 'methods'), 'Completion source')
    require(completion['schema'] == 'rp1-g1-public-fullwindow-semantic-completion-v2' and
            completion['status'] == 'independently_verified' and completion['metric_window'] == WINDOW and
            completion['episode_semantic_join_key'] == list(JOIN), 'Completion schema/window/join differs')
    require(completion['counts'] == {'physical_episode_records': 180, 'paired_cases': 90,
        'unique_motion_ids': 45, 'comparison_groups': 5, 'aggregate_views': 10,
        'maximum_display_rows_with_aggregate_views': 190, 'lafan40_episode_records': 170,
        'lafan40_paired_cases': 85, 'extreme5_episode_records': 10, 'extreme5_paired_cases': 5},
        'Completion source counts differ')
    definition = completion['completion_definition']
    exact_keys(definition, COMPLETION_DEFINITION_FIELDS, 'Completion definition')
    require(definition['criterion_id'] == CRITERION_ID and
            definition['recovered_midmotion_falls_can_complete'] is True and
            definition['precision_errors_do_not_define_completion'] is True, 'Completion criterion differs')
    require(set(completion['metric_definitions']) == set(FULL4) and
            all(completion['metric_definitions'][name] == full['metric_definitions'][name] for name in FULL4),
            'Completion source changed full-window metric definitions')
    episodes = {}
    full_episodes = {episode_key(row): row for row in full['episodes']}
    for row in completion['episodes']:
        exact_keys(row, COMPLETION_EPISODE_FIELDS, 'Completion episode')
        require(type(row['seed']) is int and row['seed'] >= 0 and row['scope'] == 'per_motion' and
                row['effective_condition'] == row['condition'] and row['metric_window'] == WINDOW,
                'Completion episode seed/condition/window differs')
        key = episode_key(row)
        require(key not in episodes and key in full_episodes, 'Duplicate/unmatched completion episode')
        original = full_episodes[key]
        require(all(row[name] == original[name] for name in (*FULL4, 'run_id', 'scientific_selected_case_id')),
                'Completion source changed full-window values or aliases')
        episodes[key] = row
    require(set(episodes) == set(full_episodes) and len(episodes) == 180, 'Completion episode population differs')
    groups = {}
    original_groups = {group_key(row): row for row in full['comparisons']}
    for group in completion['comparisons']:
        key = group_key(group)
        require(key not in groups and key in original_groups, 'Duplicate/unmatched completion group')
        original = original_groups[key]
        exact_keys(group, ('id', 'phase', 'dataset', 'condition', 'effective_condition', 'mode', 'role',
            'metric_window', 'n_unique_motions', 'paired_cases', 'episode_records', 'matched_seed_set',
            'expected_participants', 'expected_paired_motions', 'sample_set', 'sample_set_sha256',
            'robot_means', 'paired_deltas', 'paired_motion_values', 'completion'), 'Completion group')
        require(group['effective_condition'] == group['condition'] and all(group[name] == original[name] for name in
            ('id', 'phase', 'dataset', 'condition', 'mode', 'role', 'metric_window', 'n_unique_motions',
             'paired_cases', 'episode_records', 'matched_seed_set', 'expected_participants', 'expected_paired_motions',
             'sample_set', 'sample_set_sha256', 'robot_means', 'paired_deltas', 'paired_motion_values')),
             'Completion source changed frozen group values, CI, seeds or sample identity')
        exact_keys(group['completion'], COMPLETION_GROUP_FIELDS, 'Group completion')
        exact_keys(group['completion']['robots'], ('rp1', 'g1'), 'Completion robots')
        for summary in group['completion']['robots'].values():
            exact_keys(summary, COMPLETION_SUMMARY_FIELDS, 'Completion summary')
            for motion in summary['per_motion_rates']:
                exact_keys(motion, COMPLETION_MOTION_FIELDS, 'Completion motion')
        groups[key] = group
    require(set(groups) == set(original_groups) and len(groups) == 5, 'Completion group population differs')
    for field in ('primary_comparison_ids', 'secondary_comparison_ids'):
        require(completion[field] == full[field], 'Completion comparison role index differs')
    for row in data['results']:
        obj = dict.fromkeys(COMPLETION_ROW_FIELDS)
        if row['scope'] == 'per_motion':
            source = episodes[episode_key(row)]
            row['metrics'] = {name: metric_cell(source[name], data['metrics'][name]['unit'], None, 1)
                              for name in FULL4}
            status = source['completion_status']
            require(status in ('completed', 'not_completed', 'unknown'), 'Unreviewed completion status')
            obj.update(status=status, completed={'completed': True, 'not_completed': False, 'unknown': None}[status],
                reason=definition['reason_codes'][source['completion_reason_code']],
                evidence_level=source['completion_evidence_level'], reason_code=source['completion_reason_code'],
                failure_reference_time_s=source['completion_failure_reference_time_s'],
                failure_physics_time_s=source['completion_failure_physics_time_s'])
        else:
            group = groups[group_key(row)]
            summary = group['completion']['robots'][row['robot']]
            row['metrics'] = {name: metric_cell(group['robot_means'][name][row['robot']]['value'],
                data['metrics'][name]['unit'], group['robot_means'][name][row['robot']]['ci95'],
                group['n_unique_motions']) for name in FULL4}
            obj.update(status='summarized', rate_pct=summary['completion_percent'],
                       reason=summary['completion_summary_label'], summary=deepcopy(summary))
        row['completion'] = obj
    for comparison in data['comparisons']:
        group = groups[group_key(comparison)]
        for field in ('phase', 'dataset', 'condition', 'mode', 'role', 'metric_window', 'n_unique_motions',
                      'paired_cases', 'episode_records', 'matched_seed_set', 'expected_paired_motions',
                      'sample_set', 'sample_set_sha256', 'paired_deltas', 'paired_motion_values', 'completion'):
            comparison[field] = deepcopy(group[field])
    data.update(schema_version=4, publication_state=COMPLETION_PUBLIC_STATE if publication else COMPLETION_PREVIEW_STATE,
                fullwindow_source_sha256=COMPLETION_SOURCE_SHA,
                completion_contract={'status': 'verified', 'rule_version': definition['criterion_id'],
                                     'source_sha256': COMPLETION_SOURCE_SHA})
    for field in ('fullwindow', 'weighting', 'bootstrap'):
        data['methods'][field] = deepcopy(completion['methods'][field])
    data['methods']['completion'] = deepcopy(definition)


def completion_digest(data):
    obj = {'definition': data['methods']['completion'], 'contract': data['completion_contract'],
           'results': [{'id': row['id'], 'completion': row['completion']}
                       for row in sorted(data['results'], key=lambda row: row['id'])],
           'comparisons': [{'id': row['id'], 'completion': row['completion']}
                           for row in sorted(data['comparisons'], key=lambda row: row['id'])]}
    return sha(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def completion_columns(completion):
    bounds = completion['ci95']
    return {'completion_status': completion['status'], 'motion_completed': completion['completed'],
            'motion_completion_pct': completion['rate_pct'],
            'completion_ci95_low': bounds[0] if bounds else None,
            'completion_ci95_high': bounds[1] if bounds else None, 'completion_reason': completion['reason']}


def csv_columns(data, scope):
    if data['schema_version'] == 5:
        return EPISODE_COLUMNS_V5 if scope == 'per_motion' else COMPARISON_COLUMNS_V5
    if data['schema_version'] == 4:
        return EPISODE_COLUMNS_V4 if scope == 'per_motion' else COMPARISON_COLUMNS_V4
    return EPISODE_COLUMNS if scope == 'per_motion' else COMPARISON_COLUMNS


def csv_records(data, scope):
    comparisons = {c['id']: c for c in data['comparisons']}
    metrics = FULL4 + ROOT_METRICS if data['schema_version'] == 5 else FULL4
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
            record.update({name: row['metrics'][name]['value'] for name in metrics})
            if data['schema_version'] == 5:
                record.update({'root_' + key: row['rootwindow'][key] for key in ROOTWINDOW_FIELDS})
        else:
            comparison = comparisons[row['pairing']['comparison_id']]
            record.update(matched_seed_set='|'.join(map(str, row['matched_seed_set'])),
                          n_unique_motions=comparison['n_unique_motions'], paired_cases=comparison['paired_cases'])
            for name in metrics:
                cell = row['metrics'][name]
                record.update({name: cell['value'], name + '_ci95_low': cell['ci95'][0],
                               name + '_ci95_high': cell['ci95'][1]})
            if data['schema_version'] == 5:
                record['root_metric_window'] = ROOT_WINDOW
        if data['schema_version'] in (4, 5):
            obj = row['completion']
            record.update(completion_status=obj['status'], motion_completed=(json.dumps(obj['completed'])
                if obj['completed'] is not None else None),
                motion_completion_pct=obj['rate_pct'], completion_reason=obj['reason'],
                completion_evidence_level=obj['evidence_level'], completion_reason_code=obj['reason_code'],
                completion_failure_reference_time_s=obj['failure_reference_time_s'],
                completion_failure_physics_time_s=obj['failure_physics_time_s'])
            if scope == 'aggregate':
                summary = obj['summary']
                record.update(completion_possible_fraction_low=summary['possible_rate_bounds'][0],
                    completion_possible_fraction_high=summary['possible_rate_bounds'][1],
                    completion_possible_pct_low=summary['possible_percent_bounds'][0],
                    completion_possible_pct_high=summary['possible_percent_bounds'][1],
                    completion_summary_json=json.dumps(summary, ensure_ascii=False, sort_keys=True,
                                                       separators=(',', ':'), allow_nan=False))
        else:
            record.update(completion_columns(row['completion']))
        records.append(record)
    return records


def csv_bytes(data, scope):
    handle = io.StringIO(newline='')
    columns = csv_columns(data, scope)
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
                        help='stage the publication state for the selected reviewed contract')
    parser.add_argument('--source-completion', type=Path,
                        help='optional frozen public completion JSON with its sibling public episode CSV')
    parser.add_argument('--source-root', type=Path,
                        help='reviewed six-error public JSON with its SHA-bound sibling public episode CSV')
    parser.add_argument('--root-adapter', help='code-registered reviewed root adapter ID; no arbitrary module loading')
    args = parser.parse_args()
    require(not args.root_adapter or args.source_root, '--root-adapter requires --source-root')
    if args.source_root:
        require(args.source_completion is not None, '--source-root requires the frozen schema-4 completion input')
        reviewed_root_adapter(args.root_adapter)
    raw = args.fullwindow_source.read_bytes()
    identity_raw = args.identity_map.read_bytes()
    require(sha(raw) == FULL_SOURCE_SHA and sha(identity_raw) == IDENTITY_SHA, 'Unreviewed input identity')
    dest = args.output_dir.resolve()
    require('.private' in dest.parts or dest.is_relative_to(Path(tempfile.gettempdir()).resolve()),
            'Generate only in a private staging or temporary directory')
    completion = read_completion(args.source_completion) if args.source_completion else None
    data = project(parse_json(raw), parse_json(identity_raw), args.publication, completion)
    if args.source_root:
        data = prepare_schema5(data, args.source_root, args.root_adapter, args.publication)
    outputs = {'data.json': (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode(),
               'episodes.csv': csv_bytes(data, 'per_motion'), 'comparisons.csv': csv_bytes(data, 'aggregate')}
    require(args.fullwindow_source.read_bytes() == raw and args.identity_map.read_bytes() == identity_raw,
            'Input changed during projection')
    if args.source_completion:
        require(read_completion(args.source_completion) == completion, 'Completion input changed during projection')
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (dest / name).write_bytes(content)
    print(json.dumps({'schema_version': data['schema_version'], 'publication_contract_eligible': args.publication,
        'completion_ready': data['schema_version'] in (4, 5), 'publication_state': data['publication_state'], 'counts': COUNTS,
        'files': {name: {'bytes': len(content), 'sha256': sha(content)} for name, content in outputs.items()},
        'framework': framework_status()},
        ensure_ascii=False))


if __name__ == '__main__':
    main()
