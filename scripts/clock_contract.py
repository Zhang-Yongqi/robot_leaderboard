"""Closed V9 same-time body/wrist projection; no scientific recomputation.

Only a code-registered, owner-frozen public JSON/CSV pair may open schema 7.
The V8 input bytes and the complement of the four corrected metrics stay fixed.
Only the exact final two-file projection registered below can open schema 7.
"""
from copy import deepcopy
from dataclasses import dataclass
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re

FULL4 = ('full_body_pos_mm', 'full_body_ori_rad', 'full_wrist_pos_mm', 'full_wrist_ori_rad')
ROOT2 = ('full_root_pos_mm', 'full_root_ori_rad')
ENDPOINT = 'root_endpoint_pos_mm'
ALL_METRICS = FULL4 + ROOT2 + (ENDPOINT,)
JOIN = ('dataset', 'condition', 'mode', 'robot', 'motion_id', 'seed')
GROUP = ('dataset', 'condition', 'mode')
COUNTS = {'episode_records': 180, 'paired_cases': 90, 'unique_motions': 45,
          'comparison_groups': 5, 'aggregate_rows': 10, 'result_rows': 190}
V8_JSON_SHA = 'f932d85e4583544eeb942cd8eecf9804fda26dc849cc96d7d713f481044604f2'
V8_JSON_BYTES = 465766
V8_CSV_SHA = '93aeea60a60c93b302b2e9bb035fe822841e42214f1b589dcd8c7c1ea22114b7'
V8_CSV_BYTES = 73740
V8_WINDOW = 'full_replay_50hz_first_substep'
CLOCK_WINDOW = 'full_replay_50hz_same_time_raw_body_fk_at_reference'
CLOCK_PUBLIC_STATE = 'fullwindow_semantic_completion_root_endpoint_clock_corrected_published'
CLOCK_PREVIEW_STATE = 'internal_preview_semantic_completion_root_endpoint_clock_corrected'
CLOCK_SNAPSHOT_DATE = '2026-10-19'
DEFAULT_CLOCK_ADAPTER = 'public_same_time_body_wrist_completion_v9'
SOURCE_SCHEMA = 'rp1-g1-public-six-fullwindow-errors-root-endpoint-completion-v9'
SOURCE_STATUS = 'verified_offline_same_time_body_wrist_rescore_v9'
EPISODE_FIELDS = ('phase', 'dataset', 'condition', 'mode', 'robot', 'motion_id', 'seed',
    'effective_condition', 'scope', 'run_id', 'scientific_selected_case_id', 'metric_window',
    *FULL4, 'completion_status', 'completion_evidence_level', 'completion_reason_code',
    'completion_failure_reference_time_s', 'completion_failure_physics_time_s', *ROOT2, ENDPOINT)
CLOCK_METHOD_FIELDS = ('window', 'source', 'new_physical_episodes', 'sampling', 'reference_window',
    'alignment', 'position', 'orientation', 'precision', 'weighting_and_CI',
    'completion_does_not_filter_errors', 'root_endpoint_completion_unchanged', 'old_four_cache_timing',
    'reference_unchanged', 'historical_preservation_flags_scope')
EXTENSION_FIELDS = ('status', 'source_sha256', 'source_csv_sha256', 'baseline_source_sha256',
    'baseline_schema_version', 'metrics', 'window', 'old_root_endpoint_method_flags_scope',
    'new_physical_episodes')
HISTORICAL_METHOD_SCOPE = 'V8 root/endpoint extension declarations describe their historical V8 scope; V9 corrects only body/wrist scoring clocks.'
HASH = re.compile(r'[0-9a-f]{64}\Z')
REPORT_STATES = {
    'v8_pending_revision': {
        'report_status': '网页已完成既有180回合同刻离线重评分；飞书修订版待同步，原正文、PDF、DOCX最后核验为V8。',
        'labels': ('技术报告正文（最后核验 V8，修订版待同步）',
                   '全程与终点报告 PDF（最后核验 V8，修订版待同步）',
                   '全程与终点报告 DOCX（最后核验 V8，修订版待同步）')},
    'v9_synced': {
        'report_status': 'V9 已同步：既有180回合身体与手腕同刻离线重评分，原正文、PDF 和 DOCX 已更新；根部、终点与动作完成判定保持不变。',
        'labels': ('V9 技术报告正文', 'V9 全程与终点报告 PDF', 'V9 全程与终点报告 DOCX')},
}
REPORT_MANIFEST_STATES = {
    'v8_pending_revision': {'version': 8, 'status': 'V8已同步，V9修订版待同步',
        'native_version': 8, 'pdf_version': 8, 'docx_version': 8,
        'pdf_preview_pages': 15, 'docx_preview_pages': None},
    'v9_synced': {'version': 9, 'status': 'V9已同步',
        'native_version': 9, 'pdf_version': 9, 'docx_version': 9,
        'pdf_preview_pages': None, 'docx_preview_pages': None},
}
MEDIA_STATE = {'public_new_common40': 0, 'public_new_extreme5': 0,
               'source_media_sha256': '5fefaecdd12099425e4a815a90f75125818fb75c6a977e211f12b0fb49fb7f75'}


