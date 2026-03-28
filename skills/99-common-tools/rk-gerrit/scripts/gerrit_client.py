#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerrit API 统一客户端

优先使用 SSH 方式访问 Gerrit（gerrit query），REST API 作为备用。
提供认证、查询、操作、统计等通用接口。
"""

import base64
import json
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# 内网自签名证书，跳过 SSL 验证
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# SSH 方式（优先）
# ---------------------------------------------------------------------------

def _ssh_host(url):
    """从 Gerrit URL 提取主机地址"""
    return url.rstrip("/").replace("https://", "").replace("http://", "")


def _ssh_cmd(host, port, user, query_args):
    """构造 gerrit query SSH 命令

    不指定 -i，让 SSH 自动从 ~/.ssh/ 和 ssh-agent 中选择可用 key。
    """
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "IdentitiesOnly=yes",
        "-p", str(port),
    ]
    cmd += [f"{user}@{host}", "gerrit", "query", "--format=JSON"] + query_args
    return cmd


def _ssh_query(query_args, url=None, username=None, port=29418):
    """通过 SSH 执行 gerrit query，返回解析后的 JSON 对象列表"""
    if url is None:
        settings = load_settings()
        url = settings["url"]
        username = settings["username"]

    host = _ssh_host(url)
    cmd = _ssh_cmd(host, port, username, query_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                print(f"警告: SSH gerrit query 返回非零: {stderr}", file=sys.stderr)
            return []
        lines = [l for l in result.stdout.strip().splitlines() if l]
        # gerrit query 最后一行是 {"type":"stats",...}，过滤掉
        objects = []
        for line in lines:
            try:
                obj = json.loads(line)
                if obj.get("type") == "stats":
                    continue
                objects.append(obj)
            except json.JSONDecodeError:
                pass
        return objects
    except subprocess.TimeoutExpired:
        print("错误: SSH gerrit query 超时", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("错误: 未找到 ssh 命令，请确认 OpenSSH 已安装", file=sys.stderr)
        return []


def _ssh_query_single(query_args, url=None, username=None, port=29418):
    """返回单个对象（用于 change 查询）"""
    results = _ssh_query(query_args, url, username, port)
    return results[0] if results else None


def load_settings():
    """从项目根 settings.json 读取 gerrit 配置"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        settings_file = current / "settings.json"
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            gerrit = config.get("gerrit", {})
            if not gerrit.get("url") or not gerrit.get("username"):
                print("错误: settings.json 中 gerrit.url / username 配置不完整", file=sys.stderr)
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

def get_changes(since, until, url=None, username=None, password=None, query_extra=""):
    """按时间段查询提交列表，返回 List[Dict]（SSH 方式）

    默认查询 owner:self，可通过 query_extra 追加条件。
    """
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]
        password = settings.get("password")  # REST 备用，不一定存在

    query = f"owner:self+after:{since}+before:{until}"
    if query_extra:
        query += f"+{urllib.parse.quote(query_extra, safe=':')}"

    results = _ssh_query([query], url, username)
    changes = []
    for change in results:
        changes.append({
            "id": change.get("id"),
            "number": change.get("number"),
            "subject": change.get("subject"),
            "project": change.get("project"),
            "branch": change.get("branch"),
            "status": change.get("status"),
            "updated": change.get("lastUpdated"),
            "insertions": change.get("insertions", 0),
            "deletions": change.get("deletions", 0),
        })
    return changes


def get_change_detail(change_number, url=None, username=None, password=None):
    """查询 Change 详情（状态、审核人、评论）"""
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]
    return _ssh_query_single([f"change:{change_number}", "--current-patch-set"], url, username) or {}


