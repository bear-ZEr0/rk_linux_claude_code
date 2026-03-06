#!/usr/bin/env python3
"""
运营商SDK问题搜索脚本 - 在运营商相关项目中快速搜索
用法: python3 search_operator_issues.py <keyword> [--project <project>] [--limit <n>]
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

# 运营商相关项目
OPERATOR_PROJECTS = {
    'all': 'rk_sdk_display_issues_sets',  # 主项目，包含所有子项目
    'hdmi': 'hdmi',                        # 1178 - HDMI 相关
    'framework': 'op-framework',           # 1186 - Framework
    'network': 'network-op',               # 1187 - WiFi/BT/网络
    'camera': 'camera-op',                 # 1188 - Camera
    'media': 'media-op',                   # 1189 - 媒体编解码
    'audio': 'audio-op',                   # 1190 - 音频
    'kernel': 'uboot-kernel-op',           # 1191 - 底层uboot/内核
}

# 创建SSL上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def search_operator_issues(keyword, project='all', limit=20):
    """在运营商项目中搜索问题"""
    
    # 获取项目标识符
    project_id = OPERATOR_PROJECTS.get(project.lower(), OPERATOR_PROJECTS['all'])
    
    if not keyword:
        print("❌ 请提供搜索关键词")
        return []
    
    encoded_query = urllib.parse.quote(keyword)
    
    print(f"在运营商项目 [{project}] 中搜索: '{keyword}'")
    print("=" * 80)
    
    all_results = []
    seen_ids = set()
    offset = 0
    page_size = min(100, limit * 2)
    
    while len(all_results) < limit:
        # 使用Redmine搜索API，限定在项目中搜索
        url = f"{API_URL}/projects/{project_id}/search.json?key={API_KEY}&q={encoded_query}&issues=1&limit={page_size}&offset={offset}"
        
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
                    if 'issue' not in result.get('type', ''):
                        continue
                    
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
                    
                    issue_info = {
                        'id': issue_id,
                        'title': result.get('title', ''),
                        'description': result.get('description', ''),
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
        description='在运营商SDK项目中搜索问题',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "HDMI"                    # 在所有运营商项目中搜索HDMI
  %(prog)s "绿屏" --project hdmi     # 只在HDMI项目中搜索
  %(prog)s "wifi" --project network  # 在网络项目中搜索
  %(prog)s "编码" --project media    # 在媒体项目中搜索

可用项目:
  all       - 所有运营商项目 (默认)
  hdmi      - HDMI 相关问题
  framework - Framework 相关问题
  network   - WiFi/蓝牙/网络
  camera    - Camera 相关问题
  media     - 媒体编解码
  audio     - 音频相关问题
  kernel    - 底层 uboot/内核
        """
    )
    
    parser.add_argument('keyword', help='搜索关键词')
    parser.add_argument('--project', '-p', default='all', 
                       choices=['all', 'hdmi', 'framework', 'network', 'camera', 'media', 'audio', 'kernel'],
                       help='指定项目 (默认: all)')
    parser.add_argument('--limit', '-n', type=int, default=20, help='结果数量限制 (默认: 20)')
    
    args = parser.parse_args()
    
    results = search_operator_issues(args.keyword, args.project, args.limit)
    
    if not results:
        print("\n❌ 未找到匹配的问题")
        return
    
    print(f"\n找到 {len(results)} 个问题:\n")
    
    for issue in results:
        issue_id = issue.get('id')
        title = issue.get('title', '')
        updated = issue.get('updated_on', '')[:10] if issue.get('updated_on') else ''
        desc = issue.get('description', '')
        if len(desc) > 80:
            desc = desc[:80] + '...'
        
        print(f"#{issue_id}: {title}")
        if desc:
            print(f"    {desc}")
        print(f"    更新: {updated}")
        print(f"    链接: {PUBLIC_URL}/issues/{issue_id}")
        print("-" * 80)
    
    print(f"\n💡 使用 python3 scripts/get_issue_info.py <issue_id> 获取详情")


if __name__ == "__main__":
    main()
