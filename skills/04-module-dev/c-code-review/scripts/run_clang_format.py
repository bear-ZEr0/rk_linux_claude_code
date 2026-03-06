#!/usr/bin/env python3
"""clang-format 格式检查包装脚本

对 C/C++ 文件执行格式检查，输出不符合规范的位置。
支持 --fix 参数直接修复格式问题。
"""

import argparse
import difflib
import os
import shutil
import subprocess
import sys

# 脚本所在目录的 .clang-format 作为默认配置
DEFAULT_STYLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".clang-format")

C_EXTENSIONS = {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"}


def check_clang_format():
    """检查 clang-format 是否已安装"""
    if shutil.which("clang-format") is None:
        print("错误: clang-format 未安装", file=sys.stderr)
        print("", file=sys.stderr)
        print("安装方法:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt install clang-format",
              file=sys.stderr)
        print("  CentOS/RHEL:   sudo yum install clang-format",
              file=sys.stderr)
        print("  macOS:         brew install clang-format", file=sys.stderr)
        sys.exit(1)


def collect_files(path):
    """收集目标路径下的所有 C/C++ 文件"""
    if os.path.isfile(path):
        if os.path.splitext(path)[1] in C_EXTENSIONS:
            return [path]
        return []

    files = []
    for root, _dirs, names in os.walk(path):
        for name in sorted(names):
            if os.path.splitext(name)[1] in C_EXTENSIONS:
                files.append(os.path.join(root, name))
    return files


def get_formatted(filepath, style_path):
    """获取 clang-format 格式化后的内容"""
    cmd = ["clang-format", f"--style=file:{style_path}", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"警告: clang-format 处理 {filepath} 失败: {result.stderr}",
              file=sys.stderr)
        return None
    return result.stdout


def check_file(filepath, style_path):
    """检查单个文件的格式问题，返回差异列表"""
    formatted = get_formatted(filepath, style_path)
    if formatted is None:
        return []

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()

    if original == formatted:
        return []

    orig_lines = original.splitlines(keepends=True)
    fmt_lines = formatted.splitlines(keepends=True)
    diff = list(difflib.unified_diff(orig_lines, fmt_lines,
                                     fromfile=filepath, tofile=filepath))
    if not diff:
        return []

    # 解析 diff 提取行号和描述
    issues = []
    current_line = None
    for d in diff:
        if d.startswith("@@"):
            # 提取原文件行号 @@ -start,count +start,count @@
            parts = d.split()
            try:
                current_line = int(parts[1].split(",")[0].lstrip("-"))
            except (IndexError, ValueError):
                current_line = None
        elif d.startswith("-") and not d.startswith("---"):
            if current_line is not None:
                issues.append(current_line)
                current_line += 1
        elif d.startswith("+") and not d.startswith("+++"):
            pass  # 新增行不增加原文件行号
        else:
            if current_line is not None:
                current_line += 1

    # 合并连续行号为范围
    return merge_lines(filepath, issues)


def merge_lines(filepath, lines):
    """将连续行号合并为范围，返回 (file, range_str) 列表"""
    if not lines:
        return []
    lines = sorted(set(lines))
    ranges = []
    start = lines[0]
    end = lines[0]
    for ln in lines[1:]:
        if ln == end + 1:
            end = ln
        else:
            ranges.append((filepath, f"{start}-{end}" if start != end
                           else str(start)))
            start = ln
            end = ln
    ranges.append((filepath, f"{start}-{end}" if start != end
                   else str(start)))
    return ranges


def fix_file(filepath, style_path):
    """直接修复文件格式"""
    cmd = ["clang-format", "-i", f"--style=file:{style_path}", filepath]
    subprocess.run(cmd, capture_output=True, text=True)


def print_results(all_issues, output_file=None):
    """打印格式检查结果"""
    if not all_issues:
        output = "格式检查: 所有文件符合规范\n"
        print(output)
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)
        return

    files_with_issues = set(f for f, _ in all_issues)
    lines = []
    lines.append(f"格式检查: {len(files_with_issues)} 个文件有格式问题\n")
    for i, (filepath, line_range) in enumerate(all_issues, 1):
        lines.append(f"{i}. {filepath}:{line_range} — 格式不符合规范")
    lines.append(f"\n统计: {len(files_with_issues)} 个文件, "
                 f"{len(all_issues)} 处问题")

    output = "\n".join(lines)
    print(output)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"结果已保存到: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="clang-format 格式检查脚本，检查 C/C++ 代码是否符合团队规范"
    )
    parser.add_argument("path", help="要检查的文件或目录路径")
    parser.add_argument(
        "--fix", action="store_true",
        help="自动修复格式问题（执行 clang-format -i）"
    )
    parser.add_argument(
        "--style", default=None,
        help=f"clang-format 配置文件路径（默认: {DEFAULT_STYLE}）"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="输出文件路径（可选）"
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"错误: 路径不存在: {args.path}", file=sys.stderr)
        sys.exit(1)

    style_path = args.style or DEFAULT_STYLE
    if not os.path.exists(style_path):
        print(f"错误: 配置文件不存在: {style_path}", file=sys.stderr)
        sys.exit(1)

    check_clang_format()

    files = collect_files(args.path)
    if not files:
        print("未找到 C/C++ 文件")
        sys.exit(0)

    print(f"正在检查: {len(files)} 个文件")

    if args.fix:
        for filepath in files:
            fix_file(filepath, style_path)
        print(f"已修复 {len(files)} 个文件的格式")
        sys.exit(0)

    all_issues = []
    for filepath in files:
        issues = check_file(filepath, style_path)
        all_issues.extend(issues)

    print_results(all_issues, args.output)
    sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()
