#!/usr/bin/env python3
"""
Redmine 问题同步与查询脚本

功能：
- 默认（无参数）：快速获取当前用户的待处理问题列表（SessionStart Hook 专用）
- time-entries：获取指定时间段的工时记录
- issues-worked：获取指定时间段处理的问题
"""
import argparse
import base64
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request


# 内网自签名证书
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def load_config():
    """加载配置，优先 settings.json，回退到 redmine_config.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    for settings_path in [
        os.path.join(script_dir, '..', '..', '..', '..', 'settings.json'),
        os.path.join(os.getcwd(), 'settings.json'),
    ]:
        abs_path = os.path.abspath(settings_path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                redmine = data.get('redmine', {})
                if redmine.get('url') and (redmine.get('api_key') or redmine.get('username')):
                    return {
                        'base_url': redmine['url'].rstrip('/'),
                        'api_key': redmine.get('api_key', ''),
                        'username': redmine.get('username', ''),
                        'password': redmine.get('password', ''),
                        'auto_sync': redmine.get('auto_sync', True),
                    }
            except Exception:
                pass

    config_path = os.path.join(script_dir, '..', 'configs', 'redmine_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    return None


def make_redmine_headers(config):
    """创建 Redmine 请求头，支持 API Key 或 Basic Auth"""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "rk-redmine/1.0",
    }
    api_key = config.get('api_key', '')
    if api_key:
        headers["X-Redmine-API-Key"] = api_key
    else:
        username = config.get('username', '')
        password = config.get('password', '')
        if username and password:
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"
    return headers


# ---------------------------------------------------------------------------
# 查询功能
# ---------------------------------------------------------------------------

def get_time_entries(config, from_date, to_date):
    """获取工时记录"""
    base_url = config['base_url']
    headers = make_redmine_headers(config)
    api_url = f"{base_url}/time_entries.json?user_id=me&from={from_date}&to={to_date}&limit=100"

    entries = []
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
            data = json.loads(response.read().decode("utf-8"))
            for entry in data.get("time_entries", []):
                entries.append({
                    "id": entry.get("id"),
                    "hours": entry.get("hours"),
                    "activity": entry.get("activity", {}).get("name"),
                    "comments": entry.get("comments"),
                    "spent_on": entry.get("spent_on"),
                    "issue_id": entry.get("issue", {}).get("id") if entry.get("issue") else None,
                    "project": entry.get("project", {}).get("name"),
                })
    except Exception as e:
        print(f"获取 Redmine 工时失败: {e}", file=sys.stderr)
    return entries


def get_issues_worked(config, from_date, to_date):
    """获取指定时间段处理的问题"""
    base_url = config['base_url']
    headers = make_redmine_headers(config)
    encoded_from = urllib.parse.quote(f">={from_date}")
    api_url = f"{base_url}/issues.json?assigned_to_id=me&updated_on={encoded_from}&limit=100"

    issues = []
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
            data = json.loads(response.read().decode("utf-8"))
            for issue in data.get("issues", []):
                issue_data = {
                    "id": issue.get("id"),
                    "subject": issue.get("subject"),
                    "status": issue.get("status", {}).get("name"),
                    "priority": issue.get("priority", {}).get("name"),
                    "project": issue.get("project", {}).get("name"),
                    "updated_on": issue.get("updated_on"),
                    "author": issue.get("author", {}).get("name"),
                }
                custom_fields = issue.get("custom_fields", [])
                for field in custom_fields:
                    field_name = field.get("name", "")
                    field_value = field.get("value", "")
                    if field_name == "产品类型":
                        issue_data["product_type"] = field_value
                    elif field_name == "RK芯片经销商":
                        issue_data["distributor"] = field_value
                    elif field_name == "Name":
                        issue_data["customer_contact"] = field_value
                issues.append(issue_data)
    except Exception as e:
        print(f"获取 Redmine 问题失败: {e}", file=sys.stderr)
    return issues


def group_time_by_project(time_entries):
    """按项目分组工时"""
    grouped = {}
    for entry in time_entries:
        project = entry.get("project", "未知项目")
        if project not in grouped:
            grouped[project] = {"total_hours": 0, "entries": []}
        grouped[project]["total_hours"] += entry.get("hours", 0)
        grouped[project]["entries"].append(entry)
    return grouped


# ---------------------------------------------------------------------------
# 子命令处理
# ---------------------------------------------------------------------------

def cmd_sync(config):
    """原有功能：待处理问题列表"""
    if not config.get('auto_sync', True):
        return

    base_url = config.get('base_url', '').rstrip('/')
    api_key = config.get('api_key', '')

    if not base_url or not api_key:
        print("[Redmine] 缺少 base_url 或 api_key，跳过同步。")
        return

    url = f"{base_url}/issues.json?assigned_to_id=me&status_id=open&limit=5&sort=updated_on:desc"
    req = urllib.request.Request(url, headers={'X-Redmine-API-Key': api_key})

    try:
        resp = urllib.request.urlopen(req, timeout=8, context=SSL_CONTEXT)
        data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[Redmine] 同步失败（网络不可达或认证错误）: {e}")
        return

    issues = data.get('issues', [])
    total = data.get('total_count', 0)

    if total == 0:
        print("[Redmine] 当前没有待处理问题。")
        return

    print(f"## Redmine 待处理问题（共 {total} 个）\n")
    for issue in issues:
        iid = issue.get('id', '')
        subject = issue.get('subject', '')
        priority = issue.get('priority', {}).get('name', '')
        updated = issue.get('updated_on', '')[:10]
        project = issue.get('project', {}).get('name', '')
        print(f"- #{iid}: {subject} [{priority}] ({project}) 更新于 {updated}")

    if total > 5:
        print(f"\n... 还有 {total - 5} 个问题，使用 `/redmine-tracker list` 查看全部")


def cmd_time_entries(config, from_date, to_date):
    """输出工时记录"""
    entries = get_time_entries(config, from_date, to_date)
    if not entries:
        print(f"[Redmine] {from_date} ~ {to_date} 无工时记录")
        return
    grouped = group_time_by_project(entries)
    total = sum(e.get("hours", 0) for e in entries)
    print(f"## Redmine 工时记录（{from_date} ~ {to_date}，共 {total:.1f}h）\n")
    for project, info in sorted(grouped.items()):
        print(f"**{project}** ({info['total_hours']:.1f}h)")
        for e in info["entries"]:
            comment = e.get("comments") or ""
            issue = f" #{e['issue_id']}" if e.get("issue_id") else ""
            print(f"  - {e['spent_on']}{issue} {e['hours']}h {comment}")


def cmd_issues_worked(config, from_date, to_date):
    """输出处理的问题"""
    issues = get_issues_worked(config, from_date, to_date)
    if not issues:
        print(f"[Redmine] {from_date} ~ {to_date} 无处理问题")
        return
    print(f"## Redmine 处理问题（{from_date} ~ {to_date}，共 {len(issues)} 个）\n")
    for issue in issues:
        iid = issue.get('id', '')
        subject = issue.get('subject', '')
        status = issue.get('status', '')
        project = issue.get('project', '')
        print(f"- #{iid}: {subject} [{status}] ({project})")


def main():
    parser = argparse.ArgumentParser(description="Redmine 问题同步与查询")
    subparsers = parser.add_subparsers(dest="command")

    # time-entries
    p_time = subparsers.add_parser("time-entries", help="获取工时记录")
    p_time.add_argument("--from", dest="from_date", required=True, help="开始日期 YYYY-MM-DD")
    p_time.add_argument("--to", dest="to_date", required=True, help="结束日期 YYYY-MM-DD")

    # issues-worked
    p_issues = subparsers.add_parser("issues-worked", help="获取处理的问题")
    p_issues.add_argument("--from", dest="from_date", required=True, help="开始日期 YYYY-MM-DD")
    p_issues.add_argument("--to", dest="to_date", required=True, help="结束日期 YYYY-MM-DD")

    args = parser.parse_args()

    config = load_config()
    if not config:
        print("[Redmine] 未配置，跳过。请编辑 settings.json 填写 redmine 配置。")
        return

    if args.command is None:
        cmd_sync(config)
    elif args.command == "time-entries":
        cmd_time_entries(config, args.from_date, args.to_date)
    elif args.command == "issues-worked":
        cmd_issues_worked(config, args.from_date, args.to_date)


if __name__ == "__main__":
    main()
