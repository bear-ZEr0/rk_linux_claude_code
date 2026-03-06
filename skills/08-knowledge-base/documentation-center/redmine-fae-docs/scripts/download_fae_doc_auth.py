#!/usr/bin/env python3
"""
Redmine FAE文档下载工具 - 支持登录认证
下载指定的FAE文档及其附件
"""

import os
import sys
import json
import argparse
import re
import urllib.parse
import urllib.request
import http.cookiejar
import ssl

# 添加脚本目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "configs")
CONFIG_FILE = os.path.join(CONFIG_DIR, "redmine_config.json")

# 加载配置
def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()
BASE_URL = CONFIG['base_url']
CACHE_DIR = CONFIG['cache_dir']
API_KEY = CONFIG['api_key']
USERNAME = CONFIG.get('username')
PASSWORD = CONFIG.get('password')

# 创建SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 创建cookie jar
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookie_jar),
    urllib.request.HTTPSHandler(context=ssl_context)
)
urllib.request.install_opener(opener)

def login_to_redmine():
    """登录Redmine获取session cookie"""
    print("[INFO] 正在登录Redmine...")

    # 获取CSRF token
    login_url = f"{BASE_URL}/login"
    req = urllib.request.Request(login_url)
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"[ERROR] 无法获取登录页面: {e}")
        return False

    # 提取authenticity_token
    token_match = re.search(r'name="authenticity_token"\s+value="([^"]+)"', html)
    if not token_match:
        print("[ERROR] 无法获取CSRF token")
        return False

    import html as html_module
    token = html_module.unescape(token_match.group(1))

    # 准备登录数据
    login_data = {
        'utf8': '✓',
        'authenticity_token': token,
        'username': USERNAME,
        'password': PASSWORD,
        'back_url': '/'
    }

    # 发送登录请求
    data = urllib.parse.urlencode(login_data).encode('utf-8')
    req = urllib.request.Request(login_url, data=data)
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            final_url = response.geturl()
    except Exception as e:
        print(f"[ERROR] 登录失败: {e}")
        return False

    # 检查是否登录成功
    if 'Sign in' in html or 'login' in final_url:
        print("[ERROR] 登录失败，请检查用户名密码")
        return False

    print("[SUCCESS] 登录成功!")
    return True

def load_document_cache():
    """加载缓存的文档列表"""
    cache_file = os.path.join(CACHE_DIR, 'document_list.json')

    if not os.path.exists(cache_file):
        print("[ERROR] 缓存文件不存在，请先运行搜索命令建立缓存", file=sys.stderr)
        print(f"[INFO] 运行: python3 {SCRIPT_DIR}/search_fae_docs.py <关键词>", file=sys.stderr)
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 加载缓存失败: {e}", file=sys.stderr)
        return None

def find_document_by_id(doc_id):
    """根据文档ID查找文档信息"""
    data = load_document_cache()
    if not data:
        return None

    for doc in data.get('documents', []):
        if doc['id'] == str(doc_id):
            return doc

    return None

def fetch_document_page(doc_url):
    """获取文档详情页面，提取附件信息"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        }

        req = urllib.request.Request(doc_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')

        # 提取附件信息
        attachments = []
        attachment_pattern = re.compile(
            r'<a[^>]*href="(/attachments/download/\d+/[^"]+)"[^>]*>([^<]+)</a>',
            re.DOTALL
        )

        for match in attachment_pattern.finditer(html):
            att_url = f"{BASE_URL}{match.group(1)}"
            att_name = match.group(2).strip()

            # 提取文件大小（如果有）
            size_match = re.search(
                rf'{re.escape(att_name)}.*?\((\d+(?:\.\d+)?\s*[KMG]?B)\)',
                html,
                re.DOTALL
            )
            file_size = size_match.group(1) if size_match else 'Unknown'

            attachments.append({
                'filename': att_name,
                'url': att_url,
                'size': file_size
            })

        return attachments

    except Exception as e:
        print(f"[ERROR] 获取文档页面失败: {doc_url}", file=sys.stderr)
        print(f"[ERROR] {str(e)}", file=sys.stderr)
        return []

def download_file(url, output_path):
    """下载文件"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        }

        req = urllib.request.Request(url, headers=headers)

        print(f"[INFO] 正在下载: {url}")

        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()

        with open(output_path, 'wb') as f:
            f.write(content)

        file_size = len(content) / 1024  # KB
        print(f"[SUCCESS] 下载完成: {output_path} ({file_size:.1f} KB)")
        return True

    except Exception as e:
        print(f"[ERROR] 下载失败: {url}", file=sys.stderr)
        print(f"[ERROR] {str(e)}", file=sys.stderr)
        return False

def download_document(doc_id, output_dir):
    """下载文档及其所有附件"""
    # 登录Redmine
    if not login_to_redmine():
        print("[ERROR] 登录失败，无法下载文档", file=sys.stderr)
        return False

    # 查找文档信息
    doc = find_document_by_id(doc_id)
    if not doc:
        print(f"[ERROR] 未找到文档ID: {doc_id}", file=sys.stderr)
        print("[INFO] 请先运行搜索命令查找文档", file=sys.stderr)
        return False

    print(f"[INFO] 文档标题: {doc['title']}")
    print(f"[INFO] 文档URL: {doc['url']}")

    # 创建输出目录
    doc_dir = os.path.join(output_dir, f"fae_doc_{doc_id}")
    os.makedirs(doc_dir, exist_ok=True)

    # 获取文档详情页面，提取更完整的附件列表
    attachments = fetch_document_page(doc['url'])

    if not attachments:
        # 如果没有从页面提取到附件，使用缓存中的附件信息
        attachments = doc.get('attachments', [])

    if not attachments:
        print("[WARN] 文档没有附件")
        return True

    print(f"[INFO] 发现 {len(attachments)} 个附件")

    # 下载所有附件
    success_count = 0
    for i, att in enumerate(attachments, 1):
        filename = att['filename']
        url = att['url']

        # 清理文件名（移除不安全字符）
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        output_path = os.path.join(doc_dir, safe_filename)

        print(f"\n[{i}/{len(attachments)}] {filename}")
        if 'size' in att:
            print(f"      大小: {att['size']}")

        if download_file(url, output_path):
            success_count += 1

    print(f"\n[INFO] 下载完成: {success_count}/{len(attachments)} 个文件成功")
    print(f"[INFO] 保存目录: {doc_dir}")

    # 生成文档报告
    report_path = os.path.join(doc_dir, "document_info.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"文档标题: {doc['title']}\n")
        f.write(f"文档ID: {doc_id}\n")
        f.write(f"文档URL: {doc['url']}\n")
        if 'category' in doc:
            f.write(f"分类: {doc['category']}\n")
        f.write(f"\n附件列表:\n")
        for att in attachments:
            f.write(f"  - {att['filename']}")
            if 'size' in att:
                f.write(f" ({att['size']})")
            f.write(f"\n")

    print(f"[INFO] 文档信息已保存到: {report_path}")

    return success_count > 0

def main():
    parser = argparse.ArgumentParser(
        description='下载Redmine FAE文档及其附件'
    )
    parser.add_argument('doc_id', help='文档ID')
    parser.add_argument(
        '--output-dir',
        default='/tmp/fae_docs',
        help='输出目录 (默认: /tmp/fae_docs)'
    )

    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)

    # 下载文档
    success = download_document(args.doc_id, args.output_dir)

    if success:
        print("\n[SUCCESS] 文档下载完成")
        return 0
    else:
        print("\n[FAILED] 文档下载失败", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
