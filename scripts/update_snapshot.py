#!/usr/bin/env python3
"""Project a hash-approved comparison snapshot into a public field whitelist.

Standard library only. Never follows a path or copies an evidence attachment
from the comparison input. Updating requires an explicitly reviewed source SHA.
The six frozen public extensions are retained only after identity/schema checks;
--extensions-manifest initializes only the reviewed private handoff's four-file
public allowlist; --fullwindow-receipt initializes the two supplemental
files from their terminal-reviewed allowlist. No new experiments are imported.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

METRICS = ('body_pos_mm', 'body_ori_rad', 'root_pos_m', 'gpu_train_hours',
           'wrist_pos_mm', 'wrist_ori_rad', 'episode_return', 'progress_pct')
ROW = ('id', 'label', 'phase', 'robot', 'dataset', 'condition', 'mode', 'seed',
       'scope', 'motion_id', 'status', 'status_reason')
COVERAGE = ('numerator', 'denominator', 'unit', 'reason')
CI = ('low', 'high', 'level', 'unit', 'method', 'resampling_unit', 'n_clusters',
      'n_seeds', 'resamples', 'reason')
PAIRING = ('comparison_id', 'sample_set_sha256', 'verified', 'reason')
PAIR_KEY = ('phase', 'dataset', 'condition', 'mode', 'motion_id', 'seed',
            'protocol_sha256', 'runtime')
PRIVATE = re.compile(r'/home/|/Users/|file:|localhost|127\.0\.0\.1|'
                     r'\b(?:candidate_host|candidate_ssh|watchdog_pid|SSH|kex)\b|'
                     r'\b(?:10|192\.168)\.\d+\.\d+\.\d+', re.I)
ALLOWED_HOSTS = {'github.com', 'raw.githubusercontent.com',
                 'roboparty.feishu.cn', 'egalahad.github.io',
                 'huggingface.co', 'drive.google.com'}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pick(obj, keys):
    return {k: obj[k] for k in keys if k in obj}

def texts(values):
    return [x for x in values if isinstance(x, str) and not PRIVATE.search(x)]

def coverage(obj):
    return pick(obj or {}, COVERAGE)

def metrics(obj):
    out = {}
    for key in METRICS:
        cell = obj[key]
        out[key] = pick(cell, ('value', 'reason', 'sample_set_sha256'))
        out[key]['coverage'] = coverage(cell.get('coverage'))
        if 'ci' in cell:
            out[key]['ci'] = pick(cell['ci'], CI)
    return out

def link(obj):
    url = obj.get('url', '')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError('Unreviewed external link')
    out = pick(obj, ('label', 'url', 'sha256'))
    if parsed.hostname == 'roboparty.feishu.cn':
        out['access'] = 'organization_permission_required'
    return out

def video(obj):
    out = link(obj)
    out.update(pick(obj, ('description', 'synchronized', 'robot', 'clip', 'kind',
                         'full_window', 'window_sim_s', 'duration_s', 'bytes',
                         'video_manifest_sha256', 'upload_receipt_sha256',
                         'cloud_original_sha256_verified', 'mapping_status')))
    # No original video data is redistributed; hashes describe local originals.
    out['description'] = obj.get('description', '') + ' 飞书链接需组织登录/权限。'
    out['source_runs'] = [pick(x, ('run_id', 'episode_id', 'robot', 'motion',
                                 'dataset', 'condition', 'original_condition',
                                 'mode', 'seed', 'trajectory_sha256',
                                 'states_sha256', 'manifest_sha256'))
                          for x in obj.get('source_runs', [])]
    return out

def pair_key(row):
    """Effective condition is already canonicalized by the frozen adapter.

    Robot-specific configs/checkpoints are deliberately not equality keys.
    Status, progress and failure counts never determine inclusion.
    """
    return tuple(row.get(k) for k in PAIR_KEY[:6]) + tuple(
        row.get('provenance', {}).get(k) for k in PAIR_KEY[6:])

def paired_selection(source):
    """Exact two-robot intersection; reject ambiguous duplicate identities."""
    groups = defaultdict(dict)
    cohorts = defaultdict(list)
    for row in source['results']:
        if row['scope'] != 'per_motion':
            continue
        robot = row['robot']
        if robot not in {'rp1', 'g1'}:
            continue
        key = pair_key(row)
        if any(value is None or value == '' for value in key):
            raise ValueError('Missing exact pairing identity')
        if robot in groups[key]:
            raise ValueError('Duplicate robot identity in pairing key')
        groups[key][robot] = row
        cohorts[key[:4] + key[6:]].append(row)
    paired = {key: rows for key, rows in groups.items()
              if set(rows) == {'rp1', 'g1'}}
    ids = {r['id'] for rows in paired.values() for r in rows.values()}
    rows_by_id = {r['id']: r for r in source['results']}
    comparisons = set()
    for comparison in source['comparisons']:
        members = [rows_by_id.get(i) for i in comparison['expected_participants']]
        if len(members) != 2 or not all(members):
            continue
        if {r['robot'] for r in members} != {'rp1', 'g1'}:
            continue
        if any(r['scope'] != 'aggregate' for r in members):
            continue
        keys = [pair_key(r) for r in members]
        if keys[0] != keys[1]:
            continue
        cohort = keys[0][:4] + keys[0][6:]
        episodes = cohorts.get(cohort, [])
        # Frozen aggregate means/CI are reusable only if its complete input
        # population survives. Otherwise omit the aggregate; never relabel it.
        if not episodes or not all(r['id'] in ids for r in episodes):
            continue
        if any(r.get('pairing', {}).get('comparison_id') != comparison['id']
               for r in members):
            continue
        comparisons.add(comparison['id'])
        ids.update(r['id'] for r in members)
    return ids, comparisons, paired

def paired_video(item, rows):
    runs = item.get('source_runs', [])
    if not item.get('synchronized') or len(runs) != 2:
        return False
    if {run.get('robot') for run in runs} != {'rp1', 'g1'}:
        return False
    members = [rows.get(run.get('episode_id')) for run in runs]
    if not all(members) or pair_key(members[0]) != pair_key(members[1]):
        return False
    for run, row in zip(runs, members):
        if row['scope'] != 'per_motion' or any(
            run.get(a) != row.get(b) for a, b in (
                ('robot', 'robot'), ('dataset', 'dataset'), ('condition', 'condition'),
                ('mode', 'mode'), ('seed', 'seed'), ('motion', 'motion_id'))):
            return False
    return True

def project(source):
    selected_ids, selected_comparisons, pairs = paired_selection(source)
    selected_rows = {r['id']: r for r in source['results'] if r['id'] in selected_ids}
    out = pick(source, ('schema_version', 'title', 'subtitle', 'updated_utc',
                        'status', 'aggregate_sha256', 'adapter_sha256'))
    episode_count = sum(r['scope'] == 'per_motion' for r in selected_rows.values())
    motion_count = len({r['motion_id'] for r in selected_rows.values() if r['scope'] == 'per_motion'})
    out['status_message'] = (f'Phase A 共同动作快照：{motion_count} 个动作、{len(pairs)} 个条件/seed 配对、'
                             f'{episode_count} 条回合记录。失败与可配对删失按原状态保留；'
                             '各条件分别统计，重复不增加独立动作数。Phase B 正式重训尚未开始。')
    out['public_scope'] = dict(unique_motions=motion_count, paired_cases=len(pairs),
        episodes=episode_count, aggregate_rows=len(selected_ids)-episode_count,
        result_rows=len(selected_ids), comparison_groups=len(selected_comparisons),
        pairing_key=list(PAIR_KEY),
        rule='Exact RP1/G1 identity intersection; condition is canonical effective condition; no status or success filtering; original raw records preserved.')
    out['phases'] = {
        'A': dict(label='Phase A · 发布权重', status='complete', description=out['status_message']),
        'B': dict(label='Phase B · 独立重训', status='blocked',
                  description='同配置重训尚未开始；暂无 Phase B 成绩。等待独立授权和启动验收。')}
    datasets = {r['dataset'] for r in selected_rows.values()}
    out['datasets'] = [pick(x, ('id', 'label', 'expected_motions')) for x in source['datasets'] if x['id'] in datasets]
    out['results'] = []
    for row in source['results']:
        if row['id'] not in selected_ids:
            continue
        result = pick(row, ROW)
        result['coverage'] = coverage(row.get('coverage'))
        result['paired_coverage'] = coverage(row.get('paired_coverage'))
        result['metrics'] = metrics(row['metrics'])
        if 'pairing' in row:
            result['pairing'] = pick(row['pairing'], PAIRING)
        result['checkpoint'] = pick(row['checkpoint'], ('name', 'sha256'))
        prov = row.get('provenance', {})
        result['provenance'] = pick(prov, ('source_sha256', 'config_sha256',
                                         'protocol_sha256', 'runtime'))
        result['provenance']['raw_links'] = []
        result['provenance']['evidence_hashes'] = [pick(x, ('label', 'sha256'))
                                                  for x in prov.get('raw_links', [])]
        result['videos'] = [video(x) for x in row.get('videos', []) if paired_video(x, selected_rows)]
        result['notes'] = texts(row.get('notes', []))
        result['notes'].append('公开版保留原记录 SHA；内部运行附件未公开。方法与来源见 DATA_PROVENANCE.md。')
        result['failures'] = [pick(x, ('reason', 'count', 'denominator', 'unit'))
                              for x in row.get('failures', [])]
        out['results'].append(result)
    out['comparisons'] = []
    for c in source['comparisons']:
        if c['id'] not in selected_comparisons:
            continue
        result = pick(c, ('id', 'label', 'verified', 'expected_participants',
                          'sample_set_sha256', 'reason', 'protocol', 'provisional',
                          'expected_paired_motions'))
        result['paired_deltas'] = {k: pick(v, ('value', 'ci95', 'unit', 'n_motions'))
                                    for k, v in c.get('paired_deltas', {}).items()
                                    if k in METRICS}
        meta = c.get('cohort_metadata', {})
        result['cohort_metadata'] = pick(meta, ('strict_pair', 'metadata_status'))
        result['cohort_metadata']['source_provenance'] = [
            pick(x, ('source_repo', 'source_revision', 'source_manifest_sha256'))
            for x in meta.get('source_provenance', [])]
        out['comparisons'].append(result)
    out['official_references'] = []
    out['fairness'] = [pick(x, ('item', 'rp1', 'g1', 'status', 'evidence', 'phase',
                              'condition', 'mode')) for x in source['fairness']]
    out['fairness'].extend([
        dict(item='发布权重训练规模与证据范围', phase='A', status='disclosed_difference',
             rp1='发布方声明 8×8192 环境；本份权重配置与 checkpoint 均记每 rank 8192。',
             g1='v1.1 README 声明 8×8192 环境；未获得独立训练 run 日志。',
             evidence='训练代码证明 num_envs 为每 rank；8 卡为发布方声明，不是完整训练历史审计。'),
        dict(item='训练 seed 与数据', phase='A', status='disclosed_difference',
             rp1='发布包 seed=42；机器人匹配学生；未明确独立 v1.1 标签。',
             g1='v1.1 README 配方记 seed=0；本次 G1 权重的历史训练 seed 缺少直接证据。训练数据与 RP1 不同。',
             evidence='相同声明规模不代表全部训练条件公平；发布权重比较不能推断形态因果效应。')])
    for item in out['fairness']:
        if item['item'] == '训练成本':
            item.update(rp1='unknown', g1='unknown',
                        evidence='本轮完整训练成本未知；CPU 推理耗时不能转换为训练 GPU·h。')
    out['statistics'] = pick(source['statistics'], ('aggregation', 'ci_method',
        'ci_scope', 'missing_policy', 'rank_policy'))
    out['statistics']['limitations'] = texts(source['statistics'].get('limitations', []))
    out['statistics']['aggregation'] = '完整相同 seed 集先求每动作均值，再逐动作等权；各条件独立报告，重复不增加独立动作数。'
    out['notes'] = [
        '40 段共同 LAFAN40 动作；nominal / native_position：RP1 Progress 79.736%，G1 77.269%。配对差值区间跨零，不能声称 RP1 稳定优胜。',
        '当前条件下 RP1 body 误差较低，G1 wrist 姿态误差较低；各指标应分别解读。',
        '30 条名义重复逐字节确定性一致，不增加独立样本量。CI 是固定权重/当前动作条件区间。',
        '仅纳入双方共有且条件、模式、seed 匹配的动作；失败和可配对删失保留，不填 0。历史原始记录保留。',
        '七项描述性置信区间未做多重比较校正；身体位置差的区间上界接近零，应谨慎解释。',
        '共同动作技术报告与既有同步视频需组织登录/权限；视频在线预览不等于云端原字节哈希核验。',
        '公开站点仅发布字段白名单汇总与来源 SHA；内部附件、服务器信息、checkpoint、原始大包均未再分发。']
    out['downloads'] = [
        dict(label='公开汇总快照 JSON', url='./data.json'),
        dict(label='科学方法与来源说明', url='./DATA_PROVENANCE.md'),
        dict(label='版本与文件 SHA256 清单', url='./RELEASE_MANIFEST.json'),
        dict(label='技术报告正文 · 共同动作版（飞书，需组织权限）',
             url='https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb',
             access='organization_permission_required'),
        dict(label='技术报告 PDF · v3，共同动作版（飞书，需组织权限）',
             url='https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7',
             access='organization_permission_required'),
        dict(label='技术报告 DOCX · v3，共同动作版（飞书，需组织权限）',
             url='https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce',
             access='organization_permission_required')]
    out['downloads'].extend(video(x) for x in source['downloads']
                            if urlparse(x.get('url', '')).hostname == 'roboparty.feishu.cn'
                            and paired_video(x, selected_rows))
    return out

def validate_projection(source, out):
    ids, comparison_ids, _ = paired_selection(source)
    assert {x['id'] for x in out['results']} == ids
    originals = {x['id']: x for x in source['results']}
    for after in out['results']:
        before = originals[after['id']]
        assert before['metrics'] == after['metrics'], f'Metric drift: {before["id"]}'
        assert before['coverage'] == after['coverage']
        assert before['paired_coverage'] == after['paired_coverage']
        assert before.get('pairing') == after.get('pairing')
    assert {x['id'] for x in out['comparisons']} == comparison_ids
    comparisons = {x['id']: x for x in source['comparisons']}
    for after in out['comparisons']:
        before = comparisons[after['id']]
        assert before['paired_deltas'] == after['paired_deltas']
    encoded = json.dumps(out, ensure_ascii=False, allow_nan=False)
    if PRIVATE.search(encoded):
        raise ValueError('Private path or infrastructure marker in public projection')
    assert 'source_status' not in encoded
    assert len({x['id'] for x in out['results']}) == len(out['results'])

def reviewed_extensions(dest, handoff_path=None, fullwindow_receipt=None):
    """Preflight all six exact public attachments before writing any output.

    Reuse the publication contract, not private source/model assets. An explicit
    handoff is the only initialization path for a directory without the reviewed
    extension metadata. Each pinned handoff authorizes only its four or two public files.
    """
    from verify_public import DISPLAY_SCOPE, EXTENSIONS, FULLWINDOW_RECEIPT_SHA

    expected = {
        'public_extreme5.json': ('extreme5.json', EXTENSIONS['extreme5']['json_sha256'],
                                 'rp1-g1-public-extreme5-handoff-v1'),
        'public_extreme5_episodes.csv': ('extreme5.csv', EXTENSIONS['extreme5']['csv_sha256'], None),
        'public_hardware_comparison.json': ('hardware.json', EXTENSIONS['hardware']['json_sha256'],
                                            'rp1-g1-public-hardware-comparison-v1'),
        'public_hardware_comparison.csv': ('hardware.csv', EXTENSIONS['hardware']['csv_sha256'], None),
    }
    previous = {}
    previous_path = dest / 'RELEASE_MANIFEST.json'
    if previous_path.exists():
        assert previous_path.is_file() and not previous_path.is_symlink(), 'Unsafe previous manifest'
        previous = json.loads(previous_path.read_bytes())
    payloads = {}
    if handoff_path is None:
        legacy_extensions = {key: value for key, value in EXTENSIONS.items() if key != 'fullwindow'}
        accepted_extensions = [EXTENSIONS] + ([legacy_extensions] if fullwindow_receipt is not None else [])
        assert previous.get('extensions') in accepted_extensions and previous.get('display_scope') == DISPLAY_SCOPE, (
            'Reviewed extension metadata is required; initialize with --extensions-manifest '
            'and --fullwindow-receipt using the formal frozen handoffs')
        inputs = {name: dest / spec[0] for name, spec in expected.items()}
    else:
        raw = handoff_path.read_bytes()
        assert sha(raw) == EXTENSIONS['handoff_sha256'], 'Unreviewed extensions handoff'
        handoff = json.loads(raw)
        assert handoff['schema'] == 'rp1-g1-extreme5-hardware-website-handoff-v1'
        assert handoff['expected_combined_public_counts'] == DISPLAY_SCOPE
        entries = {entry['filename']: entry for entry in handoff['public_allowlist']}
        assert len(handoff['public_allowlist']) == len(entries) == 4 and set(entries) == set(expected), (
            'Extensions handoff is not the four-file public allowlist')
        inputs = {}
        for name, entry in entries.items():
            assert entry['sha256'] == expected[name][1], 'Extensions handoff file identity differs'
            inputs[name] = Path(entry['local_path'])
    for source_name, (name, digest, schema) in expected.items():
        path = inputs[source_name]
        assert path.is_file() and not path.is_symlink(), (
            'Missing reviewed public extension: ' + name + '; obtain the formal frozen handoff')
        raw = path.read_bytes()
        assert sha(raw) == digest, 'Unreviewed public extension: ' + name
        if schema is not None:
            assert json.loads(raw)['schema'] == schema, 'Public extension schema differs: ' + name
        if handoff_path is not None:
            assert len(raw) == entries[source_name]['bytes'], 'Public extension byte count differs'
        payloads[name] = raw
    supplemental = {
        'public_fullwindow.json': ('fullwindow.json', EXTENSIONS['fullwindow']['json_sha256'],
                                  'rp1-g1-public-fullwindow-handoff-v1', 407473),
        'public_episodes_fullwindow.csv': ('fullwindow.csv', EXTENSIONS['fullwindow']['csv_sha256'], None, 88651),
    }
    if fullwindow_receipt is None:
        assert previous.get('extensions') == EXTENSIONS, (
            'Terminal fullwindow receipt required for initial integration; use --fullwindow-receipt')
        full_inputs = {name: dest / spec[0] for name, spec in supplemental.items()}
    else:
        raw = fullwindow_receipt.read_bytes()
        assert sha(raw) == FULLWINDOW_RECEIPT_SHA, 'Unreviewed or historical pending fullwindow receipt'
        receipt = json.loads(raw)
        assert receipt['schema'] == 'rp1-g1-fullwindow-public-final-receipt-v1'
        assert receipt['status'] == 'PASS_TWO_PUBLIC_FILES_FROZEN_READY_FOR_OWNER_SUPPLEMENTAL_INTEGRATION'
        assert receipt['independent_final_audit']['sha256'] == EXTENSIONS['fullwindow']['independent_audit_sha256']
        assert receipt['internal_manifest']['sha256'] == EXTENSIONS['fullwindow']['historical_handoff_sha256']
        full_entries = {entry['filename']: entry for entry in receipt['public_allowlist']}
        assert len(receipt['public_allowlist']) == len(full_entries) == 2 and set(full_entries) == set(supplemental), (
            'Fullwindow terminal receipt is not the two-file public allowlist')
        full_inputs = {}
        for name, entry in full_entries.items():
            assert (entry['sha256'], entry['bytes']) == (supplemental[name][1], supplemental[name][3]), (
                'Fullwindow terminal file identity differs')
            full_inputs[name] = Path(entry['local_path'])
    for source_name, (name, digest, schema, size) in supplemental.items():
        path = full_inputs[source_name]
        assert path.is_file() and not path.is_symlink(), 'Missing reviewed fullwindow supplement: ' + name
        raw = path.read_bytes()
        assert sha(raw) == digest and len(raw) == size, 'Unreviewed fullwindow supplement: ' + name
        if schema is not None:
            assert json.loads(raw)['schema'] == schema, 'Fullwindow public schema differs'
        payloads[name] = raw
    metadata = dict(extensions=deepcopy(EXTENSIONS), display_scope=deepcopy(DISPLAY_SCOPE))
    # These are already public version labels, not the private handoff body.
    for name in ('report_revision', 'report_scope_receipt_sha256',
                 'presentation_revision', 'presentation_updated_utc'):
        if name in previous:
            assert isinstance(previous[name], str) and not PRIVATE.search(previous[name]), (
                'Private or invalid public revision metadata')
            metadata[name] = previous[name]
    return metadata, payloads

def public_file_hashes(dest):
    """Hash existing publication-whitelisted files; never enumerate/copy evidence."""
    from verify_public import PUBLISH_FILES

    files = {}
    for name in sorted(PUBLISH_FILES - {'RELEASE_MANIFEST.json'}):
        path = dest / name
        if not path.exists():
            continue
        assert path.is_file() and not path.is_symlink(), 'Unsafe public bundle file: ' + name
        raw = path.read_bytes()
        files[name] = dict(bytes=len(raw), sha256=sha(raw))
    return files

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--expected-source-sha', required=True)
    parser.add_argument('--expected-aggregate-sha', required=True)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--expected-handoff-sha', required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    parser.add_argument('--extensions-manifest', type=Path,
                        help='formal frozen Extreme5/hardware private handoff; copy only its four public files')
    parser.add_argument('--fullwindow-receipt', type=Path,
                        help='terminal frozen fullwindow private receipt; copy only its two public files')
    args = parser.parse_args()
    handoff_raw = args.handoff.read_bytes()
    assert sha(handoff_raw) == args.expected_handoff_sha, 'Unreviewed handoff manifest'
    handoff = json.loads(handoff_raw)
    assert handoff['schema'] == 'rp1-g1-website-handoff-manifest-v1'
    # A changed scientific contract requires a deliberate reviewed script update.
    assert handoff['version'] == 'phaseA503_036559d03c4a_sitehandoff_20261013_v1'
    assert handoff['data_identity']['source_site_data_sha256'] == args.expected_source_sha
    assert handoff['aggregate_sha256'] == args.expected_aggregate_sha
    identity = handoff['data_identity']
    assert (identity['planned_terminal'], identity['selected_episodes'],
            identity['selected_full'], identity['selected_censored_smoke']) == (503, 493, 488, 5)
    assert identity['phaseB_has_formal_or_heldout_scores'] is False
    chosen = {'site/dist/data.json', 'site/dist/index.html', 'site/dist/app.js',
              'site/dist/style.css', 'site/build_data.py', 'report/aggregate.json'}
    sources = []
    for entry in handoff['source_files']:
        if entry['root'] == 'round2' and entry['path'] in chosen:
            source_path = args.source_data.parent.parent.parent / entry['path']
            content = source_path.read_bytes()
            assert len(content) == entry['bytes'] and sha(content) == entry['sha256'], entry['path']
            sources.append(pick(entry, ('path', 'bytes', 'sha256')))
    assert len(sources) == len(chosen), 'Missing chosen input in reviewed handoff'
    raw = args.source_data.read_bytes()
    assert sha(raw) == args.expected_source_sha, 'Source changed or was not approved'
    source = json.loads(raw)
    assert source['aggregate_sha256'] == args.expected_aggregate_sha, 'Aggregate version mismatch'
    out = project(source)
    validate_projection(source, out)
    assert args.source_data.read_bytes() == raw, 'Source changed during build'
    dest = args.output_dir
    extension_metadata, extension_payloads = reviewed_extensions(
        dest, args.extensions_manifest, args.fullwindow_receipt)
    dest.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()
    (dest/'data.json').write_bytes(data)
    for name, payload in extension_payloads.items():
        path = dest / name
        # Default reuse preserves the exact existing bytes and file identities.
        # Explicitly pinned handoffs initialize only their reviewed public files.
        if not path.exists() or path.read_bytes() != payload:
            assert args.extensions_manifest is not None or args.fullwindow_receipt is not None, (
                'Public extension changed during build')
            path.write_bytes(payload)
    manifest = dict(schema='rp1-g1-public-snapshot-v1',
                    consumed_handoff_version=handoff['version'],
                    consumed_handoff_sha256=args.expected_handoff_sha,
                    data_version='round2-phaseA-'+args.expected_aggregate_sha[:12],
                    generated_utc=datetime.now(timezone.utc).isoformat(),
                    comparison_snapshot_updated_utc=source['updated_utc'],
                    source=dict(site_data_sha256=args.expected_source_sha,
                                aggregate_sha256=args.expected_aggregate_sha,
                                adapter_sha256=source['adapter_sha256']),
                    public_data_sha256=sha(data), result_rows=len(out['results']),
                    reviewed_source_files=sources,
                    comparison_groups=len(out['comparisons']),
                    projection='Explicit public whitelist and exact RP1/G1 pairing intersection; retained metrics, CI and denominators unchanged',
                    external_link_access='All Feishu links require organization permissions',
                    excluded=['private infrastructure','internal evidence attachments',
                              'absolute local paths','checkpoints','raw data archives'])
    manifest['public_scope'] = out['public_scope']
    manifest['scientific_contract'] = {k: deepcopy(handoff[k]) for k in ('methods', 'primary_anchor_values')}
    manifest['scientific_contract']['methods']['n_a'] = 'Missing or censored paired scores retain null and their reasons; never impute zeros or rank unavailable values.'
    manifest['scientific_contract']['coverage'] = dict(unique_common_motions=out['public_scope']['unique_motions'],
        paired_cases=out['public_scope']['paired_cases'], paired_episodes=out['public_scope']['episodes'],
        aggregate_rows=out['public_scope']['aggregate_rows'], comparison_groups=out['public_scope']['comparison_groups'])
    manifest.update(extension_metadata)
    manifest['files'] = public_file_hashes(dest)
    (dest/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(data_version=manifest['data_version'],
                         public_data_sha256=sha(data), result_rows=len(out['results']),
                         extensions=list(extension_payloads), display_scope=manifest['display_scope'])))

if __name__ == '__main__':
    main()
