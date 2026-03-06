---
name: rk-redmine
description: 检索Rockchip内部Redmine问题跟踪系统。当用户需要排查Rockchip芯片问题（RK3588、RK3576、RK3568等）、查找历史Bug修复方案、下载日志截图时使用。**支持向Redmine提交回复**：当用户说"回复这个redmine"、"帮我回复"、"提交回复"时触发。**当用户提到"补丁简报"、"rk-sdk"、"Change-Id"时必须触发此技能**，获取补丁包版本、预置固件位置、关联Gerrit代码提交。**当用户提到"运营商"、"运营商补丁"时也要触发**。典型场景："查一下这个redmine issue"、"补丁简报有什么更新"、"帮我找一下PCIe相关的补丁简报"、"运营商SDK有什么HDMI相关问题"、"回复这个redmine"。带redmine.rock-chips.com域名时触发。
allowed-tools: Bash, Read, Grep, Glob, mcp__zai-mcp-server__analyze_image
---

# Rockchip Redmine 问题搜索与补丁简报检索

搜索Rockchip内部Redmine系统获取技术问题解决方案和补丁简报信息。

## 支持的项目

### rk-sdk 补丁简报 (项目ID: 572)
以 Redmine 问题形式提供重要补丁信息。包含 Change-Id、补丁包版本历史、预置固件位置。

### 运营商SDK问题汇总 (项目ID: 1177)
记录运营商产品使用过程中的问题和补丁，按模块分为子项目：

| 项目 | 标识符 | 说明 |
|------|--------|------|
| hdmi | hdmi | HDMI 相关问题 |
| framework | op-framework | Framework 问题 |
| network | network-op | WiFi/蓝牙/网络 |
| camera | camera-op | Camera 问题 |
| media | media-op | 媒体编解码 |
| audio | audio-op | 音频问题 |
| kernel | uboot-kernel-op | 底层 uboot/内核 |

## 核心工作流程

> [!IMPORTANT]
> **工作目录规则**: 所有脚本必须在**用户的工作目录**执行，使用脚本的**绝对路径**调用。
> - Skill 目录是只读的，仅供读取脚本使用
> - 所有输出文件都会生成在**当前工作目录**
> - 不要 cd 到 skill 目录执行脚本

### 1. 补丁简报检索（优先使用，速度快）

```bash
# 搜索补丁简报
python3 /path/to/skill/scripts/search_patch_briefings.py "关键词"
python3 /path/to/skill/scripts/search_patch_briefings.py "HDMI" --chip RK3588

# 获取详情（自动关联Gerrit）
python3 /path/to/skill/scripts/get_patch_briefing.py <issue_id>
```

### 2. 运营商问题检索（速度快）

```bash
# 在所有运营商项目中搜索
python3 /path/to/skill/scripts/search_operator_issues.py "HDMI"

# 指定子项目搜索
python3 /path/to/skill/scripts/search_operator_issues.py "绿屏" --project hdmi
python3 /path/to/skill/scripts/search_operator_issues.py "wifi" --project network
python3 /path/to/skill/scripts/search_operator_issues.py "编码" --project media
```

### 3. 全局搜索（找不到时使用）

```bash
python3 /path/to/skill/scripts/search_by_keyword.py "搜索关键词" [限制数量]
```

### 4. 获取问题详情

```bash
python3 /path/to/skill/scripts/get_issue_info.py <问题ID> --dir <输出目录>
```

> [!IMPORTANT]
> 执行后必须分析附件图片。使用 zai-mcp-server 提取内容，嵌入 issue_report.md。

## 脚本列表

| 脚本 | 功能 |
|------|------|
| `search_patch_briefings.py` | **优先**，rk-sdk补丁简报搜索 |
| `search_operator_issues.py` | **优先**，运营商项目搜索 |
| `get_patch_briefing.py` | 补丁简报详情，自动关联Gerrit |
| `search_by_keyword.py` | 全局搜索（较慢） |
| `get_issue_info.py` | 问题详情+附件下载 |
| `submit_reply.py` | 提交回复到 Redmine Issue |

## 提交回复工作流

> [!CAUTION]
> **强制交互确认**：提交回复前，必须在交互中获得用户的**明确确认**。
> 1. 用户明确说"提交回复"、"回复这个redmine"
> 2. **必须先展示即将提交的完整回复内容**，让用户审阅
> 3. 明确询问："以上是即将提交到 Redmine 的完整内容，确认提交吗？"
> 4. **只有用户明确回复"确认"、"是"、"提交"等肯定词后**，才能调用脚本提交
>
> ⚠️ **禁止在用户未看到完整回复内容的情况下提交**

### 使用流程

```bash
# 用户确认后，提交回复
echo "回复内容" | python3 /path/to/scripts/submit_reply.py <issue_id>
```

详细使用说明见 `references/reply_guide.md`。

## 问题查询

`sync_my_issues.py` 提供问题查询子命令，供周报等技能复用：

```bash
# 待处理问题（默认，SessionStart Hook 使用）
python3 /path/to/scripts/sync_my_issues.py

# 查询处理的问题
python3 /path/to/scripts/sync_my_issues.py issues-worked --from 2026-02-23 --to 2026-02-27
```

也可作为 Python 模块被其他脚本 import：

```python
from sync_my_issues import get_issues_worked, group_time_by_project
```

## 参考资料

- `references/patch_briefing_guide.md` - 补丁简报字段说明
- `references/search_guide.md` - 搜索策略指南
- `references/image_analysis_guide.md` - 图片分析指南
- `references/reply_guide.md` - 回复提交详细指南