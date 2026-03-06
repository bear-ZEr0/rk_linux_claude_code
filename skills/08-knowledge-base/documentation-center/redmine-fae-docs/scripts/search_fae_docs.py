#!/usr/bin/env python3
"""
Redmine FAE文档中心搜索工具
搜索和检索Redmine FAE项目文档中心的技术文档
"""

import os
import sys
import json
import re
import argparse
import time
import ssl
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import datetime, timedelta
from urllib.parse import urljoin
from html.parser import HTMLParser

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
FAE_DOCS_URL = CONFIG.get('fae_project_url', f"{BASE_URL}/projects/fae/documents")
CACHE_DIR = CONFIG['cache_dir']
CACHE_TTL = CONFIG['cache_ttl']
API_KEY = CONFIG['api_key']
USERNAME = CONFIG.get('username')
PASSWORD = CONFIG.get('password')

# 创建SSL上下文（跳过证书验证）
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

# 确保缓存目录存在
os.makedirs(CACHE_DIR, exist_ok=True)

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
    print(f"[DEBUG] CSRF token: {token[:50]}...")

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

class RedmineDocParser(HTMLParser):
    """解析Redmine文档页面"""

    def __init__(self):
        super().__init__()
        self.categories = []  # 子分类列表
        self.documents = []   # 文档列表
        self.current_category = None
        self.in_category_link = False
        self.in_document_title = False
        self.in_document_desc = False
        self.current_doc = {}
        self.current_tag_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.current_tag_stack.append(tag)

        # 检测子分类链接 (通常在 h3 或 div.document-category 中)
        if tag == 'a':
            href = attrs_dict.get('href', '')
            # 匹配 /documents/XX 格式的子分类链接
            if re.match(r'/documents/\d+', href):
                category_id = re.search(r'/documents/(\d+)', href).group(1)
                self.current_category = {
                    'id': category_id,
                    'url': urljoin(BASE_URL, href),
                    'title': ''
                }
                self.in_category_link = True

        # 检测文档标题链接
        if tag == 'a' and 'class' in attrs_dict:
            if 'document' in attrs_dict.get('class', ''):
                href = attrs_dict.get('href', '')
                self.current_doc = {
                    'title': '',
                    'url': urljoin(BASE_URL, href),
                    'id': '',
                    'description': '',
                    'author': '',
                    'date': '',
                    'attachments': []
                }
                self.in_document_title = True

        # 检测附件链接
        if tag == 'a' and 'attachments' in attrs_dict.get('href', ''):
            href = attrs_dict.get('href', '')
            attachment_url = urljoin(BASE_URL, href)
            filename = href.split('/')[-1]
            if self.current_doc:
                self.current_doc['attachments'].append({
                    'filename': filename,
                    'url': attachment_url
                })

    def handle_endtag(self, tag):
        if self.current_tag_stack and self.current_tag_stack[-1] == tag:
            self.current_tag_stack.pop()

        if tag == 'a' and self.in_category_link:
            if self.current_category and self.current_category['title']:
                self.categories.append(self.current_category)
            self.in_category_link = False
            self.current_category = None

        if tag == 'a' and self.in_document_title:
            if self.current_doc and self.current_doc['title']:
                self.documents.append(self.current_doc)
            self.in_document_title = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_category_link and self.current_category is not None:
            self.current_category['title'] += data

        if self.in_document_title and self.current_doc:
            self.current_doc['title'] += data


