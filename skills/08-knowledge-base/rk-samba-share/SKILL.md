---
name: rk-samba-share
description: 访问 Rockchip 内网 Samba 共享服务器 (10.10.10.164)，检索和下载各类资源。当用户提到以下内容时使用：(1) 固件相关 - 历史固件、测试固件、release固件、bringup固件、update.img、品测固件；(2) SDK下载 - Android SDK、Linux SDK、RTOS SDK、完整SDK包；(3) 补丁包 - 补丁集、PATCHSETS、SDK补丁、内核补丁；(4) 开发工具 - 烧写工具、RKDevTool、FactoryTool、升级工具、USB驱动；(5) 驱动 - WiFi驱动、蓝牙驱动、Realtek驱动、Broadcom驱动；(6) AI工具 - RKNN模型、rknn-toolkit、rockface；(7) 测试资料 - 品测资料、竞品分析；(8) 网盘访问 - 10.10.10.164、内网共享、公共网盘。
allowed-tools: RunShellCommand
---

# Samba 网盘访问技能

帮助用户从 Rockchip 内网 Samba 服务器 (10.10.10.164) 浏览、搜索和下载资源。

## 何时使用

当用户提到以下内容时激活：

- **固件**: "历史固件", "测试固件", "release固件", "烧写镜像", "update.img"
- **SDK**: "SDK下载", "Android SDK", "Linux SDK", "RTOS SDK", "完整SDK包"
- **补丁**: "补丁包", "补丁集", "PATCHSETS", "SDK补丁", "内核补丁"
- **测试**: "测试资料", "品测资料", "验证固件", "竞品分析"
- **工具**: "烧写工具", "RKDevTool", "FactoryTool", "升级工具", "Pin配置工具"
- **驱动**: "WiFi驱动", "蓝牙驱动", "Realtek驱动", "Broadcom驱动"
- **AI**: "RKNN模型", "rknn-toolkit", "rockface", "AI测试"
- **服务器**: "内网共享", "Samba服务器", "10.10.10.164", "公共网盘"

**示例**:
- "帮我找一下 RK3588 的 Linux SDK"
- "下载最新的烧写工具"
- "有没有 RTL8822CS 的 WiFi 驱动"
- "找一下 Android 14 的 SDK 包"

## 核心存储区速查

### Android SDK (按版本)

| 共享 | Android版本 | 芯片支持 |
|------|------------|---------|
| `V_Repository` | Android 15 | RK3576, RK3588, RK356X |
| `U_Repository` | Android 14 | RK3576, RK3588, RK356X, RK3562 |
| `T_Repository` | Android 13 | RK3326~RK3588 |
| `S_Repository` | Android 12 | RK3326~RK3588 |
| `R_Repository` | Android 11 | RK3326~RK3588 |
| `Q_Repository` | Android 10 | RK3126C~RK3399 |
| `Pie_Repository` | Android 9 | PX30, RK3326, RK3399Pro, RK3528 |

### 其他重要存储

| 共享 | 内容 |
|------|------|
| `Linux_Repository` | Linux SDK、固件、AI/LLM、发行版 (按芯片分目录) |
| `Common_Repository` | SDK存档、RKNN工具包、工具链、测试资料 |
| `TOOLS_Repository` | 开发工具 `windows/`(烧写工具等), `linux/`, `mac/` |
| `WIFI_BT_Repository` | `Broadcom/`, `Realtek/`, `Qualcomm/`, `MediaTek/` |
| `RTOS_Repository` | RTOS SDK (RK2106, RK2108, RK3308_AMP等) |

## 使用脚本

脚本位置: `scripts/samba_browser.py`

> [!IMPORTANT]
> **工作目录规则**: 所有脚本必须在**用户的工作目录**执行，使用脚本的**绝对路径**调用。
> - 下载的文件会保存在**当前工作目录**
> - 不要 cd 到 skill 目录执行脚本

### 列出共享

```bash
python3 /path/to/rk-samba-share/scripts/samba_browser.py --shares
```

### 浏览目录

```bash
# 列出共享根目录
python3 /path/to/rk-samba-share/scripts/samba_browser.py --list Linux_Repository

# 列出子目录
python3 /path/to/rk-samba-share/scripts/samba_browser.py --list Linux_Repository RK3588
python3 /path/to/rk-samba-share/scripts/samba_browser.py --list TOOLS_Repository windows
```

### 搜索文件

```bash
# 在指定共享搜索
python3 /path/to/rk-samba-share/scripts/samba_browser.py --search "rknn" --share Common_Repository

# 在所有共享搜索 (较慢)
python3 /path/to/rk-samba-share/scripts/samba_browser.py --search "升级工具" --max-depth 2
```

### 下载文件

```bash
# 下载目录 (打包为tar)
python3 /path/to/rk-samba-share/scripts/samba_browser.py --download TOOLS_Repository "windows/android_tool"

# 下载文件
python3 /path/to/rk-samba-share/scripts/samba_browser.py --download Common_Repository "RK_SDK/RK3288_ANDROID8.1-SDK.tar.gz"
```

## 常用资源路径

### 开发工具 (TOOLS_Repository/windows/)

| 工具 | 路径 | 最新版本 | 说明 |
|------|------|---------|------|
| 烧写工具 | `android_tool/` | RKDevTool v3.37 | 支持所有芯片包括RK3538 |
| USB驱动 | `driver_assistant/` | DriverAssistant v5.14 | 必须先安装驱动 |
| 工厂工具 | `FactoryTool/` | - | 批量烧写 |
| 升级工具 | `upgrade_tool/` | - | 命令行升级工具 |
| SoC工具包 | `SocToolKit/` | - | 综合工具 |

### AI/NPU (Common_Repository/rknn/)
- `rknn-toolkit2/` - RKNN Toolkit 2
- `rockface/` - 人脸识别 SDK
- `rockx/` - RockX AI SDK

### Linux 固件 (Linux_Repository/)
- `RK3588/3_固件/` - RK3588 固件
- `RK3576/` - RK3576 相关
- `0_Release-Images/` - 发布固件

## 典型工作流示例

### 下载烧写工具支持新芯片

```bash
# 1. 查看可用版本
python3 /path/to/rk-samba-share/scripts/samba_browser.py --list TOOLS_Repository "windows/android_tool"

# 2. 下载最新版本 (支持 RK3538 等新芯片)
python3 /path/to/rk-samba-share/scripts/samba_browser.py --download TOOLS_Repository "windows/android_tool/RKDevTool_v3.37_for_window.zip"

# 3. 下载 USB 驱动
python3 /path/to/rk-samba-share/scripts/samba_browser.py --download TOOLS_Repository "windows/driver_assistant/DriverAssitant_v5.14.zip"
```

## 注意事项

- 需要在 Rockchip 内网环境
- 使用 `rkguest` 账户访问 (脚本已内置)
- 大文件下载可能需要较长时间
- 更详细的目录结构参见 `references/directory_guide.md`

