#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerrit API 统一客户端

合并 collect-weekly-data.py 和 gerrit_review.py 的 Gerrit 访问逻辑，
提供认证、查询、操作、统计等通用接口。
"""

import base64
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# 内网自签名证书，跳过 SSL 验证
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def load_settings():
    """从项目根 settings.json 读取 gerrit 配置"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        settings_file = current / "settings.json"
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            gerrit = config.get("gerrit", {})
            if not gerrit.get("url") or not gerrit.get("username") or not gerrit.get("password"):
                print("错误: settings.json 中 gerrit.url / username / password 配置不完整", file=sys.stderr)
                sys.exit(1)
            return gerrit
        current = current.parent
    print("错误: 未找到 settings.json，请先运行 /config 配置", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------

def _make_auth_header(username, password):
    """创建 Basic Auth 认证头"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {encoded}",
        "User-Agent": "gerrit-client/1.0"
    }


def login(url, username, password):
    """建立 cookie session，返回 (opener, headers, xsrf_token)

    统一认证入口，同时支持 REST 查询和 POST 操作。
    """
    headers = _make_auth_header(username, password)
    cookie_jar = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(
        cookie_jar,
        urllib.request.HTTPSHandler(context=SSL_CONTEXT)
    )

    login_url = f"{url.rstrip('/')}/login/"
    login_req = urllib.request.Request(login_url, headers=headers)
    try:
        opener.open(login_req, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"错误: Gerrit 登录失败 HTTP {e.code} — {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"错误: 无法连接 Gerrit — {e.reason}", file=sys.stderr)
        sys.exit(1)

    # 从 cookie 中提取 XSRF token
    xsrf_token = None
    for cookie in cookie_jar.cookiejar:
        if cookie.name == "XSRF_TOKEN":
            xsrf_token = cookie.value
            break
    return opener, headers, xsrf_token


# ---------------------------------------------------------------------------
# 通用 API 封装
# ---------------------------------------------------------------------------

def api_get(opener, headers, base_url, path):
    """GET 请求，自动处理 )]}' 前缀"""
    url = f"{base_url.rstrip('/')}{path}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            if content.startswith(")]}'"):
                content = content[4:]
            return json.loads(content)
    except urllib.error.HTTPError as e:
        print(f"错误: Gerrit API 返回 {e.code} — {e.reason} ({path})", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"错误: 无法连接 Gerrit — {e.reason}", file=sys.stderr)
        sys.exit(1)


