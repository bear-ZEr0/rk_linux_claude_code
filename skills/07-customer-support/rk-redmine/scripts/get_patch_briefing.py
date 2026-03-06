#!/usr/bin/env python3
"""
补丁简报获取脚本 - 自动识别类型并提取关键信息
支持两种补丁简报类型：
  类型一：单补丁简报（含Change-Id，关联Gerrit）
  类型二：补丁包简报（多版本附件，固件位置）

用法: python3 get_patch_briefing.py <issue_id> [--dir <directory>] [--download] [--no-gerrit]
"""

import sys
import urllib.request
import json
import ssl
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import os

# 加载配置
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "redmine_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    print(f"❌ 配置文件未找到: {config_path}")
    sys.exit(1)

config = load_config()
API_URL = config.get("base_url", "https://10.10.10.70")
API_KEY = config.get("api_key", "")
PUBLIC_URL = "https://redmine.rock-chips.com"

# Gerrit脚本路径
GERRIT_SCRIPT_DIR = Path(__file__).parent.parent.parent.parent / "code-repository" / "rk29-gerrit" / "scripts"

# 创建SSL上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_issue_via_api(issue_id):
    """通过Redmine API获取Issue详情"""
    url = f"{API_URL}/issues/{issue_id}.json"
    params = {
        'key': API_KEY,
        'include': 'journals,attachments,custom_fields'
    }
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{query_string}"

    try:
        req = urllib.request.Request(full_url)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "Redmine-API-Client/1.0")

        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('issue', {})
    except Exception as e:
        print(f"❌ API请求失败: {e}")
        return {}


def get_custom_field(issue_data, field_id):
    """获取自定义字段值"""
    custom_fields = issue_data.get('custom_fields', [])
    for field in custom_fields:
        if field.get('id') == field_id:
            return field.get('value', '')
    return ''


def parse_attachment_version(filename):
    """
    从附件文件名解析版本信息
    例如: AIC-Android14-Patches-20241205.7z -> {'name': 'AIC', 'system': 'Android14', 'date': '20241205'}
    """
    # 匹配日期模式 YYYYMMDD
    date_match = re.search(r'(\d{8})', filename)
    date_str = date_match.group(1) if date_match else None
    
    # 匹配系统版本 Android9/10/11/12/13/14
    system_match = re.search(r'(Android\d+)', filename, re.IGNORECASE)
    system = system_match.group(1) if system_match else None
    
    # 提取名称前缀
    name = filename.split('-')[0] if '-' in filename else filename.split('.')[0]
    
    return {
        'filename': filename,
        'name': name,
        'system': system,
        'date': date_str,
        'is_patch': any(kw in filename.lower() for kw in ['patch', '补丁']),
        'is_doc': filename.lower().endswith('.pdf')
    }


def extract_firmware_paths(journals):
    """从历史记录中提取固件路径"""
    firmware_paths = []
    path_pattern = re.compile(r'\\\\10\.10\.10\.\d+\\[^\s\r\n]+')
    
    for journal in journals:
        notes = journal.get('notes', '')
        if notes:
            matches = path_pattern.findall(notes)
            for match in matches:
                # 清理路径末尾的标点
                clean_path = match.rstrip('.,;:')
                if clean_path not in firmware_paths:
                    firmware_paths.append(clean_path)
    
    return firmware_paths


