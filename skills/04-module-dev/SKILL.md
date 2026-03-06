---
name: module-dev
description: 模块开发辅助工具集 - ADB 连接、串口调试、DTS 生成、代码审核
---

# 模块开发工具

本目录包含 Rockchip 嵌入式开发常用的辅助技能。

## 包含的技能

| 技能 | 说明 | 触发关键词 |
|------|------|-----------|
| [rk-adb](rk-adb/SKILL.md) | ADB 设备连接（本地/远程） | adb push, adb pull, 抓日志 |
| [rk-serial](rk-serial/SKILL.md) | 串口调试（Linux/Windows） | 串口日志, boot log, FIQ 调试 |
| [rk-dts-from-schematic](rk-dts-from-schematic/SKILL.md) | 从原理图生成 DTS | 生成 DTS, 原理图转 DTS |
| [c-code-review](c-code-review/SKILL.md) | C 语言代码审核 | 代码审核, code review |
| [cpp-testing](cpp-testing/SKILL.md) | C++ 测试（Google Test + GMock） | C++ 测试, gtest, gmock |

## 快速导航

### 需要连接设备？

- **有网络** → 使用 [rk-adb](rk-adb/SKILL.md)（网络 ADB 或远程 USB ADB）
- **需要串口** → 使用 [rk-serial](rk-serial/SKILL.md)（抓启动日志、FIQ 调试）

### 需要开发辅助？

- **生成 DTS** → 使用 [rk-dts-from-schematic](rk-dts-from-schematic/SKILL.md)
- **代码审核** → 使用 [c-code-review](c-code-review/SKILL.md)
- **C++ 测试** → 使用 [cpp-testing](cpp-testing/SKILL.md)

## 使用说明

每个子技能都是独立的，直接查看对应的 SKILL.md 获取详细使用方法。
