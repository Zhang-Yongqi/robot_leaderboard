"""Reviewed seven-error adapters and immutable schema-4/schema-5 protection.

The owner-frozen public JSON and CSV are bound to their reviewed byte hashes.
ROOT2 is projected from those values without calculating new scientific results.
The CLI never imports a user-selected module or treats a manifest as approval.
ROOT2 and the single endpoint scalar use separately reviewed public byte hashes.
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


class EndpointContractPending(ValueError):
    """No reviewed public endpoint source and export adapter is registered."""


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


SIX_METRICS = BASE_METRICS + ROOT_METRICS
SIX_CORE_SHA = '5b63f7ec5ca3a0a308a49bbf37d86b5935adcccb83f0692e96796ac26086e92a'
ENDPOINT_METRIC = 'root_endpoint_pos_mm'
ENDPOINT_METRICS = (ENDPOINT_METRIC,)
ENDPOINT_SOURCE_SHA = 'f932d85e4583544eeb942cd8eecf9804fda26dc849cc96d7d713f481044604f2'
ENDPOINT_CSV_SHA = '93aeea60a60c93b302b2e9bb035fe822841e42214f1b589dcd8c7c1ea22114b7'
ENDPOINT_SOURCE_BYTES = 465766
ENDPOINT_CSV_BYTES = 73740
ENDPOINT_WINDOW = 'last_valid_same_time_reference_root_endpoint'
ENDPOINT_PUBLIC_STATE = 'fullwindow_semantic_completion_root_endpoint_published'
ENDPOINT_PREVIEW_STATE = 'internal_preview_semantic_completion_root_endpoint'
DEFAULT_ENDPOINT_ADAPTER = 'public_root_endpoint_completion_v8'
ENDPOINT_DEFINITION_FIELDS = ('unit', 'label', 'role', 'higher_is_better', 'sample_count', 'window')
ENDPOINT_METHOD_FIELDS = ('window', 'sample_count_per_episode', 'definition', 'actual_reference_clock',
    'fixed_anchor', 'statistic', 'CI', 'not_success_proxy', 'existing_six_errors_and_completion_unchanged',
    'new_physical_episodes')


def schema5_core(data):
    """Freeze all six-error science while keeping report/editorial text editable."""
    require(data['counts'] == COUNTS, 'Six-error physical scope changed')
    core = baseline_core(data)
    core['root_extension'] = deepcopy(data['root_extension'])
    core['metrics'] = {metric: deepcopy(data['metrics'][metric]) for metric in SIX_METRICS}
    core['methods']['root'] = deepcopy(data['methods']['root'])
    core['datasets'] = sorted(({field: deepcopy(item[field]) for field in
        ('id', 'label', 'expected_motions')} for item in data['datasets']), key=lambda item: item['id'])
    rows = {row['id']: row for row in data['results']}
    for selected in core['results']:
        original = rows[selected['id']]
        selected['metrics'] = {metric: deepcopy(original['metrics'][metric]) for metric in SIX_METRICS}
        if original['scope'] == 'per_motion':
            selected['rootwindow'] = deepcopy(original['rootwindow'])
    comparisons = {item['id']: item for item in data['comparisons']}
    for selected in core['comparisons']:
        original = comparisons[selected['id']]
        for field in ('paired_deltas', 'paired_motion_values'):
            selected[field] = {metric: deepcopy(original[field][metric]) for metric in SIX_METRICS}
    return core


def schema5_digest(data):
    return hashlib.sha256(json.dumps(schema5_core(data), ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ReviewedEndpointAdapter(Protocol):
    """One code-reviewed mm endpoint projection from a frozen public JSON/CSV pair.

    Source field names, window/time metadata, units and byte identities must be
    bound by its concrete implementation after owner review. It never recomputes
    statistics, imports arbitrary code or appends original physical records.
    """
    contract_id: str
    endpoint_metric_units: Mapping[str, str]
    public_top_fields: tuple[str, ...]
    public_row_fields: tuple[str, ...]
    public_method_fields: tuple[str, ...]

    def normalize(self, source: Path, baseline: Mapping[str, Any]) -> Any: ...
    def project(self, baseline: Mapping[str, Any], normalized: Any, publication: bool) -> dict: ...
    def validate(self, baseline: Mapping[str, Any], candidate: Mapping[str, Any], normalized: Any) -> None: ...


# Only an implementation explicitly registered below after owner review can
# enable an adapter. A path, arbitrary name or self-declared PASS cannot open it.
_REVIEWED_ENDPOINT_ADAPTERS: dict[str, ReviewedEndpointAdapter] = {}


def reviewed_endpoint_adapter(adapter_id=None):
    adapter_id = adapter_id or DEFAULT_ENDPOINT_ADAPTER
    if not adapter_id or adapter_id not in _REVIEWED_ENDPOINT_ADAPTERS:
        raise EndpointContractPending('Schema 6 is disabled: no reviewed owner endpoint JSON/CSV contract is registered')
    return _REVIEWED_ENDPOINT_ADAPTERS[adapter_id]


def protect_schema5(baseline, candidate, *, endpoint_metric_units=None, top_fields=(),
                    row_fields=(), method_fields=()):
    """Allow only one reviewed endpoint extension on the intact schema-5 science."""
    require(baseline['schema_version'] == 5, 'Endpoint extension requires the frozen six-error baseline')
    extra = dict(endpoint_metric_units or {})
    require(not extra or (len(extra) == 1 and set(extra.values()) == {'mm'} and
        not set(extra).intersection(SIX_METRICS + tuple(FORBIDDEN_ROOT_FIELDS))),
        'Only one reviewed new millimetre endpoint metric may be added')
    def forbid(value):
        if type(value) is dict:
            require(not set(value).intersection(FORBIDDEN_ROOT_FIELDS), 'Historical root endpoint aliases cannot return')
            for child in value.values():
                forbid(child)
        elif type(value) is list:
            for child in value:
                forbid(child)
    forbid(candidate)
    require(set(candidate) == set(baseline) | set(top_fields), 'Unreviewed endpoint top-level field')
    require(set(candidate['methods']) == set(baseline['methods']) | set(method_fields),
            'Unreviewed endpoint method field')
    require(set(candidate['metrics']) == set(SIX_METRICS) | set(extra), 'Unreviewed endpoint metric')
    original_rows = {row['id']: row for row in baseline['results']}
    original_comparisons = {item['id']: item for item in baseline['comparisons']}
    for row in candidate['results']:
        additions = set(row_fields) if row['scope'] == 'per_motion' else set()
        require(row['id'] in original_rows and set(row) == set(original_rows[row['id']]) | additions,
                'Unreviewed endpoint result field or appended original ID')
        require(set(row['metrics']) == set(SIX_METRICS) | set(extra), 'Unreviewed endpoint result metric')
        for metric, unit in extra.items():
            require(candidate['metrics'][metric]['unit'] == row['metrics'][metric]['unit'] == unit,
                    'Endpoint units differ from the reviewed adapter')
    for item in candidate['comparisons']:
        require(item['id'] in original_comparisons and set(item) == set(original_comparisons[item['id']]),
                'Unreviewed endpoint comparison field')
        for field in ('paired_deltas', 'paired_motion_values'):
            require(set(item[field]) == set(SIX_METRICS) | set(extra), 'Unreviewed endpoint comparison metric')
    require(schema5_digest(candidate) == schema5_digest(baseline),
            'Existing six errors, windows, source, completion, provenance, IDs or denominators changed')


def prepare_schema6(baseline, source_endpoint, adapter_id=None, publication=False):
    """Only a reviewed adapter may project an endpoint scalar on frozen science."""
    require(baseline['schema_version'] == 5, 'Schema 6 requires verified six-error schema 5')
    require(schema5_digest(baseline) == SIX_CORE_SHA, 'Six-error frozen baseline digest differs')
    adapter = reviewed_endpoint_adapter(adapter_id)
    original = deepcopy(baseline)
    normalized = adapter.normalize(Path(source_endpoint), deepcopy(original))
    candidate = adapter.project(deepcopy(original), normalized, publication)
    require(type(candidate) is dict and type(candidate.get('schema_version')) is int and
            candidate['schema_version'] == 6, 'Reviewed endpoint adapter must produce schema 6')
    adapter.validate(original, candidate, normalized)
    protect_schema5(original, candidate, endpoint_metric_units=adapter.endpoint_metric_units,
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


class RootEndpointAdapter:
    contract_id = DEFAULT_ENDPOINT_ADAPTER
    endpoint_metric_units = {ENDPOINT_METRIC: 'mm'}
    public_top_fields = ('endpoint_extension',)
    public_row_fields = ()
    public_method_fields = ('root_endpoint',)

    def normalize(self, source, baseline):
        from update_snapshot import parse_json, sha, COMPLETION_EPISODE_FIELDS, episode_key, group_key
        source = Path(source)
        csv_path = source.with_name('public_sevenerror_episodes.csv')
        raw, csv_raw = source.read_bytes(), csv_path.read_bytes()
        require(len(raw) == ENDPOINT_SOURCE_BYTES and len(csv_raw) == ENDPOINT_CSV_BYTES and
                sha(raw) == ENDPOINT_SOURCE_SHA and sha(csv_raw) == ENDPOINT_CSV_SHA,
                'Unreviewed endpoint JSON/CSV byte identity')
        obj = parse_json(raw)
        require(obj['schema'] == 'rp1-g1-public-six-fullwindow-errors-root-endpoint-completion-v8' and
                obj['status'] == 'PASS_AUDITED_SOURCES_PUBLIC_PROJECTION' and
                obj['endpoint_metric_window'] == ENDPOINT_WINDOW and obj['root_metric_window'] == ROOT_WINDOW,
                'Unreviewed endpoint schema/status/window')
        require(set(obj['metric_definitions']) == set(SIX_METRICS + ENDPOINT_METRICS),
                'Exactly six full-window errors plus one endpoint error are required')
        definition = obj['metric_definitions'][ENDPOINT_METRIC]
        require(set(definition) == set(ENDPOINT_DEFINITION_FIELDS) and definition['unit'] == 'mm' and
                definition['label'] == '根部终点位置误差' and definition['role'] == 'endpoint_position_error' and
                definition['higher_is_better'] is False and type(definition['sample_count']) is int and
                definition['sample_count'] == 1 and definition['window'] == ENDPOINT_WINDOW,
                'Endpoint definition/unit/single-sample window differs')
        method = obj['methods']['root_endpoint']
        require(set(method) == set(ENDPOINT_METHOD_FIELDS) and method['window'] == ENDPOINT_WINDOW and
                type(method['sample_count_per_episode']) is int and method['sample_count_per_episode'] == 1 and
                method['existing_six_errors_and_completion_unchanged'] is True and
                type(method['new_physical_episodes']) is int and method['new_physical_episodes'] == 0,
                'Endpoint preservation/no-new-experiment method differs')
        columns = (*COMPLETION_EPISODE_FIELDS, *ROOT_METRICS, ENDPOINT_METRIC)
        require(len(obj['episodes']) == 180, 'Endpoint source must retain 180 physical episodes')
        handle = io.StringIO(newline='')
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\r\n')
        writer.writeheader()
        for episode in obj['episodes']:
            require(set(episode) == set(columns) and type(episode['seed']) is int,
                    'Endpoint source episode fields/integer seed differ')
            value = episode[ENDPOINT_METRIC]
            require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                    'Endpoint source scalar must be finite nonnegative millimetres')
        writer.writerows(obj['episodes'])
        require(csv_raw == handle.getvalue().encode(), 'Endpoint source CSV differs from its 180x24 JSON fields')
        # Exactly stripping the one endpoint extension must recover the prior
        # six-error public source byte for byte, including every value and CI.
        old = deepcopy(obj)
        old.pop('endpoint_metric_window')
        old['schema'] = 'rp1-g1-public-six-fullwindow-errors-semantic-completion-v3'
        old['methods'].pop('root_endpoint')
        old['metric_definitions'].pop(ENDPOINT_METRIC)
        for episode in old['episodes']:
            episode.pop(ENDPOINT_METRIC)
        for comparison in old['comparisons']:
            for field in ('robot_means', 'paired_deltas', 'paired_motion_values'):
                comparison[field].pop(ENDPOINT_METRIC)
        old_raw = (json.dumps(old, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
        require(sha(old_raw) == ROOT_SOURCE_SHA, 'Endpoint source changed the frozen six-error/completion package')
        episodes = {episode_key(row): row for row in obj['episodes']}
        expected = {episode_key(row): row for row in baseline['results'] if row['scope'] == 'per_motion'}
        require(len(episodes) == 180 and set(episodes) == set(expected),
                'Endpoint source population/six semantic identities differ')
        for key, row in expected.items():
            frozen = episodes[key]
            require(frozen['run_id'] == row['fullwindow']['run_id'] and
                    frozen['scientific_selected_case_id'] == row['fullwindow']['case_id'],
                    'Endpoint source run/case alias differs')
        groups = {group_key(row): row for row in obj['comparisons']}
        require(len(groups) == 5 and set(groups) == {group_key(row) for row in baseline['comparisons']},
                'Endpoint source comparison population differs')
        require(source.read_bytes() == raw and csv_path.read_bytes() == csv_raw,
                'Endpoint source changed during read')
        return obj

    def project(self, baseline, normalized, publication):
        from update_snapshot import episode_key, group_key, metric_cell
        data = deepcopy(baseline)
        episodes = {episode_key(row): row for row in normalized['episodes']}
        groups = {group_key(row): row for row in normalized['comparisons']}
        definition = normalized['metric_definitions'][ENDPOINT_METRIC]
        data['metrics'][ENDPOINT_METRIC] = {field: deepcopy(definition[field]) for field in
                                         ('unit', 'label', 'higher_is_better')}
        for row in data['results']:
            if row['scope'] == 'per_motion':
                row['metrics'][ENDPOINT_METRIC] = metric_cell(episodes[episode_key(row)][ENDPOINT_METRIC], 'mm', None, 1)
            else:
                group = groups[group_key(row)]
                cell = group['robot_means'][ENDPOINT_METRIC][row['robot']]
                row['metrics'][ENDPOINT_METRIC] = metric_cell(cell['value'], 'mm', cell['ci95'], group['n_unique_motions'])
        for comparison in data['comparisons']:
            source = groups[group_key(comparison)]
            require(source['id'] == comparison['fullwindow_comparison_id'] and
                    source['sample_set_sha256'] == comparison['sample_set_sha256'], 'Endpoint comparison identity differs')
            for field in ('paired_deltas', 'paired_motion_values'):
                comparison[field][ENDPOINT_METRIC] = deepcopy(source[field][ENDPOINT_METRIC])
        data.update(schema_version=6, publication_state=ENDPOINT_PUBLIC_STATE if publication else ENDPOINT_PREVIEW_STATE,
            endpoint_extension={'status': 'verified', 'source_sha256': ENDPOINT_SOURCE_SHA,
                                'metrics': [ENDPOINT_METRIC], 'definition': deepcopy(definition)})
        data['methods']['root_endpoint'] = deepcopy(normalized['methods']['root_endpoint'])
        data['stats']['report_status'] = 'V8 已同步：六项全程误差、根部终点位置误差与动作完成率，正文、PDF 和 DOCX 已更新至原地址。'
        for item in data['report_downloads']:
            item['label'] = item['label'].replace('V7', 'V8')
        return data

    def validate(self, baseline, candidate, normalized):
        expected = self.project(baseline, normalized, candidate['publication_state'] == ENDPOINT_PUBLIC_STATE)
        require(candidate == expected, 'Normalized endpoint projection differs from frozen public source')


_REVIEWED_ENDPOINT_ADAPTERS[DEFAULT_ENDPOINT_ADAPTER] = RootEndpointAdapter()


def framework_status():
    return {'schema5_enabled': True, 'root_contract_status': 'reviewed_public_source_registered',
            'root_metrics': ROOT_METRIC_CANDIDATES,
            'registered_root_adapters': sorted(_REVIEWED_ROOT_ADAPTERS),
            'schema6_enabled': bool(_REVIEWED_ENDPOINT_ADAPTERS),
            'endpoint_contract_status': 'reviewed_public_source_registered' if _REVIEWED_ENDPOINT_ADAPTERS else 'pending_reviewed_public_source',
            'registered_endpoint_adapters': sorted(_REVIEWED_ENDPOINT_ADAPTERS)}