def query_gerrit(change_id):
    """调用Gerrit脚本查询Change详情"""
    if not change_id or change_id.startswith('涉及'):
        return None
    
    # 清理Change-Id
    change_id = change_id.strip()
    if not change_id.startswith('I'):
        return None
    
    gerrit_script = GERRIT_SCRIPT_DIR / "search_changes.py"
    if not gerrit_script.exists():
        print(f"⚠️  Gerrit脚本不存在: {gerrit_script}")
        return None
    
    try:
        result = subprocess.run(
            ['python3', str(gerrit_script), '--id', change_id, '--json'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(GERRIT_SCRIPT_DIR)
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"⚠️  Gerrit查询失败: {e}")
    
    return None


def analyze_briefing_type(issue_data):
    """分析补丁简报类型"""
    change_id = get_custom_field(issue_data, 88)  # 补丁 Change-Id
    attachments = issue_data.get('attachments', [])
    
    # 检查是否有有效的Change-Id
    has_valid_change_id = change_id and change_id.startswith('I') and len(change_id) > 10
    
    # 检查附件数量和类型
    patch_attachments = [a for a in attachments if any(kw in a.get('filename', '').lower() for kw in ['patch', '补丁', '.7z', '.zip', '.tar'])]
    
    if has_valid_change_id and len(patch_attachments) <= 1:
        return 'single_patch'  # 类型一：单补丁简报
    else:
        return 'patch_package'  # 类型二：补丁包简报


def generate_report(issue_data, output_dir, gerrit_info=None, skip_gerrit=False):
    """生成补丁简报报告"""
    issue_id = issue_data.get('id', 'Unknown')
    subject = issue_data.get('subject', '')
    status = issue_data.get('status', {}).get('name', '')
    author = issue_data.get('author', {}).get('name', '未知')
    
    # 提取自定义字段
    component = get_custom_field(issue_data, 2)
    patch_type = get_custom_field(issue_data, 106)
    branch = get_custom_field(issue_data, 86)
    change_id = get_custom_field(issue_data, 88)
    problem_desc = get_custom_field(issue_data, 90)
    solution = get_custom_field(issue_data, 92)
    test_status = get_custom_field(issue_data, 93)
    
    # 分析简报类型
    briefing_type = analyze_briefing_type(issue_data)
    
    # 分析附件
    attachments = issue_data.get('attachments', [])
    parsed_attachments = [parse_attachment_version(a.get('filename', '')) for a in attachments]
    
    # 按日期排序补丁附件
    patch_attachments = sorted(
        [a for a in parsed_attachments if a['is_patch'] and a['date']],
        key=lambda x: x['date'] or '0',
        reverse=True
    )
    
    # 提取文档
    docs = [a for a in parsed_attachments if a['is_doc']]
    
    # 提取固件路径
    journals = issue_data.get('journals', [])
    firmware_paths = extract_firmware_paths(journals)
    
    # 生成报告内容
    report = f"""# 补丁简报 #{issue_id}

## {subject}

| 字段 | 值 |
|------|------|
| **状态** | {status} |
| **作者** | {author} |
| **模块** | {component} |
| **类型** | {patch_type} |
| **链接** | {PUBLIC_URL}/issues/{issue_id} |

"""
    
    # 类型一：单补丁简报
    if briefing_type == 'single_patch':
        report += f"""## 补丁信息

| 字段 | 值 |
|------|------|
| **仓库:分支** | {branch} |
| **Change-Id** | `{change_id}` |
| **测试情况** | {test_status} |

"""
        # Gerrit关联
        if gerrit_info and not skip_gerrit:
            report += f"""### Gerrit 关联

| 字段 | 值 |
|------|------|
| **Change 编号** | #{gerrit_info.get('number', 'N/A')} |
| **项目** | {gerrit_info.get('project', 'N/A')} |
| **分支** | {gerrit_info.get('branch', 'N/A')} |
| **状态** | {gerrit_info.get('status', 'N/A')} |
| **提交者** | {gerrit_info.get('owner', {}).get('name', 'N/A')} |
| **链接** | {gerrit_info.get('url', 'N/A')} |

**Commit Message:**
```
{gerrit_info.get('commitMessage', 'N/A')}
```

"""
    
    # 类型二：补丁包简报
    else:
        if patch_attachments:
            report += """## 补丁版本历史

| 文件名 | 适用系统 | 日期 |
|--------|----------|------|
"""
            for pa in patch_attachments[:10]:  # 最多显示10个
                report += f"| {pa['filename']} | {pa['system'] or '-'} | {pa['date'] or '-'} |\n"
            
            report += f"""
> **最新版本**: {patch_attachments[0]['filename']}

"""
    
    # 文档列表
    if docs:
        report += "## 相关文档\n\n"
        for doc in docs:
            report += f"- {doc['filename']}\n"
        report += "\n"
    
    # 固件位置
    if firmware_paths:
        report += "## 预置固件位置\n\n"
        for path in firmware_paths[-10:]:  # 最多显示最新10个
            report += f"- `{path}`\n"
        report += "\n"
    
    # 问题描述和解决方法
    if problem_desc:
        report += f"""## 问题描述

{problem_desc}

"""
    
    if solution:
        report += f"""## 解决方法

{solution}

"""
    
    # 附件完整列表
    if attachments:
        report += "## 附件列表\n\n"
        for a in attachments:
            filename = a.get('filename', '')
            filesize = a.get('filesize', 0)
            size_str = f"{filesize / 1024:.1f} KB" if filesize < 1024*1024 else f"{filesize / (1024*1024):.1f} MB"
            report += f"- **{filename}** ({size_str})\n"
    
    # 保存报告
    os.makedirs(output_dir, exist_ok=True)
    report_file = os.path.join(output_dir, "patch_briefing_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report_file


def main():
    if len(sys.argv) < 2:
        print("用法: python3 get_patch_briefing.py <issue_id> [--dir <directory>] [--download] [--no-gerrit]")
        print("\n示例:")
        print("  python3 get_patch_briefing.py 597064")
        print("  python3 get_patch_briefing.py 397153 --dir /tmp")
        print("  python3 get_patch_briefing.py 597064 --no-gerrit")
        sys.exit(1)
    
    issue_id = sys.argv[1]
    
    # 解析参数
    output_dir = os.path.join(os.getcwd(), f"patch_briefing_{issue_id}")
    skip_gerrit = "--no-gerrit" in sys.argv
    download = "--download" in sys.argv
    
    if "--dir" in sys.argv:
        try:
            dir_index = sys.argv.index("--dir")
            if dir_index + 1 < len(sys.argv):
                output_dir = os.path.join(os.path.abspath(sys.argv[dir_index + 1]), f"patch_briefing_{issue_id}")
        except (ValueError, IndexError):
            pass

    print(f"正在获取补丁简报 #{issue_id}...")
    
    # 获取Issue数据
    issue_data = fetch_issue_via_api(issue_id)
    if not issue_data:
        print(f"❌ 无法获取Issue #{issue_id}")
        sys.exit(1)
    
    subject = issue_data.get('subject', '')
    print(f"📋 {subject}")
    
    # 分析类型
    briefing_type = analyze_briefing_type(issue_data)
    
    if briefing_type == 'single_patch':
        print("📌 类型: 单补丁简报")
        change_id = get_custom_field(issue_data, 88)
        
        # 查询Gerrit
        gerrit_info = None
        if not skip_gerrit and change_id:
            print(f"🔍 查询Gerrit: {change_id[:20]}...")
            gerrit_info = query_gerrit(change_id)
            if gerrit_info:
                print(f"✅ 找到Gerrit Change #{gerrit_info.get('number')}")
            else:
                print("⚠️  未找到对应的Gerrit Change")
    else:
        print("📌 类型: 补丁包简报")
        gerrit_info = None
        
        # 显示附件统计
        attachments = issue_data.get('attachments', [])
        parsed = [parse_attachment_version(a.get('filename', '')) for a in attachments]
        patches = [p for p in parsed if p['is_patch']]
        docs = [p for p in parsed if p['is_doc']]
        
        print(f"📦 补丁文件: {len(patches)} 个")
        print(f"📄 文档文件: {len(docs)} 个")
        
        # 显示固件路径数量
        firmware_paths = extract_firmware_paths(issue_data.get('journals', []))
        if firmware_paths:
            print(f"💾 固件路径: {len(firmware_paths)} 个")
    
    # 生成报告
    report_file = generate_report(issue_data, output_dir, gerrit_info, skip_gerrit)
    print(f"\n📄 报告已生成: {report_file}")


if __name__ == "__main__":
    main()
