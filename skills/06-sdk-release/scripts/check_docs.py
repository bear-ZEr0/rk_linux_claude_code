#!/usr/bin/env python3
"""PDF 文档版权关键字扫描

使用 pdfgrep 扫描指定目录中的 PDF 文件，检测版权敏感关键字。
结果保存到 results_<timestamp>.txt
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime

KEYWORDS = "ac3|eac3|atmos|truehd|true-hd|dts-hd|ddp|mlp|dolby|杜比"


def check_pdfgrep():
    """检查 pdfgrep 是否已安装"""
    if shutil.which("pdfgrep") is None:
        print("错误: pdfgrep 未安装", file=sys.stderr)
        print("安装方法:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt install pdfgrep", file=sys.stderr)
        print("  CentOS/RHEL:   sudo yum install pdfgrep", file=sys.stderr)
        print("  macOS:         brew install pdfgrep", file=sys.stderr)
        sys.exit(1)


def scan_pdfs(directory, keywords):
    """递归扫描目录中的 PDF 文件，返回匹配列表"""
    matches = []
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if not filename.lower().endswith(".pdf"):
                continue
            filepath = os.path.join(root, filename)
            try:
                result = subprocess.run(
                    ["pdfgrep", "-n", keywords, filepath],
                    capture_output=True, text=True, timeout=60
                )
                if result.stdout.strip():
                    matches.append((filepath, result.stdout.strip()))
            except subprocess.TimeoutExpired:
                print(f"警告: 扫描超时，跳过文件: {filepath}")
            except OSError as e:
                print(f"警告: 无法处理文件 {filepath}: {e}")
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="扫描 PDF 文档中的版权敏感关键字（依赖 pdfgrep）"
    )
    parser.add_argument("directory", help="要扫描的目录路径")
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}", file=sys.stderr)
        sys.exit(1)

    check_pdfgrep()

    print(f"正在扫描目录: {directory}")
    matches = scan_pdfs(directory, KEYWORDS)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    result_file = f"results_{timestamp}.txt"

    with open(result_file, "w", encoding="utf-8") as f:
        for filepath, output in matches:
            msg = f"注意:有版权问题, 匹配的文件: {filepath}"
            print(msg)
            print(output)
            f.write(f"{msg}\n")
            f.write(f"{output}\n")

    print(f"\n扫描完成，共发现 {len(matches)} 个文件包含敏感关键字")
    print(f"结果已保存到: {result_file}")


if __name__ == "__main__":
    main()