def get_change_diff(change_id, url=None, username=None, password=None):
    """获取 Change 最新 patchset 的 diff，返回 (meta_dict, diff_str)

    使用 SSH 获取 meta 信息，REST 获取 diff 内容。
    """
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]
        password = settings.get("password")

    # SSH 获取 patch set 元信息
    change_data = _ssh_query_single(
        [f"change:{change_id}", "--current-patch-set"],
        url, username
    )
    if not change_data:
        return None, ""

    ps = change_data.get("currentPatchSet", {})
    patch_set_num = ps.get("number", "?")
    revision = ps.get("revision", "")

    meta = {
        "number": change_data.get("number"),
        "patch_set": patch_set_num,
        "subject": change_data.get("subject", ""),
        "project": change_data.get("project", ""),
        "branch": change_data.get("branch", ""),
        "owner": change_data.get("owner", {}).get("name", ""),
        "revision": revision[:12] if revision else "",
    }

    # diff 内容通过 REST 获取（SSH 不直接支持）
    if not password:
        return meta, "(diff 需要 HTTP 密码，请在 settings.json 中配置 gerrit.password)"

    try:
        opener, headers, _ = login(url, username, password)
        patch_url = f"{url.rstrip('/')}/changes/{change_id}/revisions/current/patch"
        req = urllib.request.Request(patch_url, headers=headers)
        with opener.open(req, timeout=60) as response:
            patch_b64 = response.read().decode("utf-8")
            diff_content = base64.b64decode(patch_b64).decode("utf-8", errors="replace")
        return meta, diff_content
    except Exception as e:
        return meta, f"(获取 diff 失败: {e})"


def get_reviewer_changes(since, until, url=None, username=None, password=None):
    """获取待自己 review 的 Change 列表"""
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]
    query = f"reviewer:self+status:open+after:{since}+before:{until}"
    return _ssh_query([query], url, username)


def get_project_changes(project, branch=None, limit=20,
                        url=None, username=None, password=None):
    """查询项目提交历史"""
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]
    query = f"project:{project}"
    if branch:
        query += f"+branch:{branch}"
    return _ssh_query([query, f"--limit={limit}"], url, username)


def get_change_messages(change_id, url=None, username=None, password=None):
    """获取 Change 所有评论/Messages（SSH 方式）

    返回 List[Dict]，每条包含 timestamp, reviewer, message。
    """
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]

    results = _ssh_query(
        [f"change:{change_id}", "--comments", "--patch-sets"],
        url, username
    )
    if not results:
        return []
    return results[0].get("comments", [])


# ---------------------------------------------------------------------------
# 操作接口
# ---------------------------------------------------------------------------

def submit_review(change_id, score, message, url=None, username=None, password=None):
    """提交 Code-Review 评分，返回 bool（SSH 方式）"""
    settings = load_settings()
    if url is None:
        url = settings["url"]
        username = settings["username"]

    VALID_SCORES = {-2, -1, 0, 1, 2}
    try:
        score_int = int(score)
    except ValueError:
        print(f"错误: 无效的打分值 '{score}'，有效值: -2, -1, 0, +1, +2", file=sys.stderr)
        return False
    if score_int not in VALID_SCORES:
        print(f"错误: 打分值 {score_int} 超出范围，有效值: -2, -1, 0, +1, +2", file=sys.stderr)
        return False

    # 先通过 SSH 获取 change 编号（gerrit review 用数字编号）
    change_data = _ssh_query_single([f"change:{change_id}"], url, username)
    if not change_data:
        print(f"错误: 未找到 Change {change_id}", file=sys.stderr)
        return False

    number = change_data.get("number")
    rev = change_data.get("currentPatchSet", {}).get("revision", "")

    host = _ssh_host(url)
    cmd = _ssh_cmd(host, 29418, username, [
        "review",
        "--code-review", str(score_int),
    ])
    if message:
        cmd += ["--message", message]
    if rev:
        cmd += [f"--project={change_data.get('project')}", rev]
    else:
        cmd += [str(number)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"错误: gerrit review 失败: {result.stderr.strip()}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("错误: gerrit review 超时", file=sys.stderr)
        return False

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
    changes = get_changes(since, until, url, username, password)
    return get_stats(changes)
