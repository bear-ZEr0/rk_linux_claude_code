---
name: rk-gerrit
description: Gerrit API 客户端 - 统一的 Gerrit 认证、查询、操作接口
---

# Gerrit API 客户端

## 何时激活

- 需要查询 Gerrit 提交记录
- 需要获取 Change diff 或详情
- 需要提交 Code-Review 评分
- 需要统计代码提交数据

## 功能

| 接口 | 说明 |
|------|------|
| `login(url, username, password)` | 统一认证，返回 (opener, headers, xsrf_token) |
| `get_changes(url, username, password, since, until)` | 按时间段查询提交列表 |
| `get_change_detail(change_number)` | 查询 Change 详情 |
| `get_change_diff(change_id)` | 获取 Change 最新 patchset diff |
| `get_reviewer_changes(since, until)` | 待自己 review 的 Change |
| `get_project_changes(project, branch, limit)` | 项目提交历史 |
| `submit_review(change_id, score, message)` | 提交 Code-Review 评分 |
| `get_stats(changes)` | 提交统计 |

## 使用示例

```python
import gerrit_client

# 查询本周提交
changes = gerrit_client.get_changes(url, user, pwd, "2026-02-23", "2026-02-27")

# 获取 diff
meta, diff = gerrit_client.get_change_diff(12345)

# 提交 review
gerrit_client.submit_review(12345, score=1, message="LGTM")
```
