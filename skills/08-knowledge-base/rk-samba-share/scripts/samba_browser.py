#!/usr/bin/env python3
"""
Samba Browser - 浏览、搜索和下载 Rockchip 内网 Samba 共享文件

用法:
    python3 samba_browser.py --shares                           # 列出所有共享
    python3 samba_browser.py --list <share> [path]              # 列出目录内容
    python3 samba_browser.py --search <keyword> --share <share> [--path <path>] [--max-depth N]  # 搜索文件
    python3 samba_browser.py --download <share> <remote_path>   # 下载文件或目录
"""
import argparse
import hashlib
import subprocess
import os
import sys
import shutil
import tempfile
import time
import zipfile
import tarfile
import re

# 配置
SMB_HOST = "10.10.10.164"
CREDENTIALS = "rkguest%rk839919"

# 所有可用的共享
SHARES = {
    # Android SDK 按版本
    "Q_Repository": "Android 10 SDK (RK3126C~RK3399)",
    "R_Repository": "Android 11 SDK (RK3326~RK3588)",
    "S_Repository": "Android 12 SDK (RK3326~RK3588)",
    "S_Repository_sys2": "Android 12 SDK (备份)",
    "T_Repository": "Android 13 SDK (RK3326~RK3588)",
    "U_Repository": "Android 14 SDK (RK3576/RK3588/RK356X)",
    "V_Repository": "Android 15 SDK (RK3576/RK3588/RK356X)",
    "Pie_Repository": "Android 9 SDK (PX30~RK3399Pro)",
    "Oreo_Repository": "Android 8 SDK (RK312X~RK3399)",
    "Nougat_Repository": "Android 7 SDK (RK3128~RK3399)",
    "Marshmallow_Repository": "Android 6 SDK",
    "Lollipop_Repository": "Android 5 SDK",
    "Kitkat_Repository": "Android 4.4 SDK",

    # 其他重要存储
    "Linux_Repository": "Linux SDK、固件、AI/LLM、发行版",
    "Common_Repository": "通用资源、RKNN工具包、SDK存档、测试资料",
    "TOOLS_Repository": "开发工具 (Windows/Linux/Mac)",
    "WIFI_BT_Repository": "WiFi/BT驱动 (Broadcom/Realtek/MTK等)",
    "RTOS_Repository": "RTOS SDK (RK2106~RK3588 AMP)",
    "SoCs_Repository": "特殊芯片 (RK628/RK630/RK621)",
    "New_SDK": "新SDK发布",
    "Android": "Android杂项",
    "home": "用户目录",
    "rk1108": "RK1108专用",
    "slt": "SLT测试",
    "RD_Dep1_Repository": "研发一部资源",
}

def run_smb_command(share, command, timeout=60):
    """执行 smbclient 命令"""
    full_cmd = [
        "smbclient",
        f"//{SMB_HOST}/{share}",
        "-U", CREDENTIALS,
        "-c", command
    ]

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"错误: 命令超时 ({timeout}s)", file=sys.stderr)
        return None
    except Exception as e:
        print(f"错误: 执行 smbclient 失败: {e}", file=sys.stderr)
        return None

def parse_ls_output(output):
    """解析 smbclient ls 输出

    smbclient ls 格式示例:
      filename                          D        0  Thu Jan 22 14:35:53 2026
      Qwen2.5-7B.embed.bin              N 1089994752  Thu Jan 22 14:35:53 2026

    属性字段 (D/N/A/H/S/R) 和文件大小之间只有单个空格，
    需要用正则精确匹配而非简单分割。
    """
    files = []
    # 匹配: 文件名(2+空格)属性(1+空格)大小(2+空格)日期
    pattern = re.compile(
        r'^(.+?)\s{2,}([DNAHSR]+)\s+(\d+)\s{2,}(.+)$'
    )

    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Domain=") or "blocks of size" in line:
            continue

        m = pattern.match(line)
        if not m:
            continue

        name = m.group(1).strip()
        attrs = m.group(2)
        size = int(m.group(3))

        if name in (".", ".."):
            continue

        # 跳过隐藏文件和临时文件
        if name.startswith(".") or name.endswith(".tmp") or name.endswith(".lnk"):
            continue

        is_dir = 'D' in attrs

        files.append({
            'name': name,
            'is_dir': is_dir,
            'size': size
        })

    return files

