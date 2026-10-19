#!/usr/bin/env python3
"""Audit reviewed full-window v3/v4, six-error v5 and endpoint v6 contracts.

--preview permits internal pending/null completion inspection. It never enables
publication. The full four-error contract may be published independently; new
completion values need a separate reviewed contract. Private inputs bind values.
Four provenance fields are exactly bound to frozen original row identities.
"""
import argparse
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit
from source_contract import (protect_baseline, framework_status, reviewed_root_adapter, prepare_schema5,
    ROOT_METRICS, ROOT_SOURCE_SHA, ROOT_CSV_SHA, ROOT_WINDOW, ROOT_WINDOW_LABEL,
    ROOT_PUBLIC_STATE, ROOT_PREVIEW_STATE, ROOT_METHOD_FIELDS, ROOTWINDOW_FIELDS, rootwindow_from_baseline,
    reviewed_endpoint_adapter, prepare_schema6, protect_schema5, ENDPOINT_METRIC, ENDPOINT_METRICS,
    ENDPOINT_SOURCE_SHA, ENDPOINT_CSV_SHA, ENDPOINT_WINDOW, ENDPOINT_PUBLIC_STATE, ENDPOINT_PREVIEW_STATE,
    ENDPOINT_METHOD_FIELDS, ENDPOINT_DEFINITION_FIELDS, SIX_CORE_SHA, schema5_digest)
from update_snapshot import (COMPLETION_CONTRACT, COMPARISON_COLUMNS, COUNTS,
    EPISODE_COLUMNS, FULL4, FULL_SOURCE_SHA, IDENTITY_SHA, PENDING, PREVIEW_STATE, PUBLIC_STATE,
    PROVENANCE_FIELDS, PROVENANCE_SHA, WINDOW, csv_bytes, episode_key, group_key,
    project, provenance_digest, read_json, parse_json, seed, sha, csv_columns, completion_digest, read_completion,
    COMPLETION_SOURCE_SHA, COMPLETION_CSV_SHA, CRITERION_ID, COMPLETION_PUBLIC_STATE,
    COMPLETION_PREVIEW_STATE, COMPLETION_ROW_FIELDS, COMPLETION_DEFINITION_FIELDS,
    COMPLETION_GROUP_FIELDS, COMPLETION_SUMMARY_FIELDS, COMPLETION_MOTION_FIELDS)
COMPLETION_PROJECTION_SHA = '1f60098e6bf38fece043474847d55936ff4aad0a6d576a7b728cfe6a42d9639b'

PUBLISH_FILES_V4 = {'.gitignore', '.nojekyll', 'README.md', 'DATA_PROVENANCE.md',
    'RELEASE_MANIFEST.json', 'index.html', 'app.js', 'style.css', 'data.json', 'media.json',
    'favicon.svg', 'hardware.json', 'hardware.csv', 'episodes.csv', 'comparisons.csv',
    'scripts/update_snapshot.py', 'scripts/verify_public.py'}
PUBLISH_FILES = PUBLISH_FILES_V4 | {'scripts/source_contract.py', 'i18n.js', 'i18n-ui.js', 'i18n-data.js', 'layout.js'}
PUBLISH_FILES_V5 = PUBLISH_FILES
DATA_FILES = {'data.json', 'episodes.csv', 'comparisons.csv'}
EXCLUDED_DIRS = {'.git', '.private', '.agents', '.aws', '.codex', 'qa', '__pycache__'}
HARDWARE_SHA = {'hardware.json': '5815d8d7e1a28305124849990dc682c85f6e6eb49b7bc78a91ae9adfa270a6af',
                'hardware.csv': '78972776c7640ec62e03bffda14caf0fb530a170ca3751109e66a79ac57614de'}
HOSTS = {'github.com', 'raw.githubusercontent.com', 'huggingface.co', 'roboparty.feishu.cn',
         'egalahad.github.io', 'zhang-yongqi.github.io', 'drive.google.com'}
SECRET = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|'
    r'AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,})\b|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|'
    r'\bssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/]{30,}')
LOCAL_PATH = re.compile(r'(?:^|[\s"\x27(=:])/(?:home|Users|root|mnt|tmp|srv|var)/|'
                       r'\b[A-Za-z]:[\\/]|\b(?:file|ssh)://', re.I)
INFRA = re.compile(r'\b(?:candidate_host|candidate_ssh|watchdog_pid|ssh_host|ssh_port|ssh_key|'
                   r'hostname|server_ip|process_id|source_status)\b|\b(?:PID|pid)\s*[:=]\s*\d+', re.I)
HASH = re.compile(r'[0-9a-f]{64}\Z')
IP_LITERAL = re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
TOP_KEYS = {'schema_version', 'publication_state', 'fullwindow_source_sha256', 'identity_map_sha256',
    'counts', 'metrics', 'results', 'comparisons', 'datasets', 'phase', 'primary_comparison_ids',
    'secondary_comparison_ids', 'methods', 'completion_contract', 'report_downloads', 'fairness', 'stats'}
ROW_KEYS = {'id', 'label', 'phase', 'dataset', 'condition', 'mode', 'robot', 'motion_id', 'seed', 'scope',
    'matched_seed_set', 'metrics', 'completion', 'coverage', 'pairing', 'provenance'}
FULLWINDOW_KEYS = {'run_id', 'case_id', 'metric_window', 'full_recorded_frames',
                  'reference_common_frames', 'reference_start_s', 'reference_end_s'}
COMPARISON_KEYS = {'id', 'label', 'phase', 'dataset', 'condition', 'mode', 'role', 'metric_window',
    'n_unique_motions', 'paired_cases', 'episode_records', 'matched_seed_set', 'expected_participants',
    'expected_paired_motions', 'sample_set', 'sample_set_sha256', 'paired_deltas', 'paired_motion_values',
    'completion', 'fullwindow_comparison_id'}
COHORTS = {('lafan40', 'nominal', 'native_position'): (40, 40, [0], 'primary'),
    ('extreme5', 'nominal', 'native_position'): (5, 5, [0], 'primary'),
    ('lafan40', 'repeat_nominal', 'native_position'): (15, 5, [0, 1, 42], 'secondary'),
    ('lafan40', 'robust_initial_velocity', 'native_position'): (25, 5, [0, 1, 2, 3, 4], 'secondary'),
    ('lafan40', 'explicit_sensitivity', 'explicit_deploy'): (5, 5, [0], 'secondary')}