def api_post(opener, headers, base_url, path, data, xsrf_token=None):
    """POST 请求，通过 cookie session + XSRF token 认证"""
    url = f"{base_url.rstrip('/')}{path}"
    body = json.dumps(data).encode("utf-8")
    post_headers = dict(headers)
    post_headers["Content-Type"] = "application/json"
    if xsrf_token:
        post_headers["X-Gerrit-Auth"] = xsrf_token
    req = urllib.request.Request(url, data=body, headers=post_headers, method="POST")
    try:
        with opener.open(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            if content.startswith(")]}'"):
                content = content[4:]
            return json.loads(content) if content.strip() else {}
    except urllib.error.HTTPError as e:
        print(f"错误: Gerrit API 返回 {e.code} — {e.reason} ({path})", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"错误: 无法连接 Gerrit — {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 查询接口
# ---------------------------------------------------------------------------

def get_changes(url, username, password, since, until, query_extra=""):
    """按时间段查询提交列表，返回 List[Dict]

    默认查询 owner:self，可通过 query_extra 追加条件。
    """
    if not url or not username:
        return []

    headers = _make_auth_header(username, password)
    cookie_handler = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(
        cookie_handler,
        urllib.request.HTTPSHandler(context=SSL_CONTEXT)
    )

    changes = []
    try:
        login_url = f"{url.rstrip('/')}/login/"
        login_req = urllib.request.Request(login_url, headers=headers)
        opener.open(login_req, timeout=30)

        query = f"owner:self+after:{since}+before:{until}"
        if query_extra:
            query += f"+{urllib.parse.quote(query_extra, safe=':')}"
        api_url = f"{url.rstrip('/')}/changes/?q={query}"

        req = urllib.request.Request(api_url, headers=headers)
        with opener.open(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            if content.startswith(")]}'"):
                content = content[4:]
            data = json.loads(content)

            for change in data:
                changes.append({
                    "id": change.get("change_id"),
                    "number": change.get("_number"),
                    "subject": change.get("subject"),
                    "project": change.get("project"),
                    "branch": change.get("branch"),
                    "status": change.get("status"),
                    "updated": change.get("updated"),
                    "insertions": change.get("insertions", 0),
                    "deletions": change.get("deletions", 0),
                })
    except urllib.error.URLError as e:
        print(f"获取 Gerrit 数据失败: {e}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"解析 Gerrit 响应失败: {e}", file=sys.stderr)

    return changes


def get_change_detail(change_number, url=None, username=None, password=None):
    """查询 Change 详情（状态、审核人、评论）"""
    if url is None:
        settings = load_settings()
        url, username, password = settings["url"], settings["username"], settings["password"]
    opener, headers, _ = login(url, username, password)
    query = urllib.parse.quote(str(change_number), safe="")
    changes = api_get(
        opener, headers, url,
        f"/changes/?q=change:{query}&o=CURRENT_REVISION&o=DETAILED_ACCOUNTS&o=DETAILED_LABELS"
    )
    if not changes:
        return {}
    return changes[0]


def get_change_diff(change_id, url=None, username=None, password=None):
    """获取 Change 最新 patchset 的 diff，返回 (meta_dict, diff_str)"""
    if url is None:
        settings = load_settings()
        url, username, password = settings["url"], settings["username"], settings["password"]
    opener, headers, _ = login(url, username, password)

    query = urllib.parse.quote(str(change_id), safe="")
    changes = api_get(
        opener, headers, url,
        f"/changes/?q=change:{query}&o=CURRENT_REVISION&o=DETAILED_ACCOUNTS"
    )
    if not changes:
        return None, ""

    change = changes[0]
    number = change.get("_number")
    current_rev = change.get("current_revision", "")
    revisions = change.get("revisions", {})
    patch_set_num = revisions.get(current_rev, {}).get("_number", "?")

    patch_url = f"{url.rstrip('/')}/changes/{number}/revisions/current/patch"
    req = urllib.request.Request(patch_url, headers=headers)
    with opener.open(req, timeout=60) as response:
        patch_b64 = response.read().decode("utf-8")
        diff_content = base64.b64decode(patch_b64).decode("utf-8", errors="replace")

    meta = {
        "number": number,
        "patch_set": patch_set_num,
        "subject": change.get("subject", ""),
        "project": change.get("project", ""),
        "branch": change.get("branch", ""),
        "owner": change.get("owner", {}).get("name", ""),
        "revision": current_rev[:12] if current_rev else "",
    }
    return meta, diff_content


def get_reviewer_changes(since, until, url=None, username=None, password=None):
    """获取待自己 review 的 Change 列表"""
    if url is None:
        settings = load_settings()
        url, username, password = settings["url"], settings["username"], settings["password"]
    opener, headers, _ = login(url, username, password)
    query = f"reviewer:self+status:open+after:{since}+before:{until}"
    api_url = f"{url.rstrip('/')}/changes/?q={query}"
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with opener.open(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            if content.startswith(")]}'"):
                content = content[4:]
            return json.loads(content)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"获取待 review 列表失败: {e}", file=sys.stderr)
        return []


def get_project_changes(project, branch=None, limit=20,
                        url=None, username=None, password=None):
    """查询项目提交历史"""
    if url is None:
        settings = load_settings()
        url, username, password = settings["url"], settings["username"], settings["password"]
    opener, headers, _ = login(url, username, password)
    query = f"project:{project}"
    if branch:
        query += f"+branch:{branch}"
    api_url = f"{url.rstrip('/')}/changes/?q={query}&n={limit}"
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with opener.open(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            if content.startswith(")]}'"):
                content = content[4:]
            return json.loads(content)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"获取项目提交历史失败: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# 操作接口
# ---------------------------------------------------------------------------

def submit_review(change_id, score, message, url=None, username=None, password=None):
    """提交 Code-Review 评分，返回 bool"""
    if url is None:
        settings = load_settings()
        url, username, password = settings["url"], settings["username"], settings["password"]
    opener, headers, xsrf_token = login(url, username, password)

    query = urllib.parse.quote(str(change_id), safe="")
    changes = api_get(opener, headers, url, f"/changes/?q=change:{query}")
    if not changes:
        print(f"错误: 未找到 Change {change_id}", file=sys.stderr)
        return False

    number = changes[0].get("_number")

    VALID_SCORES = {-2, -1, 0, 1, 2}
    try:
        score_int = int(score)
    except ValueError:
        print(f"错误: 无效的打分值 '{score}'，有效值: -2, -1, 0, +1, +2", file=sys.stderr)
        return False
    if score_int not in VALID_SCORES:
        print(f"错误: 打分值 {score_int} 超出范围，有效值: -2, -1, 0, +1, +2", file=sys.stderr)
        return False

    review_data = {
        "message": message,
        "labels": {"Code-Review": score_int}
    }

    api_post(
        opener, headers, url,
        f"/changes/{number}/revisions/current/review",
        review_data, xsrf_token
    )

    score_str = f"+{score_int}" if score_int > 0 else str(score_int)
    print(f"已提交审核: Change {number}, Code-Review {score_str}")
    return True


# ---------------------------------------------------------------------------
# 统计接口
# ---------------------------------------------------------------------------

def get_stats(changes):
    """从 changes 列表计算统计信息"""
    merged = [c for c in changes if c.get("status") == "MERGED"]
    open_changes = [c for c in changes if c.get("status") in ("NEW", "OPEN")]
    return {
        "commits": len(changes),
        "merged": len(merged),
        "open": len(open_changes),
        "insertions": sum(c.get("insertions", 0) for c in changes),
        "deletions": sum(c.get("deletions", 0) for c in changes),
    }


def get_stats_report(since, until, url=None, username=None, password=None):
    """提交统计报表（提交数、合并数、代码行数）"""
    if url is None:
        settings = load_settings()
        url, username, password = settings["url"], settings["username"], settings["password"]
    changes = get_changes(url, username, password, since, until)
    return get_stats(changes)
