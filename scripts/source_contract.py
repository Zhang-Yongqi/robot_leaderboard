"""Reviewed six-error source adapter and immutable schema-4 science protection.

The owner-frozen public JSON and CSV are bound to their reviewed byte hashes.
ROOT2 is projected from those values without calculating new scientific results.
The CLI never imports a user-selected module or treats a manifest as approval.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Protocol
import csv
import io
import math

BASE_METRICS = ('full_body_pos_mm', 'full_body_ori_rad', 'full_wrist_pos_mm', 'full_wrist_ori_rad')
ROOT_METRIC_CANDIDATES = {'full_root_pos_mm': 'mm', 'full_root_ori_rad': 'rad'}
ROOT_METRICS = tuple(ROOT_METRIC_CANDIDATES)
ROOT_SOURCE_SHA = 'ac5a4a25fd0235c2472746135de43c66eb1a091e21be72016a7c8e5bf34ace4e'
ROOT_CSV_SHA = '5f3706b8f5644d606432e0c1653a54b43f6f0bef4468b7a9cfc34e6b1765c257'
BASE_COMPLETION_SHA = '8607a1403d9fbc846a741cb141cd65b07ce7805c7fb0df11cf1f22ecb119905f'
ROOT_WINDOW = 'full_replay_50hz_same_time_raw_state_at_reference'
ROOT_WINDOW_LABEL = '50 Hz 参考时刻对应的同刻根状态（来自原 200 Hz 轨迹）'
ROOT_PUBLIC_STATE = 'fullwindow_semantic_completion_root_metrics_published'
ROOT_PREVIEW_STATE = 'internal_preview_semantic_completion_root_metrics'
ROOT_METHOD_FIELDS = ('window', 'source', 'sampling', 'alignment', 'position', 'orientation',
    'weighting_and_CI', 'old_four_window_unchanged', 'completion_unchanged', 'completion_does_not_filter_errors',
    'new_physical_episodes')
ROOTWINDOW_FIELDS = ('metric_window', 'recorded_frames', 'reference_start_s', 'reference_end_s',
                     'physics_start_s', 'physics_end_s')
DEFAULT_ROOT_ADAPTER = 'public_six_fullwindow_errors_v3'
COUNTS = {'episode_records': 180, 'paired_cases': 90, 'unique_motions': 45,
          'comparison_groups': 5, 'aggregate_rows': 10, 'result_rows': 190}
CORE_TOP = ('fullwindow_source_sha256', 'identity_map_sha256', 'counts', 'phase',
            'primary_comparison_ids', 'secondary_comparison_ids', 'completion_contract')
CORE_METHODS = ('fullwindow', 'units', 'weighting', 'bootstrap', 'completion')
CORE_ROWS = ('id', 'label', 'phase', 'dataset', 'condition', 'mode', 'robot', 'motion_id',
             'seed', 'scope', 'matched_seed_set', 'completion', 'coverage', 'pairing', 'provenance')
CORE_COMPARISONS = ('id', 'label', 'phase', 'dataset', 'condition', 'mode', 'role', 'metric_window',
    'n_unique_motions', 'paired_cases', 'episode_records', 'matched_seed_set', 'expected_participants',
    'expected_paired_motions', 'sample_set', 'sample_set_sha256', 'completion', 'fullwindow_comparison_id')
FORBIDDEN_ROOT_FIELDS = {'root_final_error_norm', 'root_final_error_z_abs', 'root_final_error_xy_norm',
    'root_endpoint_scope', 'root_endpoint_motion_t', 'root_endpoint_time_s', 'root_endpoint_sim_time_s',
    'root_endpoint_reference_time_s', 'root_endpoint_physics_time_s'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


class RootContractPending(ValueError):
    """The required owner package and adapter have not been reviewed."""


class ReviewedRootAdapter(Protocol):
    """Interface for an explicitly reviewed owner-frozen public contract.

    Implementations pin reviewed JSON/CSV hashes, independent windows and mm/rad units, and forbid
    endpoint aliases, success filtering, or appended episodes. It must copy
    owner-frozen values/CI, never compute new scientific results. Source and
    normalized payload shapes belong to the concrete code-registered adapter.
    """
    contract_id: str
    root_metric_units: Mapping[str, str]
    public_top_fields: tuple[str, ...]
    public_row_fields: tuple[str, ...]
    public_method_fields: tuple[str, ...]

    def normalize(self, source: Path, baseline: Mapping[str, Any]) -> Any: ...

    def project(self, baseline: Mapping[str, Any], normalized: Any, publication: bool) -> dict: ...

    def validate(self, baseline: Mapping[str, Any], candidate: Mapping[str, Any], normalized: Any) -> None: ...


# Filled by an explicit code review after the genuine owner contract arrives.
# A CLI adapter name, self-declared PASS, or caller-supplied SHA cannot fill it.
_REVIEWED_ROOT_ADAPTERS: dict[str, ReviewedRootAdapter] = {}


def reviewed_root_adapter(adapter_id=None):
    adapter_id = adapter_id or DEFAULT_ROOT_ADAPTER
    if not adapter_id or adapter_id not in _REVIEWED_ROOT_ADAPTERS:
        raise RootContractPending('Schema 5 is disabled: no reviewed owner root contract/adapter is registered')
    return _REVIEWED_ROOT_ADAPTERS[adapter_id]


def baseline_core(data):
    """Select all preserved science, not editorial text or new root fields."""
    require(data['counts'] == COUNTS, 'Baseline physical scope changed')
    rows, comparisons = data['results'], data['comparisons']
    require(len(rows) == 190 and len({r['id'] for r in rows}) == 190,
            'Baseline must retain 190 unique original row IDs')
    require(sum(r['scope'] == 'per_motion' for r in rows) == 180 and
            sum(r['scope'] == 'aggregate' for r in rows) == 10, 'Baseline row scopes changed')
    require(len(comparisons) == 5 and len({c['id'] for c in comparisons}) == 5,
            'Baseline must retain five original comparison IDs')
    def selected(obj, fields):
        return {field: deepcopy(obj[field]) for field in fields}
    selected_rows = []
    for row in sorted(rows, key=lambda item: item['id']):
        item = selected(row, CORE_ROWS)
        item['metrics'] = selected(row['metrics'], BASE_METRICS)
        if row['scope'] == 'per_motion':
            item['fullwindow'] = deepcopy(row['fullwindow'])
        selected_rows.append(item)
    selected_comparisons = []
    for comparison in sorted(comparisons, key=lambda item: item['id']):
        item = selected(comparison, CORE_COMPARISONS)
        for field in ('paired_deltas', 'paired_motion_values'):
            item[field] = selected(comparison[field], BASE_METRICS)
        selected_comparisons.append(item)
    return {**selected(data, CORE_TOP), 'metrics': selected(data['metrics'], BASE_METRICS),
            'methods': selected(data['methods'], CORE_METHODS), 'results': selected_rows,
            'comparisons': selected_comparisons}


def baseline_digest(data):
    return hashlib.sha256(json.dumps(baseline_core(data), ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def protect_baseline(baseline, candidate, *, root_metric_units=None, top_fields=(), row_fields=(), method_fields=()):
    require(baseline['schema_version'] == 4, 'Root extension requires the frozen schema-4 baseline')
    roots = dict(root_metric_units or {})
    require(not roots or (len(roots) == 2 and set(roots.values()) == {'mm', 'rad'} and
            not set(roots).intersection(BASE_METRICS)), 'Only two reviewed mm/rad root metrics may be added')
    def forbid(value):
        if type(value) is dict:
            require(not set(value).intersection(FORBIDDEN_ROOT_FIELDS), 'Old root endpoint fields cannot return')
            for child in value.values():
                forbid(child)
        elif type(value) is list:
            for child in value:
                forbid(child)
    forbid(candidate)
    require(set(candidate) == set(baseline) | set(top_fields), 'Unreviewed top-level extension')
    require(set(candidate['methods']) == set(baseline['methods']) | set(method_fields), 'Unreviewed method extension')
    require(set(candidate['metrics']) == set(BASE_METRICS) | set(roots), 'Unreviewed metric extension')
    original_rows = {row['id']: row for row in baseline['results']}
    original_comparisons = {row['id']: row for row in baseline['comparisons']}
    for row in candidate['results']:
        additions = set(row_fields) if row['scope'] == 'per_motion' else set()
        require(row['id'] in original_rows and set(row) == set(original_rows[row['id']]) | additions,
                'Unreviewed result field or appended original ID')
        require(set(row['metrics']) == set(BASE_METRICS) | set(roots), 'Unreviewed result metric')
        for metric, unit in roots.items():
            require(candidate['metrics'][metric]['unit'] == row['metrics'][metric]['unit'] == unit,
                    'Root units differ from the reviewed adapter')
    for comparison in candidate['comparisons']:
        require(comparison['id'] in original_comparisons and
                set(comparison) == set(original_comparisons[comparison['id']]), 'Unreviewed comparison extension')
        for field in ('paired_deltas', 'paired_motion_values'):
            require(set(comparison[field]) == set(BASE_METRICS) | set(roots), 'Unreviewed comparison metric')
    require(baseline_digest(candidate) == baseline_digest(baseline),
            'Original IDs, scope, values/CI, pairing, provenance, completion, or methods changed')


def prepare_schema5(baseline, source_root, adapter_id=None, publication=False):
    """Project the reviewed source on copies behind the immutable baseline guard."""
    require(baseline['schema_version'] == 4, 'Schema 5 requires verified schema-4 completion')
    adapter = reviewed_root_adapter(adapter_id)
    original = deepcopy(baseline)
    normalized = adapter.normalize(Path(source_root), deepcopy(original))
    candidate = adapter.project(deepcopy(original), normalized, publication)
    require(type(candidate) is dict and type(candidate.get('schema_version')) is int and
            candidate['schema_version'] == 5, 'Reviewed adapter must produce schema 5')
    adapter.validate(original, candidate, normalized)
    protect_baseline(original, candidate, root_metric_units=adapter.root_metric_units,
                     top_fields=adapter.public_top_fields, row_fields=adapter.public_row_fields,
                     method_fields=adapter.public_method_fields)
    return candidate


def rootwindow_from_baseline(row):
    """Nominal window metadata from the audited root definition, not raw stamps."""
    fw = row['fullwindow']
    return {'metric_window': ROOT_WINDOW, 'recorded_frames': fw['full_recorded_frames'],
            'reference_start_s': fw['reference_start_s'], 'reference_end_s': fw['reference_end_s'],
            'physics_start_s': fw['reference_start_s'], 'physics_end_s': fw['reference_end_s']}


class SixErrorRootAdapter:
    contract_id = DEFAULT_ROOT_ADAPTER
    root_metric_units = ROOT_METRIC_CANDIDATES
    public_top_fields = ('root_extension',)
    public_row_fields = ('rootwindow',)
    public_method_fields = ('root',)

    def normalize(self, source, baseline):
        # This import occurs after the builder has finished initializing.
        from update_snapshot import parse_json, sha, COMPLETION_EPISODE_FIELDS, episode_key, group_key
        source = Path(source)
        csv_path = source.with_name('public_sixerror_episodes.csv')
        raw, csv_raw = source.read_bytes(), csv_path.read_bytes()
        require(sha(raw) == ROOT_SOURCE_SHA and sha(csv_raw) == ROOT_CSV_SHA,
                'Unreviewed six-error root JSON/CSV identity')
        obj = parse_json(raw)
        require(obj['schema'] == 'rp1-g1-public-six-fullwindow-errors-semantic-completion-v3' and
                obj['status'] == 'PASS_AUDITED_SOURCES_PUBLIC_PROJECTION' and
                obj['root_metric_window'] == ROOT_WINDOW, 'Unreviewed root schema/status/window')
        require(set(obj['methods']['root_fullwindow']) == set(ROOT_METHOD_FIELDS), 'Root method fields differ')
        method = obj['methods']['root_fullwindow']
        require(method['window'] == ROOT_WINDOW and method['old_four_window_unchanged'] is True and
                method['completion_unchanged'] is True and method['completion_does_not_filter_errors'] is True and
                type(method['new_physical_episodes']) is int and method['new_physical_episodes'] == 0,
                'Root preservation/no-new-experiment contract differs')
        require(set(obj['metric_definitions']) == set(BASE_METRICS + ROOT_METRICS), 'Exactly six errors required')
        for metric, unit in self.root_metric_units.items():
            definition = obj['metric_definitions'][metric]
            require(set(definition) == {'unit', 'label', 'role', 'higher_is_better', 'window'} and
                    definition['unit'] == unit and definition['higher_is_better'] is False and
                    definition['window'] == ROOT_WINDOW, 'Root unit/definition/window differs')
        handle = io.StringIO(newline='')
        columns = (*COMPLETION_EPISODE_FIELDS, *ROOT_METRICS)
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\r\n')
        writer.writeheader()
        for episode in obj['episodes']:
            require(set(episode) == set(columns) and type(episode['seed']) is int,
                    'Root source episode fields/seed differ')
        writer.writerows(obj['episodes'])
        require(csv_raw == handle.getvalue().encode(), 'Root source CSV differs from its 180x23 JSON fields')
        # Removing exactly ROOT2 reconstructs the frozen completion source byte
        # for byte. This binds every old value, CI, label, identity and method.
        old = deepcopy(obj)
        old.pop('root_metric_window')
        old['schema'] = 'rp1-g1-public-fullwindow-semantic-completion-v2'
        old['status'] = 'independently_verified'
        old['methods'].pop('root_fullwindow')
        for metric in ROOT_METRICS:
            old['metric_definitions'].pop(metric)
            for episode in old['episodes']:
                episode.pop(metric)
            for comparison in old['comparisons']:
                for field in ('robot_means', 'paired_deltas', 'paired_motion_values'):
                    comparison[field].pop(metric)
        old_raw = (json.dumps(old, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
        require(sha(old_raw) == BASE_COMPLETION_SHA, 'New source changed the frozen four-error/completion package')
        episodes = {episode_key(row): row for row in obj['episodes']}
        expected = {episode_key(row): row for row in baseline['results'] if row['scope'] == 'per_motion'}
        require(len(episodes) == 180 and set(episodes) == set(expected), 'Root source population/semantic identities differ')
        for key, row in expected.items():
            root = episodes[key]
            require(root['run_id'] == row['fullwindow']['run_id'] and
                    root['scientific_selected_case_id'] == row['fullwindow']['case_id'], 'Root run/case alias differs')
        groups = {group_key(row): row for row in obj['comparisons']}
        require(len(groups) == 5 and set(groups) == {group_key(row) for row in baseline['comparisons']},
                'Root comparison population differs')
        require(source.read_bytes() == raw and csv_path.read_bytes() == csv_raw, 'Root input changed during read')
        return obj

    def project(self, baseline, normalized, publication):
        from update_snapshot import episode_key, group_key, metric_cell
        data = deepcopy(baseline)
        episodes = {episode_key(row): row for row in normalized['episodes']}
        groups = {group_key(row): row for row in normalized['comparisons']}
        for metric, unit in self.root_metric_units.items():
            definition = normalized['metric_definitions'][metric]
            data['metrics'][metric] = {'unit': unit, 'label': definition['label'], 'higher_is_better': False}
        for row in data['results']:
            if row['scope'] == 'per_motion':
                source = episodes[episode_key(row)]
                row['rootwindow'] = rootwindow_from_baseline(row)
                for metric, unit in self.root_metric_units.items():
                    row['metrics'][metric] = metric_cell(source[metric], unit, None, 1)
            else:
                group = groups[group_key(row)]
                for metric, unit in self.root_metric_units.items():
                    cell = group['robot_means'][metric][row['robot']]
                    row['metrics'][metric] = metric_cell(cell['value'], unit, cell['ci95'], group['n_unique_motions'])
        for comparison in data['comparisons']:
            source = groups[group_key(comparison)]
            require(source['id'] == comparison['fullwindow_comparison_id'] and
                    source['sample_set_sha256'] == comparison['sample_set_sha256'], 'Root comparison identity differs')
            for field in ('paired_deltas', 'paired_motion_values'):
                for metric in ROOT_METRICS:
                    comparison[field][metric] = deepcopy(source[field][metric])
        data.update(schema_version=5, publication_state=ROOT_PUBLIC_STATE if publication else ROOT_PREVIEW_STATE,
            root_extension={'status': 'verified', 'source_sha256': ROOT_SOURCE_SHA,
                            'metrics': list(ROOT_METRICS), 'window_label': ROOT_WINDOW_LABEL})
        data['methods']['root'] = deepcopy(normalized['methods']['root_fullwindow'])
        return data

    def validate(self, baseline, candidate, normalized):
        expected = self.project(baseline, normalized, candidate['publication_state'] == ROOT_PUBLIC_STATE)
        require(candidate == expected, 'Normalized root projection differs from frozen source')


_REVIEWED_ROOT_ADAPTERS[DEFAULT_ROOT_ADAPTER] = SixErrorRootAdapter()


def framework_status():
    return {'schema5_enabled': True, 'root_contract_status': 'reviewed_public_source_registered',
            'root_metrics': ROOT_METRIC_CANDIDATES,
            'registered_root_adapters': sorted(_REVIEWED_ROOT_ADAPTERS)}
