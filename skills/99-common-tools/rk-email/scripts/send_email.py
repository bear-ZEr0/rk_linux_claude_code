#!/usr/bin/env python3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import sys
import os
import argparse
import base64

# 防止生成 __pycache__ 污染技能目录
sys.dont_write_bytecode = True

try:
    from email_config import get_credentials
except ImportError:
    # 尝试从当前目录导入 (如果直接在 scripts/ 目录外运行)
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_config import get_credentials

def split_emails(email_input):
    """
    将输入（字符串或列表）转换为干净的邮件地址列表。
    支持逗号、分号分隔。
    """
    if not email_input:
        return []
    
    if isinstance(email_input, list):
        # 递归处理列表中的每一项，防止项内含有逗号
        result = []
        for item in email_input:
            result.extend(split_emails(item))
        return result
    
    if isinstance(email_input, str):
        # 替换分号为逗号，然后拆分
        raw_list = email_input.replace(';', ',').split(',')
        return [e.strip() for e in raw_list if e.strip()]
    
    return []

def send_email(to_email, subject, body, attachment_path=None, is_html=False, sender_name=None, cc_emails=None):
    """发送邮件的主逻辑"""
    config = get_credentials()
    sender_email = config.get("sender_email")
    password = config.get("password")
    smtp_server = config.get("smtp_server")
    port = config.get("smtp_port", 465)

    if not all([sender_email, password, smtp_server]):
        print("错误: 无法获取有效的邮件配置 (sender_email, password, smtp_server)")
        sys.exit(1)

    message = MIMEMultipart()
    # 设置发件人昵称 (CLI参数 > 配置文件默认值)
    display_name = sender_name or config.get("sender_name")
    if display_name:
        message["From"] = f"{display_name} <{sender_email}>"
    else:
        message["From"] = sender_email
    
    # 规范化收件人和抄送人
    final_to_list = split_emails(to_email)
    final_cc_list = split_emails(cc_emails)
    
    if not final_to_list:
        print("错误: 收件人列表为空")
        return False

    message["To"] = ", ".join(final_to_list)
    message["Subject"] = subject
    
    if final_cc_list:
        message["Cc"] = ", ".join(final_cc_list)

    # 邮件正文
    if is_html:
        message.attach(MIMEText(body, "html"))
    else:
        message.attach(MIMEText(body, "plain"))

    # 处理附件
    if attachment_path:
        abs_attachment_path = os.path.abspath(attachment_path)
        if os.path.exists(abs_attachment_path):
            try:
                filename = os.path.basename(abs_attachment_path)
                with open(abs_attachment_path, "rb") as attachment:
                    content = attachment.read()
                    try:
                        # 尝试按文本处理
                        text_content = content.decode('utf-8')
                        part = MIMEText(text_content, 'plain', 'utf-8')
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                    except UnicodeDecodeError:
                        # 二进制文件使用 MIMEApplication
                        from email.mime.application import MIMEApplication
                        part = MIMEApplication(content, 'octet-stream')
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                    message.attach(part)
                print(f"已添加附件: {filename}")
            except Exception as e:
                print(f"添加附件失败: {e}")
                return False
        else:
            print(f"警告: 找不到附件 {abs_attachment_path}")
            return False

    try:
        print(f"正在连接到 {smtp_server}:{port}...")
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            try:
                server.starttls()
            except Exception as e:
                print(f"STARTTLS 初始化提示: {e}")

        print("连接成功，正在登录...")
        server.login(sender_email, password)
        print("登录成功，正在发送邮件...")
        
        # 真正的 SMTP 接收者列表 = to + cc
        smtp_recipients = list(set(final_to_list + final_cc_list)) # 去重
        
        server.sendmail(sender_email, smtp_recipients, message.as_string())
        print("发送完成，正在断开连接...")
        server.quit()
        print(f"邮件已成功发送至 {len(smtp_recipients)} 位收件人 (To: {len(final_to_list)}, Cc: {len(final_cc_list)})")
        return True
    except smtplib.SMTPAuthenticationError:
        print("发送失败: 认证错误，请检查用户名或密码。")
        return False
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rockchip 邮件发送工具")
    parser.add_argument("to", nargs="?", help="收件人邮箱地址 (支持逗号分隔)")
    parser.add_argument("subject", nargs="?", help="邮件主题")
    parser.add_argument("body", nargs="?", help="邮件正文内容 (如果使用了 --html-file，此参数可忽略)")
    parser.add_argument("--to", dest="extra_to", action="append", help="额外的收件人 (可多次指定)")
    parser.add_argument("--attachment", "-a", help="可选附件路径", default=None)
    parser.add_argument("--html-file", help="HTML 内容文件路径 (将作为邮件正文发送)", default=None)
    parser.add_argument("--sender-name", help="发件人昵称 (如: 瑞芯微AI助理)", default=None)
    parser.add_argument("--cc", action="append", help="抄送邮箱 (可多次指定)", default=None)

    args = parser.parse_args()

    # 获取配置中的默认收件人
    config = get_credentials()
    default_to = config.get("default_to", "")

    # 如果没有指定收件人，使用默认收件人
    if not args.to and not args.extra_to:
        if default_to:
            args.to = default_to
            print(f"使用默认收件人: {default_to}")
        else:
            parser.print_help()
            print("\n错误: 必须提供收件人（或在 settings.json 中配置 email.default_to）")
            sys.exit(1)

    if not args.subject:
        parser.print_help()
        print("\n错误: 必须提供邮件主题")
        sys.exit(1)

    # 合并位置参数 to 和 --to 指定的收件人
    combined_to = split_emails(args.to)
    if args.extra_to:
        combined_to.extend(split_emails(args.extra_to))

    body_content = args.body or ""
    if args.html_file:
         try:
            with open(args.html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            success = send_email(combined_to, args.subject, html_content, args.attachment, is_html=True, sender_name=args.sender_name, cc_emails=args.cc)
         except Exception as e:
            print(f"读取 HTML 文件失败: {e}")
            sys.exit(1)
    else:
        if not body_content:
             print("错误: 必须提供邮件正文或 HTML 文件")
             sys.exit(1)
        success = send_email(combined_to, args.subject, body_content, args.attachment, is_html=False, sender_name=args.sender_name, cc_emails=args.cc)

    sys.exit(0 if success else 1)
