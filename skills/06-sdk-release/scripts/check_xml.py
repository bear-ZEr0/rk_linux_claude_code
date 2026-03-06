#!/usr/bin/env python3
"""Git 历史二进制文件版权检查

检查 repo manifests 的 git 历史中，各版本的二进制文件（libffmpeg*.so）
是否包含版权敏感字符串。
结果保存到 sensitive_strings_found.txt
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

SENSITIVE_STRINGS = (
    r"mlp_decode|mlp_encode|ac3_decode|ac3_encode|dcadec|dca_decode|"
    r"dca_encode|dolby_e_decode|dolby_e_encode|truehd_decode|truehd_encode|ff_rv1"
)


def check_dependencies():
    """检查必要的命令行工具"""
    missing = []
    for cmd in ["git", "strings"]:
        if shutil.which(cmd) is None:
            missing.append(cmd)
    if missing:
        print(f"错误: 缺少必要工具: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def run_cmd(cmd, cwd=None, timeout=300):
    """执行命令并返回输出"""
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
    )
    return result.stdout.strip(), result.returncode


def get_git_log(manifest_file, cwd):
    """获取 manifest 文件的 git 提交历史"""
    cmd = [
        "git", "log", "--since=2020-01-01",
        "--pretty=format:%H %ad %s", "--date=short", manifest_file
    ]
    output, rc = run_cmd(cmd, cwd=cwd)
    if rc != 0 or not output:
        return []
    commits = []
    for line in output.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2:
            commits.append({
                "hash": parts[0],
                "date": parts[1],
                "message": parts[2] if len(parts) > 2 else "",
            })
    return commits


def find_so_files(sdk_dir):
    """查找 libffmpeg*.so 文件"""
    so_files = []
    for root, _dirs, files in os.walk(sdk_dir):
        for f in files:
            if f.startswith("libffmpeg") and f.endswith(".so"):
                so_files.append(os.path.join(root, f))
    return so_files


def check_so_file(filepath, pattern):
    """检查 .so 文件是否包含敏感字符串"""
    try:
        output, _ = run_cmd(["strings", filepath])
        return pattern.findall(output)
    except (subprocess.TimeoutExpired, OSError):
        return []


def main():
    parser = argparse.ArgumentParser(
        description="检查 Git 历史中二进制文件的版权敏感字符串（依赖 git, strings）"
    )
    parser.add_argument("manifest_file", help="manifest 文件名（如 default.xml）")
    parser.add_argument(
        "--sdk-dir", default=os.getcwd(),
        help="SDK 根目录（默认当前目录）"
    )
    args = parser.parse_args()

    check_dependencies()

    sdk_dir = os.path.abspath(args.sdk_dir)
    manifest_dir = os.path.join(sdk_dir, ".repo", "manifests")

    if not os.path.isdir(manifest_dir):
        print(f"错误: manifest 目录不存在: {manifest_dir}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(SENSITIVE_STRINGS)
    result_file = os.path.join(sdk_dir, "sensitive_strings_found.txt")

    # 获取 git 历史
    commits = get_git_log(args.manifest_file, cwd=manifest_dir)
    if not commits:
        print("没有找到符合条件的提交记录")
        sys.exit(1)

    print(f"找到 {len(commits)} 条提交记录")
    results = []

    for commit in commits:
        commit_hash = commit["hash"]
        print(f"\n检查提交: {commit_hash} {commit['date']} {commit['message']}")

        # checkout manifest 版本
        run_cmd(["git", "checkout", commit_hash], cwd=manifest_dir)

        # repo sync
        sync_out, sync_rc = run_cmd(
            [".repo/repo/repo", "sync", "-c", "--no-tags"],
            cwd=sdk_dir, timeout=600
        )
        if sync_rc != 0:
            print(f"  警告: repo sync 失败，跳过此提交")
            continue

        # 查找并检查 .so 文件
        so_files = find_so_files(sdk_dir)
        for so_file in so_files:
            print(f"  检查文件: {so_file}")
            matched = check_so_file(so_file, pattern)
            if matched:
                unique = sorted(set(matched))
                entry = f"manifests commit: {commit_hash} ; - {so_file} 包含敏感字符串: {', '.join(unique)}"
                print(f"  {entry}")
                results.append(entry)

    # 写入结果
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"
    if results:
        print(f"\n{RED}扫描结束，【警告】以下 manifest 提交信息包含版权信息：{RESET}")
        for line in results:
            print(f"  {line}")
    else:
        print(f"\n{GREEN}扫描结束，未找到包含版权信息的文件，恭喜~{RESET}")

    print(f"结果已保存到: {result_file}")


if __name__ == "__main__":
    main()
