# Redmine 回复提交指南

本指南详细说明如何使用 `submit_reply.py` 脚本向 Redmine 提交回复。

## 安全机制

> [!CAUTION]
> **Agent 必须在交互中获得用户明确确认后才能提交回复。**
> 脚本本身不做额外确认，安全由 Agent 交互流程保证。

### 确认流程

1. 用户明确说"提交回复"、"回复这个redmine"
2. Agent 展示完整回复内容，明确询问："确认要将以上内容提交到 Redmine 吗？"
3. **只有用户明确回复"确认"、"是"、"提交"等肯定词后**，Agent 才调用脚本提交

## 使用方法

### 从 stdin 读取内容

```bash
echo "回复内容" | python3 /path/to/scripts/submit_reply.py <issue_id>
```

### 从文件读取内容

```bash
python3 /path/to/scripts/submit_reply.py <issue_id> --file reply.txt
```

## 回复内容格式建议

1. **简洁明了**：直接给出结论和可执行命令
2. **专业语气**：对客户使用尊称"您"
3. **结构清晰**：使用列表或换行分隔不同要点
4. **避免标题格式**：不使用 "问题描述"、"分析结果" 等段落标题

## 错误处理

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| HTTP 500 | 服务器临时错误 | 脚本会自动重试 3 次 |
| 回复内容为空 | 未提供内容 | 通过 stdin 或 --file 提供内容 |

## API 细节

使用 Redmine REST API 的 PUT 方法：

```
PUT /issues/{issue_id}.json
Content-Type: application/json
X-Redmine-API-Key: {api_key}

{
  "issue": {
    "notes": "回复内容"
  }
}
```

成功返回 200 或 204 状态码。
