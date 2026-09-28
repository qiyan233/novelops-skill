#!/usr/bin/env python3
"""OpenAI 兼容 chat completions 传输层（纯标准库）。

面向 Nous Hermes 系列模型：默认接本地 Ollama，Nous Portal 云端改 base_url + api_key 即可。
只负责配置解析、请求组包、HTTP 调用、<think> 推理块剥离与 mock 通道；
不包含任何业务提示词——那是 draft_chapter / auto_revise 的职责。
"""
import json
import os
import re
import socket
import urllib.error
import urllib.request
from pathlib import Path

from novelops_common import read_text

DEFAULT_LLM_CONFIG = {
    'provider': 'ollama',
    'base_url': 'http://localhost:11434/v1',
    'model': 'hermes4',
    'api_key': None,
    'api_key_env': 'NOVELOPS_LLM_API_KEY',
    'temperature': 0.6,
    'top_p': 0.95,
    'max_tokens': 4096,
    'timeout_seconds': 300,
    'strip_think': True,
}

MOCK_ENV_VAR = 'NOVELOPS_LLM_MOCK'

THINK_BLOCK_RE = re.compile(r'<think>.*?</think>\s*', re.S | re.I)


def resolve_llm_config(project_config, overrides=None):
    """DEFAULT 拷贝 → 项目配置 llm 节覆盖 → CLI overrides（仅非 None 键）覆盖。

    未知键一律 SystemExit，防拼写静默失效。
    """
    resolved = dict(DEFAULT_LLM_CONFIG)
    llm_section = (project_config or {}).get('llm') or {}
    for source_name, source in (('novelops.config.json llm section', llm_section), ('llm overrides', overrides or {})):
        for key, value in source.items():
            if key not in DEFAULT_LLM_CONFIG:
                raise SystemExit(
                    '%s has unknown key %r (known: %s)'
                    % (source_name, key, ', '.join(sorted(DEFAULT_LLM_CONFIG))))
            # None 一律视为「未设置」并跳过：配置文件里写 `"temperature": null`
            # 会把默认值覆盖成 None，请求体里就会出现 "temperature": null。
            if value is None:
                continue
            resolved[key] = value
    return resolved


def resolve_api_key(llm_config):
    """返回 (key_or_None, source)，source 为 'env' | 'config' | None；环境变量优先。"""
    env_name = llm_config.get('api_key_env')
    if env_name and os.environ.get(env_name):
        return os.environ[env_name], 'env'
    if llm_config.get('api_key'):
        return llm_config['api_key'], 'config'
    return None, None


def build_chat_payload(messages, llm_config):
    """组装 chat completions 请求体；dry-run 输出与真实请求共用此函数。"""
    return {
        'model': llm_config['model'],
        'messages': messages,
        'temperature': llm_config['temperature'],
        'top_p': llm_config['top_p'],
        'max_tokens': llm_config['max_tokens'],
        'stream': False,
    }


def strip_think_blocks(text):
    """剥离 Hermes 混合推理的 <think>...</think> 块。

    三种形态：闭合块直接剥除；只残留 </think>（模型偶发省略起始标签）时取最后一个
    闭合标签之后的内容；剥离后仍有未闭合 <think> 说明响应大概率被截断，直接报错。
    """
    text = text or ''
    stripped = THINK_BLOCK_RE.sub('', text)
    if '<think>' not in stripped.lower() and '</think>' in stripped.lower():
        lower = stripped.lower()
        stripped = stripped[lower.rindex('</think>') + len('</think>'):]
    if '<think>' in stripped.lower():
        raise SystemExit(
            'LLM response contains an unclosed <think> block; the response was likely truncated. '
            '请调大 novelops.config.json 的 llm.max_tokens 后重试。')
    return stripped.strip()


def resolve_mock_source(cli_mock_path):
    """--mock-response 优先，其次环境变量 NOVELOPS_LLM_MOCK；都没有返回 None。"""
    if cli_mock_path:
        return cli_mock_path
    return os.environ.get(MOCK_ENV_VAR) or None


def load_mock_responses(path):
    """读取 mock 文件为 assistant 响应列表。

    JSON 数组 → 逐项（字符串或 OpenAI 响应对象均可）；
    含 choices 的 JSON 对象 → 取 choices[0].message.content；
    其他 → 整个文件文本作为单条响应。
    """
    path = Path(path)
    if not path.is_file():
        raise SystemExit('Mock response file does not exist: %s' % path)
    raw = read_text(path)

    def unwrap(item):
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            try:
                return item['choices'][0]['message']['content']
            except (KeyError, IndexError, TypeError):
                raise SystemExit(
                    'Mock response object in %s is not an OpenAI chat completion '
                    '(missing choices[0].message.content)' % path)
        raise SystemExit('Mock response items in %s must be strings or OpenAI response objects' % path)

    try:
        data = json.loads(raw)
    except ValueError:
        return [raw]
    if isinstance(data, list):
        return [unwrap(item) for item in data]
    if isinstance(data, dict) and 'choices' in data:
        return [unwrap(data)]
    return [raw]


def _http_chat(payload, llm_config):
    url = llm_config['base_url'].rstrip('/') + '/chat/completions'
    headers = {'Content-Type': 'application/json'}
    api_key, _source = resolve_api_key(llm_config)
    if api_key:
        headers['Authorization'] = 'Bearer %s' % api_key
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=llm_config['timeout_seconds']) as response:
            body = response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        body = ''
        try:
            body = exc.read().decode('utf-8', errors='replace')
        except Exception:
            pass
        message = 'LLM HTTP %s from %s: %s' % (exc.code, url, body[:500])
        if exc.code in (401, 403):
            message += ' 请检查 api_key 或环境变量 %s。' % llm_config.get('api_key_env')
        raise SystemExit(message)
    except (socket.timeout, TimeoutError):
        raise SystemExit(
            'LLM request timed out after %ss: %s. 可调大 novelops.config.json 的 llm.timeout_seconds。'
            % (llm_config['timeout_seconds'], url))
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, 'reason', None), (socket.timeout, TimeoutError)):
            raise SystemExit(
                'LLM request timed out after %ss: %s. 可调大 novelops.config.json 的 llm.timeout_seconds。'
                % (llm_config['timeout_seconds'], url))
        raise SystemExit(
            'LLM request failed: cannot connect to %s. 请确认 Ollama 已启动（ollama serve），'
            '或检查 novelops.config.json 的 llm.base_url。原始错误：%s' % (url, exc.reason))
    try:
        data = json.loads(body)
    except ValueError:
        raise SystemExit('LLM response is not valid JSON from %s: %s' % (url, body[:200]))
    try:
        content = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise SystemExit('LLM response missing choices[0].message.content from %s' % url)
    return content, data.get('model'), data.get('usage')


def chat(messages, llm_config, mock_content=None):
    """执行一次 chat completion（或 mock 短路），返回统一结果结构。

    返回：{'content'(按 strip_think 配置剥离), 'raw_content', 'model', 'usage', 'transport'}。
    dry-run 不属于本函数——调用方在调用前用 build_chat_payload 组包即可。
    """
    if mock_content is not None:
        raw_content = mock_content
        model = llm_config['model']
        usage = None
        transport = 'mock'
    else:
        payload = build_chat_payload(messages, llm_config)
        raw_content, model, usage = _http_chat(payload, llm_config)
        transport = 'http'
    content = strip_think_blocks(raw_content) if llm_config.get('strip_think', True) else (raw_content or '').strip()
    return {
        'content': content,
        'raw_content': raw_content,
        'model': model or llm_config['model'],
        'usage': usage,
        'transport': transport,
    }
