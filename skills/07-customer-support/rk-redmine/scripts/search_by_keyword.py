#!/usr/bin/env python3
"""
Redmine智能关键词搜索脚本
支持多关键词搜索，模拟网页搜索行为
用法: python3 search_by_keyword.py "关键词1 关键词2" 项目ID 限制数量
"""

import urllib.request
import urllib.parse
import json
import ssl
import sys
import re

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
BASE_URL = config.get("base_url", "https://10.10.10.70")
API_KEY = config.get("api_key", "")

# 创建SSL上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def search_simple(keywords_str, limit=1000):
    """使用Redmine官方搜索API进行简单全文搜索"""
    if not keywords_str.strip():
        print("错误: 未提供有效关键词")
        return []

    print(f"搜索关键词: '{keywords_str}'")
    print(f"限制数量: {limit}")
    print("=" * 80)

    all_results = []
    seen_ids = set()
    offset = 0
    page_size = min(100, limit)  # Redmine API单页最大100条
    total_fetched = 0

    # URL编码搜索关键词
    encoded_query = urllib.parse.quote(keywords_str.strip())

    print(f"开始搜索...")

    while total_fetched < limit:
        current_limit = min(page_size, limit - total_fetched)

        # 构建搜索URL - 使用Redmine官方搜索API
        url = f"{BASE_URL}/search.json?key={API_KEY}&q={encoded_query}&issues=1&limit={current_limit}&offset={offset}"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))

                if 'results' in data and data['results']:
                    page_results = data['results']
                    print(f"  第{offset//page_size + 1}页: 找到 {len(page_results)} 个结果")

                    for result in page_results:
                        if ('issue' in result['type'] or 'support' in result['type']) and result['id'] not in seen_ids:
                            # 解析issue ID并获取详细信息
                            issue_id = result['id']

                            # 从URL中提取issue ID
                            if 'issues/' in result['url']:
                                try:
                                    issue_id = int(result['url'].split('issues/')[1].split('?')[0].split('#')[0])
                                except (ValueError, IndexError):
                                    pass

                            # 如果能解析出有效的issue ID，获取详细信息
                            if isinstance(issue_id, int) and issue_id > 0:
                                try:
                                    # 获取issue详细信息
                                    detail_url = f"{BASE_URL}/issues/{issue_id}.json?key={API_KEY}&include=journals"
                                    detail_req = urllib.request.Request(detail_url)
                                    detail_req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")

                                    with urllib.request.urlopen(detail_req, context=ctx, timeout=30) as detail_response:
                                        detail_data = json.loads(detail_response.read().decode('utf-8'))
                                        if 'issue' in detail_data:
                                            issue = detail_data['issue']
                                            issue['search_result'] = result  # 保留搜索结果信息
                                            all_results.append(issue)
                                            seen_ids.add(issue_id)

                                            print(f"    ✅ #{issue_id}: {issue['subject'][:60]}{'...' if len(issue['subject']) > 60 else ''} ({issue['status']['name']})")

                                except Exception as detail_e:
                                    # 如果获取详情失败，使用搜索结果的基本信息
                                    issue = {
                                        'id': issue_id,
                                        'subject': result['title'],
                                        'status': {'name': 'Unknown'},
                                        'project': {'name': 'Unknown'},
                                        'search_result': result
                                    }
                                    all_results.append(issue)
                                    seen_ids.add(issue_id)
                                    print(f"    ⚠️  #{issue_id}: {result['title'][:60]}{'...' if len(result['title']) > 60 else ''} (详情获取失败)")

                    total_fetched += len(page_results)

                    # 如果本页结果少于请求的数量，说明已经到最后一页
                    if len(page_results) < current_limit:
                        print(f"  搜索完成，已获取所有可用的结果")
                        break

                    offset += len(page_results)

                else:
                    print(f"  没有找到更多结果")
                    break

        except Exception as e:
            print(f"  搜索失败: {e}")
            break

    print(f"\n搜索完成！总共找到 {len(all_results)} 个结果")
    return all_results

# 主程序逻辑
if __name__ == "__main__":
    # 从命令行参数或默认值获取搜索参数
    if len(sys.argv) >= 2:
        keywords_str = sys.argv[1]
        if len(sys.argv) >= 3:
            limit = int(sys.argv[2])
        else:
            limit = 1000
    else:
        # 默认值 - 搜索关键词
        keywords_str = "3128 7.1"
        limit = 1000

    print(f"开始搜索: '{keywords_str}'")
    print()

    # 使用简单的Redmine官方搜索API
    results = search_simple(keywords_str, limit)

    print("\n" + "=" * 80)
    print(f"搜索找到 {len(results)} 个相关issue")
    print("使用 search_by_id.py <issue_id> 查询具体issue的详细信息")

    # 按更新时间排序结果
    if results:
        print("\n📋 按更新时间排序的结果:")
        for issue in sorted(results, key=lambda x: x.get('updated_on', ''), reverse=True):
            print(f"  #{issue['id']}: {issue['subject']} ({issue['status']['name']})")
