#!/usr/bin/env python3
"""Fail-closed audit of the reviewed RP1/G1 public snapshot (stdlib only).

Run without arguments to verify the distributable bundle. Add --source-data to
independently compare every result's metrics, CI, coverage and pairing with the
hash-approved Common40 private input. Separate Extreme5, hardware and fullwindow files must
match their reviewed public projection hashes. Private inputs are never copied. A changed
scientific version requires review and an explicit change to this contract.
Exit 1 means publication must stop; exit 0 records only the checks performed.
This static verifier does not claim browser QA or external link availability.
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


SOURCE_SHA = '218518aa397d938fcd84c630c6dc3a1ee65958439d797a9ce1e3f6759bb715bb'
AGGREGATE_SHA = '036559d03c4a2a3ec8198c6a703b9a09be096c7181eb62d7c0b91ec06bd42210'
ADAPTER_SHA = 'a199be0fb34219019a07bc16b8f2f91ad4d7c863f6f22522a7b5b033a5e44f04'
NOMINAL_ID = 'paired_9b95426b30027f7b'
NOMINAL_SAMPLE_SHA = '185327685ec34743ef24e818f57480664249489746fadfc7ed359a94f952d7aa'
# Scientific fields of the reviewed 178-row intersection, before changing any
# public copy or links. This pins every retained value, CI, sample and failure.
PAIRED_SCIENCE_SHA = '162e44a657d28953694998a72a2e2b1fe1394b06fe9e3e5d46f073746c20decb'
HARDWARE_JSON_SHA = '5815d8d7e1a28305124849990dc682c85f6e6eb49b7bc78a91ae9adfa270a6af'
HARDWARE_CSV_SHA = '78972776c7640ec62e03bffda14caf0fb530a170ca3751109e66a79ac57614de'
EXTREME_JSON_SHA = 'a2d3e11f3f05737b89d4332fc384a95d93eefd819f3ff76eb203a2b4c5b3803e'
EXTREME_CSV_SHA = '34fc4c3e1d08b3c8f30757f21efa8675e4e090ba050221e5a5d7d219c04473c1'
EXTREME_AGGREGATE_SHA = '086c0fa83a2eae58156c23610dd55d430fb53e4f14f5b18f7d17e6d19513544b'
EXTREME_SAMPLE_SHA = '20a4c0c34c458b6c3df712d984da5dad097d89a8ecfc175432f4285343da51fb'
EXTREME_NUMERIC_SHA = '776bc9267c40a18af0f619fae326209d0c349bab55c0deeb27c5049b12def065'
EXTREME_EXECUTION_V1_SHA = '7fe3c1fca5570abb08de9af23bdc618e604d565fbf85a9bf80c44883d5f8af02'
EXTREME_EXECUTION_V2_SHA = '5051871e0aed48da72317c616692d75d1fb7def6eeaf5a3921d75640638a5035'
EXTREME_ID = 'paired_extreme5_nominal_native_position_20261014'
FULLWINDOW_JSON_SHA = '119d981f07983b060b038e860ac0da9b2d5c10c166fc637b83d179cbf6bda5dd'
FULLWINDOW_CSV_SHA = '894a5b836fb1473202c3c3da08b11f9280fe3b572f589279dd00e444ea7e2ff4'
FULLWINDOW_RECEIPT_SHA = 'c3698c7e99ebba4167ef8cb2254f10b82aa7e4884efd97cd3745796540ced47b'
FULLWINDOW_WINDOW = 'full_replay_50hz_first_substep'
FULLWINDOW_METRICS = ('full_body_pos_mm', 'full_body_ori_rad',
                      'full_wrist_pos_mm', 'full_wrist_ori_rad')
FULLWINDOW_JOIN = ('dataset', 'condition', 'mode', 'robot', 'motion_id', 'seed')
FULLWINDOW_COHORTS = {
    ('lafan40', 'nominal', 'native_position'):
        ('fullwindow_2ed140d66171d9de', 40, 40, [0], 'primary',
         'eafa7179ed73a84956126a6f57b35740b39bf9e948b3ef37434834943336561f'),
    ('extreme5', 'nominal', 'native_position'):
        ('fullwindow_13726acb7f07e362', 5, 5, [0], 'primary',
         '64860ac299ad482c82e73819bf274de3b70585e80d0472e92243d8a215422135'),
    ('lafan40', 'repeat_nominal', 'native_position'):
        ('fullwindow_e5a4e7c58d22b83b', 15, 5, [0, 1, 42], 'secondary',
         '82fcd51b3617263a6ff9d8d060572f736391585ca62b43a0dc568ca956573f08'),
    ('lafan40', 'robust_initial_velocity', 'native_position'):
        ('fullwindow_8e62320ef9665457', 25, 5, [0, 1, 2, 3, 4], 'secondary',
         '7f10ff0df57f0d805e2fcba85aef3c00a06775eba6a56e4a14cf001fc437ff26'),
    ('lafan40', 'explicit_sensitivity', 'explicit_deploy'):
        ('fullwindow_2f2e445e5e2e664e', 5, 5, [0], 'secondary',
         '1b75372620d64a237e0b7f350c7592932254cfc2ccc195afc9c7a498a1a8cdc5'),
}
EXTREME_FRAMES = {'Take_143_Skeleton0': 431, 'Take_144_Skeleton0': 448,
                  'Take_146_Skeleton0': 375, 'Take_148_Skeleton0': 391,
                  'Take_149_Skeleton0': 462}
DISPLAY_SCOPE = {
    'datasets': 2, 'unique_motion_ids': 45, 'paired_cases': 90, 'episodes': 180,
    'aggregate_rows': 10, 'result_rows': 190, 'comparison_groups': 5,
    'groups_remain_separate': True,
}
EXTENSIONS = {
    'extreme5': {
        'json': 'extreme5.json', 'csv': 'extreme5.csv',
        'aggregate_sha256': EXTREME_AGGREGATE_SHA,
        'json_sha256': EXTREME_JSON_SHA, 'csv_sha256': EXTREME_CSV_SHA,
    },
    'hardware': {
        'json': 'hardware.json', 'csv': 'hardware.csv',
        'source_sha256': '7c3ab345adbaf55d12fe6a5bc8a3923dab7257bd7df82b248c46e651214cce8c',
        'json_sha256': HARDWARE_JSON_SHA, 'csv_sha256': HARDWARE_CSV_SHA,
    },
    'fullwindow': {
        'json': 'fullwindow.json', 'csv': 'fullwindow.csv',
        'json_sha256': FULLWINDOW_JSON_SHA, 'csv_sha256': FULLWINDOW_CSV_SHA,
        'metric_window': FULLWINDOW_WINDOW,
        'final_receipt_sha256': FULLWINDOW_RECEIPT_SHA,
        'independent_audit_sha256': '01a10684520c13dd9e00d7b0329389e3000a37e3dc7f69d985501bc486a44b57',
        'historical_handoff_sha256': '6c7707db561524f260f5a33527b6b6d61ee1c807f25fff7412e900578b44b7fd',
    },
    'handoff_sha256': '6afe9c674cc85df00d67016cedb0dfb0da23d27705b09adf00c79c0ac9e30cd2',
}
PAIR_KEY = ('phase', 'dataset', 'condition', 'mode', 'motion_id', 'seed',
            'protocol_sha256', 'runtime')
PUBLIC_SCOPE = {
    'unique_motions': 40, 'paired_cases': 85, 'episodes': 170,
    'aggregate_rows': 8, 'result_rows': 178, 'comparison_groups': 4,
    'pairing_key': list(PAIR_KEY),
    'rule': ('Exact RP1/G1 identity intersection; condition is canonical effective condition; '
             'no status or success filtering; original raw records preserved.'),
}
SCIENTIFIC_COVERAGE = {
    'unique_common_motions': 40, 'paired_cases': 85, 'paired_episodes': 170,
    'aggregate_rows': 8, 'comparison_groups': 4,
}
# condition / mode -> (comparison ID, exact cases, unique motions, seeds,
#                      immutable reviewed sample-set SHA)
COHORTS = {
    ('nominal', 'native_position'):
        (NOMINAL_ID, 40, 40, {0}, NOMINAL_SAMPLE_SHA),
    ('explicit_sensitivity', 'explicit_deploy'):
        ('paired_c179e42ff26f4ccc', 5, 5, {0},
         'f21ad5e5d3827cad625cb7b05c6a4376613902c9ba013d6ac0ef726f25af2b69'),
    ('repeat_nominal', 'native_position'):
        ('paired_af50da41bd3b816a', 15, 5, {0, 1, 42},
         'c3607519913703584a2538e879e01de88fe8d341634eba04e253db387e269c84'),
    ('robust_initial_velocity', 'native_position'):
        ('paired_826633abc5b0aceb', 25, 5, {0, 1, 2, 3, 4},
         '8e12de44ff70a24132fc06e9cc6de1fe4ff62c75df73cf0e1176c7a00f761670'),
}
METRICS = {'body_pos_mm', 'body_ori_rad', 'root_pos_m', 'gpu_train_hours',
           'wrist_pos_mm', 'wrist_ori_rad', 'episode_return', 'progress_pct'}
PUBLISH_FILES = {
    '.gitignore', '.nojekyll', 'README.md', 'DATA_PROVENANCE.md',
    'RELEASE_MANIFEST.json', 'index.html', 'app.js', 'style.css', 'data.json', 'media.json', 'favicon.svg',
    'hardware.json', 'hardware.csv',
    'extreme5.json', 'extreme5.csv',
    'fullwindow.json', 'fullwindow.csv',
    'scripts/update_snapshot.py', 'scripts/verify_public.py',
}
EXCLUDED_DIRS = {'.git', '.agents', '.aws', '.codex', '.private', 'qa', '__pycache__'}
REVIEWED_HOSTS = {'github.com', 'raw.githubusercontent.com', 'roboparty.feishu.cn',
                  'egalahad.github.io', 'huggingface.co', 'drive.google.com',
                  'zhang-yongqi.github.io'}
SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
SECRET = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|'
                    r'AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,})\b|'
                    r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|'
                    r'\bssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/]{30,}')
LOCAL_PATH = re.compile(r'(?:^|[\s"\x27(=:])/(?:home|Users|root|mnt|tmp|srv|var)/|'
                        r'\b[A-Za-z]:[\\/]|\b(?:file|ssh)://', re.I)
INFRA = re.compile(r'\b(?:candidate_host|candidate_ssh|watchdog_pid|ssh_host|'
                   r'ssh_port|ssh_key|hostname|server_ip|process_id|source_status)\b|'
                   r'\b(?:ssh|scp|rsync)\s+(?:-[^\s]+\s+)*[\w.-]+@|'
                   r'\b(?:PID|pid)\s*[:=]\s*\d+', re.I)
IP_LITERAL = re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
HASH = re.compile(r'[0-9a-f]{64}\Z')
URL_TEXT = re.compile(r'https?://[^\s<>"\x27`]+')
ROW_KEYS = {'id', 'label', 'phase', 'robot', 'dataset', 'condition', 'mode',
            'seed', 'scope', 'motion_id', 'status', 'status_reason', 'coverage',
            'paired_coverage', 'metrics', 'pairing', 'checkpoint', 'provenance',
            'videos', 'notes', 'failures'}
COVERAGE_KEYS = {'numerator', 'denominator', 'unit', 'reason'}
PAIRING_KEYS = {'comparison_id', 'sample_set_sha256', 'verified', 'reason'}
CI_KEYS = {'low', 'high', 'level', 'unit', 'method', 'resampling_unit',
           'n_clusters', 'n_seeds', 'resamples', 'reason'}
VIDEO_KEYS = {'label', 'url', 'sha256', 'access', 'description', 'synchronized',
              'robot', 'clip', 'kind', 'full_window', 'window_sim_s', 'duration_s',
              'bytes', 'video_manifest_sha256', 'upload_receipt_sha256',
              'cloud_original_sha256_verified', 'mapping_status', 'source_runs'}
SOURCE_RUN_KEYS = {'run_id', 'episode_id', 'robot', 'motion', 'dataset', 'condition',
                   'original_condition', 'mode', 'seed', 'trajectory_sha256',
                   'states_sha256', 'manifest_sha256'}
COMPARISON_KEYS = {'id', 'label', 'verified', 'expected_participants',
                   'sample_set_sha256', 'reason', 'protocol', 'provisional',
                   'expected_paired_motions', 'paired_deltas', 'cohort_metadata'}
RESULT_IDENTITY = ('id', 'label', 'phase', 'robot', 'dataset', 'condition', 'mode',
                   'seed', 'scope', 'motion_id', 'status', 'status_reason')
SCIENTIFIC_FIELDS = RESULT_IDENTITY + ('metrics', 'coverage', 'paired_coverage',
                                      'pairing', 'failures', 'checkpoint')
PROVENANCE_FIELDS = ('source_sha256', 'config_sha256', 'protocol_sha256', 'runtime')
SINGLE_SIDE_APPENDIX_URL = 'https://roboparty.feishu.cn/drive/folder/JReufYd5al9Sfzd2GEkcLGjYnJf'


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pair_key(row):
    # The canonical condition is supplied by the reviewed source. Do not infer
    # matches from names, status, score, or a video's original_condition alias.
    return tuple(row[name] for name in PAIR_KEY[:6]) + tuple(
        row['provenance'][name] for name in PAIR_KEY[6:])


def scientific_digest(data):
    protected = {
        'results': [dict({name: row.get(name) for name in SCIENTIFIC_FIELDS},
                         provenance={name: row['provenance'].get(name)
                                     for name in PROVENANCE_FIELDS})
                    for row in sorted(data['results'], key=lambda item: item['id'])],
        'comparisons': sorted(data['comparisons'], key=lambda item: item['id']),
    }
    return sha(json.dumps(protected, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode())

def strict_seed(value):
    # Accept the historical Extreme text "0", never coerce bool/float/whitespace.
    if type(value) is int and value >= 0:
        return value
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]*', value) is not None,
            'episode seed must be a strict nonnegative decimal integer')
    return int(value)

def fullwindow_join_key(row):
    require(row['phase'] == 'A', 'fullwindow join crosses phase')
    for name in FULLWINDOW_JOIN[:-1]:
        require(type(row[name]) is str and row[name], 'fullwindow semantic key is missing')
    return tuple(row[name] for name in FULLWINDOW_JOIN[:-1]) + (strict_seed(row['seed']),)


def read_json(path):
    def reject_constant(value):
        raise AuditError('JSON contains a non-finite number')
    def unique_keys(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, 'JSON contains a duplicate object key')
            obj[key] = value
        return obj
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_constant,
                      object_pairs_hook=unique_keys)


def keys(obj, allowed, location):
    require(isinstance(obj, dict), location + ': expected object')
    require(set(obj) <= allowed, location + ': contains a non-public field')


def walk(obj, location='data'):
    yield location, obj
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, location + '.' + key)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk(value, '{}[{}]'.format(location, index))


def numeric(value, location, nullable=True):
    require((nullable and value is None) or
            (type(value) in (int, float) and math.isfinite(value)),
            location + ': expected finite number or explicit null')


def coverage(obj, location):
    keys(obj, COVERAGE_KEYS, location)
    require(COVERAGE_KEYS <= set(obj), location + ': missing coverage field')
    for field in ('numerator', 'denominator'):
        numeric(obj[field], location + '.' + field)
        require(obj[field] is None or (type(obj[field]) is int and obj[field] >= 0),
                location + ': coverage must be a nonnegative integer or null')
    n, d = obj['numerator'], obj['denominator']
    require(n is None or d is None or n <= d, location + ': numerator exceeds denominator')
    require(isinstance(obj['reason'], str) and obj['reason'].strip(),
            location + ': missing coverage reason')


def metric_cells(obj, location):
    keys(obj, METRICS, location)
    require(set(obj) == METRICS, location + ': missing metric')
    for name, cell in obj.items():
        loc = location + '.' + name
        keys(cell, {'value', 'reason', 'sample_set_sha256', 'coverage', 'ci'}, loc)
        require('value' in cell, loc + ': missing value must be explicit null')
        numeric(cell['value'], loc + '.value')
        require(isinstance(cell.get('reason'), str) and cell['reason'].strip(),
                loc + ': missing metric reason')
        coverage(cell['coverage'], loc + '.coverage')
        ci = cell.get('ci', {})
        keys(ci, CI_KEYS, loc + '.ci')
        require({'low', 'high'} <= set(ci), loc + ': CI bounds must be explicit')
        for bound in ('low', 'high'):
            numeric(ci[bound], loc + '.ci.' + bound)
        require((ci['low'] is None) == (ci['high'] is None), loc + ': one-sided missing CI')
        if ci['low'] is None:
            require(isinstance(ci.get('reason'), str) and ci['reason'].strip(),
                    loc + ': missing CI must retain its reason')
        else:
            require(ci['low'] <= ci['high'], loc + ': reversed CI')
        if name == 'progress_pct' and cell['value'] is not None:
            require(0 <= cell['value'] <= 100, loc + ': progress outside 0–100')


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'src', 'href', 'poster'} and value:
                self.links.append(value)
            if key == 'id' and value:
                self.ids.add(value)


class Audit:
    def __init__(self, root, source_path=None):
        self.root = root.resolve()
        self.source_path = source_path
        self.checked = []
        self.errors = []
        self.external_links = set()
        self.internal_links = set()
        self.data = read_json(self.root / 'data.json')
        self.manifest = read_json(self.root / 'RELEASE_MANIFEST.json')
        self.episodes_by_id = {row['id']: row for row in self.data['results']
                               if row['scope'] == 'per_motion'}

    def run_check(self, label, fn):
        try:
            fn()
            self.checked.append(label)
        except (AuditError, KeyError, TypeError, ValueError, OSError) as error:
            # Error messages contain field locations, never the private value.
            self.errors.append(label + ': ' + str(error))

    def version_and_files(self):
        d, m = self.data, self.manifest
        require(d['aggregate_sha256'] == AGGREGATE_SHA, 'aggregate SHA differs from reviewed version')
        require(d['adapter_sha256'] == ADAPTER_SHA, 'adapter SHA differs from reviewed version')
        require(m['source']['site_data_sha256'] == SOURCE_SHA, 'source data SHA contract mismatch')
        require(m['source']['aggregate_sha256'] == AGGREGATE_SHA, 'manifest aggregate SHA mismatch')
        require(m['source']['adapter_sha256'] == ADAPTER_SHA, 'manifest adapter SHA mismatch')
        require(m['data_version'] == 'round2-phaseA-' + AGGREGATE_SHA[:12], 'data version mismatch')
        digest = m.get('public_data_sha256', m.get('data_sha256', m.get('data_sha')))
        require(digest == sha((self.root / 'data.json').read_bytes()), 'public data SHA mismatch')
        require(m['result_rows'] == 178 and m['comparison_groups'] == 4, 'manifest count mismatch')
        require(m['scientific_contract']['coverage'] == SCIENTIFIC_COVERAGE,
                'manifest scientific coverage must describe only the paired public cohort')
        require(m['public_scope'] == PUBLIC_SCOPE, 'manifest immutable Common40 scope differs')
        files = m.get('files')
        if files is not None:
            if isinstance(files, dict):
                entries = [(name, spec if isinstance(spec, str) else spec['sha256'])
                           for name, spec in files.items()]
            else:
                entries = [(spec.get('path', spec.get('name')), spec['sha256']) for spec in files]
            require(len({name for name, _ in entries}) == len(entries), 'duplicate manifest file')
            for name, digest in entries:
                require(name in PUBLISH_FILES and name != 'RELEASE_MANIFEST.json',
                        'manifest file is outside reviewed allowlist or is self-hashed')
                require(digest == sha((self.root / name).read_bytes()), 'manifest SHA mismatch: ' + name)
        for name in PUBLISH_FILES:
            path = self.root / name
            require(path.is_file() and not path.is_symlink(), 'missing or symlink public file: ' + name)
        for path in self.root.rglob('*'):
            rel = path.relative_to(self.root)
            if any(part in EXCLUDED_DIRS for part in rel.parts):
                continue
            if path.is_file():
                require(rel.as_posix() in PUBLISH_FILES, 'unreviewed file outside publication allowlist')

    def privacy_and_schema(self):
        d = self.data
        keys(d, {'schema_version', 'title', 'subtitle', 'updated_utc', 'status',
                 'aggregate_sha256', 'adapter_sha256', 'status_message', 'phases',
                 'datasets', 'results', 'comparisons', 'official_references',
                 'fairness', 'statistics', 'notes', 'downloads', 'public_scope'}, 'data')
        keys(d['public_scope'], set(PUBLIC_SCOPE), 'public_scope')
        require(d['public_scope'] == PUBLIC_SCOPE, 'paired public scope contract differs')
        for phase, info in d['phases'].items():
            require(phase in {'A', 'B'}, 'unknown phase')
            keys(info, {'label', 'status', 'description'}, 'phase.' + phase)
        for item in d['datasets']:
            keys(item, {'id', 'label', 'expected_motions'}, 'dataset')
        for row in d['results']:
            loc = 'result.' + row['id']
            keys(row, ROW_KEYS, loc)
            keys(row['checkpoint'], {'name', 'sha256'}, loc + '.checkpoint')
            keys(row['provenance'], {'source_sha256', 'config_sha256', 'protocol_sha256',
                                    'runtime', 'raw_links', 'evidence_hashes'}, loc + '.provenance')
            require(row['provenance'].get('raw_links') == [], loc + ': internal raw links remain')
            for evidence in row['provenance'].get('evidence_hashes', []):
                keys(evidence, {'label', 'sha256'}, loc + '.evidence')
            if 'pairing' in row:
                keys(row['pairing'], PAIRING_KEYS, loc + '.pairing')
            for failure in row['failures']:
                keys(failure, {'reason', 'count', 'denominator', 'unit'}, loc + '.failure')
            for video in row['videos']:
                self.video_schema(video, row)
        for item in d['downloads']:
            if 'source_runs' in item:
                self.video_schema(item)
            else:
                keys(item, {'label', 'url', 'sha256', 'access'}, 'download')
        for comparison in d['comparisons']:
            keys(comparison, COMPARISON_KEYS, 'comparison')
            keys(comparison['cohort_metadata'], {'strict_pair', 'metadata_status', 'source_provenance'}, 'cohort')
            for source in comparison['cohort_metadata']['source_provenance']:
                keys(source, {'source_repo', 'source_revision', 'source_manifest_sha256'}, 'cohort.source')
            for delta in comparison['paired_deltas'].values():
                keys(delta, {'value', 'ci95', 'unit', 'n_motions'}, 'paired_delta')
        for ref in d['official_references']:
            keys(ref, {'id', 'label', 'robot', 'dataset', 'status', 'context',
                       'checkpoint_cost_id', 'cost_scope', 'metrics', 'coverage', 'source'}, 'official_reference')
            keys(ref['source'], {'label', 'url', 'sha256', 'access'}, 'official_reference.source')
        for item in d['fairness']:
            keys(item, {'item', 'rp1', 'g1', 'status', 'evidence', 'phase', 'condition', 'mode'}, 'fairness')
        keys(d['statistics'], {'aggregation', 'ci_method', 'ci_scope', 'missing_policy',
                               'rank_policy', 'limitations'}, 'statistics')
        for loc, value in walk(d):
            if isinstance(value, str):
                require(not SECRET.search(value), loc + ': possible credential')
                require(not LOCAL_PATH.search(value), loc + ': absolute local path')
                require(not INFRA.search(value), loc + ': private infrastructure marker')
                require(not re.search(r'\b(?:localhost|127\.0\.0\.1)\b', value), loc + ': local host')
                for match in IP_LITERAL.finditer(value):
                    try:
                        address = ipaddress.ip_address(match.group())
                    except ValueError:
                        continue
                    require(not (address.is_private or address.is_loopback), loc + ': internal IP')
            if isinstance(value, dict):
                require('source_status' not in value, loc + ': private phase source status')
                for name, digest in value.items():
                    if name.endswith('_sha256') or name == 'sha256':
                        require(isinstance(digest, str) and (digest == '' or HASH.fullmatch(digest)),
                                loc + '.' + name + ': malformed SHA256')
        for name in PUBLISH_FILES:
            content = (self.root / name).read_text(encoding='utf-8')
            require(not SECRET.search(content), name + ': possible credential')
            # Generic localhost preview docs and privacy-detector source code are safe.
            if name in {'index.html', 'app.js', 'style.css', 'DATA_PROVENANCE.md',
                        'RELEASE_MANIFEST.json', 'hardware.json', 'hardware.csv',
                        'extreme5.json', 'extreme5.csv', 'fullwindow.json', 'fullwindow.csv'}:
                require(not LOCAL_PATH.search(content), name + ': absolute local path')
                # URL.hostname is a browser API used to label permissioned links.
                scanned = content.replace('.hostname', '') if name == 'app.js' else content
                require(not INFRA.search(scanned), name + ': private infrastructure marker')

    def video_schema(self, video, row=None):
        keys(video, VIDEO_KEYS, 'video')
        require(video.get('synchronized') is True and video.get('robot') == 'rp1_g1',
                'public video must show both robots on a synchronized timeline')
        runs = video.get('source_runs', [])
        require(isinstance(runs, list) and len(runs) == 2,
                'paired video must identify exactly two source runs')
        require({run['robot'] for run in runs} == {'rp1', 'g1'},
                'paired video source robots differ')
        episodes = []
        for run in runs:
            keys(run, SOURCE_RUN_KEYS, 'video.source_run')
            episode = self.episodes_by_id.get(run.get('episode_id'))
            require(episode is not None, 'video source episode is outside the retained paired cohort')
            for source_name, episode_name in [('robot', 'robot'), ('motion', 'motion_id'),
                                              ('dataset', 'dataset'), ('condition', 'condition'),
                                              ('mode', 'mode'), ('seed', 'seed')]:
                require(run.get(source_name) == episode[episode_name],
                        'video source run differs from retained episode: ' + source_name)
            require(video.get('clip') == episode['motion_id'], 'video clip differs from source motion')
            if row is not None:
                for name in ('phase', 'dataset', 'condition', 'mode'):
                    require(episode[name] == row[name], 'row video crosses an evaluation condition')
                if row['scope'] == 'per_motion':
                    require(episode['motion_id'] == row['motion_id'] and
                            episode['seed'] == row['seed'], 'row video motion/seed differs')
                else:
                    cohort = COHORTS.get((row['condition'], row['mode']))
                    require(cohort is not None and episode['seed'] in cohort[3],
                            'aggregate video seed lies outside its reviewed cohort')
                    seeds = sorted(cohort[3])
                    aggregate_seed = (str(seeds[0]) if len(seeds) == 1 else
                                      'pooled_' + '_'.join(str(seed) for seed in seeds))
                    require(row['seed'] == aggregate_seed,
                            'aggregate video does not match the row seed pool')
            episodes.append(episode)
        require(pair_key(episodes[0]) == pair_key(episodes[1]),
                'video source runs do not form an exact evaluation pair')
        if row is not None and row['scope'] == 'per_motion':
            require(row['id'] in {episode['id'] for episode in episodes},
                    'row video does not include the row episode')
        require(video.get('cloud_original_sha256_verified') is False,
                'video must retain unverified cloud byte-hash status')

    def public_media(self):
        media = read_json(self.root / 'media.json')
        keys(media, {'schema', 'render_revision', 'expected_common_motions',
                     'status', 'credits', 'items'}, 'public_media')
        require(media['schema'] == 'rp1-g1-public-media-v1' and
                media['expected_common_motions'] == 40, 'public media version/cohort mismatch')
        require(isinstance(media['items'], list), 'media items must be an array')
        # No new rendered asset has been accepted yet. A future integration must
        # add a reviewed asset allowlist and run/source mapping before publishing.
        require(media['status'] == 'awaiting_new_render' and not media['items'],
                'new public media assets require a reviewed publication contract')
        content = (self.root / 'media.json').read_text()
        require(not SECRET.search(content) and not LOCAL_PATH.search(content) and
                not INFRA.search(content), 'public media contains private information')

    def hardware_contract(self):
        # These are exact copies of the independently reviewed public projection.
        # No private model, checkpoint, raw CSV or physics input is read here.
        json_path, csv_path = self.root / 'hardware.json', self.root / 'hardware.csv'
        require(sha(json_path.read_bytes()) == HARDWARE_JSON_SHA,
                'hardware JSON differs from the frozen public whitelist projection')
        require(sha(csv_path.read_bytes()) == HARDWARE_CSV_SHA,
                'hardware CSV differs from the frozen public whitelist projection')
        hardware = read_json(json_path)
        require(set(hardware) == {'schema', 'title', 'dataset_asset_basis', 'per_robot',
                                  'joint_rows', 'field_definitions', 'applicability',
                                  'sources_appendix'}, 'hardware public root fields differ')
        require(hardware['schema'] == 'rp1-g1-public-hardware-comparison-v1',
                'hardware schema differs')
        require(hardware['dataset_asset_basis']['counts'] == {
            'rp1_actuated': 28, 'g1_actuated': 29, 'total_individual_robot_joints': 57,
            'anatomical_pairs': 28, 'comparison_rows': 29, 'g1_only': ['waist_pitch_joint']},
            'hardware joint/position counts differ')
        require(set(hardware['per_robot']) == {'rp1', 'g1'}, 'hardware robots differ')
        for robot, count, mass in [('rp1', 28, 40.72637536),
                                   ('g1', 29, 33.74104199999999)]:
            model = hardware['per_robot'][robot]
            require(model['actuated_joint_count'] == model['effective_actuator_count'] == count
                    and model['floating_base_dof'] == 6 and model['raw_MJCF_actuator_count'] == 0,
                    'hardware model actuator/base counts differ')
            require(model['model_mass_kg'] == mass and
                    model['model_mass_is_manufacturer_specification'] is False and
                    model['manufacturer_specification_status'] == 'unknown',
                    'hardware model mass/manufacturer boundary differs')
        definitions = hardware['field_definitions']
        for name, unit in {'effective_constraint_limits': 'rad / degree',
                           'model_mass_kg': 'kg', 'effort_limit_config_Nm': 'Nm',
                           'actuator_forcerange_Nm': 'Nm',
                           'velocity_limit_declared_rad_s': 'rad/s;另列degree/s',
                           'kp_Nm_per_rad': 'Nm/rad',
                           'kd_Nm_s_per_rad': 'Nm·s/rad'}.items():
            require(definitions[name]['unit'] == unit, 'hardware units differ: ' + name)
        rows = hardware['joint_rows']
        require(len(rows) == len({row['joint_name'] for row in rows}) == 29,
                'hardware must contain 29 unique anatomical positions')
        require(sum(row['rp1']['present'] for row in rows) == 28 and
                sum(row['g1']['present'] for row in rows) == 29 and
                sum(row['rp1']['present'] and row['g1']['present'] for row in rows) == 28,
                'hardware presence/pair counts differ')
        try:
            with csv_path.open(encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle, strict=True)
                columns = reader.fieldnames
                csv_rows = list(reader)
        except csv.Error as error:
            raise AuditError('hardware CSV cannot be parsed') from error
        require(len(csv_rows) == 29 and columns is not None and
                len(columns) == len(set(columns)) == 76 and
                not any(name.endswith(('_source_xml', '_source_line')) for name in columns),
                'hardware CSV shape/column privacy differs')

        def csv_cell(record, name, value):
            cell = record[name]
            if value is None:
                valid = cell == ''
            elif type(value) is bool:
                valid = cell.lower() == str(value).lower()
            elif type(value) in (int, float):
                valid = float(cell) == value
            else:
                valid = cell == value
            require(valid, 'hardware CSV/JSON value differs: ' + name)

        for row, record in zip(rows, csv_rows):
            csv_cell(record, 'joint_name', row['joint_name'])
            csv_cell(record, 'reference_pose_axis_dot', row['reference_pose_axis_dot'])
            csv_cell(record, 'rom_rp1_minus_g1_deg', row['rom_rp1_minus_g1_deg'])
            require(row['signed_q_ranges_directly_comparable'] is False,
                    'hardware must retain separate coordinate conventions')
            if row['rp1']['present'] and row['g1']['present']:
                require(row['mapping_status'] == 'paired_anatomical_label' and
                        record['mapping_status'] == 'SAME_ANATOMICAL_LABEL_DIFFERENT_KINEMATIC_CONVENTIONS',
                        'hardware anatomical mapping status differs')
            for robot in ('rp1', 'g1'):
                joint = row[robot]
                csv_cell(record, robot + '_present', joint['present'])
                if not joint['present']:
                    require(robot == 'rp1' and row['joint_name'] == 'waist_pitch_joint' and
                            joint['status'] == 'n/a' and row['mapping_status'] == 'g1_only_rp1_not_applicable'
                            and row['reference_pose_axis_dot'] is None and
                            row['rom_rp1_minus_g1_rad'] is None and row['rom_rp1_minus_g1_deg'] is None,
                            'unmatched waist pitch must remain not applicable')
                    require(record['mapping_status'] == 'G1_ONLY_RP1_NOT_APPLICABLE' and
                            record['rp1_training_soft_status'] == 'NOT_APPLICABLE_NO_JOINT' and
                            record['rp1_rated_peak_physical_status'] == 'NOT_APPLICABLE_NO_JOINT' and
                            all(record[name] == '' for name in columns if name.startswith('rp1_')
                                and name not in {'rp1_present', 'rp1_training_soft_status',
                                                 'rp1_rated_peak_physical_status'}),
                            'unmatched waist pitch CSV must retain blank numeric values')
                    continue
                require(joint['status'] == 'available', 'present hardware joint unavailable')
                limits, control, actuator = (joint['effective_constraint_limits'],
                                             joint['policy_control'], joint['effective_actuator'])
                require(limits['jnt_limited'] is True and
                        limits['lower_rad'] < limits['upper_rad'] and
                        math.isclose(limits['rom_rad'], limits['upper_rad'] - limits['lower_rad'],
                                     abs_tol=1e-12), 'hardware ROM/range differs')
                for name in ('lower', 'upper', 'rom'):
                    for unit in ('rad', 'deg'):
                        numeric(limits[name + '_' + unit], 'hardware.range', nullable=False)
                        csv_cell(record, robot + '_' + name + '_' + unit, limits[name + '_' + unit])
                    require(math.isclose(limits[name + '_deg'], math.degrees(limits[name + '_rad']),
                                         abs_tol=1e-10), 'hardware degree conversion differs')
                force = actuator['actuator_forcerange_Nm']
                require(actuator['actuator_forcelimited'] is True and
                        actuator['actuator_ctrllimited'] is False and
                        actuator['gear'] == [1., 0., 0., 0., 0., 0.] and
                        force[0] == -force[1] and force[1] > 0 and
                        math.isclose(force[1], control['effort_limit_config_Nm'], abs_tol=1e-5),
                        'hardware effective PD force cap differs')
                require(control['velocity_limit_runtime_clamp'] is False and
                        control['target_hard_range_clipped'] is False and
                        math.isclose(control['velocity_limit_declared_deg_s'],
                                     math.degrees(control['velocity_limit_declared_rad_s']), abs_tol=1e-9),
                        'hardware declared velocity/runtime distinction differs')
                for column, value in {
                    'effort_config_Nm': control['effort_limit_config_Nm'],
                    'velocity_declared_rad_s': control['velocity_limit_declared_rad_s'],
                    'velocity_declared_deg_s': control['velocity_limit_declared_deg_s'],
                    'forcerange_lower_Nm': force[0], 'forcerange_upper_Nm': force[1],
                    'actuator_forcelimited': actuator['actuator_forcelimited'],
                    'actuator_ctrllimited': actuator['actuator_ctrllimited'],
                    'jnt_limited': limits['jnt_limited'],
                    'kp_Nm_rad': control['kp_Nm_per_rad'],
                    'kd_Nm_s_rad': control['kd_Nm_s_per_rad'],
                    'action_scale': control['action_scale_rad_per_unit'],
                    'default_target_rad': control['default_zero_action_target_rad'],
                    'armature_kg_m2': actuator['armature_kg_m2'],
                    'frictionloss_Nm': actuator['frictionloss_Nm'],
                    'passive_viscous_damping_Nm_s_rad': actuator['passive_viscous_damping_Nm_s_rad']}.items():
                    csv_cell(record, robot + '_' + column, value)
                coordinate = joint['coordinate_contract']
                for column, field, components in [
                    ('axis_local_', 'axis_in_child_body_frame', 'xyz'),
                    ('axis_root_ref_', 'axis_in_model_root_at_reference_pose', 'xyz'),
                    ('mount_quat_', 'child_mount_in_parent_quat_wxyz', 'wxyz')]:
                    for component, value in zip(components, coordinate[field]):
                        csv_cell(record, robot + '_' + column + component, value)
                manufacturer = joint['manufacturer_physical_spec']
                require(manufacturer['status'] == 'unknown' and
                        all(value is None for key, value in manufacturer.items() if key != 'status'),
                        'manufacturer hardware specifications must remain unknown')
                csv_cell(record, robot + '_rated_peak_physical_status', 'UNKNOWN')
                soft = joint['training_soft_limit']
                require(soft['runtime_training_tensor_snapshot_verified'] is False and
                        (soft['factor'] == 0.9 if robot == 'rp1' else
                         soft['factor'] is None and soft['derived_rom_rad'] is None),
                        'hardware saved/unknown training limit boundary differs')
                csv_cell(record, robot + '_training_soft_status', soft['status'])
                for bound in ('lower', 'upper'):
                    csv_cell(record, robot + '_training_soft_derived_' + bound + '_rad',
                             soft['derived_' + bound + '_rad'])
        content = json_path.read_text() + csv_path.read_text()
        require(not SECRET.search(content) and not LOCAL_PATH.search(content) and
                not INFRA.search(content) and
                not re.search(r'checkpoint_latest|\b[0-9a-f]{64}\b|\bH200\b|luobo1|zp-nc67|'
                              r'password|credential|private_key', content, re.I),
                'hardware public files contain private information')
        for source in hardware['sources_appendix']:
            self.link(source['url'], 'hardware.source')

    def extension_manifest(self):
        require(self.manifest.get('extensions') == EXTENSIONS,
                'manifest reviewed extension identities differ')
        require(self.manifest.get('display_scope') == DISPLAY_SCOPE,
                'manifest combined display scope differs; scientific groups remain separate')

    def extreme_contract(self):
        # Keep the new cohort separate from immutable Common40 data/source checks.
        # Exact public byte hashes pin every result, CI, failure and diagnostic.
        json_path, csv_path = self.root / 'extreme5.json', self.root / 'extreme5.csv'
        require(sha(json_path.read_bytes()) == EXTREME_JSON_SHA,
                'Extreme5 JSON differs from the reviewed public projection')
        require(sha(csv_path.read_bytes()) == EXTREME_CSV_SHA,
                'Extreme5 CSV differs from the reviewed public projection')
        extension = read_json(json_path)
        require(set(extension) == {'schema', 'dataset', 'title', 'count_label',
                                  'aggregate_sha256', 'sample_set_sha256',
                                  'scientific_numeric_protocol_sha256', 'paired_samples',
                                  'results', 'comparisons', 'metrics', 'methods', 'analysis',
                                  'applicability', 'diagnostics', 'media',
                                  'lafan40_statistics_changed'}, 'Extreme5 public fields differ')
        require(extension['schema'] == 'rp1-g1-public-extreme5-handoff-v1' and
                extension['dataset'] == 'extreme5' and
                extension['aggregate_sha256'] == EXTREME_AGGREGATE_SHA and
                extension['sample_set_sha256'] == EXTREME_SAMPLE_SHA and
                extension['scientific_numeric_protocol_sha256'] == EXTREME_NUMERIC_SHA and
                extension['lafan40_statistics_changed'] is False,
                'Extreme5 scientific version or Common40 independence differs')
        require(extension['media'] == {'available': False, 'state': '待制作', 'items': []},
                'Extreme5 new media requires separate publication review')
        units = {'body_pos_mm': 'mm', 'body_ori_rad': 'rad', 'root_pos_m': 'm',
                 'wrist_pos_mm': 'mm', 'wrist_ori_rad': 'rad',
                 'episode_return': 'unitless', 'progress_pct': '%'}
        require(set(extension['metrics']) == set(units), 'Extreme5 metric definitions differ')
        for name, unit in units.items():
            require(extension['metrics'][name] == {
                'unit': unit, 'delta_unit': 'pp' if name == 'progress_pct' else unit,
                'higher_is_better': name in {'episode_return', 'progress_pct'}},
                'Extreme5 metric units/direction differ: ' + name)
        methods = extension['methods']
        require((methods['reference_hz'], methods['physics_hz'], methods['start_frame'],
                 methods['seed'], methods['landmarks'], methods['recovery_added']) ==
                (50, 200, 0, 0, 'common14_ankle_roll', False), 'Extreme5 execution methods differ')
        require(methods['bootstrap'] == {'unit': 'motion', 'resamples': 10000,
                                        'seed': 20261013, 'confidence': 0.95},
                'Extreme5 bootstrap contract differs')
        results = extension['results']
        require(len(results) == len({row['id'] for row in results}) == 12 and
                Counter(row['scope'] for row in results) == {'aggregate': 2, 'per_motion': 10},
                'Extreme5 result scope counts differ')
        require(not {row['id'] for row in results}.intersection(row['id'] for row in self.data['results']),
                'Extreme5 IDs collide with Common40')
        episodes = {row['id']: row for row in results if row['scope'] == 'per_motion'}
        aggregates = {row['robot']: row for row in results if row['scope'] == 'aggregate'}
        require(set(aggregates) == {'rp1', 'g1'}, 'Extreme5 aggregate robots differ')
        pairs = {}
        for row in results:
            loc = 'extreme5.' + row['id']
            require((row['phase'], row['dataset'], row['condition'], row['mode'], row['seed']) ==
                    ('A', 'extreme5', 'nominal', 'native_position', '0') and
                    row['robot'] in {'rp1', 'g1'} and row['status'] == 'complete',
                    'Extreme5 frozen row identity/status differs')
            require(row['pairing']['comparison_id'] == EXTREME_ID and
                    row['pairing']['sample_set_sha256'] == EXTREME_SAMPLE_SHA and
                    row['pairing']['verified'] is True, 'Extreme5 row pair identity differs')
            require(row['provenance']['protocol_sha256'] == EXTREME_NUMERIC_SHA and
                    row['provenance']['runtime'] == '50Hz_reference_200Hz_physics',
                    'Extreme5 shared numeric protocol/runtime differs')
            for field in ('coverage', 'paired_coverage'):
                coverage(row[field], loc + '.' + field)
                n = 5 if row['scope'] == 'aggregate' else 1
                require(row[field]['numerator'] == row[field]['denominator'] == n,
                        'Extreme5 coverage differs')
            require(set(row['metrics']) == METRICS, 'Extreme5 missing metric')
            unknown = row['metrics']['gpu_train_hours']
            require(unknown['value'] is None and unknown['reason'] and
                    unknown['sample_set_sha256'] == '' and 'ci' not in unknown,
                    'Extreme5 training cost must retain unknown status')
            coverage(unknown['coverage'], loc + '.gpu_train_hours.coverage')
            for name, unit in units.items():
                cell = row['metrics'][name]
                numeric(cell['value'], loc + '.' + name, nullable=False)
                require(cell['reason'] and cell['sample_set_sha256'] == EXTREME_SAMPLE_SHA,
                        'Extreme5 metric sample/reason differs')
                coverage(cell['coverage'], loc + '.' + name + '.coverage')
                require(cell['coverage']['numerator'] == cell['coverage']['denominator'] == n,
                        'Extreme5 metric denominator differs')
                if name == 'progress_pct':
                    require(0 <= cell['value'] <= 100, 'Extreme5 progress outside 0–100')
                if row['scope'] == 'aggregate':
                    ci = cell['ci']
                    keys(ci, CI_KEYS, loc + '.' + name + '.ci')
                    numeric(ci['low'], loc + '.ci.low', nullable=False)
                    numeric(ci['high'], loc + '.ci.high', nullable=False)
                    require(ci['low'] <= ci['high'] and ci['level'] == 0.95 and
                            ci['unit'] == unit and ci['method'] == 'paired motion percentile bootstrap'
                            and ci['resampling_unit'] == 'motion' and ci['n_clusters'] == 5
                            and ci['n_seeds'] == 1 and ci['resamples'] == 10000 and ci['reason'],
                            'Extreme5 metric CI/unit/sample contract differs')
                else:
                    require('ci' not in cell, 'Extreme5 episode must not invent an episode CI')
            if row['scope'] == 'aggregate':
                require(row['id'] == EXTREME_ID + '_' + row['robot'] and row['motion_id'] is None and
                        row['no_threshold_failure'] == {'numerator': 0, 'denominator': 5, 'unit': 'motions'},
                        'Extreme5 aggregate/no-threshold-failure boundary differs')
                continue
            require(row['motion_id'] in EXTREME_FRAMES and row['rollout_complete'] is True
                    and row['censored'] is False, 'Extreme5 complete replay/source motion differs')
            identity = pair_key(row)
            members = pairs.setdefault(identity, {})
            require(row['robot'] not in members, 'Extreme5 duplicate robot pairing key')
            members[row['robot']] = row
            frames = EXTREME_FRAMES[row['motion_id']]
            extra = int(row['robot'] == 'g1' and row['motion_id'] in {
                'Take_146_Skeleton0', 'Take_148_Skeleton0', 'Take_149_Skeleton0'})
            require(row['source_window'] == {'start_frame': 0, 'end_exclusive': frames,
                                             'native_frames': frames + extra, 'reference_hz': 50},
                    'Extreme5 common endpoint/native source window differs')
            execution = (EXTREME_EXECUTION_V1_SHA if row['robot'] == 'rp1' and
                         row['motion_id'] == 'Take_143_Skeleton0' else EXTREME_EXECUTION_V2_SHA)
            require(row['provenance']['execution_protocol_sha256'] == execution,
                    'Extreme5 original execution protocol identity differs')
            failure = row['failure']
            require(failure['category'] in {'height', 'gravity', 'both'} and
                    type(failure['first_policy_index']) is int and
                    0 <= failure['first_policy_index'] < frames - 1,
                    'Extreme5 natural failure record missing/invalid')
            numeric(failure['source_time_s'], loc + '.failure.source_time_s', nullable=False)
            numeric(failure['simulation_time_s'], loc + '.failure.simulation_time_s', nullable=False)
            require(math.isclose(failure['source_time_s'],
                                 (failure['first_policy_index'] + 1) / 50, abs_tol=1e-10),
                    'Extreme5 first failure source clock differs')
        require(len(pairs) == 5 and all(set(members) == {'rp1', 'g1'} for members in pairs.values()),
                'Extreme5 must contain five exact RP1/G1 pairs')
        samples = extension['paired_samples']
        require(len(samples) == 5 and {sample['motion'] for sample in samples} == set(EXTREME_FRAMES),
                'Extreme5 sample motion identities differ')
        for sample in samples:
            require(sample['seed'] == 0 and set(sample['runs']) == {'rp1', 'g1'},
                    'Extreme5 paired sample seed/robots differ')
            for robot, run_id in sample['runs'].items():
                row = episodes.get(run_id)
                require(row is not None and (row['robot'], row['motion_id'], row['seed']) ==
                        (robot, sample['motion'], '0'), 'Extreme5 sample/run binding differs')
        require(len(extension['comparisons']) == 1, 'Extreme5 comparison count differs')
        comparison = extension['comparisons'][0]
        require(comparison['id'] == EXTREME_ID and comparison['verified'] is True
                and comparison['provisional'] is False and comparison['expected_paired_motions'] == 5
                and comparison['sample_set_sha256'] == EXTREME_SAMPLE_SHA
                and set(comparison['expected_participants']) == {EXTREME_ID + '_' + r for r in aggregates}
                and set(comparison['paired_deltas']) == set(units), 'Extreme5 comparison identities differ')
        for name, unit in units.items():
            delta = comparison['paired_deltas'][name]
            numeric(delta['value'], 'extreme5.delta.' + name, nullable=False)
            require(delta['n_motions'] == 5 and delta['unit'] == ('pp' if name == 'progress_pct' else unit)
                    and len(delta['ci95']) == 2, 'Extreme5 paired CI/unit/denominator differs')
            for value in delta['ci95']:
                numeric(value, 'extreme5.delta.ci95', nullable=False)
            require(delta['ci95'][0] <= delta['ci95'][1], 'Extreme5 paired CI reversed')
            require(math.isclose(delta['value'], aggregates['rp1']['metrics'][name]['value'] -
                                 aggregates['g1']['metrics'][name]['value'], abs_tol=1e-12),
                    'Extreme5 delta must be RP1 minus G1')
        try:
            with csv_path.open(encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle, strict=True)
                csv_rows = list(reader)
        except csv.Error as error:
            raise AuditError('Extreme5 CSV cannot be parsed') from error
        require(reader.fieldnames == ['run_id', 'robot', 'motion_id', 'motion_label', 'dataset',
                                      'condition', 'seed', *units, 'failure_category',
                                      'failure_time_s', 'common_frames'] and
                len(csv_rows) == len({row['run_id'] for row in csv_rows}) == 10,
                'Extreme5 CSV columns/episode identities differ')
        require({row['run_id'] for row in csv_rows} == set(episodes), 'Extreme5 CSV episode set differs')
        for record in csv_rows:
            row = episodes[record['run_id']]
            require(all(record[name] == row[name] for name in
                        ('robot', 'motion_id', 'dataset', 'condition', 'seed')) and
                    record['motion_label'] == row['label'] and
                    record['failure_category'] == row['failure']['category'] and
                    float(record['failure_time_s']) == row['failure']['source_time_s'] and
                    int(record['common_frames']) == row['source_window']['end_exclusive'],
                    'Extreme5 CSV identity/failure/source window differs')
            for name in units:
                require(float(record[name]) == row['metrics'][name]['value'],
                        'Extreme5 CSV metric differs: ' + name)
        content = json_path.read_text() + csv_path.read_text()
        require(not SECRET.search(content) and not LOCAL_PATH.search(content) and
                not INFRA.search(content), 'Extreme5 public files contain private information')
        combined = self.data['results'] + results
        require(len(combined) == 190 and
                len({row['motion_id'] for row in combined if row['scope'] == 'per_motion'}) == 45 and
                Counter(row['scope'] for row in combined) == {'aggregate': 10, 'per_motion': 180} and
                len(self.data['comparisons']) + len(extension['comparisons']) == 5,
                'combined display scope differs; cohorts must remain separate')

    def fullwindow_contract(self):
        json_path, csv_path = self.root / 'fullwindow.json', self.root / 'fullwindow.csv'
        require(sha(json_path.read_bytes()) == FULLWINDOW_JSON_SHA and json_path.stat().st_size == 407473,
                'fullwindow JSON differs from the terminal-reviewed public supplement')
        require(sha(csv_path.read_bytes()) == FULLWINDOW_CSV_SHA and csv_path.stat().st_size == 88651,
                'fullwindow CSV differs from the terminal-reviewed public supplement')
        full = read_json(json_path)
        require(set(full) == {'schema', 'status', 'metric_window', 'counts', 'episode_semantic_join_key',
                              'paired_case_definition', 'episodes', 'comparisons', 'primary_comparison_ids',
                              'secondary_comparison_ids', 'metric_definitions', 'diagnostic_definitions', 'methods'},
                'fullwindow supplemental schema fields differ')
        require(full['schema'] == 'rp1-g1-public-fullwindow-handoff-v1' and
                full['status'] == 'independently_verified' and full['metric_window'] == FULLWINDOW_WINDOW and
                full['episode_semantic_join_key'] == list(FULLWINDOW_JOIN), 'fullwindow version/join differs')
        require(full['counts'] == {
            'physical_episode_records': 180, 'paired_cases': 90, 'unique_motion_ids': 45,
            'comparison_groups': 5, 'aggregate_views': 10, 'maximum_display_rows_with_aggregate_views': 190,
            'lafan40_episode_records': 170, 'lafan40_paired_cases': 85,
            'extreme5_episode_records': 10, 'extreme5_paired_cases': 5}, 'fullwindow immutable episode scope differs')
        units = {name: 'mm' if name.endswith('_mm') else 'rad' for name in FULLWINDOW_METRICS}
        require(set(full['metric_definitions']) == set(units), 'only four full body/wrist errors are reviewed')
        for name, unit in units.items():
            definition = full['metric_definitions'][name]
            require(definition['unit'] == unit and definition['higher_is_better'] is False and
                    definition['role'] == 'primary_fullwindow_error', 'fullwindow metric role/units differ')
        diagnostic_mapping = {
            'progress': ('progress_pct', 100, 'fraction'),
            'local_body_tracking_error': ('body_pos_mm', 1000, 'm'),
            'local_body_orientation_error': ('body_ori_rad', 1, 'rad'),
            'wrist_tracking_error': ('wrist_pos_mm', 1000, 'm'),
            'wrist_orientation_error': ('wrist_ori_rad', 1, 'rad'),
            'normalized_tracking_return': ('episode_return', 1, 'dimensionless'),
            'root_final_error_norm': ('root_pos_m', 1, 'm'),
        }
        require(set(full['diagnostic_definitions']) == set(diagnostic_mapping) | {'gpu_train_hours'},
                'fullwindow original diagnostic definitions differ')
        for name, (_, _, unit) in diagnostic_mapping.items():
            require(full['diagnostic_definitions'][name]['unit'] == unit, 'original diagnostic units differ')
        require(full['methods']['bootstrap'] == {
            'resampling_unit': 'paired_motion', 'generator': 'PCG64', 'seed': 20261013,
            'resamples': 10000, 'confidence': 0.95, 'quantile_method': 'linear',
            'reset_per_group_and_metric': True, 'shared_indices_for_robots': True,
            'delta_direction': 'RP1 minus G1'}, 'fullwindow paired motion CI protocol differs')
        extreme = read_json(self.root / 'extreme5.json')
        old_episodes = list(self.episodes_by_id.values()) + [
            row for row in extreme['results'] if row['scope'] == 'per_motion']
        originals = {fullwindow_join_key(row): row for row in old_episodes}
        require(len(old_episodes) == len(originals) == 180, 'old supplemental join is not one-to-one')
        rows = full['episodes']
        joined = {fullwindow_join_key(row): row for row in rows}
        require(len(rows) == len(joined) == 180 and set(joined) == set(originals),
                'fullwindow must join the same 180 original episodes without appending a new cohort')
        episode_fields = set(FULLWINDOW_JOIN) | {'phase', 'effective_condition', 'scope', 'run_id',
            'scientific_selected_case_id', 'metric_window', 'full_recorded_frames', 'reference_common_frames',
            'full_reference_start_s', 'full_reference_end_s', *FULLWINDOW_METRICS, *diagnostic_mapping,
            'threshold_failure', 'first_failure_policy_index', 'first_failure_reference_time_s',
            'first_failure_physics_time_s', 'failure_category', 'root_endpoint_motion_t',
            'root_endpoint_reference_time_s', 'root_endpoint_physics_time_s', 'root_endpoint_scope', 'gpu_train_hours'}
        runs, cases = {}, {}
        new_value_checks = old_value_checks = 0
        for key, row in joined.items():
            require(set(row) == episode_fields and row['scope'] == 'per_motion' and
                    type(row['seed']) is int and row['effective_condition'] == row['condition'] and
                    row['metric_window'] == FULLWINDOW_WINDOW, 'fullwindow episode shape/identity differs')
            require(re.fullmatch(r'[0-9a-f]{24}', row['run_id']) and row['run_id'] not in runs,
                    'fullwindow opaque run aliases are missing/duplicated')
            require(re.fullmatch(r'case_[0-9a-f]{24}', row['scientific_selected_case_id']),
                    'fullwindow case alias malformed')
            runs[row['run_id']] = row
            case_key = key[:3] + key[4:]
            members = cases.setdefault(case_key, {})
            require(row['robot'] in {'rp1', 'g1'} and row['robot'] not in members,
                    'fullwindow duplicate robot for the same semantic case')
            members[row['robot']] = row
            frames = row['reference_common_frames']
            require(type(frames) is int and frames > 2 and row['full_recorded_frames'] == frames - 1 and
                    row['full_reference_start_s'] == .02 and
                    math.isclose(row['full_reference_end_s'], (frames - 1) / 50, abs_tol=1e-10),
                    'fullwindow must include every 50Hz first-substep frame after initialization')
            for name in units:
                numeric(row[name], 'fullwindow.' + name, nullable=False)
                require(row[name] >= 0, 'fullwindow error is negative')
                new_value_checks += 1
            for name, (alias, scale, _) in diagnostic_mapping.items():
                numeric(row[name], 'fullwindow.original.' + name, nullable=False)
                require(row[name] * scale == originals[key]['metrics'][alias]['value'],
                        'fullwindow original diagnostic/display mapping changed: ' + name)
                old_value_checks += 1
            require(0 <= row['progress'] <= 1 and row['gpu_train_hours'] is None,
                    'original Progress/training-cost boundary differs')
            require(type(row['threshold_failure']) is bool, 'threshold failure must be a boolean')
            failure_fields = ('first_failure_policy_index', 'first_failure_reference_time_s',
                              'first_failure_physics_time_s', 'failure_category')
            if not row['threshold_failure']:
                require(all(row[name] is None for name in failure_fields),
                        'absent first failure must preserve explicit nulls')
            else:
                index = row['first_failure_policy_index']
                require(type(index) is int and 0 <= index < frames - 1 and
                        row['failure_category'] in {'height', 'gravity', 'both'} and
                        math.isclose(row['first_failure_reference_time_s'], (index + 1) / 50, abs_tol=1e-10),
                        'original first failure/clock differs')
                numeric(row['first_failure_physics_time_s'], 'fullwindow.failure.physics_time', nullable=False)
            require(row['root_endpoint_scope'] == 'last_valid_same_time_frame' and
                    row['root_endpoint_motion_t'] == frames - 2 and
                    math.isclose(row['root_endpoint_reference_time_s'], row['root_endpoint_motion_t'] / 50,
                                 abs_tol=1e-10), 'original root endpoint differs from its retained raw clock')
            numeric(row['root_endpoint_physics_time_s'], 'fullwindow.root.physics_time', nullable=False)
            # Preserve the recorded physics clock. It is not the reference clock
            # or the last full-window body/wrist sample, and must not be replaced.
            require(0 < row['root_endpoint_reference_time_s'] - row['root_endpoint_physics_time_s'] < .02,
                    'original root physics/reference clock relationship differs')
        require(new_value_checks == 720 and old_value_checks == 1260, 'fullwindow value coverage differs')
        require(len(cases) == 90 and len({row['motion_id'] for row in rows}) == 45,
                'fullwindow pair/motion count differs')
        require(Counter(row['dataset'] for row in rows) == {'lafan40': 170, 'extreme5': 10},
                'fullwindow datasets must retain original physical episode counts')
        for members in cases.values():
            require(set(members) == {'rp1', 'g1'} and
                    members['rp1']['scientific_selected_case_id'] == members['g1']['scientific_selected_case_id'],
                    'fullwindow case must identify both original robots')
            require(all(members['rp1'][name] == members['g1'][name] for name in
                        ('full_recorded_frames', 'reference_common_frames', 'full_reference_start_s',
                         'full_reference_end_s')), 'fullwindow paired complete source windows differ')
        require(len(full['comparisons']) == 5 and
                set(full['primary_comparison_ids']) == {s[0] for s in FULLWINDOW_COHORTS.values() if s[4] == 'primary'}
                and set(full['secondary_comparison_ids']) == {s[0] for s in FULLWINDOW_COHORTS.values() if s[4] == 'secondary'},
                'fullwindow must retain two primary and three secondary groups')
        seen_cases = set()
        for comparison in full['comparisons']:
            group = tuple(comparison[name] for name in ('dataset', 'condition', 'mode'))
            spec = FULLWINDOW_COHORTS.get(group)
            require(spec is not None, 'fullwindow unreviewed dataset/condition/mode group')
            cid, n_cases, n_motions, seeds, role, sample_sha = spec
            require(comparison['id'] == cid and comparison['phase'] == 'A' and
                    comparison['effective_condition'] == comparison['condition'] and
                    comparison['metric_window'] == FULLWINDOW_WINDOW and comparison['role'] == role and
                    comparison['paired_cases'] == n_cases and comparison['episode_records'] == 2 * n_cases and
                    comparison['n_unique_motions'] == comparison['expected_paired_motions'] == n_motions and
                    comparison['matched_seed_set'] == seeds and comparison['expected_participants'] == ['rp1', 'g1'],
                    'fullwindow group coverage/seed/motion denominator differs')
            samples = comparison['sample_set']
            require(len(samples) == n_cases and comparison['sample_set_sha256'] == sample_sha and
                    sha(json.dumps(samples, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()) == sample_sha,
                    'fullwindow reviewed paired sample identity differs')
            for sample in samples:
                case_key = group + (sample['motion_id'], strict_seed(sample['seed']))
                require(case_key in cases and case_key not in seen_cases and
                        set(sample['participants']) == {'rp1', 'g1'}, 'fullwindow sample case duplicated/unmatched')
                seen_cases.add(case_key)
                for robot, run_id in sample['participants'].items():
                    require(cases[case_key][robot]['run_id'] == run_id and
                            cases[case_key][robot]['scientific_selected_case_id'] == sample['scientific_selected_case_id'],
                            'fullwindow paired sample/run alias binding differs')
            require(set(comparison['robot_means']) == set(comparison['paired_deltas']) ==
                    set(comparison['paired_motion_values']) == set(units), 'fullwindow group metric columns differ')
            for name, unit in units.items():
                motions = comparison['paired_motion_values'][name]
                require(len(motions) == len({x['motion_id'] for x in motions}) == n_motions,
                        'fullwindow repeated seeds must not expand independent motion count')
                mean = comparison['robot_means'][name]
                delta = comparison['paired_deltas'][name]
                require(mean['unit'] == delta['unit'] == unit and mean['higher_is_better'] is False
                        and delta['n_motions'] == n_motions, 'fullwindow CI unit/denominator differs')
                for item in motions:
                    require(item['seeds'] == seeds and item['repeats_per_robot'] == len(seeds),
                            'fullwindow within-motion seed weighting differs')
                    for robot in ('rp1', 'g1'):
                        values = [cases[group + (item['motion_id'], seed)][robot][name] for seed in seeds]
                        require(math.isclose(item[robot], math.fsum(values) / len(values), abs_tol=1e-10),
                                'fullwindow motion value differs from its complete original seed group')
                    require(math.isclose(item['delta_rp1_minus_g1'], item['rp1'] - item['g1'], abs_tol=1e-10),
                            'fullwindow motion delta must be RP1 minus G1')
                for cell in [mean['rp1'], mean['g1'], delta]:
                    numeric(cell['value'], 'fullwindow.summary.value', nullable=False)
                    require(len(cell['ci95']) == 2, 'fullwindow CI bounds must have two values')
                    for value in cell['ci95']:
                        numeric(value, 'fullwindow.summary.ci95', nullable=False)
                    require(cell['ci95'][0] <= cell['ci95'][1], 'fullwindow CI reversed')
                for robot in ('rp1', 'g1'):
                    require(math.isclose(mean[robot]['value'], math.fsum(x[robot] for x in motions) / n_motions,
                                         abs_tol=1e-10), 'fullwindow group mean must weight motions equally')
                require(math.isclose(delta['value'], mean['rp1']['value'] - mean['g1']['value'], abs_tol=1e-10),
                        'fullwindow paired group delta must be RP1 minus G1')
        require(seen_cases == set(cases), 'fullwindow samples must partition all 90 cases across five groups')
        try:
            with csv_path.open(encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle, strict=True)
                csv_rows = list(reader)
        except csv.Error as error:
            raise AuditError('fullwindow CSV cannot be parsed') from error
        require(reader.fieldnames == list(rows[0]) and len(csv_rows) == 180 and len(reader.fieldnames) == 37,
                'fullwindow CSV must preserve the exact 180 by 37 supplemental table')
        for record, row in zip(csv_rows, rows):
            for name, value in row.items():
                text = record[name]
                valid = (text == '' if value is None else text.lower() == str(value).lower() if type(value) is bool
                         else strict_seed(text) == value if name == 'seed'
                         else float(text) == value if type(value) in (int, float) else text == value)
                require(valid, 'fullwindow CSV/JSON value differs: ' + name)
        content = json_path.read_text() + csv_path.read_text()
        require(not SECRET.search(content) and not LOCAL_PATH.search(content) and not INFRA.search(content),
                'fullwindow supplement contains private information')
        self.fullwindow_value_checks = {'new_values': new_value_checks, 'old_diagnostics': old_value_checks,
                                       'csv_fields': 180 * 37}

    def counts_and_missing(self):
        rows = self.data['results']
        # 511 source display rows = 18 aggregate + 493 per-motion. The public
        # intersection is 178 display rows, not 178 independent experiments.
        require(len(rows) == 178 and len({row['id'] for row in rows}) == 178,
                'expected 178 unique paired result IDs')
        require(Counter(row['scope'] for row in rows) == {'aggregate': 8, 'per_motion': 170},
                'paired scope counts changed')
        motions = [row for row in rows if row['scope'] == 'per_motion']
        require(all(row['dataset'] == 'lafan40' for row in rows), 'unpaired dataset remains public')
        require(len({row['motion_id'] for row in motions}) == 40, 'expected 40 unique common motions')
        require(self.data['official_references'] == [], 'single-robot official references remain public')
        require(len(self.data['datasets']) == 1 and self.data['datasets'][0]['id'] == 'lafan40' and
                self.data['datasets'][0]['expected_motions'] == 40, 'dataset scope must be common LAFAN40')
        require(all(row['phase'] == 'A' for row in rows), 'Phase B result rows are prohibited before training')
        require(self.data['phases']['B']['status'] == 'blocked', 'Phase B boundary changed')
        for row in rows + self.data['official_references']:
            metric_cells(row['metrics'], row['id'] + '.metrics')
            coverage(row['coverage'], row['id'] + '.coverage')
            if row in rows:
                coverage(row['paired_coverage'], row['id'] + '.paired_coverage')
                require(row['metrics']['gpu_train_hours']['value'] is None, 'measured training cost remains unknown')
                if row['status'] == 'partial':
                    require(all(cell['value'] is None for cell in row['metrics'].values()),
                            'censored record must not supply a fabricated score')
        for comparison in self.data['comparisons']:
            for delta in comparison['paired_deltas'].values():
                numeric(delta['value'], 'comparison.delta.value')
                bounds = delta['ci95']
                if bounds is None:
                    require(comparison.get('reason'), 'missing paired CI lacks comparison reason')
                else:
                    require(isinstance(bounds, list) and len(bounds) == 2, 'paired CI shape')
                    for value in bounds:
                        numeric(value, 'comparison.delta.ci95', nullable=False)
                    require(bounds[0] <= bounds[1], 'paired CI reversed')
                if delta['value'] is None:
                    require(comparison.get('reason') and bounds is None, 'missing paired value/CI reason')

    def exact_episode_pairs(self):
        episodes = list(self.episodes_by_id.values())
        pairs = {}
        for row in episodes:
            require(row['robot'] in {'rp1', 'g1'}, 'unknown paired robot')
            require(isinstance(row['motion_id'], str) and row['motion_id'], 'missing paired motion identity')
            require(type(row['seed']) is int, 'paired episode seed must be an exact integer')
            require(HASH.fullmatch(row['provenance']['protocol_sha256']) and
                    isinstance(row['provenance']['runtime'], str) and row['provenance']['runtime'].strip(),
                    'paired episode protocol/runtime identity is missing')
            identity = pair_key(row)
            members = pairs.setdefault(identity, {})
            require(row['robot'] not in members, 'duplicate robot for the same exact pairing key')
            members[row['robot']] = row
        require(len(pairs) == 85 and all(set(members) == {'rp1', 'g1'} for members in pairs.values()),
                'expected 85 exact RP1/G1 pairs; no forced or one-sided matches')
        expected_counts = {cohort: spec[1] * 2 for cohort, spec in COHORTS.items()}
        require(Counter((row['condition'], row['mode']) for row in episodes) == expected_counts,
                'paired episode cohort counts changed')
        for cohort, (comparison_id, n_cases, n_motions, seeds, sample) in COHORTS.items():
            selected = [row for row in episodes if (row['condition'], row['mode']) == cohort]
            identities = {pair_key(row) for row in selected}
            require(len(identities) == n_cases, 'cohort exact pair count changed: ' + comparison_id)
            for robot in ('rp1', 'g1'):
                members = [row for row in selected if row['robot'] == robot]
                motion_ids = {row['motion_id'] for row in members}
                require(len(motion_ids) == n_motions and {row['seed'] for row in members} == seeds,
                        'cohort motion/seed coverage changed: ' + comparison_id)
                require({(row['motion_id'], row['seed']) for row in members} ==
                        {(motion, seed) for motion in motion_ids for seed in seeds},
                        'cohort must retain its complete reviewed seed set: ' + comparison_id)
            aggregates = [row for row in self.data['results'] if row['scope'] == 'aggregate' and
                          (row['condition'], row['mode']) == cohort]
            require(len(aggregates) == 2 and {row['robot'] for row in aggregates} == {'rp1', 'g1'},
                    'cohort aggregate participants differ: ' + comparison_id)
            protocol_runtime = {(row['provenance']['protocol_sha256'], row['provenance']['runtime'])
                                for row in selected + aggregates}
            require(len(protocol_runtime) == 1, 'cohort protocol/runtime differs; cannot force pairing')

    def retained_scientific_values(self):
        require(scientific_digest(self.data) == PAIRED_SCIENCE_SHA,
                'reviewed paired metrics, CI, sample identities, failures or scientific fields changed')

    def pairing_and_nominal(self):
        rows = {row['id']: row for row in self.data['results']}
        comparisons = {item['id']: item for item in self.data['comparisons']}
        require(len(self.data['comparisons']) == len(comparisons) == 4 and
                set(comparisons) == {spec[0] for spec in COHORTS.values()},
                'expected four reviewed common comparison IDs')
        for comparison in comparisons.values():
            require(comparison['verified'] is True, 'unverified comparison remains public')
            cohort, spec = next((cohort, spec) for cohort, spec in COHORTS.items()
                                if spec[0] == comparison['id'])
            sample = comparison['sample_set_sha256']
            require(sample == spec[4] and comparison['expected_paired_motions'] == spec[2],
                    'reviewed comparison sample identity/motion count differs')
            require(set(comparison['expected_participants']) ==
                    {comparison['id'] + '_' + robot for robot in ('rp1', 'g1')},
                    'reviewed participant IDs differ')
            members = [rows.get(name) for name in comparison['expected_participants']]
            require(len(members) == 2 and all(members), 'verified pair participant missing')
            require({row['robot'] for row in members} == {'rp1', 'g1'}, 'verified pair robot identities')
            for row in members:
                require(row['scope'] == 'aggregate' and row['status'] == 'complete', 'verified pair is incomplete')
                require((row['dataset'], row['condition'], row['mode'], row['phase']) ==
                        ('lafan40', *cohort, 'A'), 'verified participant evaluation condition differs')
                require(row['pairing']['comparison_id'] == comparison['id'] and
                        row['pairing']['sample_set_sha256'] == sample and row['pairing']['verified'],
                        'verified participant pairing differs')
                n = comparison['expected_paired_motions']
                require(row['paired_coverage']['numerator'] == row['paired_coverage']['denominator'] == n,
                        'verified participant denominator differs')
                for name in METRICS - {'gpu_train_hours'}:
                    cell = row['metrics'][name]
                    require(cell['sample_set_sha256'] == sample and
                            cell['coverage']['numerator'] == cell['coverage']['denominator'] == n,
                            'verified metric sample identity/denominator differs')
        nominal = comparisons[NOMINAL_ID]
        require(nominal['sample_set_sha256'] == NOMINAL_SAMPLE_SHA and
                nominal['verified'] and nominal['expected_paired_motions'] == 40,
                'LAFAN40 nominal pair identity changed')
        expected_progress = {'rp1': 79.7356922333541, 'g1': 77.2689768900195}
        expected_ci = {'rp1': (67.98309951919597, 90.19895946953002),
                       'g1': (65.11698902064144, 88.55903867340652)}
        for robot, expected in expected_progress.items():
            row = rows[NOMINAL_ID + '_' + robot]
            require((row['dataset'], row['condition'], row['mode'], row['phase']) ==
                    ('lafan40', 'nominal', 'native_position', 'A'), 'nominal identity changed')
            cell = row['metrics']['progress_pct']
            require(cell['value'] == expected, 'nominal progress changed')
            require((cell['ci']['low'], cell['ci']['high']) == expected_ci[robot], 'nominal mean CI changed')
            identities = [(item['motion_id'], item['seed']) for item in rows.values()
                          if (item['scope'], item['dataset'], item['condition'], item['mode'], item['robot']) ==
                          ('per_motion', 'lafan40', 'nominal', 'native_position', robot)]
            require(len(identities) == len(set(identities)) == 40, 'nominal must contain 40 distinct motion/seed identities')
            if robot == 'rp1':
                rp1_identities = set(identities)
            else:
                require(set(identities) == rp1_identities, 'nominal robot motion/seed identities differ')
        delta = nominal['paired_deltas']['progress_pct']
        require(delta == {'value': 2.4667153433346143,
                          'ci95': [-0.5367038425396738, 6.980247441475868],
                          'unit': 'pp', 'n_motions': 40}, 'nominal paired progress/CI changed')
        require(nominal['paired_deltas']['body_pos_mm']['value'] < 0 and
                nominal['paired_deltas']['body_ori_rad']['value'] < 0 and
                nominal['paired_deltas']['wrist_ori_rad']['value'] > 0, 'metric direction changed')

    def link(self, value, location):
        require(isinstance(value, str) and value.strip(), location + ': empty URL')
        require(value != SINGLE_SIDE_APPENDIX_URL, location + ': single-robot appendix entry remains public')
        require('\\' not in value and not re.search(r'[\x00-\x20]', value), location + ': unsafe URL characters')
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            require(parsed.scheme == 'https' and parsed.hostname in REVIEWED_HOSTS and
                    not parsed.username and not parsed.password and parsed.port in {None, 443},
                    location + ': unreviewed external URL')
            self.external_links.add(value)
            return
        require(not parsed.path.startswith('/'), location + ': absolute local link')
        path = unquote(parsed.path)
        require('\\' not in path and '..' not in PurePosixPath(path).parts and '%' not in path,
                location + ': relative path traversal')
        target = self.root / path if path else self.root / 'index.html'
        require(target.resolve().is_relative_to(self.root) and target.is_file(), location + ': missing internal target')
        require(target.relative_to(self.root).as_posix() in PUBLISH_FILES, location + ': non-public internal target')
        self.internal_links.add(value)

    def links(self):
        for loc, value in walk(self.data):
            if isinstance(value, dict) and 'url' in value:
                self.link(value['url'], loc)
                if urlsplit(value['url']).hostname == 'roboparty.feishu.cn':
                    require(value.get('access') == 'organization_permission_required',
                            loc + ': Feishu permission boundary missing')
        html = HTMLLinks()
        html.feed((self.root / 'index.html').read_text())
        for asset in ('app.js', 'style.css'):
            versioned = './' + asset + '?v=' + sha((self.root / asset).read_bytes())[:12]
            require(versioned in html.links, 'unversioned or stale browser asset: ' + asset)
        require(not html.ids.intersection({'official', 'official-body', 'official-references',
                                          'appendix', 'single-robot-results', 'unpaired-results'}),
                'official/single-robot appendix table entry remains public')
        for value in html.links:
            self.link(value, 'index.html')
            if value.startswith('#') and len(value) > 1:
                require(value[1:] in html.ids, 'index.html: missing section anchor')
        for name in ('README.md', 'DATA_PROVENANCE.md'):
            content = (self.root / name).read_text()
            for value in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                self.link(value, name)
        for name in ('app.js', 'style.css'):
            content = (self.root / name).read_text()
            for value in URL_TEXT.findall(content):
                if value == SVG_NAMESPACE:
                    continue
                self.link(value.rstrip('),.;'), name)
            for value in re.findall(r'(?:url\s*:\s*|fetch\s*\()(["\x27])([^"\x27]+)\1', content):
                self.link(value[1], name)
            for value in re.findall(r'url\(\s*["\x27]?([^\s)"\x27]+)', content):
                self.link(value, name)

    def source_comparison(self):
        # Compare against the reviewed generator's public intersection, rather
        # than requiring the excluded 333 display rows to remain public.
        from update_snapshot import project, validate_projection

        raw = self.source_path.read_bytes()
        require(sha(raw) == SOURCE_SHA, 'input is not the reviewed source bytes')
        source = read_json(self.source_path)
        require(source['aggregate_sha256'] == AGGREGATE_SHA, 'source aggregate differs')
        require(source['adapter_sha256'] == ADAPTER_SHA, 'source adapter differs')
        expected = project(source)
        try:
            validate_projection(source, expected)
        except AssertionError as error:
            raise AuditError('reviewed paired projection failed its scientific validation') from error
        require(expected == self.data,
                'public snapshot differs from the exact reviewed paired-only source projection')
        require(scientific_digest(expected) == PAIRED_SCIENCE_SHA,
                'source paired projection changed reviewed scientific fields')
        require(self.source_path.read_bytes() == raw, 'source changed during verification')

    def run(self):
        for label, fn in [('version_and_manifest_hashes', self.version_and_files),
                          ('public_schema_and_privacy', self.privacy_and_schema),
                          ('row_counts_missing_values_and_phase_boundary', self.counts_and_missing),
                          ('exact_episode_pair_intersection', self.exact_episode_pairs),
                          ('verified_pair_identities_and_nominal_contract', self.pairing_and_nominal),
                          ('immutable_retained_scientific_values', self.retained_scientific_values),
                          ('public_media_pending_boundary', self.public_media),
                          ('frozen_hardware_metadata_and_csv_contract', self.hardware_contract),
                          ('independent_extreme5_science_and_csv_contract', self.extreme_contract),
                          ('supplemental_fullwindow_values_join_ci_and_csv_contract', self.fullwindow_contract),
                          ('reviewed_extensions_and_separate_display_scope', self.extension_manifest),
                          ('internal_targets_and_reviewed_https_links', self.links)]:
            self.run_check(label, fn)
        if self.source_path is not None:
            self.run_check('exact_reviewed_input_comparison', self.source_comparison)
        return {'ok': not self.errors, 'publication_allowed': not self.errors,
                'data_version': self.manifest.get('data_version'),
                'public_data_sha256': sha((self.root / 'data.json').read_bytes()),
                'source_data_sha256': SOURCE_SHA, 'source_compared': self.source_path is not None,
                'result_rows': len(self.data.get('results', [])),
                'paired_cases': self.data.get('public_scope', {}).get('paired_cases'),
                'paired_episodes': len(self.episodes_by_id),
                'unique_common_motions': len({row['motion_id'] for row in self.episodes_by_id.values()}),
                'display_scope': self.manifest.get('display_scope'),
                'extensions_sha256': {'hardware_json': HARDWARE_JSON_SHA,
                                      'hardware_csv': HARDWARE_CSV_SHA,
                                      'extreme5_json': EXTREME_JSON_SHA,
                                      'extreme5_csv': EXTREME_CSV_SHA,
                                      'fullwindow_json': FULLWINDOW_JSON_SHA,
                                      'fullwindow_csv': FULLWINDOW_CSV_SHA},
                'fullwindow_value_checks': getattr(self, 'fullwindow_value_checks', None),
                'checked': self.checked, 'errors': self.errors,
                'unique_external_links': len(self.external_links),
                'unique_internal_links': len(self.internal_links),
                'external_availability_checked': False,
                'browser_qa_checked': False,
                'feishu_access': 'organization_permission_required'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source-data', type=Path, help='optional private reviewed source; read only')
    parser.add_argument('--report', type=Path, help='optional JSON audit output')
    args = parser.parse_args()
    try:
        report = Audit(args.repo_root, args.source_data).run()
    except (AuditError, ValueError, KeyError, TypeError, OSError) as error:
        report = {'ok': False, 'publication_allowed': False, 'errors': [str(error)]}
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(encoded, encoding='utf-8')
    print(encoded, end='')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
