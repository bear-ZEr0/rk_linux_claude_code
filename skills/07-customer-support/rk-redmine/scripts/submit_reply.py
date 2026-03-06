#!/usr/bin/env python3
"""
Redmine 回复提交脚本

用法:
  echo "回复内容" | python3 submit_reply.py <issue_id>
  python3 submit_reply.py <issue_id> --file reply.txt

注意: 安全确认由 Agent 在交互层面完成，脚本本身不做额外确认。
"""

import sys
import os
import json
import urllib.request
import urllib.error
import ssl
import argparse

# 加载配置
def load_config():
    """加载 Redmine 配置"""
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

# SSL 上下文（忽略自签名证书）
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def post_reply(issue_id: str, message: str, max_retries: int = 3) -> bool:
    """
    向 Redmine Issue 提交回复

    Args:
        issue_id: Issue ID
        message: 回复内容
        max_retries: 最大重试次数

    Returns:
        bool: 是否成功
    """
    url = f"{API_URL}/issues/{issue_id}.json"
    payload = {
        "issue": {
            "notes": message
        }
    }

    import time
    for attempt in range(max_retries):
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, method='PUT')
            req.add_header("X-Redmine-API-Key", API_KEY)
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "RK-Redmine-Skill/1.0")

            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                if response.status in (200, 204):
                    return True
                else:
                    print(f"❌ 提交失败，状态码: {response.status}")

        except urllib.error.HTTPError as e:
            if e.code == 500 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"⚠️ HTTP 500 错误，{wait_time}秒后重试... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ HTTP 错误 {e.code}: {e.reason}")

        except Exception as e:
            print(f"❌ 提交失败: {e}")

        return False

    return False


def main():
    parser = argparse.ArgumentParser(
        description="向 Redmine Issue 提交回复",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  echo "回复内容" | python3 submit_reply.py 39507
  python3 submit_reply.py 39507 --file reply.txt

注意: 安全确认由 Agent 在交互层面完成。
"""
    )

    parser.add_argument("issue_id", help="Redmine Issue ID")
    parser.add_argument("--file", "-f", help="从文件读取回复内容")

    args = parser.parse_args()

    # 读取回复内容
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ 文件不存在: {args.file}")
            sys.exit(1)
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    elif not sys.stdin.isatty():
        content = sys.stdin.read().strip()
    else:
        print("❌ 请通过 --file 参数或 stdin 提供回复内容")
        print("   示例: echo '回复内容' | python3 submit_reply.py 39507")
        sys.exit(1)

    if not content:
        print("❌ 回复内容不能为空")
        sys.exit(1)

    # 提交回复
    print(f"📤 正在提交回复到 Issue #{args.issue_id}...")
    if post_reply(args.issue_id, content):
        print(f"✅ 回复已成功提交!")
        print(f"   查看: https://redmine.rock-chips.com/issues/{args.issue_id}")
    else:
        print("❌ 提交失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
