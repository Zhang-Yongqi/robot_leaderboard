#!/usr/bin/env python3
"""Project a hash-approved comparison snapshot into a public field whitelist.

Standard library only. Never follows a path or copies an evidence attachment
from the input. Updating requires an explicitly reviewed source SHA.
"""
import argparse
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

def project(source):
    out = pick(source, ('schema_version', 'title', 'subtitle', 'updated_utc',
                        'status', 'aggregate_sha256', 'adapter_sha256'))
    out['status_message'] = ('Phase A 排期快照已记录：493 个计划结果 = 488 个完整有效回合 + '
                             '5 个删失 smoke；另保留 10 条旧时钟终态记录，其成绩已被修正结果替换。'
                             '这不代表七组双机器人全量验收。Phase B 正式重训尚未开始。')
    out['phases'] = {
        'A': dict(label='Phase A · 发布权重', status='complete', description=out['status_message']),
        'B': dict(label='Phase B · 独立重训', status='blocked',
                  description='同配置重训尚未开始；暂无 Phase B 成绩。等待独立授权和启动验收。')}
    out['datasets'] = [pick(x, ('id', 'label', 'expected_motions')) for x in source['datasets']]
    out['results'] = []
    for row in source['results']:
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
        result['videos'] = [video(x) for x in row.get('videos', [])]
        result['notes'] = texts(row.get('notes', []))
        result['notes'].append('公开版保留原记录 SHA；内部运行附件未公开。方法与来源见 DATA_PROVENANCE.md。')
        result['failures'] = [pick(x, ('reason', 'count', 'denominator', 'unit'))
                              for x in row.get('failures', [])]
        out['results'].append(result)
    out['comparisons'] = []
    for c in source['comparisons']:
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
    for r in source['official_references']:
        result = pick(r, ('id', 'label', 'robot', 'dataset', 'status', 'context',
                          'checkpoint_cost_id', 'cost_scope'))
        result.update(metrics=metrics(r['metrics']), coverage=coverage(r['coverage']),
                      source=link(r['source']))
        out['official_references'].append(result)
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
    out['statistics'] = pick(source['statistics'], ('aggregation', 'ci_method',
        'ci_scope', 'missing_policy', 'rank_policy'))
    out['statistics']['limitations'] = texts(source['statistics'].get('limitations', []))
    out['notes'] = [
        '40 段共同 LAFAN40 动作；nominal / native_position：RP1 Progress 79.736%，G1 77.269%。配对差值区间跨零，不能声称 RP1 稳定优胜。',
        '当前条件下 RP1 body 误差较低，G1 wrist 姿态误差较低；各指标应分别解读。',
        '30 条名义重复逐字节确定性一致，不增加独立样本量。CI 是固定权重/当前动作条件区间。',
        '缺失或仅 G1 数据独立展示，不填 0；全目标数据集共同配对尚未齐全。',
        'G1 另有 318 段补充动作，缺少全套 RP1 配对；PHUMA30 缺有效 FPS，Root90 使用推定元数据。',
        '七项描述性置信区间未做多重比较校正；身体位置差的区间上界接近零，应谨慎解释。',
        '飞书完整报告与 35 个视频均需组织登录/权限；链接权限未变更。视频核验是在线预览，不等于云端原字节哈希核验。',
        '原始附录本地 42 分卷 + 5 控制文件已验收；云端仅确认 34/42 分卷、0/5 控制文件，13 项终态未知。',
        '公开站点仅发布字段白名单汇总与来源 SHA；内部附件、服务器信息、checkpoint、原始大包均未再分发。']
    out['downloads'] = [
        dict(label='公开汇总快照 JSON', url='./data.json'),
        dict(label='科学方法与来源说明', url='./DATA_PROVENANCE.md'),
        dict(label='版本与文件 SHA256 清单', url='./RELEASE_MANIFEST.json'),
        dict(label='技术报告正文 · 专业改写版（飞书，需组织权限）',
             url='https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb',
             access='organization_permission_required'),
        dict(label='技术报告 PDF · v2，10 页（飞书，需组织权限）',
             url='https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7',
             access='organization_permission_required'),
        dict(label='技术报告 DOCX · v2，10 页（飞书，需组织权限）',
             url='https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce',
             access='organization_permission_required')]
    out['downloads'].extend(video(x) for x in source['downloads']
                            if urlparse(x.get('url', '')).hostname == 'roboparty.feishu.cn')
    return out

def validate_projection(source, out):
    assert len(out['results']) == len(source['results'])
    assert [x['id'] for x in out['results']] == [x['id'] for x in source['results']]
    for before, after in zip(source['results'], out['results']):
        assert before['metrics'] == after['metrics'], f'Metric drift: {before["id"]}'
        assert before['coverage'] == after['coverage']
        assert before['paired_coverage'] == after['paired_coverage']
        assert before.get('pairing') == after.get('pairing')
    for before, after in zip(source['comparisons'], out['comparisons']):
        assert before['paired_deltas'] == after['paired_deltas']
    encoded = json.dumps(out, ensure_ascii=False, allow_nan=False)
    if PRIVATE.search(encoded):
        raise ValueError('Private path or infrastructure marker in public projection')
    assert 'source_status' not in encoded
    assert len({x['id'] for x in out['results']}) == len(out['results'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--expected-source-sha', required=True)
    parser.add_argument('--expected-aggregate-sha', required=True)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--expected-handoff-sha', required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
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
    dest.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()
    (dest/'data.json').write_bytes(data)
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
                    projection='Explicit field whitelist; numbers, CI, coverage, pairing unchanged',
                    external_link_access='All Feishu links require organization permissions',
                    excluded=['private infrastructure','internal evidence attachments',
                              'absolute local paths','checkpoints','raw data archives'])
    manifest['scientific_contract'] = {k: handoff[k] for k in ('methods', 'coverage', 'primary_anchor_values')}
    (dest/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(data_version=manifest['data_version'],
                         public_data_sha256=sha(data), result_rows=len(out['results']))))

if __name__ == '__main__':
    main()
