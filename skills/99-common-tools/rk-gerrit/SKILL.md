---
name: rk-gerrit
description: Gerrit 客户端 - 优先 SSH 方式，统一认证、查询、操作接口
---

# Gerrit 客户端

## 何时激活

- 需要查询 Gerrit 提交记录
- 需要获取 Change diff 或详情
- 需要获取/提交 Code-Review 评论
- 需要统计代码提交数据

## 配置 (settings.json)

```json
{
  "gerrit": {
    "url": "https://10.10.10.29",
    "username": "your-user",
    "ssh_key": "~/.ssh/id_ed25519",
    "password": "xxx"
  }
}
```

- `ssh_key`（可选）: SSH 私钥路径，默认 `~/.ssh/id_ed25519`
- `password`（可选）: REST API 备用，仅 `get_change_diff` 需要

## 功能

| 接口 | 说明 |
|------|------|
| `get_changes(since, until)` | 按时间段查询自己提交列表 |
| `get_change_detail(change_number)` | 查询 Change 详情 |
| `get_change_diff(change_id)` | 获取 Change 最新 patchset diff |
| `get_change_messages(change_id)` | 获取 Change 所有评论/Messages |
| `get_reviewer_changes(since, until)` | 待自己 review 的 Change |
| `get_project_changes(project, branch, limit)` | 项目提交历史 |
| `submit_review(change_id, score, message)` | 提交 Code-Review 评分 |
| `get_stats(changes)` | 提交统计 |
| `get_stats_report(since, until)` | 提交统计报表 |

## 使用示例

```python
import gerrit_client

# 查询本周提交
changes = gerrit_client.get_changes("2026-03-01", "2026-03-28")

# 获取评论
messages = gerrit_client.get_change_messages(288038)

# 提交 review
gerrit_client.submit_review(288038, 1, "LGTM")
```