def fetch_page(url):
    """获取页面内容 - 使用session cookie获取HTML"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')

            # 检查是否被重定向到登录页面
            if 'redirected' in html or 'login' in html.lower():
                print(f"[WARN] 页面需要认证，session可能已过期: {url}", file=sys.stderr)
                return None

            return html
    except Exception as e:
        print(f"[ERROR] 获取页面失败: {url}", file=sys.stderr)
        print(f"[ERROR] {str(e)}", file=sys.stderr)
        return None


def parse_document_list_page(html_content):
    """解析文档列表页面，提取文档信息"""
    documents = []

    # 使用正则表达式提取文档信息
    # 匹配文档标题和链接
    doc_pattern = re.compile(
        r'<a[^>]*href="(/documents/\d+)"[^>]*>([^<]+)</a>',
        re.DOTALL
    )

    # 匹配附件链接
    attachment_pattern = re.compile(
        r'<a[^>]*href="(/attachments/download/\d+/[^"]+)"[^>]*>([^<]+)</a>.*?'
        r'<span[^>]*class="author"[^>]*>([^<]+)</span>.*?'
        r'<span[^>]*class="created_on"[^>]*>([^<]+)</span>',
        re.DOTALL
    )

    # 提取文档信息
    for match in doc_pattern.finditer(html_content):
        doc_url = urljoin(BASE_URL, match.group(1))
        doc_title = match.group(2).strip()
        doc_id = re.search(r'/documents/(\d+)', match.group(1)).group(1)

        documents.append({
            'id': doc_id,
            'title': doc_title,
            'url': doc_url,
            'attachments': []
        })

    # 提取附件信息
    for match in attachment_pattern.finditer(html_content):
        attachment_url = urljoin(BASE_URL, match.group(1))
        attachment_name = match.group(2).strip()
        author = match.group(3).strip()
        date = match.group(4).strip()

        # 关联到最近的文档
        if documents:
            documents[-1]['attachments'].append({
                'filename': attachment_name,
                'url': attachment_url,
                'author': author,
                'date': date
            })

    return documents


def crawl_fae_documents():
    """爬取FAE文档中心的所有文档"""
    print("[INFO] 开始爬取FAE文档中心...")

    # 0. 登录Redmine
    if not login_to_redmine():
        print("[ERROR] 登录失败，无法继续爬取", file=sys.stderr)
        return None

    # 1. 获取主页
    html = fetch_page(FAE_DOCS_URL)
    if not html:
        print("[ERROR] 无法获取FAE文档中心主页", file=sys.stderr)
        return None

    # 2. 解析主页，提取子分类链接
    parser = RedmineDocParser()
    parser.feed(html)

    categories = parser.categories
    main_page_docs = parse_document_list_page(html)

    print(f"[INFO] 发现 {len(categories)} 个子分类")
    print(f"[INFO] 主页包含 {len(main_page_docs)} 个文档")

    all_documents = main_page_docs.copy()
    category_index = []

    # 3. 遍历子分类
    for i, category in enumerate(categories, 1):
        print(f"[INFO] 正在爬取子分类 {i}/{len(categories)}: {category['title']} ({category['url']})")

        time.sleep(0.5)  # 避免请求过快

        cat_html = fetch_page(category['url'])
        if not cat_html:
            print(f"[WARN] 跳过子分类: {category['title']}", file=sys.stderr)
            continue

        # 解析子分类页面的文档
        cat_docs = parse_document_list_page(cat_html)

        category_info = {
            'id': category['id'],
            'title': category['title'],
            'url': category['url'],
            'document_count': len(cat_docs)
        }
        category_index.append(category_info)

        # 为每个文档添加分类信息
        for doc in cat_docs:
            doc['category'] = category['title']
            doc['category_id'] = category['id']

        all_documents.extend(cat_docs)
        print(f"[INFO] 子分类 '{category['title']}' 包含 {len(cat_docs)} 个文档")

    print(f"[INFO] 总共爬取到 {len(all_documents)} 个文档")

    return {
        'categories': category_index,
        'documents': all_documents,
        'crawl_time': datetime.now().isoformat(),
        'total_count': len(all_documents)
    }


def load_cache():
    """加载缓存的文档列表"""
    cache_file = os.path.join(CACHE_DIR, 'document_list.json')

    if not os.path.exists(cache_file):
        return None

    # 检查缓存是否过期
    cache_age = time.time() - os.path.getmtime(cache_file)
    if cache_age > CACHE_TTL:
        print("[INFO] 缓存已过期，将重新爬取")
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cache_hours = cache_age / 3600
        print(f"[INFO] 使用缓存数据 (更新于 {cache_hours:.1f} 小时前)")
        return data
    except Exception as e:
        print(f"[WARN] 加载缓存失败: {e}", file=sys.stderr)
        return None


def save_cache(data):
    """保存文档列表到缓存"""
    cache_file = os.path.join(CACHE_DIR, 'document_list.json')

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 缓存已保存到: {cache_file}")
    except Exception as e:
        print(f"[WARN] 保存缓存失败: {e}", file=sys.stderr)


def search_documents(keywords, limit=10, force_refresh=False):
    """搜索文档"""
    # 加载或爬取文档列表
    if force_refresh:
        data = crawl_fae_documents()
        if data:
            save_cache(data)
    else:
        data = load_cache()
        if not data:
            data = crawl_fae_documents()
            if data:
                save_cache(data)

    if not data:
        print("[ERROR] 无法获取文档列表", file=sys.stderr)
        return []

    documents = data['documents']

    # 关键词匹配
    keywords_lower = keywords.lower()
    matched_docs = []

    for doc in documents:
        score = 0

        # 标题匹配
        if keywords_lower in doc['title'].lower():
            score += 10

        # 分类匹配
        if 'category' in doc and keywords_lower in doc.get('category', '').lower():
            score += 5

        # 附件文件名匹配
        for att in doc.get('attachments', []):
            if keywords_lower in att['filename'].lower():
                score += 3

        if score > 0:
            doc['score'] = score
            matched_docs.append(doc)

    # 按匹配分数排序
    matched_docs.sort(key=lambda x: x['score'], reverse=True)

    return matched_docs[:limit]


def main():
    parser = argparse.ArgumentParser(
        description='搜索Redmine FAE文档中心的技术文档'
    )
    parser.add_argument('keywords', help='搜索关键词')
    parser.add_argument('--limit', type=int, default=10, help='返回结果数量限制')
    parser.add_argument('--refresh', action='store_true', help='强制刷新缓存')

    args = parser.parse_args()

    # 搜索文档
    results = search_documents(args.keywords, limit=args.limit, force_refresh=args.refresh)

    if not results:
        print(f"\n未找到匹配 '{args.keywords}' 的文档")
        return

    print(f"\n找到 {len(results)} 个匹配的文档:\n")
    print("=" * 80)

    for i, doc in enumerate(results, 1):
        print(f"\n[{i}] {doc['title']}")
        print(f"    文档ID: {doc['id']}")
        print(f"    URL: {doc['url']}")

        if 'category' in doc:
            print(f"    分类: {doc['category']}")

        if doc.get('attachments'):
            print(f"    附件数量: {len(doc['attachments'])}")
            for att in doc['attachments'][:3]:  # 只显示前3个附件
                print(f"      - {att['filename']}")
                if 'author' in att:
                    print(f"        作者: {att['author']}, 更新: {att.get('date', 'N/A')}")

            if len(doc['attachments']) > 3:
                print(f"      ... 还有 {len(doc['attachments']) - 3} 个附件")

        print(f"    匹配分数: {doc['score']}")

    print("\n" + "=" * 80)
    print(f"\n使用以下命令下载文档:")
    print(f"python3 {SCRIPT_DIR}/download_fae_doc.py <文档ID>")


if __name__ == '__main__':
    main()
