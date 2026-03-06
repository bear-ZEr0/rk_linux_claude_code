#!/usr/bin/env python3
"""
补丁简报搜索脚本 - 在rk-sdk补丁简报项目中搜索
用法: python3 search_patch_briefings.py <keyword> [--chip <chip>] [--component <module>] [--limit <n>]
"""

import sys
import urllib.request
import urllib.parse
import json
import ssl

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
API_URL = config.get("base_url", "https://10.10.10.70")
API_KEY = config.get("api_key", "")
PUBLIC_URL = "https://redmine.rock-chips.com"

# rk-sdk 项目标识符
RK_SDK_PROJECT = "rk-sdk"

# 创建SSL上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def search_patch_briefings(keyword, chip=None, component=None, limit=20):
    """在rk-sdk项目中搜索补丁简报"""
    
    # 构建搜索关键词
    search_terms = []
    if keyword:
        search_terms.append(keyword)
    if chip:
        search_terms.append(chip)
    if component:
        search_terms.append(component)
    
    if not search_terms:
        print("❌ 请提供搜索关键词或过滤条件")
        return []
    
    search_query = ' '.join(search_terms)
    encoded_query = urllib.parse.quote(search_query)
    
    print(f"在 rk-sdk 项目中搜索补丁简报: '{search_query}'")
    print("=" * 80)
    
    all_results = []
    seen_ids = set()
    offset = 0
    page_size = min(100, limit * 2)  # 获取更多结果以便过滤
    
    while len(all_results) < limit:
        # 使用Redmine搜索API，限定在rk-sdk项目中搜索
        url = f"{API_URL}/projects/{RK_SDK_PROJECT}/search.json?key={API_KEY}&q={encoded_query}&issues=1&limit={page_size}&offset={offset}"
        
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Redmine-API-Client/1.0")
            req.add_header("Accept", "application/json")
            
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if 'results' not in data or not data['results']:
                    break
                
                print(f"  找到 {len(data['results'])} 个搜索结果...")
                
                for result in data['results']:
                    # 只处理issue类型
                    if 'issue' not in result.get('type', ''):
                        continue
                    
                    # 检查标题是否包含"补丁简报"标识
                    title = result.get('title', '')
                    
                    # 从URL提取issue ID
                    issue_id = None
                    if 'issues/' in result.get('url', ''):
                        try:
                            issue_id = int(result['url'].split('issues/')[1].split('?')[0].split('#')[0])
                        except (ValueError, IndexError):
                            continue
                    
                    if not issue_id or issue_id in seen_ids:
                        continue
                    
                    seen_ids.add(issue_id)
                    
                    # 构建结果对象
                    issue_info = {
                        'id': issue_id,
                        'subject': title.replace('补丁简报 #%d: ' % issue_id, '').replace('补丁简报 #%d ' % issue_id, ''),
                        'title': title,
                        'description': result.get('description', ''),
                        'url': result.get('url', ''),
                        'updated_on': result.get('datetime', '')
                    }
                    
                    all_results.append(issue_info)
                    
                    if len(all_results) >= limit:
                        break
                
                if len(data['results']) < page_size:
                    break
                
                offset += page_size
                
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            break
    
    return all_results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='在rk-sdk项目中搜索补丁简报',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "PCIe"                    # 搜索PCIe相关补丁简报
  %(prog)s "HDMI" --chip RK3588      # 搜索RK3588 HDMI补丁
  %(prog)s "休眠唤醒"                  # 搜索休眠唤醒相关补丁
  %(prog)s "AIC" --limit 10          # 搜索AIC补丁，限制10条
        """
    )
    
    parser.add_argument('keyword', nargs='?', default='', help='搜索关键词')
    parser.add_argument('--chip', '-c', help='按芯片过滤 (RK3588, RK3576等)')
    parser.add_argument('--component', '-m', help='按模块过滤 (PCIe, HDMI, System等)')
    parser.add_argument('--limit', '-n', type=int, default=20, help='结果数量限制 (默认: 20)')
    
    args = parser.parse_args()
    
    if not args.keyword and not args.chip and not args.component:
        parser.print_help()
        print("\n⚠️  请提供搜索关键词或过滤条件")
        sys.exit(1)
    
    results = search_patch_briefings(
        args.keyword,
        chip=args.chip,
        component=args.component,
        limit=args.limit
    )
    
    if not results:
        print("\n❌ 未找到匹配的补丁简报")
        return
    
    print(f"\n找到 {len(results)} 个补丁简报:\n")
    
    for issue in results:
        issue_id = issue.get('id')
        subject = issue.get('subject', '')
        updated = issue.get('updated_on', '')[:10] if issue.get('updated_on') else ''
        desc = issue.get('description', '')[:80] + '...' if len(issue.get('description', '')) > 80 else issue.get('description', '')
        
        print(f"补丁简报 #{issue_id}: {subject}")
        if desc:
            print(f"    {desc}")
        print(f"    更新: {updated}")
        print(f"    链接: {PUBLIC_URL}/issues/{issue_id}")
        print("-" * 80)
    
    print(f"\n💡 使用 python3 scripts/get_patch_briefing.py <issue_id> 获取详情")


if __name__ == "__main__":
    main()
