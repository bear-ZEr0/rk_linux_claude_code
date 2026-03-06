#!/usr/bin/env python3
"""源代码版权关键字扫描

递归扫描指定目录中的文本文件，检测是否包含版权敏感关键字。
结果保存到 ./results/result_<timestamp>.txt
"""

import argparse
import os
import re
import sys
from datetime import datetime

KEYWORDS = (
    r"mlp_decode|ac3_decode|dcadec_decode_frame|latm_decode_frame|"
    r"fdk_aac_decode_frame|ff_mlp_encoder|ff_ac3_encoder|ff_eac3_encoder|"
    r"ff_dca_encoder|aac_encode_frame|ff_dolby_e_decoder|ff_truehd_encoder|"
    r"ff_truehd_decoder|ff_rv10_decoder|ff_rv20_decoder|ff_rv30_decoder|"
    r"ff_rv40_decoder|ff_vc1_decoder|dtsdec|dtshddec|dtshdaparse"
)

# 跳过的二进制文件扩展名
BINARY_EXTENSIONS = {
    ".o", ".so", ".a", ".bin", ".elf", ".hex", ".png", ".jpg", ".jpeg",
    ".gif", ".bmp", ".ico", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".pdf", ".pyc", ".class", ".exe", ".dll",
}


def is_text_file(filepath):
    """判断文件是否为文本文件"""
    _, ext = os.path.splitext(filepath)
    if ext.lower() in BINARY_EXTENSIONS:
        return False
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" not in chunk
    except (OSError, PermissionError):
        return False


def scan_directory(directory, pattern):
    """递归扫描目录，返回匹配列表 [(filepath, line_no, line_text), ...]"""
    matches = []
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not is_text_file(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_no, line in enumerate(f, 1):
                        if pattern.search(line):
                            matches.append((filepath, line_no, line.rstrip()))
            except (OSError, PermissionError):
                continue
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="扫描源代码中的版权敏感关键字"
    )
    parser.add_argument("directory", help="要扫描的目录路径")
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(KEYWORDS)

    print(f"正在扫描目录: {directory}")
    matches = scan_directory(directory, pattern)

    # 保存结果
    result_dir = "./results"
    os.makedirs(result_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    result_file = os.path.join(result_dir, f"result_{timestamp}.txt")

    with open(result_file, "w", encoding="utf-8") as f:
        for filepath, line_no, line_text in matches:
            msg = f"注意:可能有版权风险!!! 匹配的文件: {filepath}, 行号: {line_no}"
            print(msg)
            print(f"匹配的文本: {line_text}")
            f.write(f"{msg}\n")
            f.write(f"匹配的文本: {line_text}\n")

    print(f"\n扫描完成，共发现 {len(matches)} 处匹配")
    print(f"结果已保存到: {result_file}")


if __name__ == "__main__":
    main()