def list_shares():
    """列出所有可用共享"""
    print("=== 可用的 Samba 共享 ===\n")

    # Android SDK
    print("【Android SDK (按版本)】")
    android_shares = ["V_Repository", "U_Repository", "T_Repository", "S_Repository",
                      "R_Repository", "Q_Repository", "Pie_Repository", "Oreo_Repository",
                      "Nougat_Repository"]
    for share in android_shares:
        if share in SHARES:
            print(f"  {share:25} - {SHARES[share]}")

    print("\n【通用资源】")
    common_shares = ["Linux_Repository", "Common_Repository", "TOOLS_Repository",
                     "WIFI_BT_Repository", "RTOS_Repository", "SoCs_Repository"]
    for share in common_shares:
        if share in SHARES:
            print(f"  {share:25} - {SHARES[share]}")

    print("\n【其他】")
    other_shares = [s for s in SHARES if s not in android_shares and s not in common_shares]
    for share in sorted(other_shares):
        print(f"  {share:25} - {SHARES[share]}")

def list_directory(share, path=""):
    """列出目录内容"""
    if path:
        cmd = f'cd "{path}"; ls'
    else:
        cmd = 'ls'

    result = run_smb_command(share, cmd)
    if not result or result.returncode != 0:
        error_msg = result.stderr if result else "未知错误"
        print(f"错误: 无法列出目录 - {error_msg}", file=sys.stderr)
        return []

    files = parse_ls_output(result.stdout)

    if files:
        path_display = path if path else "/"
        print(f"\n=== {share}/{path_display} ===\n")

        # 先显示目录
        dirs = sorted([f for f in files if f['is_dir']], key=lambda x: x['name'].lower())
        regular_files = sorted([f for f in files if not f['is_dir']], key=lambda x: x['name'].lower())

        for f in dirs:
            print(f"  [DIR]  {f['name']}/")

        for f in regular_files:
            size_str = format_size(f['size'])
            print(f"  {size_str:>10}  {f['name']}")

        print(f"\n共 {len(dirs)} 个目录, {len(regular_files)} 个文件")
    else:
        print("目录为空或不存在")

    return files

def format_size(size):
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/(1024*1024):.1f} MB"
    else:
        return f"{size/(1024*1024*1024):.1f} GB"

def search_files(keyword, share=None, path="", max_depth=2):
    """在共享中搜索文件

    Args:
        keyword: 搜索关键词
        share: 指定共享（必须指定）
        path: 起始路径，如 "RK_SDK" 或 "RK356X/云终端/云终端补丁集"
        max_depth: 最大搜索深度
    """
    if not share:
        print("错误: 必须指定 --share 参数", file=sys.stderr)
        return []

    results = []

    print(f"搜索关键词: '{keyword}'")
    print(f"搜索范围: {share}/{path if path else ''}")
    print(f"搜索深度: {max_depth}")
    print("")

    _search_recursive(share, path, keyword, results, 0, max_depth)

    if results:
        print(f"\n=== 找到 {len(results)} 个匹配结果 ===\n")
        for r in results:
            type_mark = "[DIR]" if r['is_dir'] else "[FILE]"
            print(f"{type_mark} //{SMB_HOST}/{r['share']}/{r['path']}")
    else:
        print("未找到匹配结果")

    return results

