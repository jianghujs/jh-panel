# coding:utf-8
"""
Utility helpers for keepalived configuration parsing/writing.
"""

import re

VRRP_INSTANCE_NAME = 'VI_MYSQL'
VRRP_PANEL_UNICAST_TAG = '# panel_unicast_disabled'


class KeepalivedConfigError(Exception):
    """Raised when keepalived configuration mutations fail."""


def normalize_arg(value):
    if value is None:
        return ''
    return value.replace('\\n', '\n').replace('\\r', '\r')


def _leading_spaces(line):
    match = re.match(r'^(\s*)', line)
    if not match:
        return ''
    return match.group(1)


def _find_vrrp_block(content, instance_name=None):
    instance = instance_name.strip() if instance_name else VRRP_INSTANCE_NAME
    lines = content.splitlines()
    block_lines = []
    start = -1
    depth = 0
    seen_brace = False
    target = re.compile(r'^\s*vrrp_instance\s+' + re.escape(instance) + r'\b')

    for idx, line in enumerate(lines):
        if start == -1 and target.search(line):
            start = idx

        if start != -1:
            block_lines.append(line)
            brace_delta = line.count('{') - line.count('}')
            if brace_delta > 0:
                seen_brace = True
            depth += brace_delta
            if seen_brace and depth == 0:
                end = idx
                return {'start': start, 'end': end, 'lines': block_lines}
    return None


def has_vrrp_instance(conf_content, instance_name=None):
    instance = instance_name.strip() if instance_name else VRRP_INSTANCE_NAME
    return _find_vrrp_block(conf_content, instance) is not None


def _extract_block(lines, start_idx):
    block = []
    depth = 0
    seen_brace = False
    idx = start_idx
    total = len(lines)
    while idx < total:
        line = lines[idx]
        block.append(line)
        brace_delta = line.count('{') - line.count('}')
        if brace_delta > 0:
            seen_brace = True
        depth += brace_delta
        if seen_brace and depth == 0:
            break
        idx += 1
    return block, idx


def _parse_vrrp_block(block_text):
    data = {
        'interface': '',
        'virtual_ipaddress': '',
        'unicast_src_ip': '',
        'unicast_peer_list': [],
        'priority': '',
        'auth_pass': '',
        'panel_unicast_disabled': VRRP_PANEL_UNICAST_TAG in block_text
    }

    match_interface = re.search(r'^\s*interface\s+([^\s]+)', block_text, re.M)
    if match_interface:
        data['interface'] = match_interface.group(1).strip()

    match_priority = re.search(r'^\s*priority\s+([^\s]+)', block_text, re.M)
    if match_priority:
        data['priority'] = match_priority.group(1).strip()

    match_auth = re.search(r'^\s*auth_pass\s+([^\s]+)', block_text, re.M)
    if match_auth:
        data['auth_pass'] = match_auth.group(1).strip()

    match_vip = re.search(r'virtual_ipaddress\s*{([^}]*)}', block_text, re.S)
    if match_vip:
        lines = match_vip.group(1).splitlines()
        ips = [ip.strip() for ip in lines if ip.strip() != '']
        if ips:
            data['virtual_ipaddress'] = ips[0]

    match_unicast_src = re.search(r'^\s*unicast_src_ip\s+([^\s]+)', block_text, re.M)
    if match_unicast_src:
        data['unicast_src_ip'] = match_unicast_src.group(1).strip()

    match_unicast_peer = re.search(r'unicast_peer\s*{([^}]*)}', block_text, re.S)
    if match_unicast_peer:
        peers = match_unicast_peer.group(1).splitlines()
        peers = [p.strip() for p in peers if p.strip() != '']
        data['unicast_peer_list'] = peers

    data['unicast_enabled'] = (len(data['unicast_peer_list']) > 0 or data['unicast_src_ip'] != '')
    if data['panel_unicast_disabled']:
        data['unicast_enabled'] = False
    return data


def _get_vrrp_defaults(tpl_content, instance_name=None):
    default = {
        'interface': '',
        'virtual_ipaddress': '',
        'unicast_src_ip': '',
        'unicast_peer_list': [],
        'priority': '',
        'auth_pass': '',
        'unicast_enabled': True,
        'panel_unicast_disabled': False
    }

    if not tpl_content:
        return default

    block = _find_vrrp_block(tpl_content, instance_name)
    if not block:
        return default

    block_text = "\n".join(block['lines'])
    parsed = _parse_vrrp_block(block_text)
    parsed['unicast_enabled'] = True
    return parsed


def _build_peer_block(indent, peers):
    block = [indent + 'unicast_peer {']
    inner_indent = indent + '    '
    for peer in peers:
        block.append(inner_indent + peer)
    block.append(indent + '}')
    return block


