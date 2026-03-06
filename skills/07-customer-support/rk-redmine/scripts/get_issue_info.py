#!/usr/bin/env python3
"""
Redmine Issue信息获取脚本 - API版本
使用Redmine REST API获取完整Issue详情，比网页爬取更稳定可靠
用法: python3 get_issue_info_api.py <issue_id>
"""

import sys
import urllib.request
import json
import ssl
import os
import urllib.parse
import re
from datetime import datetime
from urllib.parse import urljoin

# 加载配置
def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, '..', 'configs', 'redmine_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    print(f"❌ 配置文件未找到: {config_path}")
    sys.exit(1)

config = load_config()
API_URL = config.get("base_url", "https://10.10.10.70")
API_KEY = config.get("api_key", "")
PUBLIC_URL = "https://redmine.rock-chips.com"

# 创建SSL上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 用户缓存，避免重复查询
user_cache = {}

# 加载字段映射配置
def load_field_mappings():
    """加载字段ID到名称的映射配置"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, '..', 'configs', 'field_mappings.json')

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # 如果配置文件不存在，返回默认映射
        return {
            "chip_ids": {},
            "custom_field_names": {},
            "patch_acceptance_status": {}
        }

# 全局映射配置
FIELD_MAPPINGS = load_field_mappings()

def find_image_references(text_content):
    """
    在文本中查找图片引用

    Args:
        text_content: 要搜索的文本内容

    Returns:
        list: 找到的图片文件名列表
    """
    # Redmine图片引用格式: !filename.ext!
    pattern = r'!([^!]+\.(png|jpg|jpeg|gif|bmp|webp))!'
    matches = re.findall(pattern, text_content, re.IGNORECASE)
    return [match[0] for match in matches]


def create_download_directory(issue_id, custom_dir=None):
    """创建下载文件夹"""
    if custom_dir:
        # 用户指定了目录，在此目录下创建issue子目录
        download_dir = os.path.join(custom_dir, f"redmine_issue_{issue_id}")
    else:
        # 默认使用当前工作目录
        current_dir = os.getcwd()
        download_dir = os.path.join(current_dir, f"redmine_issues_{issue_id}")

    # 创建目录（如果不存在）
    os.makedirs(download_dir, exist_ok=True)

    return download_dir

def download_attachment(attachment, download_dir, issue_id):
    """下载附件文件（静默模式）"""
    try:
        filename = attachment.get('filename', '')
        content_url = attachment.get('content_url', '')

        if not filename or not content_url:
            return False

        # 构建完整的下载URL
        # Redmine附件下载通常需要通过公共URL而不是API URL
        if content_url.startswith('/'):
            # 使用公共URL下载附件
            full_url = f"{PUBLIC_URL}{content_url}"
        elif content_url.startswith('http'):
            # 如果已经是完整URL，直接使用
            full_url = content_url
        else:
            # 默认使用公共URL
            full_url = f"{PUBLIC_URL}/{content_url}"

        # 本地文件路径
        local_filepath = os.path.join(download_dir, filename)

        # 避免重复下载
        if os.path.exists(local_filepath):
            file_size = os.path.getsize(local_filepath)
            remote_size = attachment.get('filesize', 0)
            if file_size == remote_size:
                return True

        # 创建下载请求
        # 对于公共URL，可能不需要API密钥，但为了兼容性还是加上
        req = urllib.request.Request(full_url)
        if not full_url.startswith(PUBLIC_URL):
            req.add_header("X-Redmine-API-Key", API_KEY)
        req.add_header("User-Agent", "Redmine-API-Client/1.0")
        # 添加必要的Referer头以避免某些服务器的防盗链检查
        req.add_header("Referer", PUBLIC_URL)

        # 下载文件
        with urllib.request.urlopen(req, context=ctx, timeout=60) as response:
            content_type = response.headers.get('Content-Type', '')

            # 写入文件
            with open(local_filepath, 'wb') as f:
                f.write(response.read())

            # 验证下载大小
            downloaded_size = os.path.getsize(local_filepath)
            expected_size = attachment.get('filesize', 0)

            if expected_size > 0 and downloaded_size != expected_size:
                os.remove(local_filepath)
                return False

            return True

    except Exception as e:
        return False

def generate_issue_report(issue_data, download_dir, download_results):
    """生成问题的markdown报告"""
    issue_id = issue_data.get('id', 'Unknown')
    subject = issue_data.get('subject', '')
    tracker = issue_data.get('tracker', {}).get('name', 'Defect')
    status = issue_data.get('status', {}).get('name', '')
    priority = issue_data.get('priority', {}).get('name', '')
    author = issue_data.get('author', {}).get('name', '未知')
    created_on = issue_data.get('created_on', '')
    updated_on = issue_data.get('updated_on', '')
    description = issue_data.get('description', '')
    attachments = issue_data.get('attachments', [])
    journals = issue_data.get('journals', [])

    # 预填充用户缓存：从issue数据中提取所有用户信息
    def cache_user_from_dict(user_dict):
        """从用户字典中缓存用户名"""
        if user_dict and isinstance(user_dict, dict):
            user_id = str(user_dict.get('id', ''))
            user_name = user_dict.get('name', '')
            if user_id and user_name:
                user_cache[user_id] = user_name

    # 缓存author、assigned_to等用户
    cache_user_from_dict(issue_data.get('author'))
    cache_user_from_dict(issue_data.get('assigned_to'))

    # 缓存附件上传者
    for attachment in attachments:
        cache_user_from_dict(attachment.get('author'))

    # 缓存历史记录中的用户
    for journal in journals:
        cache_user_from_dict(journal.get('user'))

    # 格式化时间
    def format_time(time_str):
        if time_str:
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return time_str[:19].replace('T', ' ')
        return '未知时间'

    # 生成markdown内容
    report_content = f"""# {tracker} #{issue_id} - {subject}

