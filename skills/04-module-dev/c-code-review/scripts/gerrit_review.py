#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerrit Code Review 辅助脚本
- get-diff: 获取 Change 最新 patchset 的 diff
- submit-review: 提交审核结论到 Gerrit
"""

import argparse
import sys
from pathlib import Path
import io

# Fix encoding issues on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def _import_gerrit():
    """动态导入 rk-gerrit 客户端"""
    scripts = Path(__file__).resolve().parent.parent.parent.parent / "99-common-tools" / "rk-gerrit" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import gerrit_client
    return gerrit_client


def get_change_diff(change_id):
    """获取 Change 最新 patchset 的 diff"""
    gerrit = _import_gerrit()
    meta, diff_content = gerrit.get_change_diff(change_id)

    if meta is None:
        print(f"错误: 未找到 Change {change_id}", file=sys.stderr)
        sys.exit(1)

    print(f"## Gerrit Change {meta['number']} — Patch Set {meta['patch_set']}")
    print(f"- Subject: {meta['subject']}")
    print(f"- Project: {meta['project']}")
    print(f"- Branch: {meta['branch']}")
    print(f"- Owner: {meta['owner']}")
    print(f"- Revision: {meta['revision']}")
    print()
    print("## Diff")
    print()
    print(diff_content)


def submit_review(change_id, message, score):
    """提交审核结论到 Gerrit"""
    gerrit = _import_gerrit()
    success = gerrit.submit_review(change_id, score, message)
    if not success:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Gerrit Code Review 辅助工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_diff = subparsers.add_parser("get-diff", help="获取 Change 的 diff")
    p_diff.add_argument("change_id", help="Gerrit Change 编号或 Change-Id")

    p_review = subparsers.add_parser("submit-review", help="提交审核结论")
    p_review.add_argument("change_id", help="Gerrit Change 编号或 Change-Id")
    p_review.add_argument("--score", required=True, help="打分: +1 或 -1")
    p_review.add_argument("--message", required=True, help="审核报告内容")

    args = parser.parse_args()

    if args.command == "get-diff":
        get_change_diff(args.change_id)
    elif args.command == "submit-review":
        submit_review(args.change_id, args.message, args.score)


if __name__ == "__main__":
    main()
