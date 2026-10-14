#!/usr/bin/env python3
"""Audit the reviewed v3 four-error contract with honest pending/null completion.

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
from update_snapshot import (COMPLETION_CONTRACT, COMPARISON_COLUMNS, COUNTS,
    EPISODE_COLUMNS, FULL4, FULL_SOURCE_SHA, IDENTITY_SHA, PENDING, PREVIEW_STATE, PUBLIC_STATE,
    PROVENANCE_FIELDS, PROVENANCE_SHA, WINDOW, csv_bytes, episode_key, group_key,
    project, provenance_digest, read_json, seed, sha)

PUBLISH_FILES = {'.gitignore', '.nojekyll', 'README.md', 'DATA_PROVENANCE.md',
    'RELEASE_MANIFEST.json', 'index.html', 'app.js', 'style.css', 'data.json', 'media.json',
    'favicon.svg', 'hardware.json', 'hardware.csv', 'episodes.csv', 'comparisons.csv',
    'scripts/update_snapshot.py', 'scripts/verify_public.py'}
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
    def __init__(self, root, preview=False, source=None, identities=None):
        self.root = Path(root).resolve()
        self.preview = preview
        self.source = source
        self.identities = identities
        self.data = read_json(self.root / 'data.json')
        self.checked, self.errors = [], []
        self.value_checks = {'episode_values': 0, 'aggregate_scalars': 0, 'paired_delta_scalars': 0}
        self.provenance_checks = {'hash_values': 0, 'null_values': 0, 'source_fields': 0}
        self.episodes, self.cases, self.aliases, self.by_id = {}, {}, {}, {}

    def check(self, name, fn):
        try:
            fn()
            self.checked.append(name)
        except (ValueError, TypeError, KeyError, IndexError, OSError, csv.Error) as error:
            self.errors.append(name + ': ' + str(error))

    def schema(self):
        d = self.data
        exact_keys(d, TOP_KEYS, 'data')
        require(d['schema_version'] == 3 and d['phase'] == 'A' and d['counts'] == COUNTS,
                'v3 schema/physical scope differs')
        require(d['publication_state'] == (PREVIEW_STATE if self.preview else PUBLIC_STATE)
                and d['completion_contract'] == COMPLETION_CONTRACT,
                'Publication state or pending/null completion contract differs')
        require(d['fullwindow_source_sha256'] == FULL_SOURCE_SHA and d['identity_map_sha256'] == IDENTITY_SHA,
                'Reviewed projection source identities differ')
        require(set(d['metrics']) == set(FULL4), 'Exactly four full-window metrics are reviewed')
        for name, definition in d['metrics'].items():
            exact_keys(definition, {'unit', 'label', 'higher_is_better'}, 'metric definition')
            require(definition['unit'] == ('mm' if name.endswith('_mm') else 'rad')
                    and definition['higher_is_better'] is False, 'Full-window units/direction differ')
        exact_keys(d['methods'], {'fullwindow', 'units', 'weighting', 'bootstrap'}, 'methods')
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
        require(set(d['stats']) <= {'aggregation', 'ci_method', 'scope', 'limitations'}, 'Statistics fields differ')

    def rows_and_pairs(self):
        rows = self.data['results']
        require(len(rows) == len({r['id'] for r in rows}) == 190 and
                Counter(r['scope'] for r in rows) == {'per_motion': 180, 'aggregate': 10}, 'Result counts differ')
        episodes, cases, aliases = {}, {}, {}
        for row in rows:
            is_episode = row['scope'] == 'per_motion'
            exact_keys(row, ROW_KEYS | ({'fullwindow'} if is_episode else set()), 'result')
            require(row['phase'] == 'A' and row['robot'] in {'rp1', 'g1'} and group_key(row) in COHORTS,
                    'Unreviewed result identity')
            pending(row['completion'])
            exact_keys(row['provenance'], PROVENANCE_FIELDS, 'scientific provenance')
            for value in row['provenance'].values():
                require(value is None or (type(value) is str and HASH.fullmatch(value)),
                        'Scientific provenance must be SHA256 or null')
                self.provenance_checks['null_values' if value is None else 'hash_values'] += 1
            exact_keys(row['coverage'], {'numerator', 'denominator', 'unit'}, 'coverage')
            exact_keys(row['pairing'], {'comparison_id', 'sample_set_sha256', 'case_id'}, 'pairing')
            require(HASH.fullmatch(row['pairing']['sample_set_sha256']), 'Malformed paired sample identity')
            require(set(row['metrics']) == set(FULL4), 'Result contains an unreviewed metric')
            n = 1 if is_episode else COHORTS[group_key(row)][1]
            require(row['coverage'] == {'numerator': n, 'denominator': n,
                    'unit': 'episodes' if is_episode else 'motions'}, 'Coverage unit/denominator differs')
            for name, cell in row['metrics'].items():
                exact_keys(cell, {'value', 'unit', 'ci95', 'n_motions'}, 'metric cell')
                number(cell['value'], 'full-window value')
                require(cell['value'] >= 0 and cell['unit'] == self.data['metrics'][name]['unit']
                        and cell['n_motions'] == n, 'Full-window value/unit/motion denominator differs')
                if is_episode:
                    require(cell['ci95'] is None, 'Individual episode cannot invent a group interval')
                    self.value_checks['episode_values'] += 1
                else:
                    bounds(cell['ci95'], 'aggregate interval')
                    self.value_checks['aggregate_scalars'] += 3
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
            require(set(c['paired_deltas']) == set(c['paired_motion_values']) == set(FULL4),
                    'Comparison must contain only four reviewed errors')
            robot_means = {r['robot']: r for r in members}
            for metric in FULL4:
                delta = c['paired_deltas'][metric]
                exact_keys(delta, {'value', 'ci95', 'unit', 'n_motions'}, 'paired delta')
                number(delta['value'], 'paired value')
                bounds(delta['ci95'], 'paired interval')
                require(delta['unit'] == self.data['metrics'][metric]['unit'] and delta['n_motions'] == motions,
                        'Paired interval units/denominator differ')
                self.value_checks['paired_delta_scalars'] += 3
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
        for name, scope, n, columns in [('episodes.csv', 'per_motion', 180, EPISODE_COLUMNS),
                                        ('comparisons.csv', 'aggregate', 10, COMPARISON_COLUMNS)]:
            raw = (self.root / name).read_bytes()
            require(raw == csv_bytes(self.data, scope), 'CSV is not the exact canonical v3 export: ' + name)
            with (self.root / name).open(encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle, strict=True)
                rows = list(reader)
            require(reader.fieldnames == columns and len(rows) == n, 'CSV rows/columns differ')
            require(all(row['completion_status'] == 'pending' and all(row[field] == '' for field in
                    ('motion_completed', 'motion_completion_pct', 'completion_ci95_low', 'completion_ci95_high'))
                    for row in rows), 'Unknown completion must retain blank numeric/boolean CSV cells')

    def sources(self):
        require(self.source is not None and self.identities is not None,
                'Both reviewed private inputs are required for the independent source comparison')
        raw, identity_raw = Path(self.source).read_bytes(), Path(self.identities).read_bytes()
        require(sha(raw) == FULL_SOURCE_SHA and sha(identity_raw) == IDENTITY_SHA, 'Unreviewed source identity')
        identities = read_json(self.identities)
        original_by_id = {row['id']: row for row in identities['results']}
        for row in self.data['results']:
            original = original_by_id[row['id']].get('provenance', {})
            for field in PROVENANCE_FIELDS:
                require(row['provenance'][field] == original.get(field),
                        'Scientific provenance differs from frozen identity: ' + field)
                self.provenance_checks['source_fields'] += 1
        require(self.provenance_checks['source_fields'] == 760, 'Incomplete scientific provenance source comparison')
        expected = project(read_json(self.source), identities, publication=not self.preview)
        for name in ('schema_version', 'publication_state', 'fullwindow_source_sha256', 'identity_map_sha256',
                     'counts', 'metrics', 'results', 'comparisons', 'phase', 'primary_comparison_ids',
                     'secondary_comparison_ids', 'completion_contract'):
            require(self.data[name] == expected[name], 'Projection differs from frozen source: ' + name)
        require(Path(self.source).read_bytes() == raw and Path(self.identities).read_bytes() == identity_raw,
                'Private input changed during audit')

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
        for name in (DATA_FILES if self.preview else PUBLISH_FILES):
            content = (self.root / name).read_text(encoding='utf-8')
            require(not SECRET.search(content), 'Possible credential in public file')
            if name not in {'scripts/verify_public.py', 'scripts/update_snapshot.py', 'README.md'}:
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
        require(target.is_file() and target.relative_to(self.root).as_posix() in PUBLISH_FILES,
                'Link target is outside the v3 publication allowlist')

    def bundle(self):
        for name in (DATA_FILES if self.preview else PUBLISH_FILES):
            path = self.root / name
            require(path.is_file() and not path.is_symlink(), 'Missing or symlink public file: ' + name)
        for path in self.root.rglob('*'):
            rel = path.relative_to(self.root)
            if any(x in EXCLUDED_DIRS for x in rel.parts):
                continue
            if path.is_file():
                require(rel.as_posix() in PUBLISH_FILES, 'File is outside the v3 publication allowlist')
        if self.preview:
            return
        manifest = read_json(self.root / 'RELEASE_MANIFEST.json')
        require(manifest['schema_version'] == 3 and manifest['public_data_sha256'] ==
                sha((self.root / 'data.json').read_bytes()) and manifest['counts'] == COUNTS,
                'Manifest v3 data identity/counts differ')
        require(manifest['publication_state'] == self.data['publication_state'],
                'Manifest publication state differs')
        require(manifest['fullwindow_source_sha256'] == FULL_SOURCE_SHA and
                manifest['identity_map_sha256'] == IDENTITY_SHA and
                manifest['completion_contract'] == self.data['completion_contract'], 'Manifest source closure differs')
        files = manifest['files']
        require(set(files) == PUBLISH_FILES - {'RELEASE_MANIFEST.json'}, 'Manifest file allowlist differs')
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
        for name in ('app.js', 'style.css'):
            content = (self.root / name).read_text()
            for _, value in re.findall(r'(?:fetch\s*\(|url\s*:\s*)(["\x27])([^"\x27]+)\1', content):
                self.link(value)
            for value in re.findall(r'url\(\s*["\x27]?([^\s)"\x27]+)', content):
                self.link(value)

    def publication_gate(self):
        require(self.data['publication_state'] == (PREVIEW_STATE if self.preview else PUBLIC_STATE)
                and self.data['completion_contract'] == COMPLETION_CONTRACT,
                'Only the reviewed four-error contract with pending/null completion is eligible')
        for obj in self.data['results'] + self.data['comparisons']:
            pending(obj['completion'])

    def run(self):
        for name, fn in [('v3_positive_schema', self.schema), ('physical_rows_and_exact_pairs', self.rows_and_pairs),
                         ('five_independent_fullwindow_comparisons', self.comparisons),
                         ('canonical_csv_exports', self.exports), ('v3_publication_file_allowlist', self.bundle),
                         ('privacy', self.privacy)]:
            self.check(name, fn)
        if self.source is not None or self.identities is not None:
            self.check('frozen_source_720_values_and_original_ID_mapping', self.sources)
        self.check('pending_completion_publication_gate', self.publication_gate)
        return {'ok': not self.errors, 'publication_allowed': not self.errors and not self.preview,
            'completion_ready': False, 'preview_only': self.preview,
            'schema_version': self.data.get('schema_version'), 'counts': self.data.get('counts'),
            'completion_status': self.data.get('completion_contract', {}).get('status'),
            'value_checks': self.value_checks, 'provenance_checks': self.provenance_checks,
            'source_compared': 'frozen_source_720_values_and_original_ID_mapping' in self.checked,
            'public_data_sha256': sha((self.root / 'data.json').read_bytes()),
            'checked': self.checked, 'errors': self.errors, 'browser_qa_checked': False,
            'external_availability_checked': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--preview', action='store_true', help='audit an internal pending/null preview; never publish')
    parser.add_argument('--source-fullwindow', type=Path)
    parser.add_argument('--identity-map', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        report = Audit(args.repo_root, args.preview, args.source_fullwindow, args.identity_map).run()
    except (ValueError, TypeError, KeyError, IndexError, OSError) as error:
        report = {'ok': False, 'publication_allowed': False, 'errors': [str(error)]}
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.report:
        args.report.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
