#!/usr/bin/env python3
"""SDK 版本差异对比工具 - 比较 repo 管理的 SDK 前后版本变更"""
import argparse, json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

def run_cmd(cmd, cwd=None, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", -1

def get_repo_projects(sdk_path):
    out, rc = run_cmd("repo list", cwd=sdk_path)
    if rc != 0:
        print(f"错误: repo list 失败，确认 {sdk_path} 是 repo 目录"); sys.exit(1)
    projects = []
    for line in out.splitlines():
        if " : " in line:
            path, name = line.split(" : ", 1)
            projects.append({"path": path.strip(), "name": name.strip()})
    return projects

def get_heads(sdk_path, projects):
    heads = {}
    for p in projects:
        pp = os.path.join(sdk_path, p["path"])
        if not os.path.isdir(pp): continue
        out, rc = run_cmd("git rev-parse HEAD", cwd=pp)
        if rc == 0: heads[p["path"]] = {"name": p["name"], "head": out.strip()}
    return heads

def save_snapshot(sdk_path, heads, label=None):
    d = os.path.join(sdk_path, ".sdk-diff", "snapshots"); os.makedirs(d, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = os.path.join(d, f"snapshot_{ts}{'_'+label if label else ''}.json")
    with open(fp, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "label": label or ts,
                    "sdk_path": sdk_path, "heads": heads}, f, indent=2, ensure_ascii=False)
    print(f"快照已保存: {fp}"); return fp

def load_latest_snapshots(sdk_path, count=2):
    d = os.path.join(sdk_path, ".sdk-diff", "snapshots")
    if not os.path.isdir(d): return []
    files = sorted(Path(d).glob("snapshot_*.json"), reverse=True)
    return [json.load(open(f)) for f in files[:count]]

def compare_heads(sdk_path, old_heads, new_heads):
    changes = []
    for path, ni in new_heads.items():
        oi = old_heads.get(path)
        if not oi:
            changes.append({"path": path, "name": ni["name"], "type": "new", "commits": []}); continue
        if oi["head"] == ni["head"]: continue
        pp = os.path.join(sdk_path, path)
        if not os.path.isdir(pp): continue
        out, rc = run_cmd(f"git log --oneline --no-merges {oi['head']}..{ni['head']}", cwd=pp)
        commits = []
        if rc == 0 and out:
            for l in out.splitlines():
                p = l.split(" ", 1)
                if len(p) == 2: commits.append({"hash": p[0], "msg": p[1]})
        stat, _ = run_cmd(f"git diff --stat {oi['head']}..{ni['head']}", cwd=pp)
        changes.append({"path": path, "name": ni["name"], "type": "updated",
                        "old": oi["head"][:8], "new": ni["head"][:8],
                        "commits": commits, "stat": stat})
    for path in old_heads:
        if path not in new_heads:
            changes.append({"path": path, "name": old_heads[path]["name"], "type": "removed", "commits": []})
    return changes

def get_log_changes(sdk_path, projects, since, until=None):
    changes = []
    ua = f'--until="{until}"' if until else ""
    for p in projects:
        pp = os.path.join(sdk_path, p["path"])
        if not os.path.isdir(pp): continue
        out, rc = run_cmd(f'git log --oneline --no-merges --since="{since}" {ua}', cwd=pp)
        if rc != 0 or not out: continue
        commits = [{"hash": l.split(" ",1)[0], "msg": l.split(" ",1)[1]}
                   for l in out.splitlines() if " " in l]
        if commits:
            changes.append({"path": p["path"], "name": p["name"], "type": "log", "commits": commits})
    return changes

def generate_report(changes, title, sdk_path, save=True):
    if not changes:
        print(f"# {title}\n\n无变更。"); return
    lines = [f"# {title}\n", f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    total = sum(len(c["commits"]) for c in changes)
    updated = [c for c in changes if c["type"] in ("updated", "log")]
    lines.append(f"**变更概览**: {len(updated)} 个项目更新, {total} 个提交\n\n---\n")
    for c in changes:
        if not c["commits"] and c["type"] not in ("new", "removed"): continue
        lines.append(f"\n## {c['path']}")
        lines.append(f"**项目**: {c['name']}\n")
        if c["type"] == "new": lines.append("*新增项目*\n")
        elif c["type"] == "removed": lines.append("*已移除*\n")
        elif c.get("old"): lines.append(f"`{c['old']}` → `{c['new']}`\n")
        if c["commits"]:
            lines.append("| Commit | 说明 |")
            lines.append("|--------|------|")
            for cm in c["commits"]:
                lines.append(f"| `{cm['hash']}` | {cm['msg']} |")
        if c.get("stat"):
            lines.append(f"\n<details><summary>文件变更统计</summary>\n\n```\n{c['stat']}\n```\n</details>")
        lines.append("\n---")
    report = "\n".join(lines)
    print(report)
    if save:
        rd = os.path.join(sdk_path, ".sdk-diff", "reports"); os.makedirs(rd, exist_ok=True)
        rp = os.path.join(rd, f"diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(rp, "w") as f: f.write(report)
        print(f"\n报告已保存: {rp}")
    return report

def resolve_sdk_path(path_arg):
    if os.path.isdir(path_arg): return os.path.abspath(path_arg)
    for cp in [os.path.join(os.getcwd(), "settings.json"),
               os.path.expanduser("~/.openclaw/workspace/settings.json")]:
        if os.path.isfile(cp):
            with open(cp) as f: cfg = json.load(f)
            paths = cfg.get("sdk_diff", {}).get("sdk_paths", {})
            if path_arg in paths: return paths[path_arg]
    print(f"错误: 路径 {path_arg} 不存在"); sys.exit(1)

def cmd_snapshot(args):
    sp = resolve_sdk_path(args.sdk_path); projects = get_repo_projects(sp)
    heads = get_heads(sp, projects); save_snapshot(sp, heads, args.label)
    print(f"已记录 {len(heads)} 个项目的 HEAD")

def cmd_sync(args):
    sp = resolve_sdk_path(args.sdk_path); projects = get_repo_projects(sp)
    print("保存 sync 前快照..."); old = get_heads(sp, projects); save_snapshot(sp, old, "pre-sync")
    print("\n执行 repo sync..."); run_cmd("repo sync -c -j4 --no-tags", cwd=sp, timeout=600)
    projects = get_repo_projects(sp); new = get_heads(sp, projects); save_snapshot(sp, new, "post-sync")
    changes = compare_heads(sp, old, new)
    generate_report(changes, f"SDK 变更报告 - {os.path.basename(sp)} ({datetime.now().strftime('%Y-%m-%d')})", sp)

def cmd_diff(args):
    sp = resolve_sdk_path(args.sdk_path); snaps = load_latest_snapshots(sp, 2)
    if len(snaps) < 2: print("错误: 需要至少 2 个快照"); sys.exit(1)
    new_s, old_s = snaps[0], snaps[1]
    print(f"对比: {old_s['label']} → {new_s['label']}\n")
    changes = compare_heads(sp, old_s["heads"], new_s["heads"])
    generate_report(changes, f"SDK 变更报告 - {os.path.basename(sp)} ({old_s['label']} → {new_s['label']})", sp)

def cmd_log(args):
    sp = resolve_sdk_path(args.sdk_path); projects = get_repo_projects(sp)
    changes = get_log_changes(sp, projects, args.since, args.until)
    period = args.since + (f" ~ {args.until}" if args.until else "")
    generate_report(changes, f"SDK 变更日志 - {os.path.basename(sp)} ({period})", sp)

def cmd_list(args):
    sp = resolve_sdk_path(args.sdk_path)
    d = os.path.join(sp, ".sdk-diff", "snapshots")
    if not os.path.isdir(d): print("暂无快照"); return
    files = sorted(Path(d).glob("snapshot_*.json"), reverse=True)
    if not files: print("暂无快照"); return
    print(f"共 {len(files)} 个快照:\n")
    for f in files:
        data = json.load(open(f))
        print(f"  {f.name}  ({data.get('timestamp','?')})  {len(data.get('heads',{}))} 个项目")

def main():
    parser = argparse.ArgumentParser(description="SDK 版本差异对比工具")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("snapshot", help="保存当前 HEAD 快照")
    p.add_argument("sdk_path"); p.add_argument("--label")
    p = sub.add_parser("sync", help="repo sync 并对比变更")
    p.add_argument("sdk_path")
    p = sub.add_parser("diff", help="对比最近两次快照")
    p.add_argument("sdk_path")
    p = sub.add_parser("log", help="查看日期范围变更")
    p.add_argument("sdk_path"); p.add_argument("--since", required=True); p.add_argument("--until")
    p = sub.add_parser("list", help="列出所有快照")
    p.add_argument("sdk_path")
    args = parser.parse_args()
    {"snapshot": cmd_snapshot, "sync": cmd_sync, "diff": cmd_diff,
     "log": cmd_log, "list": cmd_list}[args.command](args)

if __name__ == "__main__":
    main()
