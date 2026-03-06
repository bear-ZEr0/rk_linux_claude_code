#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OA 考勤客户端

从泛微 OA 获取考勤打卡记录，支持 RSA 加密登录 + 验证码 OCR 自动识别。
提供工时计算、月度统计、异常检测等功能。
"""

import base64
import http.cookiejar
import json
import os
import re
import ssl
import sys
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


# ---------------------------------------------------------------------------
# OCR 引擎加载（多种后端自动探测）
# ---------------------------------------------------------------------------

def _load_ddddocr_direct():
    from ddddocr.core.ocr_engine import OCREngine
    return OCREngine, "ddddocr"

def _load_ddddocr_legacy():
    import ddddocr as mod
    return mod.DdddOcr, "ddddocr"

def _load_ddddocr_importlib():
    import importlib.util as ilu
    spec = ilu.find_spec("ddddocr")
    if spec is None or not spec.submodule_search_locations:
        raise ImportError("ddddocr package not found")
    ocreng_path = os.path.join(
        spec.submodule_search_locations[0], "core", "ocr_engine.py")
    if not os.path.isfile(ocreng_path):
        raise FileNotFoundError(f"{ocreng_path} not found")
    ocreng_spec = ilu.spec_from_file_location("ddddocr.core.ocr_engine", ocreng_path)
    ocreng_mod = ilu.module_from_spec(ocreng_spec)
    ocreng_spec.loader.exec_module(ocreng_mod)
    cls = getattr(ocreng_mod, "OCREngine", None)
    if cls is None:
        raise AttributeError("OCREngine not found in ocr_engine module")
    return cls, "ddddocr"

def _load_pytesseract():
    import pytesseract  # noqa: F811
    from PIL import Image  # noqa: F811
    import io  # noqa: F811
    return None, "pytesseract"

HAS_OCR = False
OCR_ENGINE = ""
_DdddOcr = None
for _loader in [_load_ddddocr_direct, _load_ddddocr_legacy,
                _load_ddddocr_importlib, _load_pytesseract]:
    try:
        _DdddOcr, OCR_ENGINE = _loader()
        HAS_OCR = True
        break
    except (ImportError, AttributeError, FileNotFoundError, OSError):
        continue

# 内网自签名证书 - 使用 TLS_CLIENT 解决 Windows SSL 兼容性问题
try:
    SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except AttributeError:
    SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _extract_time(time_str: str) -> str:
    """从时间字符串中提取 HH:MM"""
    if not time_str:
        return ""
    time_str = str(time_str).strip()
    m = re.search(r'(\d{1,2}:\d{2})', time_str)
    return m.group(1) if m else ""


def _parse_attendance_record(item: dict) -> Optional[Dict]:
    """解析单条考勤记录（兼容泛微不同版本字段名）"""
    date = (item.get("kqdate") or item.get("signdate") or
            item.get("date") or item.get("attendanceDate") or "")
    sign_in = (item.get("signintime") or item.get("signInTime") or
               item.get("onduty") or item.get("startTime") or "")
    sign_out = (item.get("signouttime") or item.get("signOutTime") or
                item.get("offduty") or item.get("endTime") or "")

    if not date:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            date = datetime.strptime(date, fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            continue

    sign_in = _extract_time(sign_in)
    sign_out = _extract_time(sign_out)

    hours = 0.0
    if sign_in and sign_out:
        try:
            t_in = datetime.strptime(sign_in, "%H:%M")
            t_out = datetime.strptime(sign_out, "%H:%M")
            diff = (t_out - t_in).total_seconds() / 3600
            hours = round(diff, 1) if diff > 0 else 0.0
        except ValueError:
            pass

    return {"date": date, "sign_in": sign_in, "sign_out": sign_out, "hours": hours}


def _recognize_captcha(image_bytes: bytes) -> str:
    """识别验证码图片（优先 ddddocr，备选 pytesseract）"""
    if not HAS_OCR:
        return ""
    try:
        if OCR_ENGINE == "ddddocr":
            if not hasattr(_recognize_captcha, "_ocr"):
                _recognize_captcha._ocr = _DdddOcr()
            ocr = _recognize_captcha._ocr
            if hasattr(ocr, 'classification'):
                return ocr.classification(image_bytes)
            return ocr.predict(image_bytes)
        else:
            from PIL import Image
            import io
            import pytesseract
            img = Image.open(io.BytesIO(image_bytes))
            code = pytesseract.image_to_string(
                img, config="--psm 7 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            ).strip()
            return code
    except Exception:
        return ""


def _calc_daily_hours(sign_in: str, sign_out: str) -> float:
    """计算单日工时（12点前上班扣午餐1.5h，19点后下班再扣晚餐1h）"""
    if not sign_in or not sign_out:
        return 0.0
    try:
        t_in = datetime.strptime(sign_in, "%H:%M")
        t_out = datetime.strptime(sign_out, "%H:%M")
        raw = (t_out - t_in).total_seconds() / 3600
        deduct = 0.0
        if t_in.hour < 12:
            deduct += 1.5  # 午餐
        if t_out.hour >= 19:
            deduct += 1.0  # 晚餐
        return round(max(raw - deduct, 0), 1)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------

def oa_login(url: str, username: str, password: str, captcha: str = "",
             max_retries: int = 5):
    """RSA 加密 + 验证码登录泛微 OA，返回 (opener, userid) 或 (None, None)"""
    if not HAS_CRYPTOGRAPHY:
        print("缺少 cryptography 库，无法登录 OA (pip install cryptography)", file=sys.stderr)
        return None, None

    base = url.rstrip("/")
    ajax = {"X-Requested-With": "XMLHttpRequest", "Referer": f"{base}/wui/index.html"}

    # 禁用代理，直接连接内网 OA
    proxy_handler = urllib.request.ProxyHandler({})
    for attempt in range(max_retries + 1):
        try:
            cookie_jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(
                proxy_handler,
                urllib.request.HTTPCookieProcessor(cookie_jar),
                urllib.request.HTTPSHandler(context=SSL_CONTEXT),
            )

            # 1. 初始化 session
            opener.open(urllib.request.Request(f"{base}/wui/index.html"), timeout=15)

            # 2. 获取 RSA 公钥
            with opener.open(urllib.request.Request(
                    f"{base}/rsa/weaver.rsa.GetRsaInfo"), timeout=15) as r:
                rsa_info = json.loads(r.read().decode("utf-8"))

            pem = ("-----BEGIN PUBLIC KEY-----\n"
                   + rsa_info["rsa_pub"]
                   + "\n-----END PUBLIC KEY-----")
            pub_key = serialization.load_pem_public_key(pem.encode())

            def rsa_encrypt(value):
                plaintext = (value + rsa_info["rsa_code"]).encode("utf-8")
                return base64.b64encode(
                    pub_key.encrypt(plaintext, asym_padding.PKCS1v15())
                ).decode("ascii") + rsa_info["rsa_flag"]

            # 3. 获取验证码
            vk = str(uuid.uuid4())
            cap_url = (f"{base}/weaver/weaver.file.MakeValidateCode"
                       f"?seriesnum_=0&validateCodeKey={vk}")
            with opener.open(urllib.request.Request(cap_url), timeout=15) as r:
                captcha_img = r.read()

            # 确定验证码文本
            code = captcha
            if not code and HAS_OCR:
                code = _recognize_captcha(captcha_img)
                if code:
                    print(f"OCR 识别验证码: {code} (第{attempt+1}次)", file=sys.stderr)
                elif attempt < max_retries:
                    print(f"OCR 识别为空，重试 ({attempt+1}/{max_retries})...",
                          file=sys.stderr)
                    continue
            if not code:
                import tempfile
                cap_path = os.path.join(tempfile.gettempdir(), f"oa_captcha_{username}.png")
                with open(cap_path, "wb") as f:
                    f.write(captcha_img)
                print(f"OA 验证码图片已保存: {cap_path}", file=sys.stderr)
                try:
                    code = input("请输入 OA 验证码: ").strip()
                except EOFError:
                    code = ""
                finally:
                    try:
                        os.unlink(cap_path)
                    except OSError:
                        pass
                if not code:
                    print("非交互环境，无法手动输入验证码", file=sys.stderr)
                    return None, None

            # 4. RSA 加密登录
            params = {
                "loginid": rsa_encrypt(username),
                "userpassword": rsa_encrypt(password),
                "validatecode": code,
                "validateCodeKey": vk,
                "logintype": "1",
            }
            data = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(
                f"{base}/api/hrm/login/checkLogin", data=data, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            for k, v in ajax.items():
                req.add_header(k, v)

            with opener.open(req, timeout=15) as r:
                resp = json.loads(r.read().decode("utf-8"))

            if resp.get("loginstatus") == "true":
                userid = resp.get("userid", "")
                return opener, userid

            msg = resp.get("msg", "")
            if "验证码" in msg and attempt < max_retries and not captcha:
                print(f"验证码错误，重试 ({attempt+1}/{max_retries})...",
                      file=sys.stderr)
                continue

            print(f"OA 登录失败: {msg}", file=sys.stderr)
            return None, None

        except Exception as e:
            print(f"OA 登录异常: {e}", file=sys.stderr)
            if attempt < max_retries and not captcha:
                continue
            return None, None

    return None, None


# ---------------------------------------------------------------------------
# 考勤数据获取
# ---------------------------------------------------------------------------

def get_oa_attendance(url: str, username: str, password: str,
                      from_date: str, to_date: str,
                      captcha: str = "") -> List[Dict]:
    """从泛微 OA 获取考勤打卡记录（使用月历接口）"""
    if not url or not username or not password:
        print("OA 配置不完整，跳过考勤数据收集", file=sys.stderr)
        return []

    opener, userid = oa_login(url, username, password, captcha)
    if not opener:
        return []

    base = url.rstrip("/")
    ajax = {"X-Requested-With": "XMLHttpRequest", "Referer": f"{base}/wui/index.html"}

    start_dt = datetime.strptime(from_date, "%Y-%m-%d")
    end_dt = datetime.strptime(to_date, "%Y-%m-%d")
    months = set()
    cur = start_dt
    while cur <= end_dt:
        months.add(cur.strftime("%Y-%m"))
        cur += timedelta(days=1)

    records = []
    for month in sorted(months):
        try:
            params = {"typevalue": month, "type": "2"}
            data = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(
                f"{base}/api/kq/myattendance/getHrmKQMonthReportInfo",
                data=data, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            for k, v in ajax.items():
                req.add_header(k, v)
            with opener.open(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            day_map = result.get("result", {})
            for _day_key, day_info in day_map.items():
                date_str = day_info.get("date", "")
                if not date_str or date_str < from_date or date_str > to_date:
                    continue

                sign_in = ""
                sign_out = ""
                for si in day_info.get("signInfo", []):
                    t = _extract_time(si.get("signTime", ""))
                    if "上班" in si.get("title", ""):
                        sign_in = t
                    elif "下班" in si.get("title", ""):
                        sign_out = t

                hours = _calc_daily_hours(sign_in, sign_out)

                records.append({
                    "date": date_str,
                    "sign_in": sign_in,
                    "sign_out": sign_out,
                    "hours": hours,
                    "is_work_day": day_info.get("isWorkDay", False),
                    "types": day_info.get("types", []),
                })
        except Exception as e:
            print(f"OA 考勤数据获取失败 ({month}): {e}", file=sys.stderr)

    records.sort(key=lambda r: r["date"])
    return records


# ---------------------------------------------------------------------------
# 工时计算
# ---------------------------------------------------------------------------

def calculate_work_hours(attendance_records: List[Dict],
                         from_date: str, to_date: str) -> dict:
    """根据打卡记录计算工时

    规则（使用 OA 返回的 isWorkDay 判断工作日）：
    - 工作日有完整打卡 → 按时间差计算
    - 工作日打卡不全或无记录 → 8h
    - 非工作日有打卡 → 按时间差计算（加班）
    - 非工作日无打卡 → 0h
    """
    record_map = {rec["date"]: rec for rec in attendance_records}
    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")

    daily = []
    total_hours = 0.0
    overtime_hours = 0.0
    current = start

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        if current.date() > datetime.now().date():
            current += timedelta(days=1)
            continue
        rec = record_map.get(date_str)
        is_work_day = rec["is_work_day"] if rec and "is_work_day" in rec else current.weekday() < 5

        if is_work_day:
            if rec and rec["hours"] > 0:
                hours = rec["hours"]
                day_type = "normal"
                if hours > 8:
                    overtime_hours += hours - 8
            else:
                hours = 8.0
                day_type = "default"
        else:
            if rec and rec["hours"] > 0:
                hours = rec["hours"]
                day_type = "overtime"
                overtime_hours += hours
            else:
                hours = 0.0
                day_type = "weekend"

        total_hours += hours
        daily.append({
            "date": date_str,
            "weekday": current.weekday(),
            "sign_in": rec["sign_in"] if rec else "",
            "sign_out": rec["sign_out"] if rec else "",
            "hours": hours,
            "type": day_type,
        })
        current += timedelta(days=1)

    return {
        "total_hours": round(total_hours, 1),
        "overtime_hours": round(overtime_hours, 1),
        "daily": daily,
    }


# ---------------------------------------------------------------------------
# 新增功能
# ---------------------------------------------------------------------------

def get_monthly_attendance(url: str, username: str, password: str,
                           year: int, month: int, captcha: str = "") -> dict:
    """月度考勤统计"""
    from_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_dt = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_dt = datetime(year, month + 1, 1) - timedelta(days=1)
    to_date = end_dt.strftime("%Y-%m-%d")

    records = get_oa_attendance(url, username, password, from_date, to_date, captcha)
    work_hours = calculate_work_hours(records, from_date, to_date)
    anomalies = check_anomalies(records)
    return {
        "year": year,
        "month": month,
        "records": records,
        "work_hours": work_hours,
        "anomalies": anomalies,
    }


def check_anomalies(records: List[Dict]) -> List[Dict]:
    """考勤异常检测（迟到、早退、缺卡）"""
    anomalies = []
    for rec in records:
        if not rec.get("is_work_day", True):
            continue
        sign_in = rec.get("sign_in", "")
        sign_out = rec.get("sign_out", "")

        if not sign_in and not sign_out:
            anomalies.append({"date": rec["date"], "type": "缺卡", "detail": "全天无打卡记录"})
            continue
        if not sign_in:
            anomalies.append({"date": rec["date"], "type": "缺卡", "detail": "缺少上班打卡"})
        elif sign_in > "09:30":
            anomalies.append({"date": rec["date"], "type": "迟到",
                              "detail": f"上班打卡 {sign_in}"})
        if not sign_out:
            anomalies.append({"date": rec["date"], "type": "缺卡", "detail": "缺少下班打卡"})
        elif sign_out < "18:00":
            anomalies.append({"date": rec["date"], "type": "早退",
                              "detail": f"下班打卡 {sign_out}"})
    return anomalies


def get_business_trips(url: str, username: str, password: str,
                       from_date: str, to_date: str,
                       captcha: str = "") -> List[Dict]:
    """出差记录查询（从考勤类型中提取）"""
    records = get_oa_attendance(url, username, password, from_date, to_date, captcha)
    trips = []
    for rec in records:
        types = rec.get("types", [])
        for t in types:
            if "出差" in str(t):
                trips.append({"date": rec["date"], "type": t})
                break
    return trips
