---
name: rk-oa
description: OA 考勤客户端 - 泛微 OA 登录与考勤数据获取
---

# OA 考勤客户端

## 何时激活

- 需要获取 OA 考勤打卡记录
- 需要计算工时统计
- 需要查询月度考勤或异常检测

## 功能

| 接口 | 说明 |
|------|------|
| `oa_login(url, username, password)` | RSA 加密 + 验证码登录泛微 OA |
| `get_oa_attendance(url, username, password, from_date, to_date)` | 获取考勤打卡记录 |
| `calculate_work_hours(records, from_date, to_date)` | 根据打卡记录计算工时 |
| `get_monthly_attendance(url, username, password, year, month)` | 月度考勤统计 |
| `check_anomalies(records)` | 考勤异常检测（迟到、早退、缺卡） |

## 使用示例

```python
import oa_client

records = oa_client.get_oa_attendance(url, user, pwd, "2026-02-23", "2026-02-27")
work_hours = oa_client.calculate_work_hours(records, "2026-02-23", "2026-02-27")
anomalies = oa_client.check_anomalies(records)
```