## 基本信息

- **状态**: {status}
- **优先级**: {priority}
- **作者**: {author}
- **链接**: https://redmine.rock-chips.com/issues/{issue_id}

"""

    # 添加自定义字段
    custom_fields = issue_data.get('custom_fields', [])
    if custom_fields:
        report_content += "## 自定义字段\n\n"
        for field in custom_fields:
            field_id = field.get('id', '')
            name = field.get('name', '')
            value = field.get('value', '')

            if not value:
                continue

            # 特殊处理：可能受影响的芯片 (ID 77)
            if field_id == 77 and isinstance(value, list):
                chip_names = []
                for chip_id in value:
                    chip_name = FIELD_MAPPINGS.get('chip_ids', {}).get(str(chip_id), f'芯片ID_{chip_id}')
                    chip_names.append(chip_name)
                value_str = ', '.join(chip_names) if chip_names else '未指定'
                report_content += f"- **{name}**: {value_str}\n"

            # 特殊处理：补丁作者 (ID 89)
            elif field_id == 89 and isinstance(value, list):
                author_names = []
                for user_id in value:
                    user_name = get_user_name(user_id)
                    if user_name:
                        author_names.append(user_name)
                value_str = ', '.join(author_names) if author_names else '未指定'
                report_content += f"- **{name}**: {value_str}\n"

            # 特殊处理：接收情况 (ID 95)
            elif field_id == 95 and isinstance(value, list):
                if value:
                    status_names = []
                    for status_id in value:
                        status_name = FIELD_MAPPINGS.get('patch_acceptance_status', {}).get(str(status_id), f'状态{status_id}')
                        status_names.append(status_name)
                    value_str = ', '.join(status_names)
                    report_content += f"- **{name}**: {value_str}\n"
                # 如果为空，不显示此字段

            # 普通字段
            else:
                # 列表类型转换为字符串
                if isinstance(value, list):
                    value_str = ', '.join(map(str, value))
                else:
                    value_str = str(value)

                report_content += f"- **{name}**: {value_str}\n"
        report_content += "\n"

    # 添加描述
    if description:
        report_content += f"""## 问题描述

{description}

