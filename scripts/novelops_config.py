#!/usr/bin/env python3
"""项目级配置 novelops.config.json 的加载与合并原语。

供 audit_chapter / knowledge_check / llm_client 三处消费；
无配置文件时一切走默认，行为与未配置化之前完全一致。
"""
import json
from pathlib import Path
from novelops_common import posix_path

CONFIG_FILE_NAME = 'novelops.config.json'

VALID_KEYWORD_MODES = ('extend', 'replace', 'disable')


def config_file_path(project):
    """配置文件存在时返回其路径字符串，否则返回 None。"""
    path = Path(project) / CONFIG_FILE_NAME
    return posix_path(path) if path.is_file() else None


def load_project_config(project):
    """读取项目根的 novelops.config.json；不存在返回 {}，损坏时 SystemExit。"""
    path = Path(project) / CONFIG_FILE_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise SystemExit('Invalid novelops.config.json at %s: %s' % (path, exc))
    if not isinstance(data, dict):
        raise SystemExit('Invalid novelops.config.json at %s: top-level value must be an object' % path)
    return data


def resolve_keyword_table(table_name, default_items, spec):
    """按 spec 合并关键词表，返回 (合并后列表, 来源标签)。

    spec 为 None 时返回默认表；否则 spec 形如
    {"mode": "extend"|"replace"|"disable", "items": [...]}，mode 缺省为 extend。
    extend = 默认在前去重追加；replace = 只用 items；disable = 空表。
    """
    if spec is None:
        return list(default_items), 'default'
    if not isinstance(spec, dict):
        raise SystemExit(
            'novelops.config.json keyword table %r must be an object with "mode"/"items", got %r'
            % (table_name, spec))
    mode = spec.get('mode', 'extend')
    if mode not in VALID_KEYWORD_MODES:
        raise SystemExit(
            'novelops.config.json keyword table %r has unknown mode %r (expected one of %s)'
            % (table_name, mode, '/'.join(VALID_KEYWORD_MODES)))
    if mode == 'disable':
        return [], 'disable'
    items = spec.get('items', [])
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise SystemExit(
            'novelops.config.json keyword table %r: "items" must be a list of strings' % table_name)
    if mode == 'replace':
        return list(items), 'replace'
    merged = list(default_items)
    for item in items:
        if item not in merged:
            merged.append(item)
    return merged, 'extend'


def resolve_thresholds(defaults, overrides):
    """逐规则浅覆盖阈值。defaults/overrides 均为 {rule_id: {阈值键: 值}}。

    未知 rule_id 或未知阈值键直接 SystemExit，防止拼写错误静默失效。
    """
    resolved = {rule_id: dict(values) for rule_id, values in defaults.items()}
    for rule_id, values in (overrides or {}).items():
        if rule_id not in resolved:
            raise SystemExit(
                'novelops.config.json audit.thresholds has unknown rule id %r (known: %s)'
                % (rule_id, ', '.join(sorted(resolved))))
        if not isinstance(values, dict):
            raise SystemExit(
                'novelops.config.json audit.thresholds[%r] must be an object' % rule_id)
        for key, value in values.items():
            if key not in resolved[rule_id]:
                raise SystemExit(
                    'novelops.config.json audit.thresholds[%r] has unknown key %r (known: %s)'
                    % (rule_id, key, ', '.join(sorted(resolved[rule_id]))))
            resolved[rule_id][key] = value
    return resolved


def resolve_disabled(valid_ids, disabled_list, label):
    """校验并返回禁用 id 集合；未知 id SystemExit。"""
    disabled = set()
    for item in disabled_list or []:
        if item not in valid_ids:
            raise SystemExit(
                'novelops.config.json %s has unknown id %r (known: %s)'
                % (label, item, ', '.join(sorted(valid_ids))))
        disabled.add(item)
    return disabled
