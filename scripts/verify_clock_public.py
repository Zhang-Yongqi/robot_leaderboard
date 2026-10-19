#!/usr/bin/env python3
"""Independent schema7 verification; old schema3–6 verification stays unchanged.

Rebuild the original schema6 science from its original sources and identity map,
then apply the code-registered V9 source. Never compute new bootstrap intervals.
The prepared version is deliberately closed while final science is pending.
"""
import argparse
from copy import deepcopy
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys

from clock_contract import (ALL_METRICS, CLOCK_METHOD_FIELDS, CLOCK_PUBLIC_STATE, CLOCK_PREVIEW_STATE,
    COUNTS, EXTENSION_FIELDS, V8_CSV_SHA, CLOCK_SNAPSHOT_DATE, REPORT_STATES,
    REPORT_MANIFEST_STATES, MEDIA_STATE, apply_clock_rescore, canonical, changed_paths,
    clock_csv_bytes, exact, framework_status, normalize_clock_source, parse_json,
    protect_schema6, read_stable, reviewed_clock_adapter, sha, strip_public_mutable,
    strip_source_mutable, load_v8_source)

EXTRA_FILES = {'scripts/clock_contract.py', 'scripts/verify_clock_public.py'}
MANIFEST_FIELDS = {'schema_version', 'public_data_sha256', 'counts', 'fullwindow_source_sha256',
    'identity_map_sha256', 'completion_contract', 'publication_state', 'generated_utc', 'media_state',
    'report_state', 'hardware', 'files', 'completion_source_csv_sha256', 'root_extension',
    'root_source_csv_sha256', 'endpoint_extension', 'endpoint_source_csv_sha256',
    'clock_extension', 'clock_source_csv_sha256'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def rebuild_schema6(args):
    from update_snapshot import (FULL_SOURCE_SHA, IDENTITY_SHA, project, read_completion)
    from source_contract import prepare_schema5, prepare_schema6
    raw = read_stable(args.source_fullwindow)
    identity_raw = read_stable(args.identity_map)
    require(sha(raw) == FULL_SOURCE_SHA and sha(identity_raw) == IDENTITY_SHA,
            'Original fullwindow/identity bytes differ')
    identities = parse_json(identity_raw)
    completion = read_completion(args.source_completion)
    data = project(parse_json(raw), identities, publication=not args.preview, completion=completion)
    data = prepare_schema5(data, args.source_root, args.root_adapter, not args.preview)
    data = prepare_schema6(data, args.source_endpoint, args.endpoint_adapter, not args.preview)
    require(data['schema_version'] == 6 and data['counts'] == COUNTS, 'Rebuilt V8 baseline differs')
    return data


def validate_editorial(data, baseline):
    require(type(data['stats']) is dict and set(data['stats']) == set(baseline['stats']) | {'updated_utc'},
            'Unreviewed report/editorial field')
    require(data['stats']['updated_utc'] == CLOCK_SNAPSHOT_DATE, 'Fixed clock rescore date differs')
    require(exact({k: v for k, v in data['stats'].items() if k not in {'report_status', 'updated_utc'}},
                  {k: v for k, v in baseline['stats'].items() if k != 'report_status'}),
            'Only report status may change in statistics metadata')
    require(type(data['report_downloads']) is list and len(data['report_downloads']) == len(baseline['report_downloads']),
            'Report link population changed')
    for original, current in zip(baseline['report_downloads'], data['report_downloads']):
        require(set(current) == set(original) and all(current[k] == original[k] for k in current if k != 'label'),
                'Original report URL/field contract changed')
        require(all(type(value) is str for value in current.values()), 'Report metadata must be text')
    matches = [key for key, state in REPORT_STATES.items()
               if data['stats']['report_status'] == state['report_status'] and
               tuple(item['label'] for item in data['report_downloads']) == state['labels']]
    require(len(matches) == 1, 'Report metadata is outside the two explicit editorial states')
    return matches[0]


def bundle_and_privacy(args, data, adapter, report_state):
    # Reuse the original, unmodified file/link/hardware/media checks. Its schema
    # validator and scientific source adapters are not asked to accept schema7.
    from verify_public import (Audit, PUBLISH_FILES, SECRET, LOCAL_PATH, INFRA, IP_LITERAL,
        EXCLUDED_DIRS, HARDWARE_SHA, COMPLETION_CSV_SHA, ROOT_CSV_SHA)
    audit = Audit(args.repo_root, args.preview, args.source_fullwindow, args.identity_map,
        args.source_completion, args.source_root, args.root_adapter,
        args.source_endpoint, args.endpoint_adapter)
    audit.data = data
    audit.has_root = audit.has_endpoint = True
    audit.metrics = ALL_METRICS
    audit.publish_files = set(PUBLISH_FILES) | EXTRA_FILES
    # Reject public symlinks/directories outside the named bundle before rglob
    # checks; excluded local worktree metadata never forms part of publication.
    for path in args.repo_root.rglob('*'):
        rel = path.relative_to(args.repo_root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        require(not path.is_symlink(), 'Symlink in public bundle')
        if path.is_file():
            require(rel.as_posix() in audit.publish_files, 'File outside explicit schema7 whitelist')
    audit.bundle()
    manifest = parse_json(read_stable(args.repo_root / 'RELEASE_MANIFEST.json'))
    require(set(manifest) == MANIFEST_FIELDS, 'Schema7 manifest fields differ from explicit whitelist')
    require(exact(manifest['report_state'], REPORT_MANIFEST_STATES[report_state]) and
            exact(manifest['media_state'], MEDIA_STATE), 'Manifest report/media state differs from actual metadata')
    require(exact(manifest['clock_extension'], data['clock_extension']) and
            manifest['clock_source_csv_sha256'] == adapter.csv_sha256,
            'Manifest V9 JSON/CSV closure differs')
    require(manifest['completion_source_csv_sha256'] == COMPLETION_CSV_SHA and
            manifest['root_source_csv_sha256'] == ROOT_CSV_SHA and
            manifest['endpoint_source_csv_sha256'] == V8_CSV_SHA, 'Historical source CSV anchors changed')
    def strings(value):
        if type(value) is str:
            yield value
        elif type(value) is dict:
            for key, child in value.items():
                yield str(key)
                yield from strings(child)
        elif type(value) is list:
            for child in value:
                yield from strings(child)
    for value in strings(data):
        require(not SECRET.search(value) and not LOCAL_PATH.search(value) and not INFRA.search(value)
                and not re.search(r'\blocalhost\b', value, re.I), 'Private data in public projection')
        for match in IP_LITERAL.finditer(value):
            try:
                address = ipaddress.ip_address(match.group())
            except ValueError:
                continue
            require(not (address.is_private or address.is_loopback), 'Internal IP in public data')
    for name in audit.publish_files:
        content = (args.repo_root / name).read_text(encoding='utf-8')
        require(not SECRET.search(content), 'Possible credential in public file')
        if not name.startswith('scripts/') and name != 'README.md':
            require(not LOCAL_PATH.search(content), 'Absolute private path in public file')
            require(not INFRA.search(content.replace('.hostname', '') if name == 'app.js' else content),
                    'Private infrastructure in public file')
    for name, digest in HARDWARE_SHA.items():
        require(sha(read_stable(args.repo_root / name)) == digest, 'Hardware bytes changed')
    return sorted(audit.publish_files)


def run(args):
    adapter = reviewed_clock_adapter(args.clock_adapter)  # No provisional source is read while closed.
    baseline = rebuild_schema6(args)
    source_v8 = load_v8_source(args.source_endpoint)
    source_v9 = normalize_clock_source(args.source_clock, args.source_endpoint, args.clock_adapter)
    expected = apply_clock_rescore(baseline, args.source_clock, not args.preview,
                                  args.clock_adapter, source_v8=args.source_endpoint)
    raw = read_stable(args.repo_root / 'data.json')
    actual = parse_json(raw)
    protect_schema6(baseline, actual)
    report_state = validate_editorial(actual, baseline)
    require(exact({k: v for k, v in actual.items() if k not in {'stats', 'report_downloads'}},
                  {k: v for k, v in expected.items() if k not in {'stats', 'report_downloads'}}),
            'Schema7 public projection differs from exact frozen V9 source')
    require(set(actual['clock_extension']) == set(EXTENSION_FIELDS) and
            set(actual['methods']['clock_rescore']) == set(CLOCK_METHOD_FIELDS), 'Clock field whitelist differs')
    require(actual['publication_state'] == (CLOCK_PREVIEW_STATE if args.preview else CLOCK_PUBLIC_STATE),
            'Schema7 publication state differs')
    for name, scope in [('episodes.csv', 'per_motion'), ('comparisons.csv', 'aggregate')]:
        require(read_stable(args.repo_root / name) == clock_csv_bytes(actual, scope), 'Canonical schema7 CSV differs')
    files = bundle_and_privacy(args, actual, adapter, report_state)
    return {'ok': True, 'publication_allowed': not args.preview, 'schema_version': 7,
        'counts': COUNTS, 'four_error_source_verified': True, 'all_invariants_verified': True,
        'public_data_sha256': sha(raw), 'source_v8_canonical_sha256': sha(canonical(source_v8)),
        'source_v9_raw_sha256': adapter.json_sha256, 'public_files': files,
        'source_complement_sha256': sha(canonical(strip_source_mutable(source_v8))),
        'public_complement_sha256': sha(canonical(strip_public_mutable(baseline))),
        'source_changed_paths': changed_paths(source_v8, source_v9),
        'public_changed_paths': changed_paths(baseline, actual),
        'browser_qa_checked': False, 'external_availability_checked': False,
        'new_physical_episodes': 0, 'errors': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--source-fullwindow', type=Path)
    parser.add_argument('--identity-map', type=Path)
    parser.add_argument('--source-completion', type=Path)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--root-adapter')
    parser.add_argument('--source-endpoint', type=Path)
    parser.add_argument('--endpoint-adapter')
    parser.add_argument('--source-clock', type=Path)
    parser.add_argument('--clock-adapter')
    parser.add_argument('--framework-status', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.framework_status:
        print(json.dumps(framework_status(), ensure_ascii=False, indent=2))
        return 0
    try:
        require(all(getattr(args, name) is not None for name in ('source_fullwindow', 'identity_map',
            'source_completion', 'source_root', 'source_endpoint', 'source_clock')), 'All frozen sources are required')
        args.repo_root = args.repo_root.resolve()
        if args.report:
            require(not args.report.resolve().is_relative_to(args.repo_root), 'Internal audit report cannot be published')
        report = run(args)
    except (ValueError, KeyError, TypeError, IndexError, OSError, ImportError) as error:
        report = {'ok': False, 'publication_allowed': False, 'errors': [str(error)]}
    report['framework'] = framework_status()
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.report:
        with args.report.open('x', encoding='utf-8') as handle:
            handle.write(text)
    print(text, end='')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
