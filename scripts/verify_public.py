#!/usr/bin/env python3
"""Fail-closed audit of the reviewed RP1/G1 public snapshot (stdlib only).

Run without arguments to verify the distributable bundle. Add --source-data to
independently compare every result's metrics, CI, coverage and pairing with the
hash-approved private input. The input is read only and never copied. A changed
scientific version requires review and an explicit change to this contract.
Exit 1 means publication must stop; exit 0 records only the checks performed.
This static verifier does not claim browser QA or external link availability.
"""
import argparse
from collections import Counter
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
            if name in {'index.html', 'app.js', 'style.css', 'DATA_PROVENANCE.md', 'RELEASE_MANIFEST.json'}:
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
