#!/usr/bin/env python3
"""
邮件配置模块 - SMTP 发件 / IMAP 收件统一凭证管理

凭证读取优先级:
1. 环境变量 (RK_EMAIL_USER / RK_EMAIL_PASSWORD)
2. settings.json 中的 email.username / email.password
3. 混淆默认值（仅用于防止明文暴露，非真正加密）

配置示例 (settings.json):
  "email": {
    "username": "your-name@rock-chips.com",
    "password": "your-password"
  }
"""
import os
import base64
import json

_OBFUSCATED_USER = "bW9jLnNwaWhjLWtjb3JAdG5hdHNpc3NhLWlh"
_OBFUSCATED_PASS = "S3hKMnNhVVhAYg=="


def _deobfuscate(data: str) -> str:
    try:
        return base64.b64decode(data).decode()[::-1]
    except Exception:
        return ""


def _load_settings():
    """加载 settings.json 配置文件"""
    # 查找 settings.json（从脚本目录向上查找）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
        os.path.join(script_dir, "../../../../settings.json"),  # skills/99-common-tools/rk-email/scripts -> root
        os.path.join(os.getcwd(), "settings.json"),  # 当前工作目录
    ]

    for path in search_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def get_credentials():
    """
    获取邮件配置（SMTP 发件）

    优先级:
    1. 环境变量 (最高优先，用于自定义账号或 CI/CD)
    2. settings.json 中的 email.username / email.password
    3. 混淆默认值
    """
    settings = _load_settings()
    email_settings = settings.get("email", {})

    return {
        "sender_email": os.getenv("RK_EMAIL_USER") or email_settings.get("username") or _deobfuscate(_OBFUSCATED_USER),
        "password": os.getenv("RK_EMAIL_PASSWORD") or email_settings.get("password") or _deobfuscate(_OBFUSCATED_PASS),
        "smtp_server": os.getenv("RK_EMAIL_SMTP") or email_settings.get("smtp_server", "smtp.rock-chips.com"),
        "smtp_port": int(os.getenv("RK_EMAIL_PORT") or email_settings.get("smtp_port", 465)),
        "sender_name": os.getenv("RK_EMAIL_SENDER_NAME") or email_settings.get("sender_name", "瑞芯微AI助理"),
        "default_to": email_settings.get("default_to", ""),
    }


def get_imap_config() -> dict:
    """获取 IMAP 收件配置（用于邮件信号收集）"""
    settings = _load_settings()
    email_cfg = settings.get("email", {})
    return {
        "username": os.getenv("RK_EMAIL_USER") or email_cfg.get("username") or _deobfuscate(_OBFUSCATED_USER),
        "password": os.getenv("RK_EMAIL_PASSWORD") or email_cfg.get("password") or _deobfuscate(_OBFUSCATED_PASS),
        "imap_server": os.getenv("RK_IMAP_SERVER") or email_cfg.get("imap_server", "imap.rock-chips.com"),
        "imap_port": int(os.getenv("RK_IMAP_PORT") or email_cfg.get("imap_port", 993)),
        "filter": email_cfg.get("filter", {}),
    }


if __name__ == "__main__":
    # 测试解码
    creds = get_credentials()
    print(f"发件人: {creds['sender_email']}")
    print(f"SMTP: {creds['smtp_server']}:{creds['smtp_port']}")
    print(f"密码已配置: {'是' if creds['password'] else '否'}")
    print(f"发件人昵称: {creds['sender_name']}")
    print(f"默认收件人: {creds['default_to'] or '(未配置)'}")
