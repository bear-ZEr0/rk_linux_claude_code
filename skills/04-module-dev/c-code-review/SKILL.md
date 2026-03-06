---
name: c-code-review
description: C 语言代码审核 - 针对嵌入式系统的代码质量和安全检查
---

# C 语言代码审核

## 何时激活

- 用户请求代码审核
- 提交代码前检查
- 合并分支前审核

> 审核标准、检查清单和输出格式见 `agents/code-reviewer.md`（单一事实源）。

## 自动化格式检查

使用 `scripts/run_clang_format.py` 检查代码是否符合团队 .clang-format 规范。

```bash
# 检查格式问题
python3 scripts/run_clang_format.py <文件或目录>

# 自动修复格式
python3 scripts/run_clang_format.py <文件或目录> --fix

# 指定配置文件
python3 scripts/run_clang_format.py src/ --style /path/to/.clang-format

# 保存结果到文件
python3 scripts/run_clang_format.py src/ --output report.txt
```

> 未安装 clang-format 时脚本会给出安装提示。

## Gerrit 远程审核

支持直接审核 Gerrit Change，自动获取 diff 并将审核结论提交回 Gerrit。

### 使用方式

```bash
/code-review 292250              # 通过 Change 编号审核
/code-review Ieb1a7f3c4d5e6f7   # 通过 Change-Id 审核
```

### 流程

1. 从 Gerrit 获取最新 patchset 的 unified diff
2. 使用 code-reviewer agent 按现有标准审核
3. 生成审核报告，展示给用户确认
4. 用户确认后提交 Code-Review 打分（+1 通过 / -1 不通过）

### 辅助脚本

```bash
# 获取 diff
python3 scripts/gerrit_review.py get-diff <change_id>

# 提交审核
python3 scripts/gerrit_review.py submit-review <change_id> --score +1 --message "审核报告"
```

> `gerrit_review.py` 委托 `99-common-tools/rk-gerrit/scripts/gerrit_client.py` 执行 Gerrit API 调用。
> 需要先在 `settings.json` 中配置 gerrit 连接信息，参见 `settings.example.json`。