"""

    # 添加附件信息
    if attachments:
        report_content += "## 附件\n\n"
        for attachment in attachments:
            filename = attachment.get('filename', '')
            filesize = attachment.get('filesize', 0)
            author_name = attachment.get('author', {}).get('name', '未知')
            created_on = attachment.get('created_on', '')

            # 格式化文件大小
            if filesize > 1024 * 1024:
                size_str = f"{filesize / (1024*1024):.1f} MB"
            elif filesize > 1024:
                size_str = f"{filesize / 1024:.1f} KB"
            else:
                size_str = f"{filesize} B"

            report_content += f"- **{filename}** ({size_str}) - 上传者: {author_name}, 时间: {format_time(created_on)}\n"
        report_content += "\n"

    # 添加历史记录
    if journals:
        report_content += "## 历史记录\n\n"
        for i, journal in enumerate(journals, 1):
            user = journal.get('user', {}).get('name', '未知')
            notes = journal.get('notes', '').strip()
            created_on = journal.get('created_on', '')
            details = journal.get('details', [])

            report_content += f"### #{i} - {user} ({format_time(created_on)})\n\n"

            # 显示状态变更
            if details:
                for detail in details:
                    property_name = detail.get('name', '')
                    old_value = detail.get('old_value', '')
                    new_value = detail.get('new_value', '')

                    if property_name == 'status_id':
                        report_content += "- 状态变更\n"
                    elif property_name == 'assigned_to_id':
                        report_content += f"- 指派变更\n"

            # 显示备注
            if notes:
                report_content += f"- 备注: {notes}\n"

            report_content += "\n"

    # 添加下载结果
    if download_results:
        report_content += "## 下载结果\n\n"
        for result in download_results:
            filename = result['filename']
            status = "✅ 成功" if result['success'] else "❌ 失败"
            size = result['size']
            if size > 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size} B"
            report_content += f"- **{filename}** ({size_str}) - {status}\n"

    # 保存报告
    report_file = os.path.join(download_dir, "issue_report.md")
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return True
    except Exception as e:
        print(f"生成报告失败: {e}")
        return False

def download_all_attachments(issue_data, download_dir):
    """下载所有附件（静默模式）"""
    attachments = issue_data.get('attachments', [])

    if not attachments:
        print("此Issue没有附件")
        return []

    download_results = []

    for attachment in attachments:
        filename = attachment.get('filename', '')
        file_size = attachment.get('filesize', 0)

        if download_attachment(attachment, download_dir, issue_data.get('id', '')):
            download_results.append({
                'filename': filename,
                'size': file_size,
                'success': True
            })
        else:
            download_results.append({
                'filename': filename,
                'size': file_size,
                'success': False
            })

    return download_results

def get_user_name(user_id):
    """获取用户名称，使用缓存避免重复查询"""
    if not user_id:
        return None

    user_id_str = str(user_id)
    if user_id_str in user_cache:
        return user_cache[user_id_str]

    try:
        url = f"{API_URL}/users/{user_id}.json"
        req = urllib.request.Request(url)
        req.add_header("X-Redmine-API-Key", API_KEY)
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            user_data = data.get('user', {})

            # 尝试从name字段获取，如果没有则拼接firstname和lastname
            user_name = user_data.get('name')
            if not user_name:
                firstname = user_data.get('firstname', '')
                lastname = user_data.get('lastname', '')
                if firstname or lastname:
                    user_name = f"{lastname} {firstname}".strip()
                else:
                    user_name = f"用户{user_id}"

            user_cache[user_id_str] = user_name
            return user_name

    except Exception as e:
        # 如果查询失败，返回用户ID
        user_cache[user_id_str] = f"用户{user_id}"
        return f"用户{user_id}"

def fetch_issue_via_api(issue_id):
    """通过Redmine API获取Issue详情"""
    url = f"{API_URL}/issues/{issue_id}.json"

    # 包含所有需要的信息
    params = {
        'include': 'journals,attachments,custom_fields,relations,watchers,children'
    }

    # 构建查询字符串
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{query_string}"

    try:
        req = urllib.request.Request(full_url)
        req.add_header("X-Redmine-API-Key", API_KEY)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "Redmine-API-Client/1.0")

        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('issue', {})

    except Exception as e:
        print(f"❌ API请求失败: {e}")
        return {}

def format_relative_time(iso_time_str):
    """格式化相对时间显示"""
    try:
        from datetime import datetime, timezone
        if not iso_time_str:
            return "未知时间"

        # 解析ISO时间字符串
        dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)

        # 计算时间差
        delta = now - dt

        if delta.days > 0:
            return f"大约 {delta.days} 天前"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"大约 {hours} 小时前"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"大约 {minutes} 分钟前"
        else:
            return "刚刚"
    except Exception:
        return iso_time_str

def format_basic_info(issue_data):
    """格式化输出Issue基本信息（渐进式披露）"""

    # 基本信息
    issue_id = issue_data.get('id', 'Unknown')
    subject = issue_data.get('subject', '')
    tracker = issue_data.get('tracker', {}).get('name', 'Defect')

    print(f"{tracker} #{issue_id}")
    print(subject)
    print()

    # 状态信息
    status = issue_data.get('status', {}).get('name', '')
    priority = issue_data.get('priority', {}).get('name', '')
    assigned_to = issue_data.get('assigned_to', {}).get('name', '')

    print(f"状态: {status} | 优先级: {priority}")
    if assigned_to:
        print(f"指派给: {assigned_to}")
    print()

    # 自定义字段
    custom_fields = issue_data.get('custom_fields', [])
    if custom_fields:
        # 按重要性排序的自定义字段
        field_order = [
            'RK芯片经销商', '项目进度', '产品类型', 'Component_fae',
            'Name', 'Tel.', 'Probability of occurrence'
        ]

        print("业务信息:")
        for field in custom_fields:
            name = field.get('name', '')
            value = field.get('value', '')
            if value and name in field_order:
                print(f"  {name}: {value}")
        print()

    # 描述
    description = issue_data.get('description', '')
    if description:
        print("问题描述:")
        # 简化描述，只显示前几行
        lines = description.replace('\r\n', '\n').strip().split('\n')[:3]
        for line in lines:
            if line.strip():
                print(f"  {line}")

        if len(description.replace('\r\n', '\n').strip().split('\n')) > 3:
            print("  ... (完整描述见 issue_report.md)")
        print()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 get_issue_info.py <问题ID> [--no-download] [--dir <directory>]")
        print("示例: python3 get_issue_info.py 593691")
        print("      python3 get_issue_info.py 593691 --no-download")
        print("      python3 get_issue_info.py 593691 --dir /home/cw/work")
        print("      python3 get_issue_info.py 593691 --dir ./download")
        print("")
        print("参数说明:")
        print("  <问题ID>           Redmine Issue ID")
        print("  --no-download        仅显示信息，不下载附件")
        print("  --dir <directory>    指定下载目录 (默认: ./redmine_issues_<问题ID>/)")
        print("")
        print("说明:")
        print("  - 默认情况下会自动下载所有附件")
        print("  - 如果指定了 --dir，附件将下载到 <directory>/redmine_issue_<问题ID>/ 目录")
        print("  - 如果没有指定 --dir，附件将下载到 ./redmine_issues_<问题ID>/ 目录")
        print("  - 使用 --no-download 可以只查看信息而不下载附件")
        sys.exit(1)

    issue_id = sys.argv[1]
    # 默认下载附件，使用 --no-download 禁用下载
    download_attachments = "--no-download" not in sys.argv

    # 解析下载目录参数
    custom_dir = None
    if "--dir" in sys.argv:
        try:
            dir_index = sys.argv.index("--dir")
            if dir_index + 1 < len(sys.argv):
                custom_dir = sys.argv[dir_index + 1]
                # 转换为绝对路径
                custom_dir = os.path.abspath(custom_dir)
                # 检查目录是否存在或可以创建
                os.makedirs(custom_dir, exist_ok=True)
            else:
                print("❌ --dir 参数需要指定目录路径")
                sys.exit(1)
        except Exception as e:
            print(f"❌ 无效的目录参数: {e}")
            sys.exit(1)

    print(f"正在通过API获取Issue #{issue_id} 的详细信息...")

    # 通过API获取数据
    issue_data = fetch_issue_via_api(issue_id)

    if issue_data:
        # 输出基本信息（渐进式披露）
        format_basic_info(issue_data)

        # 总是生成目录和报告
        download_dir = create_download_directory(issue_id, custom_dir)

        if download_attachments:
            download_results = download_all_attachments(issue_data, download_dir)
        else:
            # 如果不下载附件，创建空的下载结果
            download_results = []

        # 生成完整的markdown报告
        report_generated = generate_issue_report(issue_data, download_dir, download_results)

        # 输出最终结果
        if report_generated:
            print(f"📄 完整信息已保存到: {download_dir}/issue_report.md")

            # 如果下载了附件，显示简要统计
            if download_attachments and download_results:
                success_count = sum(1 for r in download_results if r['success'])
                if success_count > 0:
                    print(f"📎 已下载 {success_count} 个附件到同一目录")
        else:
            print("❌ 生成报告失败")

    else:
        print(f"❌ 无法获取Issue #{issue_id} 的信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