BOOTSTRAP = {'resampling_unit': 'paired_motion', 'generator': 'PCG64', 'seed': 20261013,
    'resamples': 10000, 'confidence': 0.95, 'quantile_method': 'linear',
    'reset_per_group_and_metric': True, 'shared_indices_for_robots': True, 'delta_direction': 'RP1 minus G1'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exact_keys(obj, names, location):
    require(type(obj) is dict and set(obj) == set(names), location + ': public fields differ')


def same_json(left, right):
    """Preserve source numeric/boolean types; Python equality equates True and 1."""
    return json.dumps(left, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) == \
           json.dumps(right, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def number(value, location):
    require(type(value) in (int, float) and math.isfinite(value), location + ': expected finite number')


def bounds(values, location):
    require(type(values) is list and len(values) == 2, location + ': expected two interval bounds')
    for value in values:
        number(value, location)
    require(values[0] <= values[1], location + ': interval reversed')


def pending(obj):
    require(obj == PENDING, 'Completion remains pending/null until the reviewed label contract arrives')


def walk(obj):
    yield obj
    if type(obj) is dict:
        for value in obj.values():
            yield from walk(value)
    elif type(obj) is list:
        for value in obj:
            yield from walk(value)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {'href', 'src', 'poster'} and value:
                self.links.append(value)
            if name == 'id' and value:
                self.ids.add(value)


class Audit:
    def __init__(self, root, preview=False, source=None, identities=None, completion=None,
                 source_root=None, root_adapter=None, source_endpoint=None, endpoint_adapter=None):
        self.root = Path(root).resolve()
        self.preview = preview
        self.source = source
        self.identities = identities
        self.completion_source = completion
        self.root_source, self.root_adapter = source_root, root_adapter
        self.data = read_json(self.root / 'data.json')
        self.endpoint_source, self.endpoint_adapter = source_endpoint, endpoint_adapter
        if source_endpoint is not None or self.data.get('schema_version') == 6:
            reviewed_endpoint_adapter(endpoint_adapter)
        self.has_endpoint = self.data.get('schema_version') == 6
        self.has_root = self.data.get('schema_version') in (5, 6)
        self.metrics = FULL4 + ROOT_METRICS + ENDPOINT_METRICS if self.has_endpoint else (
                       FULL4 + ROOT_METRICS if self.has_root else FULL4)
        self.publish_files = PUBLISH_FILES if self.has_root else PUBLISH_FILES_V4
        self.root_source_verified = False
        self.endpoint_source_verified = False
        self.checked, self.errors = [], []
        self.value_checks = {'episode_values': 0, 'aggregate_scalars': 0, 'paired_delta_scalars': 0}
        self.root_value_checks = {'episode_values': 0, 'aggregate_scalars': 0, 'paired_delta_scalars': 0}
        self.endpoint_value_checks = {'episode_values': 0, 'aggregate_scalars': 0, 'paired_delta_scalars': 0}
        self.provenance_checks = {'hash_values': 0, 'null_values': 0, 'source_fields': 0}
        self.completion_checks = {'episode_labels': 0, 'aggregate_summaries': 0, 'motion_summaries': 0}
        self.episodes, self.cases, self.aliases, self.by_id = {}, {}, {}, {}

    def check(self, name, fn):
        try:
            fn()
            self.checked.append(name)
        except (ValueError, TypeError, KeyError, IndexError, OSError, csv.Error) as error:
            self.errors.append(name + ': ' + str(error))

    def schema(self):
        d = self.data
        exact_keys(d, TOP_KEYS | ({'root_extension'} if self.has_root else set()) |
                   ({'endpoint_extension'} if self.has_endpoint else set()), 'data')
        require(type(d['schema_version']) is int and d['schema_version'] in (3, 4, 5, 6) and
                d['phase'] == 'A' and d['counts'] == COUNTS, 'Reviewed schema/physical scope differs')
        semantic = d['schema_version'] in (4, 5, 6)
        expected_state = ((ENDPOINT_PREVIEW_STATE if self.preview else ENDPOINT_PUBLIC_STATE) if self.has_endpoint else
                          (ROOT_PREVIEW_STATE if self.preview else ROOT_PUBLIC_STATE) if self.has_root else
                          (COMPLETION_PREVIEW_STATE if self.preview else COMPLETION_PUBLIC_STATE) if semantic else
                          (PREVIEW_STATE if self.preview else PUBLIC_STATE))
        expected_contract = ({'status': 'verified', 'rule_version': CRITERION_ID,
                              'source_sha256': COMPLETION_SOURCE_SHA} if semantic else COMPLETION_CONTRACT)
        require(d['publication_state'] == expected_state and d['completion_contract'] == expected_contract,
                'Publication state or frozen completion contract differs')
        require(d['fullwindow_source_sha256'] == (COMPLETION_SOURCE_SHA if semantic else FULL_SOURCE_SHA) and
                d['identity_map_sha256'] == IDENTITY_SHA,
                'Reviewed projection source identities differ')
        require(set(d['metrics']) == set(self.metrics), 'Reviewed full-window metric set differs')
        for name, definition in d['metrics'].items():
            exact_keys(definition, {'unit', 'label', 'higher_is_better'}, 'metric definition')
            require(definition['unit'] == ('mm' if name.endswith('_mm') else 'rad')
                    and definition['higher_is_better'] is False, 'Full-window units/direction differ')
        exact_keys(d['methods'], {'fullwindow', 'units', 'weighting', 'bootstrap'} |
                   ({'completion'} if semantic else set()) | ({'root'} if self.has_root else set()) |
                   ({'root_endpoint'} if self.has_endpoint else set()), 'methods')
        if self.has_root:
            require(d['root_extension'] == {'status': 'verified', 'source_sha256': ROOT_SOURCE_SHA,
                'metrics': list(ROOT_METRICS), 'window_label': ROOT_WINDOW_LABEL}, 'Root source extension differs')
            exact_keys(d['methods']['root'], ROOT_METHOD_FIELDS, 'Root full-window method')
            method = d['methods']['root']
            require(method['window'] == ROOT_WINDOW and method['old_four_window_unchanged'] is True and
                method['completion_unchanged'] is True and method['completion_does_not_filter_errors'] is True and
                type(method['new_physical_episodes']) is int and method['new_physical_episodes'] == 0,
                'Independent root window or no-new-experiment preservation differs')
        if self.has_endpoint:
            extension = d['endpoint_extension']
            exact_keys(extension, {'status', 'source_sha256', 'metrics', 'definition'}, 'Endpoint extension')
            require(extension['status'] == 'verified' and extension['source_sha256'] == ENDPOINT_SOURCE_SHA and
                    extension['metrics'] == [ENDPOINT_METRIC], 'Endpoint source identity differs')
            definition = extension['definition']
            exact_keys(definition, ENDPOINT_DEFINITION_FIELDS, 'Endpoint definition')
            require(definition == {'unit': 'mm', 'label': '根部终点位置误差', 'role': 'endpoint_position_error',
                'higher_is_better': False, 'sample_count': 1, 'window': ENDPOINT_WINDOW} and
                type(definition['sample_count']) is int, 'Endpoint definition/single-sample window differs')
            method = d['methods']['root_endpoint']
            exact_keys(method, ENDPOINT_METHOD_FIELDS, 'Endpoint method')
            require(method['window'] == ENDPOINT_WINDOW and type(method['sample_count_per_episode']) is int and
                method['sample_count_per_episode'] == 1 and method['existing_six_errors_and_completion_unchanged'] is True and
                type(method['new_physical_episodes']) is int and method['new_physical_episodes'] == 0,
                'Endpoint method/window/preservation differs')
            require(schema5_digest(d) == SIX_CORE_SHA, 'Preserved six-error scientific digest differs')
        require(d['methods']['bootstrap'] == BOOTSTRAP, 'Paired motion bootstrap protocol differs')
        require(len(d['datasets']) == 2 and {(x['id'], x['expected_motions']) for x in d['datasets']} ==
                {('lafan40', 40), ('extreme5', 5)}, 'Two datasets must remain separate')
        for dataset in d['datasets']:
            require(set(dataset) <= {'id', 'label', 'expected_motions', 'description'}, 'Dataset fields differ')
        require(type(d['fairness']) is list and type(d['report_downloads']) is list and type(d['stats']) is dict,
                'Auxiliary explanations have invalid shape')
        for item in d['fairness']:
            require(type(item) is dict and set(item) <= {'item', 'rp1', 'g1', 'status', 'evidence'},
                    'Fairness explanation fields differ')
        require(set(d['stats']) <= {'report_status', 'updated_utc', 'notes', 'limitations'}, 'Statistics fields differ')

    def rows_and_pairs(self):
        rows = self.data['results']
        require(len(rows) == len({r['id'] for r in rows}) == 190 and
                Counter(r['scope'] for r in rows) == {'per_motion': 180, 'aggregate': 10}, 'Result counts differ')
        episodes, cases, aliases = {}, {}, {}
        for row in rows:
            is_episode = row['scope'] == 'per_motion'
            exact_keys(row, ROW_KEYS | ({'fullwindow'} if is_episode else set()) |
                       ({'rootwindow'} if self.has_root and is_episode else set()), 'result')
            require(row['phase'] == 'A' and row['robot'] in {'rp1', 'g1'} and group_key(row) in COHORTS,
                    'Unreviewed result identity')
            if self.data['schema_version'] == 3:
                pending(row['completion'])
            exact_keys(row['provenance'], PROVENANCE_FIELDS, 'scientific provenance')
            for value in row['provenance'].values():
                require(value is None or (type(value) is str and HASH.fullmatch(value)),
                        'Scientific provenance must be SHA256 or null')
                self.provenance_checks['null_values' if value is None else 'hash_values'] += 1
            exact_keys(row['coverage'], {'numerator', 'denominator', 'unit'}, 'coverage')
            exact_keys(row['pairing'], {'comparison_id', 'sample_set_sha256', 'case_id'}, 'pairing')
            require(HASH.fullmatch(row['pairing']['sample_set_sha256']), 'Malformed paired sample identity')
            require(set(row['metrics']) == set(self.metrics), 'Result contains an unreviewed metric')
            n = 1 if is_episode else COHORTS[group_key(row)][1]
            require(row['coverage'] == {'numerator': n, 'denominator': n,
                    'unit': 'episodes' if is_episode else 'motions'}, 'Coverage unit/denominator differs')
            for name, cell in row['metrics'].items():
                counters = self.endpoint_value_checks if name in ENDPOINT_METRICS else (
                           self.root_value_checks if name in ROOT_METRICS else self.value_checks)
                exact_keys(cell, {'value', 'unit', 'ci95', 'n_motions'}, 'metric cell')
                number(cell['value'], 'full-window value')
                require(cell['value'] >= 0 and cell['unit'] == self.data['metrics'][name]['unit']
                        and cell['n_motions'] == n, 'Full-window value/unit/motion denominator differs')
                if is_episode:
                    require(cell['ci95'] is None, 'Individual episode cannot invent a group interval')
                    counters['episode_values'] += 1
                else:
                    bounds(cell['ci95'], 'aggregate interval')
                    counters['aggregate_scalars'] += 3
            if is_episode:
                require(type(row['seed']) is int and row['seed'] >= 0 and row['matched_seed_set'] == [row['seed']],
                        'Episode seed must remain a strict integer')
                k = episode_key(row)
                require(k not in episodes, 'Duplicate semantic episode identity')
                episodes[k] = row
                case = k[:3] + k[4:]
                members = cases.setdefault(case, {})
                require(row['robot'] not in members, 'Duplicate robot for the same paired case')
                members[row['robot']] = row
                fw = row['fullwindow']
                exact_keys(fw, FULLWINDOW_KEYS, 'episode full-window metadata')
                require(fw['metric_window'] == WINDOW and re.fullmatch(r'[0-9a-f]{24}', fw['run_id'])
                        and fw['run_id'] not in aliases and re.fullmatch(r'case_[0-9a-f]{24}', fw['case_id']),
                        'Source run/case alias differs')
                aliases[fw['run_id']] = row
                require(row['pairing']['case_id'] == fw['case_id'], 'Row/source case alias differs')
                frames = fw['reference_common_frames']
                require(type(frames) is int and frames > 2 and fw['full_recorded_frames'] == frames - 1 and
                        fw['reference_start_s'] == .02 and math.isclose(fw['reference_end_s'],
                        (frames - 1) / 50, rel_tol=0, abs_tol=1e-10), 'Complete 50Hz first-substep window differs')
                if self.has_root:
                    rw = row['rootwindow']
                    exact_keys(rw, ROOTWINDOW_FIELDS, 'Independent root window metadata')
                    require(type(rw['recorded_frames']) is int and rw == rootwindow_from_baseline(row),
                        'Root nominal semantic window differs from valid 1..Ncommon-1 reference contract')
            else:
                require(row['seed'] is None and row['motion_id'] is None and row['pairing']['case_id'] is None
                        and row['matched_seed_set'] == COHORTS[group_key(row)][2], 'Aggregate seed pool differs')
        require(len(episodes) == 180 and len(cases) == 90 and
                len({r['motion_id'] for r in episodes.values()}) == 45 and
                Counter(r['dataset'] for r in episodes.values()) == {'lafan40': 170, 'extreme5': 10},
                'Physical episode/pair/motion scope differs')
        for members in cases.values():
            require(set(members) == {'rp1', 'g1'} and
                    members['rp1']['fullwindow']['case_id'] == members['g1']['fullwindow']['case_id'],
                    'Case must identify both robots')
            require(all(members['rp1']['fullwindow'][field] == members['g1']['fullwindow'][field] for field in
                    ('full_recorded_frames', 'reference_common_frames', 'reference_start_s', 'reference_end_s')),
                    'Paired full replay windows differ')
        require(provenance_digest(rows) == PROVENANCE_SHA, 'Frozen scientific provenance differs')
        require(self.provenance_checks['hash_values'] == 556 and
                self.provenance_checks['null_values'] == 204, 'Scientific hash/null coverage differs')
        self.episodes, self.cases, self.aliases = episodes, cases, aliases
        self.by_id = {row['id']: row for row in rows}

    def comparisons(self):
        comparisons = self.data['comparisons']
        require(len(comparisons) == len({c['id'] for c in comparisons}) == 5,
                'Five unique independent comparisons required')
        seen_cases, seen_groups, participants = set(), set(), set()
        for c in comparisons:
            exact_keys(c, COMPARISON_KEYS, 'comparison')
            g = group_key(c)
            require(g in COHORTS and g not in seen_groups, 'Comparison group duplicated/unreviewed')
            seen_groups.add(g)
            pairs, motions, seeds, role = COHORTS[g]
            require(c['phase'] == 'A' and c['metric_window'] == WINDOW and c['role'] == role
                    and c['paired_cases'] == pairs and c['episode_records'] == pairs * 2
                    and c['n_unique_motions'] == c['expected_paired_motions'] == motions
                    and c['matched_seed_set'] == seeds, 'Comparison coverage/weighting differs')
            if self.data['schema_version'] == 3:
                pending(c['completion'])
            members = [self.by_id[x] for x in c['expected_participants']]
            require(len(members) == 2 and {r['robot'] for r in members} == {'rp1', 'g1'} and
                    all(r['scope'] == 'aggregate' and group_key(r) == g for r in members),
                    'Comparison must retain its two original aggregate participant IDs')
            participants.update(r['id'] for r in members)
            require(all(r['pairing']['comparison_id'] == c['id'] and
                    r['pairing']['sample_set_sha256'] == c['sample_set_sha256'] for r in members),
                    'Aggregate pairing metadata differs')
            require(HASH.fullmatch(c['sample_set_sha256']) and len(c['sample_set']) == pairs and
                    sha(json.dumps(c['sample_set'], ensure_ascii=False, sort_keys=True,
                    separators=(',', ':')).encode()) == c['sample_set_sha256'], 'Paired sample SHA differs')
            for sample in c['sample_set']:
                exact_keys(sample, {'scientific_selected_case_id', 'motion_id', 'seed', 'participants'}, 'sample')
                require(type(sample['seed']) is int and sample['seed'] in seeds, 'Sample seed differs')
                k = g + (sample['motion_id'], sample['seed'])
                require(k in self.cases and k not in seen_cases and set(sample['participants']) == {'rp1', 'g1'},
                        'Paired sample duplicated/missing')
                seen_cases.add(k)
                for robot, alias in sample['participants'].items():
                    row = self.cases[k][robot]
                    require(row['fullwindow']['run_id'] == alias and
                            row['fullwindow']['case_id'] == sample['scientific_selected_case_id'] and
                            row['pairing']['comparison_id'] == c['id'] and
                            row['pairing']['sample_set_sha256'] == c['sample_set_sha256'], 'Sample/run binding differs')
            require(set(c['paired_deltas']) == set(c['paired_motion_values']) == set(self.metrics),
                    'Comparison reviewed error set differs')
            robot_means = {r['robot']: r for r in members}
            for metric in self.metrics:
                delta = c['paired_deltas'][metric]
                exact_keys(delta, {'value', 'ci95', 'unit', 'n_motions'}, 'paired delta')
                number(delta['value'], 'paired value')
                bounds(delta['ci95'], 'paired interval')
                require(delta['unit'] == self.data['metrics'][metric]['unit'] and delta['n_motions'] == motions,
                        'Paired interval units/denominator differ')
                counters = self.endpoint_value_checks if metric in ENDPOINT_METRICS else (
                           self.root_value_checks if metric in ROOT_METRICS else self.value_checks)
                counters['paired_delta_scalars'] += 3
                values = c['paired_motion_values'][metric]
                require(len(values) == len({x['motion_id'] for x in values}) == motions,
                        'Repeated seeds cannot increase motion denominator')
                for value in values:
                    exact_keys(value, {'motion_id', 'rp1', 'g1', 'delta_rp1_minus_g1', 'seeds', 'repeats_per_robot'},
                               'paired motion value')
                    require(value['seeds'] == seeds and value['repeats_per_robot'] == len(seeds),
                            'Matched seed set differs')
                    for robot in ('rp1', 'g1'):
                        expected = math.fsum(self.cases[g + (value['motion_id'], s)][robot]['metrics'][metric]['value']
                                             for s in seeds) / len(seeds)
                        require(math.isclose(value[robot], expected, rel_tol=0, abs_tol=1e-10),
                                'Within-motion mean differs from complete matched seed set')
                    require(math.isclose(value['delta_rp1_minus_g1'], value['rp1'] - value['g1'],
                                         rel_tol=0, abs_tol=1e-10), 'Paired motion delta direction differs')
                for robot in ('rp1', 'g1'):
                    cell = robot_means[robot]['metrics'][metric]
                    require(math.isclose(cell['value'], math.fsum(x[robot] for x in values) / motions,
                                         rel_tol=0, abs_tol=1e-10), 'Aggregate must weight independent motions equally')
                require(math.isclose(delta['value'], robot_means['rp1']['metrics'][metric]['value'] -
                                     robot_means['g1']['metrics'][metric]['value'], rel_tol=0, abs_tol=1e-10),
                        'Paired aggregate delta direction differs')
        require(seen_groups == set(COHORTS) and seen_cases == set(self.cases) and len(participants) == 10,
                'Five groups must partition all 90 cases and ten aggregate views')
        require(set(self.data['primary_comparison_ids']) == {c['id'] for c in comparisons if c['role'] == 'primary'}
                and set(self.data['secondary_comparison_ids']) == {c['id'] for c in comparisons if c['role'] == 'secondary'},
                'Primary/secondary indices differ')

    def exports(self):
        for name, scope, n in [('episodes.csv', 'per_motion', 180), ('comparisons.csv', 'aggregate', 10)]:
            columns = csv_columns(self.data, scope)
            raw = (self.root / name).read_bytes()
            require(raw == csv_bytes(self.data, scope), 'CSV is not the exact canonical reviewed export: ' + name)
            with (self.root / name).open(encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle, strict=True)
                rows = list(reader)
            require(reader.fieldnames == columns and len(rows) == n, 'CSV rows/columns differ')
            if self.data['schema_version'] == 3:
                require(all(row['completion_status'] == 'pending' and all(row[field] == '' for field in
                        ('motion_completed', 'motion_completion_pct', 'completion_ci95_low', 'completion_ci95_high'))
                        for row in rows), 'Pending completion must retain blank numeric/boolean CSV cells')
            else:
                require(not any('completion_ci' in name.lower() for name in columns), 'Completion CSV cannot invent CI')
                if scope == 'per_motion':
                    require(all(row['motion_completion_pct'] == '' and row['motion_completed'] ==
                        {'completed': 'true', 'not_completed': 'false', 'unknown': ''}[row['completion_status']]
                        for row in rows), 'Episode CSV boolean/unknown mapping differs')

    def completions(self):
        if self.data['schema_version'] == 3:
            for obj in self.data['results'] + self.data['comparisons']:
                pending(obj['completion'])
            return
        definition = self.data['methods']['completion']
        exact_keys(definition, COMPLETION_DEFINITION_FIELDS, 'Completion definition')
        require(definition['criterion_id'] == CRITERION_ID and
                definition['recovered_midmotion_falls_can_complete'] is True and
                definition['precision_errors_do_not_define_completion'] is True, 'Completion criterion differs')
        exact_keys(definition['statuses'], ('completed', 'not_completed', 'unknown'), 'Completion states')
        exact_keys(definition['reason_codes'], ('terminal_tracking_complete', 'persistent_fall_unable_to_resume',
                   'unknown_evidence'), 'Completion reasons')
        require(definition['evidence_levels'] == ['verified_geometry_reference_and_valid_endpoint',
                'unknown_insufficient_evidence'], 'Completion evidence levels differ')
        mapping = {'completed': (True, 'terminal_tracking_complete', 'verified_geometry_reference_and_valid_endpoint'),
                   'not_completed': (False, 'persistent_fall_unable_to_resume', 'verified_geometry_reference_and_valid_endpoint'),
                   'unknown': (None, 'unknown_evidence', 'unknown_insufficient_evidence')}
        for row in self.data['results']:
            obj = row['completion']
            exact_keys(obj, COMPLETION_ROW_FIELDS, 'Result semantic completion')
            require(obj['ci95'] is None, 'Completion cannot invent a statistical CI')
            if row['scope'] == 'per_motion':
                require(obj['status'] in mapping, 'Episode completion state differs')
                completed, code, level = mapping[obj['status']]
                require(obj['completed'] is completed and obj['rate_pct'] is None and obj['summary'] is None and
                        obj['reason_code'] == code and obj['evidence_level'] == level and
                        obj['reason'] == definition['reason_codes'][code], 'Episode completion/evidence mapping differs')
                for field in ('failure_reference_time_s', 'failure_physics_time_s'):
                    value = obj[field]
                    if obj['status'] == 'not_completed':
                        number(value, 'Semantic failure time')
                        require(0 <= value <= row['fullwindow']['reference_end_s'], 'Semantic failure time outside reference')
                    else:
                        require(value is None, 'Completed/unknown episode cannot have a failure time')
                self.completion_checks['episode_labels'] += 1
            else:
                require(obj['status'] == 'summarized' and all(obj[field] is None for field in
                    ('completed', 'evidence_level', 'reason_code', 'failure_reference_time_s', 'failure_physics_time_s')),
                    'Aggregate completion cannot be an episode label')
        for comparison in self.data['comparisons']:
            group = comparison['completion']
            exact_keys(group, COMPLETION_GROUP_FIELDS, 'Comparison semantic completion')
            require(group['aggregation_rule'] == 'seed_binary_mean_within_motion_then_equal_motion_mean' and
                    group['ratio_unit'] == 'fraction' and group['display_unit'] == '%' and
                    group['range_type'] == 'unknown_label_logical_bounds_not_statistical_CI' and
                    group['completion_CI_created'] is False, 'Completion weighting/range/CI contract differs')
            exact_keys(group['robots'], ('rp1', 'g1'), 'Completion participants')
            for robot, summary in group['robots'].items():
                self.completion_summary(summary, comparison, robot)
                rows = [self.by_id[name] for name in comparison['expected_participants']
                        if self.by_id[name]['robot'] == robot]
                require(len(rows) == 1, 'Completion aggregate participant differs')
                row = rows[0]
                require(row['completion']['summary'] == summary and
                        row['completion']['rate_pct'] == summary['completion_percent'] and
                        row['completion']['reason'] == summary['completion_summary_label'],
                        'Aggregate/source completion summary differs')
                self.completion_checks['aggregate_summaries'] += 1
        require(completion_digest(self.data) == COMPLETION_PROJECTION_SHA,
                'Completion labels/times/definition/summary differ from frozen public source')

    def completion_summary(self, summary, comparison, robot):
        exact_keys(summary, COMPLETION_SUMMARY_FIELDS, 'Robot completion summary')
        motions = {sample['motion_id'] for sample in comparison['sample_set']}
        n, s = len(motions), len(comparison['matched_seed_set'])
        require(type(summary['expected_motion_denominator']) is int and summary['expected_motion_denominator'] == n and
                type(summary['expected_seeds_per_motion']) is int and summary['expected_seeds_per_motion'] == s and
                summary['completion_CI_created'] is False, 'Completion denominator or CI differs')
        provided = summary['per_motion_rates']
        require(len(provided) == n and len({row['motion_id'] for row in provided}) == n and
                {row['motion_id'] for row in provided} == motions, 'Completion motion population differs')
        seed_totals = Counter({name: 0 for name in ('completed', 'not_completed', 'unknown')})
        equivalents = {name: [] for name in seed_totals}
        unknown_motions = 0
        for motion in provided:
            exact_keys(motion, COMPLETION_MOTION_FIELDS, 'Motion completion')
            counts = motion['seed_counts']
            exact_keys(counts, ('completed', 'not_completed', 'unknown'), 'Completion seed counts')
            require(all(type(value) is int and value >= 0 for value in counts.values()) and
                    sum(counts.values()) == s and type(motion['expected_seed_denominator']) is int and
                    motion['expected_seed_denominator'] == s, 'Completion fixed seed denominator differs')
            selected = [row for row in self.episodes.values() if group_key(row) == group_key(comparison) and
                        row['robot'] == robot and row['motion_id'] == motion['motion_id']]
            require(len(selected) == s and sorted(row['seed'] for row in selected) == comparison['matched_seed_set'] and
                    dict(Counter(row['completion']['status'] for row in selected) + Counter()) ==
                    {name: value for name, value in counts.items() if value}, 'Completion counts differ from episode labels')
            low, high = counts['completed'] / s, (counts['completed'] + counts['unknown']) / s
            self.completion_ratio(motion['completion_fraction'], motion['completion_percent'],
                motion['possible_fraction_bounds'], motion['possible_percent_bounds'], low, high, counts['unknown'] > 0)
            unknown_motions += int(counts['unknown'] > 0)
            seed_totals.update(counts)
            for name in equivalents:
                equivalents[name].append(counts[name] / s)
            self.completion_checks['motion_summaries'] += 1
        exact_keys(summary['seed_counts'], seed_totals, 'Group completion seed counts')
        require(all(type(value) is int and value >= 0 for value in summary['seed_counts'].values()) and
                summary['seed_counts'] == dict(seed_totals), 'Group seed counts differ')
        exact_keys(summary['motion_completion_equivalents'], equivalents, 'Completion motion equivalents')
        for name, values in equivalents.items():
            value = summary['motion_completion_equivalents'][name]
            number(value, 'Completion motion equivalent')
            require(math.isclose(value, math.fsum(values), rel_tol=0, abs_tol=1e-12), 'Motion equivalent differs')
        require(type(summary['n_unknown_motions']) is int and summary['n_unknown_motions'] == unknown_motions and
                type(summary['effective_adjudicated_motions']) is int and
                summary['effective_adjudicated_motions'] == n - unknown_motions, 'Unknown/effective motion count differs')
        e = summary['motion_completion_equivalents']
        self.completion_ratio(summary['completion_rate'], summary['completion_percent'],
            summary['possible_rate_bounds'], summary['possible_percent_bounds'], e['completed'] / n,
            (e['completed'] + e['unknown']) / n, unknown_motions > 0)
        if comparison['role'] == 'primary' and s == 1:
            require(type(summary['integer_completed_motions']) is int and
                    summary['integer_completed_motions'] == seed_totals['completed'] and
                    summary['completion_summary_label'] == '完成动作数 / 动作数', 'Primary integer completion count differs')
        else:
            require(summary['integer_completed_motions'] is None and
                    summary['completion_summary_label'] == '动作等权平均完成比例 / 完成动作当量',
                    'Sensitivity completion must remain an average/equivalent')

    def completion_ratio(self, fraction, percent, fraction_bounds, percent_bounds, low, high, unknown):
        bounds(fraction_bounds, 'Completion logical fraction bounds')
        bounds(percent_bounds, 'Completion logical percent bounds')
        require(0 <= low <= high <= 1 and all(math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
                for actual, expected in zip(fraction_bounds + percent_bounds, [low, high, low * 100, high * 100])),
                'Completion logical bounds differ')
        if unknown:
            require(fraction is None and percent is None, 'Unknown must keep a null point and full denominator')
        else:
            number(fraction, 'Completion fraction')
            number(percent, 'Completion percent')
            require(math.isclose(fraction, low, rel_tol=0, abs_tol=1e-12) and
                    math.isclose(percent, low * 100, rel_tol=0, abs_tol=1e-12), 'Completion fraction/percent differs')

    def sources(self):
        require(self.source is not None and self.identities is not None,
                'Both reviewed private inputs are required for the independent source comparison')
        raw, identity_raw = Path(self.source).read_bytes(), Path(self.identities).read_bytes()
        require(sha(raw) == FULL_SOURCE_SHA and sha(identity_raw) == IDENTITY_SHA, 'Unreviewed source identity')
        identities = parse_json(identity_raw)
        original_by_id = {row['id']: row for row in identities['results']}
        for row in self.data['results']:
            original = original_by_id[row['id']].get('provenance', {})
            for field in PROVENANCE_FIELDS:
                require(row['provenance'][field] == original.get(field),
                        'Scientific provenance differs from frozen identity: ' + field)
                self.provenance_checks['source_fields'] += 1
        require(self.provenance_checks['source_fields'] == 760, 'Incomplete scientific provenance source comparison')
        completion = read_completion(self.completion_source) if self.completion_source else None
        require((self.data['schema_version'] in (4, 5, 6)) == (completion is not None), 'Completion source/schema differs')
        expected = project(parse_json(raw), identities, publication=not self.preview, completion=completion)
        if self.data['schema_version'] == 4:
            protect_baseline(expected, self.data)
        if self.has_root:
            require(self.root_source is not None, 'Root metrics require the reviewed six-error JSON/CSV source comparison')
            adapter = reviewed_root_adapter(self.root_adapter)
            if not self.has_endpoint:
                protect_baseline(expected, self.data, root_metric_units=adapter.root_metric_units,
                    top_fields=adapter.public_top_fields, row_fields=adapter.public_row_fields,
                    method_fields=adapter.public_method_fields)
            expected = prepare_schema5(expected, self.root_source, self.root_adapter, not self.preview)
            require(self.data['root_extension'] == expected['root_extension'] and
                    self.data['methods']['root'] == expected['methods']['root'], 'Root source method/identity differs')
        else:
            require(self.root_source is None, 'Root source requires a schema-5 public projection')
        if self.has_endpoint:
            require(self.endpoint_source is not None, 'Schema 6 requires the reviewed endpoint JSON/CSV source comparison')
            adapter = reviewed_endpoint_adapter(self.endpoint_adapter)
            protect_schema5(expected, self.data, endpoint_metric_units=adapter.endpoint_metric_units,
                top_fields=adapter.public_top_fields, row_fields=adapter.public_row_fields,
                method_fields=adapter.public_method_fields)
            expected = prepare_schema6(expected, self.endpoint_source, self.endpoint_adapter, not self.preview)
            require(same_json(self.data['endpoint_extension'], expected['endpoint_extension']) and
                    same_json(self.data['methods']['root_endpoint'], expected['methods']['root_endpoint']),
                    'Endpoint source definition/method/identity differs')
        else:
            require(self.endpoint_source is None, 'Endpoint source requires a schema-6 public projection')
        for name in ('schema_version', 'publication_state', 'fullwindow_source_sha256', 'identity_map_sha256',
                     'counts', 'metrics', 'results', 'comparisons', 'phase', 'primary_comparison_ids',
                     'secondary_comparison_ids', 'completion_contract'):
            require(same_json(self.data[name], expected[name]), 'Projection differs from frozen source: ' + name)
        if completion is not None:
            require(self.data['methods']['completion'] == expected['methods']['completion'],
                    'Completion definition differs from frozen public source')
            require(read_completion(self.completion_source) == completion, 'Completion input changed during audit')
        require(Path(self.source).read_bytes() == raw and Path(self.identities).read_bytes() == identity_raw,
                'Private input changed during audit')
        self.root_source_verified = self.has_root
        self.endpoint_source_verified = self.has_endpoint

    def privacy(self):
        for value in walk(self.data):
            if type(value) is str:
                require(not SECRET.search(value) and not LOCAL_PATH.search(value) and not INFRA.search(value),
                        'Private value in public projection')
                require(not re.search(r'\blocalhost\b', value, re.I), 'Local host in public projection')
                for match in IP_LITERAL.finditer(value):
                    try:
                        address = ipaddress.ip_address(match.group())
                    except ValueError:
                        continue
                    require(not (address.is_private or address.is_loopback), 'Internal IP in public projection')
        for name in (DATA_FILES if self.preview else self.publish_files):
            content = (self.root / name).read_text(encoding='utf-8')
            require(not SECRET.search(content), 'Possible credential in public file')
            if name not in {'scripts/verify_public.py', 'scripts/update_snapshot.py', 'scripts/source_contract.py', 'README.md'}:
                require(not LOCAL_PATH.search(content), 'Absolute path in public file')
                scanned = content.replace('.hostname', '') if name == 'app.js' else content
                require(not INFRA.search(scanned), 'Private infrastructure in public file')

    def link(self, value):
        require(type(value) is str and value and '\\' not in value and not re.search(r'[\x00-\x20]', value),
                'Unsafe link')
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            require(parsed.scheme == 'https' and parsed.hostname in HOSTS and not parsed.username
                    and not parsed.password and parsed.port in {None, 443}, 'Unreviewed external link')
            return
        path = unquote(parsed.path)
        require(not path.startswith('/') and '..' not in PurePosixPath(path).parts and '%' not in path,
                'Unsafe local link')
        target = self.root / (path or 'index.html')
        require(target.is_file() and target.relative_to(self.root).as_posix() in self.publish_files,
                'Link target is outside the publication allowlist')

    def bundle(self):
        for name in (DATA_FILES if self.preview else self.publish_files):
            path = self.root / name
            require(path.is_file() and not path.is_symlink(), 'Missing or symlink public file: ' + name)
        for path in self.root.rglob('*'):
            rel = path.relative_to(self.root)
            if any(x in EXCLUDED_DIRS for x in rel.parts):
                continue
            if path.is_file():
                require(rel.as_posix() in self.publish_files, 'File is outside the publication allowlist')
        if self.preview:
            return
        manifest = read_json(self.root / 'RELEASE_MANIFEST.json')
        require(manifest['schema_version'] == self.data['schema_version'] and manifest['public_data_sha256'] ==
                sha((self.root / 'data.json').read_bytes()) and manifest['counts'] == COUNTS,
                'Manifest data identity/counts differ')
        require(manifest['publication_state'] == self.data['publication_state'],
                'Manifest publication state differs')
        require(manifest['fullwindow_source_sha256'] == self.data['fullwindow_source_sha256'] and
                manifest['identity_map_sha256'] == IDENTITY_SHA and
                manifest['completion_contract'] == self.data['completion_contract'], 'Manifest source closure differs')
        if self.data['schema_version'] in (4, 5, 6):
            require(manifest['completion_source_csv_sha256'] == COMPLETION_CSV_SHA,
                    'Manifest public completion CSV source identity differs')
        if self.has_root:
            require(manifest['root_extension'] == self.data['root_extension'] and
                    manifest['root_source_csv_sha256'] == ROOT_CSV_SHA, 'Manifest root JSON/CSV source closure differs')
        if self.has_endpoint:
            require(manifest['endpoint_extension'] == self.data['endpoint_extension'] and
                    manifest['endpoint_source_csv_sha256'] == ENDPOINT_CSV_SHA,
                    'Manifest endpoint JSON/CSV source closure differs')
        files = manifest['files']
        require(set(files) == self.publish_files - {'RELEASE_MANIFEST.json'}, 'Manifest file allowlist differs')
        for name, record in files.items():
            raw = (self.root / name).read_bytes()
            require(record['sha256'] == sha(raw) and record['bytes'] == len(raw), 'Manifest file identity differs')
        for name, digest in HARDWARE_SHA.items():
            require(sha((self.root / name).read_bytes()) == digest, 'Frozen hardware bytes changed')
        hardware = read_json(self.root / 'hardware.json')
        require(hardware['schema'] == 'rp1-g1-public-hardware-comparison-v1'
                and len(hardware['joint_rows']) == 29, 'Hardware schema/count differs')
        media = read_json(self.root / 'media.json')
        require(media['schema'] == 'rp1-g1-public-media-v1' and media['status'] == 'awaiting_new_render'
                and media['expected_common_motions'] == 40 and media['items'] == [],
                'New media requires its own reviewed publication contract')
        for item in self.data['report_downloads']:
            require(set(item) <= {'label', 'url', 'access'}, 'Report download fields differ')
            self.link(item['url'])
        html = Links()
        html.feed((self.root / 'index.html').read_text())
        for value in html.links:
            self.link(value)
            if value.startswith('#') and len(value) > 1:
                require(value[1:] in html.ids, 'Missing section anchor')
        for name in ('README.md', 'DATA_PROVENANCE.md'):
            for value in re.findall(r'\[[^\]]*\]\(([^)]+)\)', (self.root / name).read_text()):
                self.link(value)
        for name in sorted(self.publish_files):
            if not name.endswith(('.js', '.css')):
                continue
            content = (self.root / name).read_text()
            for _, value in re.findall(r'(?:fetch\s*\(|url\s*:\s*)(["\x27])([^"\x27]+)\1', content):
                self.link(value)
            for value in re.findall(r'url\(\s*["\x27]?([^\s)"\x27]+)', content):
                self.link(value)
            if name.endswith('.js'):
                for _, value in re.findall(
                        r'\b(?:import|export)\s+(?:[^;"\x27\n]*?\s+from\s*)?(["\x27])([^"\x27]+)\1', content):
                    self.link(value)
                for _, value in re.findall(
                        r'\b(?:import|importScripts|Worker|SharedWorker)\s*\(\s*(["\x27])([^"\x27]+)\1', content):
                    self.link(value)

    def publication_gate(self):
        if not self.preview and self.data['schema_version'] in (4, 5, 6):
            require(self.source is not None and self.identities is not None and self.completion_source is not None and
                    'frozen_source_720_values_and_original_ID_mapping' in self.checked,
                    'Private framework publication eligibility requires the complete frozen source comparison')
        if self.has_root:
            require(self.root_source is not None and self.root_source_verified,
                    'Schema 5 requires the complete reviewed six-error JSON/CSV source comparison')
        if self.has_endpoint:
            require(self.endpoint_source is not None and self.endpoint_source_verified,
                    'Schema 6 requires the complete reviewed endpoint JSON/CSV source comparison')
        if self.data['schema_version'] == 3:
            require(self.data['publication_state'] == (PREVIEW_STATE if self.preview else PUBLIC_STATE)
                    and self.data['completion_contract'] == COMPLETION_CONTRACT,
                    'Only the reviewed pending four-error contract is eligible')
            for obj in self.data['results'] + self.data['comparisons']:
                pending(obj['completion'])
        else:
            expected_state = ((ENDPOINT_PREVIEW_STATE if self.preview else ENDPOINT_PUBLIC_STATE) if self.has_endpoint else
                             (ROOT_PREVIEW_STATE if self.preview else ROOT_PUBLIC_STATE) if self.has_root else
                             (COMPLETION_PREVIEW_STATE if self.preview else COMPLETION_PUBLIC_STATE))
            require(self.data['schema_version'] in (4, 5, 6) and self.data['publication_state'] == expected_state and
                    self.data['completion_contract'] == {'status': 'verified', 'rule_version': CRITERION_ID,
                    'source_sha256': COMPLETION_SOURCE_SHA}, 'Only the frozen semantic completion contract is eligible')

    def run(self):
        for name, fn in [('reviewed_positive_schema', self.schema), ('physical_rows_and_exact_pairs', self.rows_and_pairs),
                         ('five_independent_fullwindow_comparisons', self.comparisons),
                         ('frozen_semantic_completion_contract', self.completions),
                         ('canonical_csv_exports', self.exports), ('publication_file_allowlist', self.bundle),
                         ('privacy', self.privacy)]:
            self.check(name, fn)
        if any(arg is not None for arg in (self.source, self.identities, self.completion_source, self.root_source,
                                         self.endpoint_source)):
            self.check('frozen_source_720_values_and_original_ID_mapping', self.sources)
        self.check('reviewed_completion_publication_gate', self.publication_gate)
        return {'ok': not self.errors, 'publication_allowed': not self.errors and not self.preview,
            'completion_ready': not self.errors and self.data.get('schema_version') in (4, 5, 6), 'preview_only': self.preview,
            'schema_version': self.data.get('schema_version'), 'counts': self.data.get('counts'),
            'completion_status': self.data.get('completion_contract', {}).get('status'),
            'value_checks': self.value_checks, 'root_value_checks': self.root_value_checks,
            'endpoint_value_checks': self.endpoint_value_checks,
            'endpoint_source_compared': self.endpoint_source_verified,
            'root_source_compared': self.root_source_verified, 'provenance_checks': self.provenance_checks,
            'completion_checks': self.completion_checks,
            'source_compared': 'frozen_source_720_values_and_original_ID_mapping' in self.checked,
            'completion_source_compared': self.completion_source is not None and
                'frozen_source_720_values_and_original_ID_mapping' in self.checked,
            'public_data_sha256': sha((self.root / 'data.json').read_bytes()),
            'checked': self.checked, 'errors': self.errors, 'browser_qa_checked': False,
            'external_availability_checked': False}


def main():
    if any(value == '--source-clock' or value.startswith('--source-clock=') for value in sys.argv[1:]):
        from verify_clock_public import main as clock_main
        return clock_main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--preview', action='store_true', help='audit an internal pending/null preview; never publish')
    parser.add_argument('--source-fullwindow', type=Path)
    parser.add_argument('--identity-map', type=Path)
    parser.add_argument('--source-completion', type=Path)
    parser.add_argument('--source-root', type=Path,
                        help='reviewed six-error public JSON with its SHA-bound sibling public episode CSV')
    parser.add_argument('--root-adapter', help='code-registered reviewed root adapter ID')
    parser.add_argument('--source-endpoint', type=Path,
                        help='reviewed endpoint JSON with its SHA-bound public_sevenerror_episodes.csv sibling')
    parser.add_argument('--endpoint-adapter', help='code-registered reviewed endpoint adapter ID')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        require(not args.root_adapter or args.source_root, '--root-adapter requires --source-root')
        require(not args.endpoint_adapter or args.source_endpoint, '--endpoint-adapter requires --source-endpoint')
        if args.source_endpoint:
            require(args.source_root is not None and args.source_completion is not None,
                    '--source-endpoint requires the intact reviewed six-error and completion inputs')
            reviewed_endpoint_adapter(args.endpoint_adapter)
        if args.source_root:
            reviewed_root_adapter(args.root_adapter)
        report = Audit(args.repo_root, args.preview, args.source_fullwindow, args.identity_map, args.source_completion,
                       args.source_root, args.root_adapter, args.source_endpoint, args.endpoint_adapter).run()
    except (ValueError, TypeError, KeyError, IndexError, OSError) as error:
        report = {'ok': False, 'publication_allowed': False, 'errors': [str(error)]}
    report['framework'] = framework_status()
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.report:
        args.report.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
