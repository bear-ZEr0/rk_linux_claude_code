---
name: rk-email
description: Rockchip 内部邮件发送技能。当用户需要发送通知、日志文件、每日报告或验证 SMTP 网络连通性时使用。
---

# 邮件发送工具 (rk-email)

本技能提供命令行工具，用于通过 Rockchip 内部 SMTP 服务器发送邮件。

> [!IMPORTANT]
> **工作目录规则**: 所有辅助脚本必须在**用户的工作目录**执行，使用脚本的**绝对路径**调用。
> - 不要 `cd` 到技能目录执行脚本。
> - 这样可以确保生成的 wrapper 和配置文件保存在当前项目目录下。

## 核心功能

### 1. 发送基础邮件

直接执行脚本发送纯文本邮件。

```bash
# 格式 A: 逗号/分号分隔字符串 (最常用)
python3 <SKILL_PATH>/scripts/send_email.py "user1@rock-chips.com, user2@rock-chips.com" "主题" "正文"

# 格式 B: 使用追加参数 (更清晰)
python3 <SKILL_PATH>/scripts/send_email.py "user1@rock-chips.com" "主题" "正文" --to "user2@rock-chips.com" --to "user3@rock-chips.com"
```

### 2. 发送带附件邮件

使用 `--attachment` 参数添加附件（支持相对或绝对路径）。

```bash
/path/to/rk-skills/99-dev-utilities/rk-email/scripts/send_email.py "接收人邮箱" "邮件主题" "邮件正文" --attachment ./report.pdf
```

### 3. 发送 HTML 富文本报告

使用 `--html-file` 参数发送渲染好的 HTML 页面。

```bash
/path/to/rk-skills/99-dev-utilities/rk-email/scripts/send_email.py "接收人" "HTML 邮件测试" --html-file ./my_report.html
```

## 高级配置 (可选)

### 抄送多人 (CC)

支持逗号分隔或多次指定 `--cc` 参数：

```bash
# 混合用法示例
python3 <SKILL_PATH>/scripts/send_email.py user@rock-chips.com "主题" "正文" \
    --cc "cc1@rock-chips.com, cc2@rock-chips.com" \
    --cc cc3@rock-chips.com
```

### 自定义发件人昵称

使用 `--sender-name` 参数覆盖默认昵称（默认: `瑞芯微AI助理`）：

```bash
python3 <SKILL_PATH>/scripts/send_email.py user@rock-chips.com "主题" "正文" \
    --sender-name "AI团队周报"
```

### 环境变量配置

如需使用自定义邮箱账号，或者在 CI/CD 环境中使用：

```bash
export RK_EMAIL_USER="your-email@rock-chips.com"
export RK_EMAIL_PASSWORD="your-password"
export RK_EMAIL_SENDER_NAME="自定义昵称"
# 运行命令...
```