def _search_recursive(share, path, keyword, results, depth, max_depth):
    """递归搜索"""
    if depth > max_depth:
        return

    if path:
        cmd = f'cd "{path}"; ls'
    else:
        cmd = 'ls'

    result = run_smb_command(share, cmd)
    if not result or result.returncode != 0:
        return

    files = parse_ls_output(result.stdout)

    for f in files:
        name = f['name']
        full_path = f"{path}/{name}" if path else name

        # 检查是否匹配
        if keyword.lower() in name.lower():
            results.append({
                'share': share,
                'path': full_path,
                'name': name,
                'is_dir': f['is_dir']
            })

        # 递归搜索子目录
        if f['is_dir'] and depth < max_depth:
            _search_recursive(share, full_path, keyword, results, depth + 1, max_depth)

# ============== 校验辅助函数 ==============

def calculate_local_md5(filepath):
    """计算本地文件的 MD5 值"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def get_remote_md5(share, remote_path):
    """获取远程文件的 MD5（通过临时文件下载计算）"""
    parent_path = os.path.dirname(remote_path)
    filename = os.path.basename(remote_path.rstrip('/'))

    with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
        tmp_path = tmp.name

    try:
        if parent_path:
            cmd = f'cd "{parent_path}"; get "{filename}" "{tmp_path}"'
        else:
            cmd = f'get "{filename}" "{tmp_path}"'

        # 大文件需要更长超时
        result = run_smb_command(share, cmd, timeout=1800)

        if result and result.returncode == 0 and os.path.exists(tmp_path):
            file_size = os.path.getsize(tmp_path)
            if file_size > 0:
                return calculate_local_md5(tmp_path)
        print(f"  警告: 无法获取远程文件 MD5", file=sys.stderr)
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ============== 下载函数 ==============

def download_file_raw(share, remote_path, dest_dir="."):
    """下载单个文件（不带校验的原始下载）

    Returns:
        下载成功返回本地文件路径，失败返回 None
    """
    filename = os.path.basename(remote_path.rstrip('/'))
    parent_path = os.path.dirname(remote_path)

    if parent_path:
        cmd = f'cd "{parent_path}"; prompt OFF; get "{filename}"'
    else:
        cmd = f'prompt OFF; get "{filename}"'

    full_cmd = [
        "smbclient",
        f"//{SMB_HOST}/{share}",
        "-U", CREDENTIALS,
        "-c", cmd
    ]

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            cwd=dest_dir,
            timeout=1800  # 30 分钟，支持大文件
        )
        if result.returncode == 0:
            local_file = os.path.join(dest_dir, filename)
            if os.path.exists(local_file):
                return local_file
            else:
                print(f"下载异常: smbclient 返回成功但文件不存在")
                return None
        else:
            print(f"下载失败: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"下载超时 (1800s)")
        return None
    except Exception as e:
        print(f"下载错误: {e}")
        return None


def download_file(share, remote_path, dest_dir=".", max_retries=3):
    """下载文件或目录（带大小+MD5校验和重试）"""
    filename = os.path.basename(remote_path.rstrip('/'))
    parent_path = os.path.dirname(remote_path)

    # 检查是文件还是目录
    if parent_path:
        cmd = f'cd "{parent_path}"; ls'
    else:
        cmd = 'ls'

    result = run_smb_command(share, cmd)
    if not result or result.returncode != 0:
        print(f"错误: 无法访问路径 - {result.stderr if result else '未知错误'}")
        return None

    files = parse_ls_output(result.stdout)
    target = next((f for f in files if f['name'] == filename), None)

    if not target:
        print(f"错误: 找不到 '{filename}'")
        return None

    # 目录下载：打包为 tar，不做 MD5 校验
    if target['is_dir']:
        print(f"下载目录: {remote_path} (打包为 tar)")
        local_tar = os.path.join(dest_dir, f"{filename}.tar")

        full_cmd = [
            "smbclient",
            f"//{SMB_HOST}/{share}",
            "-U", CREDENTIALS,
            "-D", parent_path if parent_path else "",
            "-Tc", local_tar,
            filename
        ]

        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=1800)
            if result.returncode == 0:
                print(f"下载成功: {local_tar}")
                return local_tar
            else:
                print(f"下载失败: {result.stderr}")
                return None
        except Exception as e:
            print(f"下载错误: {e}")
            return None

    # 文件下载：带大小 + MD5 校验
    remote_size = target['size']
    print(f"下载文件: {remote_path}")
    print(f"  远程文件大小: {format_size(remote_size)} ({remote_size} bytes)")

    local_file = os.path.join(dest_dir, filename)

    for attempt in range(1, max_retries + 1):
        print(f"\n[尝试 {attempt}/{max_retries}] 下载中...")

        # 删除可能存在的残留文件
        if os.path.exists(local_file):
            os.remove(local_file)

        downloaded = download_file_raw(share, remote_path, dest_dir)
        if not downloaded or not os.path.exists(downloaded):
            if attempt < max_retries:
                print(f"  ✗ 下载失败，2秒后重试...")
                time.sleep(2)
            continue

        # 校验文件大小
        local_size = os.path.getsize(downloaded)
        print(f"  本地文件大小: {format_size(local_size)} ({local_size} bytes)")

        if remote_size is not None and local_size != remote_size:
            print(f"  ✗ 大小不匹配! 远程: {remote_size}, 本地: {local_size}")
            os.remove(downloaded)
            if attempt < max_retries:
                print(f"  大小校验失败，2秒后重试...")
                time.sleep(2)
            continue

        print(f"  ✓ 大小校验通过")

        # 大小匹配后，获取远程 MD5 进行二次校验
        # 延迟到此处避免提前多下载一次完整文件
        print(f"  计算远程文件 MD5...")
        remote_md5 = get_remote_md5(share, remote_path)
        if remote_md5:
            print(f"  远程文件 MD5:  {remote_md5}")
            local_md5 = calculate_local_md5(downloaded)
            print(f"  本地文件 MD5:  {local_md5}")
            if local_md5 != remote_md5:
                print(f"  ✗ MD5 不匹配! 远程: {remote_md5}, 本地: {local_md5}")
                os.remove(downloaded)
                if attempt < max_retries:
                    print(f"  MD5 校验失败，2秒后重试...")
                    time.sleep(2)
                continue
            print(f"  ✓ MD5 校验通过")
        else:
            print("  警告: 无法获取远程 MD5，跳过 MD5 校验")

        print(f"\n✓ 下载完成: {downloaded}")
        return downloaded

    print(f"\n✗ 下载失败，已尝试 {max_retries} 次")
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Rockchip Samba 共享浏览器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s --shares                           # 列出所有共享
    %(prog)s --list Linux_Repository            # 列出 Linux_Repository 根目录
    %(prog)s --list Linux_Repository RK3588     # 列出 Linux_Repository/RK3588
    %(prog)s --search rknn --share Common_Repository                    # 在共享根目录搜索
    %(prog)s --search RK3588 --share Common_Repository --path RK_SDK    # 在指定路径下搜索（更快）
    %(prog)s --download TOOLS_Repository windows/android_tool           # 下载目录
        """
    )

    parser.add_argument("--shares", action="store_true", help="列出所有可用共享")
    parser.add_argument("--list", nargs='+', metavar=('SHARE', 'PATH'), help="列出目录内容")
    parser.add_argument("--search", type=str, help="搜索关键词")
    parser.add_argument("--share", type=str, help="指定搜索的共享（必须）")
    parser.add_argument("--path", type=str, default="", help="指定搜索起始路径，如 RK_SDK 或 RK356X/云终端")
    parser.add_argument("--max-depth", type=int, default=2, help="搜索最大深度 (默认: 2)")
    parser.add_argument("--download", nargs=2, metavar=('SHARE', 'PATH'), help="下载文件或目录")

    args = parser.parse_args()

    if args.shares:
        list_shares()
    elif args.list:
        share = args.list[0]
        path = args.list[1] if len(args.list) > 1 else ""
        list_directory(share, path)
    elif args.search:
        search_files(args.search, args.share, args.path, args.max_depth)
    elif args.download:
        share, path = args.download
        download_file(share, path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