def _rewrite_vrrp_block(block_lines, values):
    lines = list(block_lines)
    result = []
    i = 0
    interface_index = None
    interface_indent = '    '
    unicast_src_present = False
    unicast_src_index = None
    unicast_peer_present = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith(VRRP_PANEL_UNICAST_TAG):
            i += 1
            continue

        if stripped.startswith('interface '):
            indent = _leading_spaces(line)
            interface_indent = indent if indent != '' else '    '
            interface_index = len(result)
            result.append(indent + 'interface ' + values['interface'])
            i += 1
            continue

        if stripped.startswith('priority '):
            indent = _leading_spaces(line)
            result.append(indent + 'priority ' + str(values['priority']))
            i += 1
            continue

        if stripped.startswith('unicast_src_ip'):
            if values['unicast_enabled']:
                indent = _leading_spaces(line)
                unicast_line = indent + 'unicast_src_ip ' + values['unicast_src_ip']
                result.append(unicast_line)
                unicast_src_present = True
                unicast_src_index = len(result) - 1
            i += 1
            continue

        if stripped.startswith('unicast_peer'):
            block, block_end = _extract_block(lines, i)
            if values['unicast_enabled']:
                indent = _leading_spaces(block[0])
                peers_block = _build_peer_block(indent, values['unicast_peer_list'])
                result.extend(peers_block)
                unicast_peer_present = True
            i = block_end + 1
            continue

        if stripped.startswith('virtual_ipaddress'):
            block, block_end = _extract_block(lines, i)
            indent = _leading_spaces(block[0])
            vip_block = [indent + 'virtual_ipaddress {']
            inner_indent = indent + '    '
            vip_value = values['virtual_ipaddress']
            if vip_value != '':
                vip_block.append(inner_indent + vip_value)
            vip_block.append(indent + '}')
            result.extend(vip_block)
            i = block_end + 1
            continue

        if stripped.startswith('authentication'):
            block, block_end = _extract_block(lines, i)
            replaced = False
            for idx in range(len(block)):
                if re.match(r'^\s*auth_pass\b', block[idx].strip()):
                    indent = _leading_spaces(block[idx])
                    block[idx] = indent + 'auth_pass ' + values['auth_pass']
                    replaced = True
                    break
            if not replaced:
                indent = _leading_spaces(block[0]) + '    '
                block.insert(len(block) - 1, indent + 'auth_pass ' + values['auth_pass'])
            result.extend(block)
            i = block_end + 1
            continue

        result.append(line)
        i += 1

    if values['unicast_enabled']:
        if not unicast_src_present:
            indent = interface_indent
            insert_line = indent + 'unicast_src_ip ' + values['unicast_src_ip']
            insert_pos = interface_index + 1 if interface_index is not None else len(result)
            result.insert(insert_pos, insert_line)
            unicast_src_index = insert_pos

        if not unicast_peer_present:
            indent = interface_indent
            peers_block = _build_peer_block(indent, values['unicast_peer_list'])
            if unicast_src_index is not None:
                insert_pos = unicast_src_index + 1
            elif interface_index is not None:
                insert_pos = interface_index + 1
            else:
                insert_pos = len(result)
            for offset, peer_line in enumerate(peers_block):
                result.insert(insert_pos + offset, peer_line)
    else:
        existing_tag = any(VRRP_PANEL_UNICAST_TAG in line for line in result)
        if not existing_tag:
            indent = interface_indent
            insert_pos = interface_index + 1 if interface_index is not None else len(result)
            result.insert(insert_pos, indent + VRRP_PANEL_UNICAST_TAG)

    return result


def _merge_vrrp_values(current, defaults):
    merged = defaults.copy()
    merged['interface'] = current['interface'] or defaults.get('interface', '')
    merged['virtual_ipaddress'] = current['virtual_ipaddress'] or defaults.get('virtual_ipaddress', '')
    merged['unicast_src_ip'] = current['unicast_src_ip'] or ''
    merged['unicast_peer_list'] = current['unicast_peer_list'] if len(current['unicast_peer_list']) > 0 else []
    merged['priority'] = current['priority'] or defaults.get('priority', '')
    merged['auth_pass'] = current['auth_pass'] or defaults.get('auth_pass', '')
    merged['unicast_enabled'] = current['unicast_enabled']
    return merged


def get_vrrp_form_data(conf_content, tpl_content, instance_name=None):
    instance = instance_name.strip() if instance_name else VRRP_INSTANCE_NAME
    block = _find_vrrp_block(conf_content, instance)
    if not block:
        raise KeepalivedConfigError('未找到 vrrp_instance ' + instance + ' 配置块!')

    block_text = "\n".join(block['lines'])
    current = _parse_vrrp_block(block_text)
    defaults = _get_vrrp_defaults(tpl_content, instance)
    merged = _merge_vrrp_values(current, defaults)

    return {
        'interface': merged['interface'],
        'virtual_ipaddress': merged['virtual_ipaddress'],
        'unicast_enabled': True if merged['unicast_enabled'] else False,
        'unicast_src_ip': merged['unicast_src_ip'],
        'unicast_peer_list': "\n".join(merged['unicast_peer_list']),
        'priority': merged['priority'],
        'auth_pass': merged['auth_pass']
    }


def build_vrrp_content(conf_content, values, instance_name=None):
    instance = instance_name.strip() if instance_name else VRRP_INSTANCE_NAME
    block = _find_vrrp_block(conf_content, instance)
    if not block:
        raise KeepalivedConfigError('未找到 vrrp_instance ' + instance + ' 配置块!')

    new_block_lines = _rewrite_vrrp_block(block['lines'], values)
    lines = conf_content.splitlines()
    new_lines = lines[:block['start']] + new_block_lines + lines[block['end'] + 1:]
    new_content = "\n".join(new_lines)
    if conf_content.endswith("\n"):
        new_content += "\n"
    return new_content
