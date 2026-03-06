#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周报数据自动收集脚本
从 Gerrit、Redmine 和邮箱收集本周工作数据，生成 Markdown 周报
"""

import argparse
import imaplib
import json
import os
import re
import sys
import ssl
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# 创建不验证 SSL 证书的上下文 (内网自签名证书)
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

CHIP_PATTERNS = [
    "RK3588", "RK3572", "RK3568", "RK3566", "RK3562", "RK3506",
    "RK3399", "RK3328", "RK3308", "RK3288", "RK3128",
    "RK1808", "RK1806", "RK1820", "RK1828", "RK182X",
    "RK186X", "RK3668",
    "RV1103", "RV1106", "RV1109", "RV1126",
]

CHIP_NORMALIZE = {
    "RK1820": "RK182X",
    "RK1828": "RK182X",
    "RK3566": "RK356X",
    "RK3568": "RK356X",
}

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]

DEFAULT_NOISE_SENDERS = [
    "gerrit@rock-chips.com", "redmine@rock-chips.com",
    "noreply@rock-chips.com", "jenkins@rock-chips.com",
    "notice@qiye.163.com", "postmaster@rock-chips.com",
]

DEFAULT_NOISE_SUBJECT_PATTERNS = [
    r"^\[Gerrit\]", r"^\[gerrit\]", r"^\[Redmine\]",
    r"^Change in .* \[", r"^Build (SUCCESS|FAILURE|UNSTABLE)",
    r"考勤异常提醒",
    r"^\[tv-rockchips\]", r"^\[core-rockchip\]",
    r"^Updates to .* Privacy Policy", r"Alfresco Share:",
    r"邮件测试", r"^Test$", r"默认收件人测试",
    r"^\S+\s*-\s*周报\s*-", r"个人工作总结", r"工作周报\s*\d{8}", r"^\d{8}-\d{8}$",
    r"考勤汇总", r"法律简报", r"年会.*通知", r"年度表彰", r"季度之星", r"防騙", r"验证码",
    r"^🤖\s*每日AI新闻",
    r"【瑞芯微CRM】项目周报.*未提交提醒",
    r"^发布[:：]", r"SDK.*发布", r"Datasheet.*发布", r"技术.*简报",
]

DEFAULT_CATEGORIES = {
    "会议": ["会议", "meeting", "邀请", "invite", "日程", "纪要"],
    "跨部门协调": ["协调", "配合", "支持", "协助", "跨部门", "对接"],
    "技术讨论": ["方案", "设计", "讨论", "review", "评审", "技术"],
    "项目沟通": ["进度", "排期", "计划", "需求", "项目"],
}


# ---------------------------------------------------------------------------
# 动态导入外部模块
# ---------------------------------------------------------------------------

def _import_gerrit():
    scripts = Path(__file__).parent.parent.parent / "99-common-tools" / "rk-gerrit" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import gerrit_client
    return gerrit_client


def _import_oa():
    scripts = Path(__file__).parent.parent.parent / "99-common-tools" / "rk-oa" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import oa_client
    return oa_client


def _import_redmine():
    scripts = Path(__file__).parent.parent.parent / "07-customer-support" / "rk-redmine" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import sync_my_issues
    return sync_my_issues


def _import_email_config():
    email_scripts = Path(__file__).parent.parent.parent / "99-common-tools" / "rk-email" / "scripts"
    if str(email_scripts) not in sys.path:
        sys.path.insert(0, str(email_scripts))
    import email_config
    return email_config


# ---------------------------------------------------------------------------
# 周报特有的工具函数
# ---------------------------------------------------------------------------

def extract_chip_platform(text: str) -> Optional[str]:
    """从文本中提取芯片平台标识"""
    text_upper = text.upper()
    for chip in CHIP_PATTERNS:
        if chip in text_upper:
            return CHIP_NORMALIZE.get(chip, chip)
    return None


def get_monday_date() -> str:
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.strftime("%Y-%m-%d")


def get_week_number(date_str: str) -> int:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.isocalendar()[1]


def get_config(config_path: Path) -> dict:
    if not config_path.exists():
        print("警告: 配置文件不存在，使用默认配置", file=sys.stderr)
        return {
            "redmine": {"url": "", "username": "", "password": ""},
            "gerrit": {"url": "", "username": "", "password": ""},
            "weekly_report": {"author": "", "department": ""}
        }
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("配置文件格式错误")
            return data
    except (json.JSONDecodeError, ValueError) as e:
        print(f"警告: 配置文件解析失败({e})，使用默认配置", file=sys.stderr)
        return {
            "redmine": {"url": "", "username": "", "password": ""},
            "gerrit": {"url": "", "username": "", "password": ""},
            "weekly_report": {"author": "", "department": ""}
        }


# ---------------------------------------------------------------------------
# Gerrit 数据收集（委托 gerrit_client）
# ---------------------------------------------------------------------------

def get_gerrit_changes(url, username, password, since, until, email=None):
    gerrit = _import_gerrit()
    changes = gerrit.get_changes(url, username, password, since, until)
    for change in changes:
        text = f"{change.get('subject', '')} {change.get('project', '')} {change.get('branch', '')}"
        chip = extract_chip_platform(text)
        if chip:
            change["chip"] = chip
    return changes


def get_gerrit_stats(changes):
    gerrit = _import_gerrit()
    return gerrit.get_stats(changes)


# ---------------------------------------------------------------------------
# Redmine 数据收集（委托 sync_my_issues）
# ---------------------------------------------------------------------------

def get_redmine_time_entries(url, username, password, from_date, to_date, api_key=None):
    redmine = _import_redmine()
    config = {
        'base_url': url.rstrip('/'),
        'api_key': api_key or '',
        'username': username or '',
        'password': password or '',
    }
    if not url or (not api_key and (not username or not password)):
        print("Redmine 配置不完整，跳过工时收集", file=sys.stderr)
        return []
    return redmine.get_time_entries(config, from_date, to_date)


def get_redmine_issues_worked(url, username, password, from_date, to_date, api_key=None):
    redmine = _import_redmine()
    config = {
        'base_url': url.rstrip('/'),
        'api_key': api_key or '',
        'username': username or '',
        'password': password or '',
    }
    if not url:
        return []
    issues = redmine.get_issues_worked(config, from_date, to_date)
    for issue in issues:
        chip = extract_chip_platform(issue.get("subject", ""))
        if chip:
            issue["chip"] = chip
    return issues


def group_time_by_project(time_entries):
    redmine = _import_redmine()
    return redmine.group_time_by_project(time_entries)


# ---------------------------------------------------------------------------
# OA 考勤数据收集（委托 oa_client）
# ---------------------------------------------------------------------------

def get_oa_attendance(url, username, password, from_date, to_date, captcha=""):
    oa = _import_oa()
    return oa.get_oa_attendance(url, username, password, from_date, to_date, captcha)


def calculate_work_hours(attendance_records, from_date, to_date):
    oa = _import_oa()
    return oa.calculate_work_hours(attendance_records, from_date, to_date)


# ---------------------------------------------------------------------------
# 邮件信号收集（保留在本文件）
# ---------------------------------------------------------------------------

def _decode_mime_header(header: str) -> str:
    if not header:
        return ""
    parts = decode_header(header)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return "".join(decoded)


def _is_noise_email(subject, sender, noise_senders, noise_patterns):
    sender_lower = sender.lower()
    for ns in noise_senders:
        if ns.lower() in sender_lower:
            return True
    for pattern in noise_patterns:
        if re.search(pattern, subject, re.IGNORECASE):
            return True
    return False


def _categorize_email(subject, categories):
    subject_lower = subject.lower()
    for cat, keywords in categories.items():
        for kw in keywords:
            if kw.lower() in subject_lower:
                return cat
    return "其他沟通"


def _normalize_subject(subject: str) -> str:
    prev = None
    s = subject.strip()
    while s != prev:
        prev = s
        s = re.sub(
            r'^(Re:\s*|RE:\s*|回复[:：]\s*|答复[:：]\s*|Fw:\s*|FW:\s*|Fwd:\s*|转发[:：]\s*|更新[:：]\s*|提醒[:：]\s*)',
            '', s, flags=re.IGNORECASE
        ).strip()
    return s


def _merge_email_threads(signals):
    threads = {}
    order = []
    for sig in signals:
        base = _normalize_subject(sig['subject'])
        key = f"{sig['category']}|{base}"
        if key not in threads:
            threads[key] = {
                'date_start': sig['date'],
                'date_end': sig['date'],
                'subject': base,
                'category': sig['category'],
                'count': 1,
            }
            order.append(key)
        else:
            threads[key]['count'] += 1
            if sig['date'] < threads[key]['date_start']:
                threads[key]['date_start'] = sig['date']
            if sig['date'] > threads[key]['date_end']:
                threads[key]['date_end'] = sig['date']
    return [threads[k] for k in order]


def _find_sent_folder(imap_conn):
    candidates = ["Sent", "INBOX.Sent", "已发送", "Sent Messages", "INBOX.Sent Messages"]
    status, folders = imap_conn.list()
    if status != "OK":
        return None
    folder_names = []
    for f in folders:
        if isinstance(f, bytes):
            f = f.decode("utf-8", errors="replace")
        parts = f.rsplit('" ', 1)
        if len(parts) == 2:
            folder_names.append(parts[1].strip('"'))
    for candidate in candidates:
        for fn in folder_names:
            if fn.lower() == candidate.lower() or fn.lower().endswith("/" + candidate.lower()):
                return fn
    return None


def get_email_signals(server, port, user, pwd, since, until, filter_config=None):
    filter_config = filter_config or {}
    noise_senders = filter_config.get("noise_senders", DEFAULT_NOISE_SENDERS)
    noise_patterns = filter_config.get("noise_subject_patterns", DEFAULT_NOISE_SUBJECT_PATTERNS)
    categories = filter_config.get("categories", DEFAULT_CATEGORIES)

    signals = []
    since_dt = datetime.strptime(since, "%Y-%m-%d")
    until_dt = datetime.strptime(until, "%Y-%m-%d")
    imap_since = since_dt.strftime("%d-%b-%Y")
    imap_before = (until_dt + timedelta(days=1)).strftime("%d-%b-%Y")

    try:
        conn = imaplib.IMAP4_SSL(server, port, ssl_context=SSL_CONTEXT)
        conn.login(user, pwd)
        try:
            folders_to_search = ["INBOX"]
            sent = _find_sent_folder(conn)
            if sent:
                folders_to_search.append(sent)

            seen_ids = set()
            for folder in folders_to_search:
                try:
                    status, _ = conn.select(folder, readonly=True)
                    if status != "OK":
                        continue
                    search_criteria = f'(SINCE {imap_since} BEFORE {imap_before})'
                    status, msg_nums = conn.search(None, search_criteria)
                    if status != "OK" or not msg_nums[0]:
                        continue

                    for num in msg_nums[0].split():
                        status, msg_data = conn.fetch(num, "(BODY[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])")
                        if status != "OK":
                            continue
                        raw = msg_data[0][1]
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8", errors="replace")

                        unfolded = re.sub(r'\r?\n[ \t]+', ' ', raw)
                        subject = ""
                        sender = ""
                        date_str = ""
                        msg_id = ""
                        for line in re.split(r'\r?\n', unfolded):
                            if not line:
                                continue
                            lower = line.lower()
                            if lower.startswith("subject:"):
                                subject = _decode_mime_header(line[8:].strip())
                            elif lower.startswith("from:"):
                                sender = _decode_mime_header(line[5:].strip())
                            elif lower.startswith("date:"):
                                date_str = line[5:].strip()
                            elif lower.startswith("message-id:"):
                                msg_id = line[11:].strip()

                        dedup_key = msg_id or f"{subject}|{sender}|{date_str}"
                        if dedup_key in seen_ids:
                            continue
                        seen_ids.add(dedup_key)

                        if _is_noise_email(subject, sender, noise_senders, noise_patterns):
                            continue

                        email_date = ""
                        try:
                            dt = parsedate_to_datetime(date_str)
                            email_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            email_date = since

                        category = _categorize_email(subject, categories)
                        is_sent = (folder != "INBOX")
                        signals.append({
                            "date": email_date,
                            "subject": subject,
                            "sender": sender,
                            "category": category,
                            "direction": "sent" if is_sent else "received",
                        })
                except Exception as e:
                    print(f"搜索邮件文件夹 {folder} 失败: {e}", file=sys.stderr)
        finally:
            conn.logout()
    except Exception as e:
        print(f"IMAP 连接失败: {e}", file=sys.stderr)

    signals.sort(key=lambda x: x.get("date", ""))
    stats = {}
    for s in signals:
        cat = s["category"]
        stats[cat] = stats.get(cat, 0) + 1
    return {"signals": signals, "stats": stats}


# ---------------------------------------------------------------------------
# 周报生成
# ---------------------------------------------------------------------------

def generate_markdown_report(data: dict, author: str) -> str:
    period = data["period"]
    end_date = datetime.strptime(period["end"], "%Y-%m-%d")
    year = end_date.year
    week = get_week_number(period["end"])

    lines = []
    lines.append(f"# 周报 - {year}年第{week}周")
    lines.append("")
    lines.append(f"**作者**: {author}")
    lines.append(f"**统计周期**: {period['start']} ~ {period['end']}")
    lines.append("")

    oa_wh = data.get("oa", {}).get("work_hours", {})
    if oa_wh.get("daily"):
        lines.append("## 工时统计（OA 打卡）")
        lines.append("")
        lines.append("| 日期 | 上班 | 下班 | 工时 | 备注 |")
        lines.append("|------|------|------|------|------|")
        for day in oa_wh["daily"]:
            d = datetime.strptime(day["date"], "%Y-%m-%d")
            date_label = f"{d.strftime('%m-%d')} ({WEEKDAY_NAMES[day['weekday']]})"
            sign_in = day["sign_in"] or "—"
            sign_out = day["sign_out"] or "—"
            hours_str = f"{day['hours']}h"
            note = ""
            if day["type"] == "overtime":
                note = "加班"
            elif day["type"] == "default":
                note = "打卡缺失，按默认"
            elif day["type"] == "weekend":
                note = "周末"
            elif day["type"] == "normal" and day["hours"] > 8:
                note = "加班"
            lines.append(f"| {date_label} | {sign_in} | {sign_out} | {hours_str} | {note} |")
        normal_hours = round(oa_wh["total_hours"] - oa_wh["overtime_hours"], 1)
        lines.append(f"**本周总工时**: {oa_wh['total_hours']}h"
                     f"（正常 {normal_hours}h + 加班 {oa_wh['overtime_hours']}h）")
        lines.append("")

    lines.append("## 一、项目详情")
    lines.append("")

    changes = data["gerrit"]["changes"]
    issues = data["redmine"]["issues_worked"]
    email_signals = data.get("email", {}).get("signals", [])

    platform_data = {}
    for change in changes:
        chip = change.get("chip") or "其他"
        if chip not in platform_data:
            platform_data[chip] = {"gerrit": [], "redmine": [], "email": []}
        platform_data[chip]["gerrit"].append(change)

    for issue in issues:
        chip = issue.get("chip") or "其他"
        if chip not in platform_data:
            platform_data[chip] = {"gerrit": [], "redmine": [], "email": []}
        platform_data[chip]["redmine"].append(issue)

    for sig in email_signals:
        chip = extract_chip_platform(sig.get("subject", ""))
        chip = chip or "其他"
        if chip not in platform_data:
            platform_data[chip] = {"gerrit": [], "redmine": [], "email": []}
        platform_data[chip]["email"].append(sig)

    if platform_data:
        sorted_chips = sorted(k for k in platform_data if k != "其他")
        if "其他" in platform_data:
            sorted_chips.append("其他")

        for chip in sorted_chips:
            pdata = platform_data[chip]
            lines.append(f"**【{chip}】**")
            for change in pdata["gerrit"]:
                status = "已合并" if change["status"] == "MERGED" else "审核中"
                lines.append(f"- {change['subject']}（{status}）")
            for issue in pdata["redmine"]:
                customer = issue.get("author", "未知客户")
                product = issue.get("product_type", "")
                status = issue.get("status", "")
                priority = issue.get("priority", "")
                issue_id = issue.get("id", "")
                desc = f"#{issue_id} " if issue_id else ""
                desc += f"[{customer}"
                if product:
                    desc += f"/{product}"
                desc += f"] {issue['subject']}"
                if priority == "Urgent":
                    desc += " — 紧急"
                elif status:
                    desc += f" — {status}"
                lines.append(f"- {desc}")
            for sig in pdata["email"]:
                lines.append(f"- [{sig['date']}] {sig['subject']}（{sig['category']}）")
            lines.append("")
    else:
        lines.append("（本周无工作数据）")
        lines.append("")

    lines.append("<!-- RAW_DATA: 以上为脚本自动收集的原始数据，需要 AI 归纳优化 -->")
    lines.append("## 二、风险前瞻")
    lines.append("")
    lines.append("（请补充风险事项及控制动作，用 → 连接）")
    lines.append("")
    lines.append("## 三、其他部门支持")
    lines.append("")
    lines.append("（请补充需要其他部门配合的事项）")
    lines.append("")
    lines.append("## 四、下周工作计划")
    lines.append("")
    lines.append("（请补充下周可验证的阶段目标）")
    lines.append("")
    return "\n".join(lines)


def save_report(content, output_dir, start_date, end_date, author):
    date = datetime.strptime(end_date, "%Y-%m-%d")
    year = date.year
    week = get_week_number(end_date)
    start_md = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m-%d")
    end_md = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m-%d")
    year_dir = output_dir / "weekly_report" / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    filename = f"周报-{year}年第{week}周({start_md}~{end_md})-{author}.md"
    filepath = year_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def print_collection_result(data, output_json=False):
    if output_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print()
    print("## 周报数据收集完成")
    print()
    print(f"**统计周期**: {data['period']['start']} ~ {data['period']['end']}")
    print()
    print("### Gerrit 统计")
    stats = data["gerrit"]["stats"]
    print(f"- 提交数: {stats['commits']}")
    print(f"- 已合并: {stats['merged']}")
    print(f"- 待审核: {stats['open']}")
    print()
    print("### Redmine 统计")
    print(f"- 总工时: {data['redmine']['total_hours']} 小时")
    print(f"- 处理问题: {len(data['redmine']['issues_worked'])} 个")
    print()
    oa_data = data.get("oa", {})
    wh = oa_data.get("work_hours", {})
    if wh.get("total_hours"):
        print("### OA 考勤工时")
        print(f"- 总工时: {wh['total_hours']} 小时")
        print(f"- 加班工时: {wh['overtime_hours']} 小时")
        print()
    email_data = data.get("email", {})
    if email_data.get("signals"):
        print("### 邮件信号")
        print(f"- 有效邮件: {len(email_data['signals'])} 封")
        for cat, count in sorted(email_data.get("stats", {}).items()):
            print(f"  - {cat}: {count}")
        print()


def _send_report_email(report, config, start_date, end_date, author):
    email_scripts = Path(__file__).parent.parent.parent / "99-common-tools" / "rk-email" / "scripts"
    if str(email_scripts) not in sys.path:
        sys.path.insert(0, str(email_scripts))
    from send_email import send_email

    email_cfg = config.get("email", {})
    to = email_cfg.get("default_to") or email_cfg.get("username", "")
    if not to:
        print("未配置收件人（email.default_to 或 email.username），跳过邮件发送", file=sys.stderr)
        return

    week = get_week_number(end_date)
    year = datetime.strptime(end_date, "%Y-%m-%d").year
    subject = f"周报 - {year}年第{week}周({start_date}~{end_date}) - {author}"

    success = send_email(to, subject, report)
    if success:
        print(f"周报已发送到: {to}")
    else:
        print("周报邮件发送失败", file=sys.stderr)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="周报数据自动收集")
    parser.add_argument("--start-date", help="开始日期，默认本周一")
    parser.add_argument("--end-date", help="结束日期，默认本周日")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--gerrit-only", action="store_true", help="仅收集 Gerrit 数据")
    parser.add_argument("--redmine-only", action="store_true", help="仅收集 Redmine 数据")
    parser.add_argument("--email-only", action="store_true", help="仅收集邮件信号数据")
    parser.add_argument("--oa-only", action="store_true", help="仅收集 OA 考勤数据")
    parser.add_argument("--no-oa", action="store_true", help="跳过 OA 考勤数据")
    parser.add_argument("--oa-captcha", help="OA 登录验证码（不提供则交互输入）")
    parser.add_argument("--send-email", action="store_true", help="收集完成后发送周报邮件")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    skill_root = script_dir.parent
    project_root = skill_root.parent.parent
    config_path = project_root / "settings.json"
    output_dir = project_root / "output"

    start_date = args.start_date or get_monday_date()
    today = datetime.now()
    days_to_sunday = 6 - today.weekday()
    sunday = today + timedelta(days=days_to_sunday)
    end_date = args.end_date or sunday.strftime("%Y-%m-%d")

    if not args.json:
        print("正在收集周报数据...", file=sys.stderr)
        print(f"统计周期: {start_date} ~ {end_date}", file=sys.stderr)
        print(file=sys.stderr)

    config = get_config(config_path)
    author = config.get("weekly_report", {}).get("author", "")
    if not author:
        author = config.get("redmine", {}).get("username", "未知")

    # 收集 Gerrit 数据
    gerrit_changes = []
    gerrit_stats = {"commits": 0, "merged": 0, "open": 0, "insertions": 0, "deletions": 0}
    if not args.redmine_only and not args.email_only and not args.oa_only:
        if not args.json:
            print("收集 Gerrit 数据...", file=sys.stderr)
        gerrit_config = config.get("gerrit", {})
        gerrit_changes = get_gerrit_changes(
            gerrit_config.get("url", ""),
            gerrit_config.get("username", ""),
            gerrit_config.get("password", ""),
            start_date, end_date,
            gerrit_config.get("email", "")
        )
        gerrit_stats = get_gerrit_stats(gerrit_changes)

    # 收集 Redmine 数据
    time_entries = []
    issues_worked = []
    if not args.gerrit_only and not args.email_only and not args.oa_only:
        if not args.json:
            print("收集 Redmine 数据...", file=sys.stderr)
        redmine_config = config.get("redmine", {})
        time_entries = get_redmine_time_entries(
            redmine_config.get("url", ""),
            redmine_config.get("username", ""),
            redmine_config.get("password", ""),
            start_date, end_date,
            redmine_config.get("api_key", "")
        )
        issues_worked = get_redmine_issues_worked(
            redmine_config.get("url", ""),
            redmine_config.get("username", ""),
            redmine_config.get("password", ""),
            start_date, end_date,
            redmine_config.get("api_key", "")
        )

    # 收集邮件信号
    email_data = {"signals": [], "stats": {}}
    if not args.gerrit_only and not args.redmine_only and not args.oa_only:
        if not args.json:
            print("收集邮件信号...", file=sys.stderr)
        try:
            email_config = _import_email_config()
            imap_cfg = email_config.get_imap_config()
            if imap_cfg.get("username") and imap_cfg.get("password"):
                email_data = get_email_signals(
                    imap_cfg["imap_server"],
                    imap_cfg["imap_port"],
                    imap_cfg["username"],
                    imap_cfg["password"],
                    start_date, end_date,
                    imap_cfg.get("filter"),
                )
        except Exception as e:
            print(f"邮件信号收集失败: {e}", file=sys.stderr)

    # 收集 OA 考勤数据
    oa_attendance = []
    oa_work_hours = {"total_hours": 0, "overtime_hours": 0, "daily": []}
    if not args.no_oa and not args.gerrit_only and not args.redmine_only and not args.email_only:
        if not args.json:
            print("收集 OA 考勤数据...", file=sys.stderr)
        oa_config = config.get("oa", {})
        oa_attendance = get_oa_attendance(
            oa_config.get("url", ""),
            oa_config.get("username", ""),
            oa_config.get("password", ""),
            start_date, end_date,
            captcha=getattr(args, "oa_captcha", "") or "",
        )
        oa_work_hours = calculate_work_hours(oa_attendance, start_date, end_date)

    # 构建数据
    redmine_hours = sum(e.get("hours", 0) for e in time_entries)
    if oa_attendance and oa_work_hours["total_hours"] > 0:
        total_hours = oa_work_hours["total_hours"]
    else:
        total_hours = redmine_hours
    data = {
        "period": {
            "start": start_date,
            "end": end_date,
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        },
        "gerrit": {"stats": gerrit_stats, "changes": gerrit_changes},
        "redmine": {
            "time_entries": time_entries,
            "total_hours": redmine_hours,
            "by_project": group_time_by_project(time_entries),
            "issues_worked": issues_worked
        },
        "email": email_data,
        "oa": {"attendance": oa_attendance, "work_hours": oa_work_hours},
        "summary": {
            "total_commits": gerrit_stats.get("commits", 0),
            "total_merged": gerrit_stats.get("merged", 0),
            "total_hours": total_hours,
            "issues_count": len(issues_worked)
        }
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        report = generate_markdown_report(data, author)
        filepath = save_report(report, output_dir, start_date, end_date, author)
        if args.send_email:
            _send_report_email(report, config, start_date, end_date, author)
        print_collection_result(data)
        print(f"周报已保存到: {filepath}")
        print()
        print("---")
        print()
        print(report)


if __name__ == "__main__":
    main()
