---
name: sdk-diff
description: 比较 repo 管理的 SDK 前后版本差异。当用户提到以下内容时使用：(1) SDK 更新了什么、SDK 变更、SDK diff；(2) repo sync 后有什么变化；(3) 每日 SDK 变更检查；(4) 某个 SDK 目录的提交历史对比。支持快照保存、跨天对比、repo sync 前后对比。
---

# SDK 版本差异对比

比较 repo 管理的多仓库 SDK 前后版本变更，生成结构化差异报告。

## 快速使用

```bash
# 保存当前快照
python skills/05-sdk-dev/sdk-diff/scripts/sdk_diff.py snapshot /path/to/sdk

# repo sync 并对比变更
python skills/05-sdk-dev/sdk-diff/scripts/sdk_diff.py sync /path/to/sdk

# 对比最近两次快照
python skills/05-sdk-dev/sdk-diff/scripts/sdk_diff.py diff /path/to/sdk

# 查看指定日期范围的变更
python skills/05-sdk-dev/sdk-diff/scripts/sdk_diff.py log /path/to/sdk --since 2026-02-20 --until 2026-02-27

# 列出所有快照
python skills/05-sdk-dev/sdk-diff/scripts/sdk_diff.py list /path/to/sdk
```

## 工作流程

### 每日检查

1. 运行 `sdk_diff.py sync /path/to/sdk`，脚本自动：
   - 保存当前 HEAD 快照
   - 执行 `repo sync`
   - 保存更新后 HEAD 快照
   - 输出变更报告

### 手动对比

1. 运行 `sdk_diff.py snapshot` 保存快照
2. 任意时间再次保存快照
3. 运行 `sdk_diff.py diff` 对比两次快照

## 输出格式

报告按子项目分组，包含：
- 项目名称和路径
- 新增提交列表（hash + 摘要）
- 变更文件统计

报告保存到 SDK 目录下 `.sdk-diff/reports/`。

## 配置

在 `settings.json` 中可配置默认 SDK 路径：

```json
{
  "sdk_diff": {
    "sdk_paths": {
      "rk1820": "/home/hkh/projects/rk1820",
      "rk3588": "/home/hkh/projects/rk3588"
    }
  }
}
```

配置后可用别名：
```bash
python sdk_diff.py sync rk1820
```