class ClockContractPending(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def exact(left, right):
    return canonical(left) == canonical(right)


def parse_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    def invalid(_):
        raise ValueError('Nonfinite JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)


def read_stable(path, limit=4 * 1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Expected ordinary frozen input')
    before = path.stat()
    require(before.st_size <= limit, 'Input byte cap')
    raw = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Input changed during read')
    return raw


def seed(value):
    if type(value) is int and value >= 0:
        return value
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]*', value), 'Strict integer seed required')
    return int(value)


def episode_key(row):
    require(row.get('phase') == 'A', 'Episode phase differs')
    require(all(type(row.get(k)) is str and row[k] for k in JOIN[:-1]), 'Missing semantic key')
    return tuple(row[k] for k in JOIN[:-1]) + (seed(row['seed']),)


def group_key(row):
    return tuple(row[k] for k in GROUP)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def interval(value):
    return type(value) is list and len(value) == 2 and all(finite(x) for x in value) and value[0] <= value[1]


def validate_clock_method(method):
    require(type(method) is dict and set(method) == set(CLOCK_METHOD_FIELDS), 'Clock method field whitelist differs')
    require(method['window'] == CLOCK_WINDOW and all(method[k] is True for k in
            ('completion_does_not_filter_errors', 'root_endpoint_completion_unchanged', 'reference_unchanged'))
            and type(method['new_physical_episodes']) is int and method['new_physical_episodes'] == 0,
            'Clock method preservation/no-new-simulation contract differs')
    text_fields = set(CLOCK_METHOD_FIELDS) - {'new_physical_episodes', 'completion_does_not_filter_errors',
        'root_endpoint_completion_unchanged', 'reference_unchanged'}
    require(all(type(method[k]) is str and method[k].strip() for k in text_fields), 'Clock method text is missing')


def source_csv_bytes(source):
    require(len(source['episodes']) == 180, 'Exactly 180 physical episodes required')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=EPISODE_FIELDS, lineterminator='\r\n')
    writer.writeheader()
    for row in source['episodes']:
        require(set(row) == set(EPISODE_FIELDS) and type(row['seed']) is int, 'Source 180x24 shape differs')
    writer.writerows(source['episodes'])
    return stream.getvalue().encode()


def load_v8_source(json_path, csv_path=None):
    json_path = Path(json_path)
    csv_path = Path(csv_path) if csv_path else json_path.with_name('public_sevenerror_episodes.csv')
    raw, csv_raw = read_stable(json_path), read_stable(csv_path)
    require(len(raw) == V8_JSON_BYTES and sha(raw) == V8_JSON_SHA and
            len(csv_raw) == V8_CSV_BYTES and sha(csv_raw) == V8_CSV_SHA, 'Frozen V8 JSON/CSV identity differs')
    source = parse_json(raw)
    require(source['schema'] == 'rp1-g1-public-six-fullwindow-errors-root-endpoint-completion-v8'
            and source['metric_window'] == V8_WINDOW, 'Frozen V8 schema/window differs')
    require(csv_raw == source_csv_bytes(source), 'V8 CSV is not the exact episode projection')
    return source


def strip_source_mutable(source):
    """Retain every invariant, including units and paired-motion identity fields."""
    value = deepcopy(source)
    value.pop('schema'); value.pop('status'); value.pop('metric_window')
    value['methods'].pop('fullwindow')
    value['methods'].pop('clock_rescore', None)
    for row in value['episodes']:
        row.pop('metric_window')
        for name in FULL4:
            row.pop(name)
    for comparison in value['comparisons']:
        comparison.pop('metric_window')
        for name in FULL4:
            for robot in ('rp1', 'g1'):
                comparison['robot_means'][name][robot].pop('value')
                comparison['robot_means'][name][robot].pop('ci95')
            comparison['paired_deltas'][name].pop('value')
            comparison['paired_deltas'][name].pop('ci95')
            for item in comparison['paired_motion_values'][name]:
                for field in ('rp1', 'g1', 'delta_rp1_minus_g1'):
                    item.pop(field)
    return value


def validate_source_invariants(baseline, candidate):
    require(exact(strip_source_mutable(baseline), strip_source_mutable(candidate)),
            'V8 source complement changed: root/endpoint/completion/IDs/pairing/units/methods')
    require(len({episode_key(r) for r in candidate['episodes']}) == 180, 'Duplicate or missing episode key')
    for row in candidate['episodes']:
        require(set(row) == set(EPISODE_FIELDS) and type(row['seed']) is int, 'Unreviewed source episode field')
        require(all(finite(row[name]) and row[name] >= 0 for name in FULL4), 'Invalid corrected episode value')
    for group in candidate['comparisons']:
        for name in FULL4:
            for robot in ('rp1', 'g1'):
                cell = group['robot_means'][name][robot]
                require(set(cell) == {'value', 'ci95'} and finite(cell['value']) and cell['value'] >= 0
                        and interval(cell['ci95']), 'Invalid corrected robot mean/CI')
            delta = group['paired_deltas'][name]
            require(finite(delta['value']) and interval(delta['ci95']), 'Invalid corrected paired delta/CI')
            require(all(all(finite(item[k]) for k in ('rp1', 'g1', 'delta_rp1_minus_g1'))
                        and item['rp1'] >= 0 and item['g1'] >= 0
                        for item in group['paired_motion_values'][name]), 'Invalid corrected motion value')


def strip_public_mutable(data):
    value = deepcopy(data)
    value.pop('schema_version'); value.pop('publication_state')
    value.pop('clock_extension', None)
    value['methods'].pop('fullwindow')
    value['methods'].pop('clock_rescore', None)
    # Report/editorial metadata is handled explicitly by the final bundle validator.
    value.pop('stats'); value.pop('report_downloads')
    for row in value['results']:
        for name in FULL4:
            row['metrics'][name].pop('value'); row['metrics'][name].pop('ci95')
        if row['scope'] == 'per_motion':
            row['fullwindow'].pop('metric_window')
    for comparison in value['comparisons']:
        comparison.pop('metric_window')
        for name in FULL4:
            comparison['paired_deltas'][name].pop('value'); comparison['paired_deltas'][name].pop('ci95')
            for item in comparison['paired_motion_values'][name]:
                for field in ('rp1', 'g1', 'delta_rp1_minus_g1'):
                    item.pop(field)
    return value


def protect_schema6(baseline, candidate):
    require(baseline['schema_version'] == 6 and candidate['schema_version'] == 7, 'Clock correction requires 6→7')
    require(baseline['counts'] == candidate['counts'] == COUNTS, 'Physical populations changed')
    require(set(candidate) == set(baseline) | {'clock_extension'}, 'Unreviewed public top-level field')
    require(set(candidate['methods']) == set(baseline['methods']) | {'clock_rescore'}, 'Unreviewed public method field')
    require(set(candidate['stats']) == set(baseline['stats']) | {'updated_utc'} and
            candidate['stats']['updated_utc'] == CLOCK_SNAPSHOT_DATE,
            'Clock correction snapshot date or editorial fields differ')
    validate_clock_method(candidate['methods']['clock_rescore'])
    extension = candidate['clock_extension']
    require(type(extension) is dict and set(extension) == set(EXTENSION_FIELDS)
            and extension['status'] == 'verified' and extension['metrics'] == list(FULL4)
            and extension['window'] == CLOCK_WINDOW and extension['baseline_source_sha256'] == V8_JSON_SHA
            and type(extension['baseline_schema_version']) is int and extension['baseline_schema_version'] == 6
            and type(extension['new_physical_episodes']) is int and extension['new_physical_episodes'] == 0
            and all(type(extension[k]) is str and HASH.fullmatch(extension[k]) for k in
                    ('source_sha256', 'source_csv_sha256'))
            and extension['old_root_endpoint_method_flags_scope'] == HISTORICAL_METHOD_SCOPE,
            'Clock extension field/source/window contract differs')
    require(exact(strip_public_mutable(baseline), strip_public_mutable(candidate)),
            'Public complement changed: root/endpoint/completion/provenance/IDs/denominators/windows')
    for row in candidate['results']:
        for name in FULL4:
            cell = row['metrics'][name]
            require(finite(cell['value']) and cell['value'] >= 0, 'Invalid corrected public metric')
            require(cell['ci95'] is None if row['scope'] == 'per_motion' else interval(cell['ci95']),
                    'Per-episode CI must stay null; aggregate CI must be valid')


def changed_paths(old, new, path=''):
    """Complete leaf diff; original array order is preserved by the projection."""
    if type(old) is dict and type(new) is dict:
        result = []
        for key in sorted(set(old) | set(new)):
            target = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in old:
                result.append({'path': target, 'change': 'added', 'new': deepcopy(new[key])})
            elif key not in new:
                result.append({'path': target, 'change': 'removed', 'old': deepcopy(old[key])})
            else:
                result.extend(changed_paths(old[key], new[key], target))
        return result
    if type(old) is list and type(new) is list and len(old) == len(new):
        return [item for i, (a, b) in enumerate(zip(old, new)) for item in changed_paths(a, b, path + '/' + str(i))]
    return [] if exact(old, new) else [{'path': path, 'change': 'changed', 'old': deepcopy(old), 'new': deepcopy(new)}]


@dataclass(frozen=True)
class ReviewedClockAdapter:
    json_name: str
    csv_name: str
    json_sha256: str
    csv_sha256: str
    json_bytes: int
    csv_bytes: int
    fullwindow_description: str
    method: dict
    producer_audit_sha256: str
    independent_audit_sha256: str
    contract_id: str = DEFAULT_CLOCK_ADAPTER

    def normalize(self, source, baseline_source):
        require(all(HASH.fullmatch(h) for h in (self.json_sha256, self.csv_sha256,
                self.producer_audit_sha256, self.independent_audit_sha256)), 'Incomplete reviewed registration')
        source = Path(source)
        require(source.name == self.json_name and Path(self.csv_name).name == self.csv_name,
                'Unreviewed public source basename')
        raw, csv_raw = read_stable(source), read_stable(source.with_name(self.csv_name))
        require(len(raw) == self.json_bytes and sha(raw) == self.json_sha256 and
                len(csv_raw) == self.csv_bytes and sha(csv_raw) == self.csv_sha256, 'Unreviewed V9 JSON/CSV bytes')
        obj = parse_json(raw)
        require(obj['schema'] == SOURCE_SCHEMA and obj['status'] == SOURCE_STATUS and
                obj['metric_window'] == CLOCK_WINDOW, 'Unreviewed V9 schema/status/clock')
        require(set(obj) == set(baseline_source), 'Unreviewed V9 source top-level field')
        require(set(obj['methods']) == set(baseline_source['methods']) | {'clock_rescore'}, 'Unreviewed clock methods')
        validate_clock_method(self.method)
        require(exact(obj['methods']['clock_rescore'], self.method) and
                obj['methods']['fullwindow'] == self.fullwindow_description, 'Clock method text differs from reviewed source')
        require(all(row['metric_window'] == CLOCK_WINDOW for row in obj['episodes']) and
                all(row['metric_window'] == CLOCK_WINDOW for row in obj['comparisons']), 'Mixed body/wrist clocks')
        validate_source_invariants(baseline_source, obj)
        require(csv_raw == source_csv_bytes(obj), 'V9 CSV differs from exact 180×24 source rows')
        return obj

    def extension(self):
        return {'status': 'verified', 'source_sha256': self.json_sha256,
            'source_csv_sha256': self.csv_sha256, 'baseline_source_sha256': V8_JSON_SHA,
            'baseline_schema_version': 6, 'metrics': list(FULL4), 'window': CLOCK_WINDOW,
            'old_root_endpoint_method_flags_scope': HISTORICAL_METHOD_SCOPE, 'new_physical_episodes': 0}


# Frozen from the independently reviewed all180 science and exact two-file public projection.
# Caller-supplied hashes, a self-declared PASS or a CLI adapter name cannot register one.
_REVIEWED_CLOCK_ADAPTERS = {
    DEFAULT_CLOCK_ADAPTER: ReviewedClockAdapter(
        json_name='public_sevenerror_completion.json',
        csv_name='public_sevenerror_episodes.csv',
        json_sha256='8531f0cb539d6e713334efcbc6211ae3896f42bd000cd793cb896933a65b061f',
        csv_sha256='ee64fb6c35d368fd6913f29baecb9f63c8b19e8252fe0f81a7207e0b2af2162c',
        json_bytes=471938, csv_bytes=77532,
        fullwindow_description='身体/手腕四项由既有200Hz实际qpos离线运动学重建，在50Hz参考同刻评分；motion_t=1..Ncommon−1，含首次失败及其后全部记录，frame0初始化与参考后hold不新增评分。',
        method={'window': 'full_replay_50hz_same_time_raw_body_fk_at_reference',
 'source': '同一批既有180回合、90个条件/seed配对、45个不同动作；仅离线重评分，不增加物理回放或policy推理。',
 'new_physical_episodes': 0,
 'sampling': '原200Hz raw qpos索引4*m−1对应参考时刻0.02*m秒；只调用mj_kinematics重建实际body世界姿态，不执行物理积分。',
 'reference_window': '保留原参考身体/手腕数组与motion_t=1..Ncommon−1全部评分序列；包含失败后记录，frame0初始化和参考后hold排除。',
 'alignment': '每帧实际与参考分别减去自身根XY，再逆旋转自身projected yaw；Z保持绝对值。沿用Common14（踝而非脚趾）与双手腕。',
 'position': '局部三维位置欧氏距离先按该帧身体/双手腕平均，再全窗样本算术平均；单位mm，不是RMS或均值向量的范数。',
 'orientation': '保留原wxyz四元数与不归一化的评分代数，相对姿态为conjugate(reference_local)*actual_local，按2*atan2(norm(xyz),max(abs(w),1e−9))取最短角再平均；单位rad，q与−q等价。',
 'precision': 'FK世界姿态先按原缓存精度转FP32，逐帧沿用原writer的row.mean()，再按原float64时窗求均值；原四项逐帧值和回合均值均精确复现后才替换实际身体采样时刻。',
 'weighting_and_CI': '完整固定seed先动作内等权平均，再按动作等权；五组分别沿用PCG64 seed20261013、10000次配对动作bootstrap与linear分位区间。',
 'completion_does_not_filter_errors': True,
 'root_endpoint_completion_unchanged': True,
 'old_four_cache_timing': '旧四项actual body缓存比其参考早20ms；不同于旧root首次物理子步记录早15ms。本次只更正四项身体/手腕actual body时刻。',
 'reference_unchanged': True,
 'historical_preservation_flags_scope': 'root_fullwindow.old_four_window_unchanged及root_endpoint.existing_six_errors_and_completion_unchanged描述各自原V7/V8加入时的保留范围；本V9仅更正身体/手腕四项时钟，原两项全程根误差、根终点、完成率及失败诊断钟均保持。'},
        producer_audit_sha256='a1e935baa8c6c9f5cf8b3cbcf4d8ee775ca91407c6d6ce27762a5aa20d9ab644',
        independent_audit_sha256='c7d73da6119a56fa1365d526ac6e5fb80ae97aa6c4f5abdba14f77ed515efa08'),
}


def reviewed_clock_adapter(adapter_id=None):
    adapter_id = adapter_id or DEFAULT_CLOCK_ADAPTER
    if adapter_id not in _REVIEWED_CLOCK_ADAPTERS:
        raise ClockContractPending('Schema 7 disabled: final V9 public JSON/CSV and both audits are not code-registered')
    return _REVIEWED_CLOCK_ADAPTERS[adapter_id]


def normalize_clock_source(source_clock, source_v8, adapter_id=None):
    adapter = reviewed_clock_adapter(adapter_id)
    return adapter.normalize(Path(source_clock), load_v8_source(source_v8))


def apply_clock_rescore(data, source_clock, publication=False, adapter_id=None, *, source_v8=None):
    adapter = reviewed_clock_adapter(adapter_id)  # Closed before any unreviewed source is read.
    require(source_v8 is not None, 'Frozen V8 public source is required')
    baseline_source = load_v8_source(source_v8)
    source = adapter.normalize(Path(source_clock), baseline_source)
    require(data['schema_version'] == 6, 'Apply clock correction only after rebuilding the intact schema6 baseline')
    episodes = {episode_key(row): row for row in source['episodes']}
    expected = {episode_key(row): row for row in data['results'] if row['scope'] == 'per_motion'}
    require(len(episodes) == len(expected) == 180 and set(episodes) == set(expected), 'Strict six-key episode left join differs')
    groups = {group_key(item): item for item in source['comparisons']}
    require(len(groups) == 5 and set(groups) == {group_key(item) for item in data['comparisons']}, 'Five comparison groups differ')
    output = deepcopy(data)
    for row in output['results']:
        if row['scope'] == 'per_motion':
            item = episodes[episode_key(row)]
            require(item['run_id'] == row['fullwindow']['run_id'] and
                    item['scientific_selected_case_id'] == row['fullwindow']['case_id'], 'Original run/case identity differs')
            for name in FULL4:
                row['metrics'][name]['value'] = item[name]
            row['fullwindow']['metric_window'] = CLOCK_WINDOW
        else:
            group = groups[group_key(row)]
            for name in FULL4:
                cell = group['robot_means'][name][row['robot']]
                row['metrics'][name]['value'] = cell['value']
                row['metrics'][name]['ci95'] = deepcopy(cell['ci95'])
    for item in output['comparisons']:
        group = groups[group_key(item)]
        require(group['id'] == item['fullwindow_comparison_id'] and
                group['sample_set_sha256'] == item['sample_set_sha256'], 'Original aggregate comparison identity differs')
        for field in ('paired_deltas', 'paired_motion_values'):
            for name in FULL4:
                item[field][name] = deepcopy(group[field][name])
        item['metric_window'] = CLOCK_WINDOW
    output.update(schema_version=7, publication_state=CLOCK_PUBLIC_STATE if publication else CLOCK_PREVIEW_STATE,
                  clock_extension=adapter.extension())
    output['methods']['fullwindow'] = adapter.fullwindow_description
    output['methods']['clock_rescore'] = deepcopy(adapter.method)
    output['stats']['updated_utc'] = CLOCK_SNAPSHOT_DATE
    protect_schema6(data, output)
    return output


def framework_status():
    return {'schema7_enabled': bool(_REVIEWED_CLOCK_ADAPTERS),
            'clock_contract_status': 'reviewed_public_source_registered' if _REVIEWED_CLOCK_ADAPTERS else 'pending_final_producer_and_independent_audits',
            'registered_clock_adapters': sorted(_REVIEWED_CLOCK_ADAPTERS),
            'baseline_source_sha256': V8_JSON_SHA, 'four_metric_clock': CLOCK_WINDOW}


def set_report_state(data, state):
    """Editorial state only; caller must have genuine cloud evidence for V9 sync."""
    require(data['schema_version'] == 7 and state in REPORT_STATES, 'Unknown schema7 report state')
    require(len(data['report_downloads']) == 3, 'Original three report URLs required')
    output = deepcopy(data)
    selected = REPORT_STATES[state]
    output['stats']['report_status'] = selected['report_status']
    for item, label in zip(output['report_downloads'], selected['labels']):
        item['label'] = label
    return output


def clock_csv_columns(data, scope):
    """Schema7 retains the established46/55 export columns, not source24 columns."""
    require(data['schema_version'] == 7 and scope in ('per_motion', 'aggregate'), 'Schema7 CSV scope differs')
    from update_snapshot import EPISODE_COLUMNS_V6, COMPARISON_COLUMNS_V6
    return EPISODE_COLUMNS_V6 if scope == 'per_motion' else COMPARISON_COLUMNS_V6


def clock_csv_records(data, scope):
    """Reuse old column projection on a copy; change only the body/wrist window label."""
    require(data['schema_version'] == 7 and scope in ('per_motion', 'aggregate'), 'Schema7 CSV scope differs')
    from update_snapshot import csv_records
    view = deepcopy(data)
    view['schema_version'] = 6  # Reuse the seven-metric column serializer, never an old source validator.
    records = csv_records(view, scope)
    for record in records:
        record['metric_window'] = CLOCK_WINDOW
    return records


def clock_csv_bytes(data, scope):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=clock_csv_columns(data, scope), lineterminator='\r\n')
    writer.writeheader()
    writer.writerows(clock_csv_records(data, scope))
    return stream.getvalue().encode()
