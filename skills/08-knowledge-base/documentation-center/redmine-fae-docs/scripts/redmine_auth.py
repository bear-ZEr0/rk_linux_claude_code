#!/usr/bin/env python3
"""
Redmine FAE文档中心认证工具
提供登录认证和会话管理功能
"""

import os
import sys
import json
import re
import argparse
import urllib.parse
import urllib.request
import http.cookiejar
import ssl
import pickle
import time
from datetime import datetime, timedelta

# 配置
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs")
CONFIG_FILE = os.path.join(CONFIG_DIR, "redmine_config.json")

# 默认配置（仅作为后备）
DEFAULT_CONFIG = {
    "base_url": "https://10.10.10.70",
    "cache_dir": "/tmp/fae_docs_cache",
    "session_file": "/tmp/redmine_session.pkl"
}

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return DEFAULT_CONFIG.copy()

def create_ssl_context():
    """创建SSL上下文"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

class RedmineAuth:
    def __init__(self):
        self.config = load_config()
        self.base_url = self.config['base_url']
        self.username = self.config['username']
        self.password = self.config['password']
        self.session_file = self.config.get('session_file', '/tmp/redmine_session.pkl')
        self.ssl_context = create_ssl_context()
        self.cookie_jar = None
        self.opener = None

    def setup_opener(self):
        """设置HTTP opener"""
        if not self.cookie_jar:
            self.cookie_jar = http.cookiejar.CookieJar()

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=self.ssl_context)
        )
        urllib.request.install_opener(self.opener)

    def get_csrf_token(self):
        """获取CSRF token"""
        login_url = f"{self.base_url}/login"

        self.setup_opener()

        req = urllib.request.Request(login_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')

        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            print(f"[ERROR] 无法获取登录页面: {e}")
            return None

        # 提取authenticity_token
        token_match = re.search(r'name="authenticity_token"\s+value="([^"]+)"', html)
        if not token_match:
            print("[ERROR] 无法获取CSRF token")
            return None

        import html as html_module
        token = html_module.unescape(token_match.group(1))
        return token

    def login(self, save_session=True):
        """登录Redmine"""
        print(f"[INFO] 正在登录 {self.base_url} as {self.username}")

        # 获取CSRF token
        token = self.get_csrf_token()
        if not token:
            return False

        print(f"[DEBUG] CSRF token: {token[:50]}...")

        # 准备登录数据
        login_data = {
            'utf8': '✓',
            'authenticity_token': token,
            'username': self.username,
            'password': self.password,
            'back_url': '/'
        }

        # 发送登录请求
        data = urllib.parse.urlencode(login_data).encode('utf-8')
        login_url = f"{self.base_url}/login"
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

        # 保存session
        if save_session:
            self.save_session()

        return True

    def save_session(self):
        """保存session到文件"""
        try:
            session_data = {
                'cookie_jar': self.cookie_jar,
                'timestamp': time.time(),
                'base_url': self.base_url,
                'username': self.username
            }

            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)

            print(f"[SUCCESS] Session已保存到: {self.session_file}")
        except Exception as e:
            print(f"[WARN] 保存session失败: {e}")

    def load_session(self, max_age=3600):
        """从文件加载session"""
        if not os.path.exists(self.session_file):
            return False

        try:
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)

            # 检查session是否过期
            session_age = time.time() - session_data['timestamp']
            if session_age > max_age:
                print(f"[INFO] Session已过期 ({session_age:.1f}s > {max_age}s)")
                return False

            # 检查session是否匹配当前配置
            if (session_data.get('base_url') != self.base_url or
                session_data.get('username') != self.username):
                print("[INFO] Session配置不匹配")
                return False

            # 恢复cookie jar
            self.cookie_jar = session_data['cookie_jar']
            self.setup_opener()

            print(f"[SUCCESS] Session已加载 (年龄: {session_age:.1f}s)")
            return True

        except Exception as e:
            print(f"[WARN] 加载session失败: {e}")
            return False

    def verify_session(self):
        """验证session是否有效"""
        try:
            # 尝试访问需要认证的页面
            test_url = f"{self.base_url}/my/account"
            req = urllib.request.Request(test_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')

            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')

            # 如果页面包含登录表单，说明session无效
            if 'name="username"' in html:
                return False

            return True

        except Exception:
            return False

    def ensure_authenticated(self, force_login=False):
        """确保已认证"""
        if force_login:
            return self.login()

        # 尝试加载已保存的session
        if self.load_session() and self.verify_session():
            print("[INFO] 使用已保存的有效session")
            return True

        # 登录
        return self.login()

    def fetch_page(self, url):
        """获取页面内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            print(f"[ERROR] 获取页面失败: {url} - {e}")
            return None

    def download_file(self, url, output_path):
        """下载文件"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }

            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()

            with open(output_path, 'wb') as f:
                f.write(content)

            file_size = len(content) / 1024  # KB
            print(f"[SUCCESS] 下载完成: {output_path} ({file_size:.1f} KB)")
            return True

        except Exception as e:
            print(f"[ERROR] 下载失败: {url} - {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Redmine FAE文档中心认证工具')
    parser.add_argument('--login', action='store_true', help='强制登录')
    parser.add_argument('--verify', action='store_true', help='验证session是否有效')
    parser.add_argument('--test', action='store_true', help='测试访问受保护的页面')
    parser.add_argument('--clean', action='store_true', help='清理已保存的session')
    parser.add_argument('--info', action='store_true', help='显示配置信息')

    args = parser.parse_args()

    auth = RedmineAuth()

    if args.info:
        print("当前配置:")
        print(f"  服务器: {auth.base_url}")
        print(f"  用户名: {auth.username}")
        print(f"  Session文件: {auth.session_file}")
        return

    if args.clean:
        if os.path.exists(auth.session_file):
            os.remove(auth.session_file)
            print("[INFO] Session文件已清理")
        else:
            print("[INFO] 没有找到Session文件")
        return

    if args.verify:
        if auth.load_session():
            if auth.verify_session():
                print("[SUCCESS] Session有效")
            else:
                print("[WARN] Session无效")
        else:
            print("[INFO] 没有找到已保存的Session")
        return

    if args.test:
        if auth.ensure_authenticated():
            print("[SUCCESS] 认证成功!")

            # 测试访问FAE文档页面
            test_url = f"{auth.base_url}/projects/fae/documents"
            html = auth.fetch_page(test_url)

            if html:
                doc_count = len(re.findall(r'/documents/\d+', html))
                print(f"[SUCCESS] 成功访问FAE文档页面，发现 {doc_count} 个文档分类")
            else:
                print("[WARN] 访问FAE文档页面失败")
        else:
            print("[ERROR] 认证失败!")
        return

    # 默认行为：确保认证
    if auth.ensure_authenticated():
        print("\n[SUCCESS] 认证成功!")
        print("现在可以使用其他脚本访问FAE文档中心")
    else:
        print("\n[ERROR] 认证失败!")
        sys.exit(1)

if __name__ == '__main__':
    main()