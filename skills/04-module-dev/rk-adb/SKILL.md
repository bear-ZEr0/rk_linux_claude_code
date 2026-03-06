---
name: rk-adb
description: Rockchip 设备 ADB 连接技能。支持本地网络 ADB 和通过 SSH 连接远程 Windows/Linux PC 的 USB ADB。当用户需要：推送文件到设备、抓取 kernel log/系统日志、重启设备、执行 adb shell 命令、查看硬件状态时，使用此技能确保 ADB 连接可用。
---

# Rockchip ADB 连接

此技能帮助用户连接 Rockchip Linux 设备，支持两种模式：
1. **本地模式**：设备与终端同网段，直接网络 ADB
2. **远程模式**：通过 SSH 连接远程 PC（Windows/Linux），PC 与设备 USB 连接

## 何时激活

检测到以下需求时触发：
- 推送文件 / adb push / adb pull
- 抓取日志 / kernel log / dmesg / journalctl
- 重启设备 / reboot
- 执行 shell 命令 / adb shell
- 查看硬件状态 / i2c / gpio / io

> [!IMPORTANT]
> **工作目录规则**: 所有辅助脚本必须在**用户的工作目录**执行，使用脚本的**绝对路径**调用。
> - 不要 `cd` 到技能目录执行脚本。
> - 这样可以确保生成的 wrapper 和配置文件保存在当前项目目录下。

---

## 使用流程

> ⚠️ **重要**：每次使用此技能时，必须先检查是否有已保存的配置！

### Step 0: 检查已保存配置（必须执行）

```bash
python3 <SKILL_PATH>/scripts/adb_helper.py list-profiles
```

**如果有配置** → 询问用户是否复用，确认后生成 wrapper 或直接使用配置信息

**如果没有配置** → 进入「首次使用引导」

---

## 首次使用引导

### Step 1: 确定连接模式

> 请选择 ADB 连接方式：
> 1. **本地网络 ADB** - 设备与终端在同一网段
> 2. **远程 USB ADB** - 设备通过 USB 连接到远程 Windows/Linux PC

### Step 2a: 本地模式

```bash
adb connect <设备IP>:5555
adb devices
```

### Step 2b: 远程模式

询问远程 PC 操作系统（Windows/Linux）。

**Windows 用户**需先确认：
1. 已开启 OpenSSH 服务器
2. **防火墙已允许 SSH 连接**（如果连接超时，尝试关闭防火墙）

收集 SSH 信息后测试连接：
```bash
python3 <SKILL_PATH>/scripts/adb_helper.py test-ssh --host IP --user 用户名 --password "密码"
python3 <SKILL_PATH>/scripts/adb_helper.py discover-devices --host IP --user 用户名 --password "密码"
```

### Step 3: 保存配置

```bash
python3 <SKILL_PATH>/scripts/adb_helper.py save-profile \
  --name "profile-name" \
  --host IP --user 用户名 --password "密码" \
  --platform linux/windows
```

---

## 无感使用远程 ADB（推荐）

> 通过 ADB wrapper，可以像使用本地 adb 一样操作远程设备，无需手动处理 SSH。

### 生成 Wrapper

```bash
python3 <SKILL_PATH>/scripts/adb_helper.py generate-wrapper --profile "profile-name"
```

### 使用 Wrapper

```bash
./adb devices
./adb shell getprop ro.build.fingerprint
./adb pull /sdcard/test.txt ./
./adb push ./file.apk /sdcard/
./adb logcat -d > logcat.txt
```

### 支持的命令

| 命令 | 处理方式 |
|-----|---------|
| `pull` | 先拉取到远程 PC 临时目录，再 scp 到本地 |
| `push` | 先 scp 到远程 PC 临时目录，再 push 到设备 |
| 其他 | 直接通过 SSH 转发执行 |

### 切换 Profile

```bash
# 重新生成 wrapper
python3 <SKILL_PATH>/scripts/adb_helper.py generate-wrapper --profile "other-profile"

# 或使用环境变量
ADB_PROFILE="other-profile" ./adb devices
```

---

## 本地模式常用命令

| 操作 | 命令 |
|------|------|
| 推送文件 | `adb push <本地路径> <设备路径>` |
| 拉取文件 | `adb pull <设备路径> <本地路径>` |
| 查看系统信息 | `adb shell uname -a` |
| 查看发行版 | `adb shell cat /etc/os-release` |
| 抓取 kernel log | `adb shell dmesg` |
| 查看系统日志 | `adb shell journalctl -n 100` |
| 查看服务状态 | `adb shell systemctl status <服务名>` |
| 重启设备 | `adb shell reboot` |
| 查看磁盘空间 | `adb shell df -h` |
| 查看内存使用 | `adb shell free -h` |
| 查看进程列表 | `adb shell ps aux` |
| I2C 设备扫描 | `adb shell i2cdetect -y <bus>` |
| 读取寄存器 | `adb shell io -4 <地址>` |
| 查看 GPIO | `adb shell cat /sys/kernel/debug/gpio` |

---

## 故障排除

### 本地模式连接失败

1. **检查 USB 连接**：确认 USB 线连接正常，设备已开机
2. **检查 ADB 服务**：设备端需要运行 adbd 服务
3. **检查网络 ADB**：`ping <设备IP>` 和 `nc -zv <设备IP> 5555`

### 远程模式连接失败

```bash
# 测试 SSH
python3 <SKILL_PATH>/scripts/adb_helper.py test-ssh --host IP --user 用户名 --password "密码"

# 发现设备
python3 <SKILL_PATH>/scripts/adb_helper.py discover-devices --host IP --user 用户名 --password "密码"
```

### Windows SSH 未开启

使用 PowerShell（管理员）：
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# 警告：如果连接失败，可能是防火墙拦截。
# 尝试关闭防火墙（仅测试用）：
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# 或仅允许 SSH 端口（推荐）：
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

---

## Windows 远程 PC 注意事项

> ⚠️ 通过 SSH 连接 Windows 远程 PC 时，命令在 Windows cmd 环境执行，与 Linux 行为不同。

### 1. 避免在 Windows 上使用 grep

Windows 没有 `grep` 命令。过滤输出应在**本地 Linux 端**进行：

```bash
# ❌ 错误：grep 在 Windows 上执行，会报错
./adb shell "getprop | grep hdr"

# ✅ 正确：adb shell 输出后，在本地 grep
./adb shell getprop 2>/dev/null | grep -i hdr
```

### 2. 处理乱码输出

Windows SSH 返回的中文可能显示为乱码（编码问题），这是正常的，不影响功能。

### 3. 使用 adb shell 内置命令过滤

如需在设备端过滤，使用 Android shell 自带的工具：

```bash
# 在 Android shell 内使用 grep（设备上有）
./adb shell "getprop | grep ro.build"

# 查看 DRI 节点（HDR 状态）
./adb shell "cat /d/dri/0/summary"
```

---

## 常见错误

| 错误 | 原因 | 解决 |
|-----|------|-----|
| `Permission denied` | SSH 密码错误 | 确认密码 |
| `Connection refused` | SSH 未开启 | 开启远程 PC 的 SSH 服务 |
| `no devices found` | 无 ADB 设备 | 检查 USB 连接和设备授权 |
| `device unauthorized` | 设备未授权 | 在设备上确认调试授权弹窗 |
| `adb: command not found` | ADB 未安装 | 在远程 PC 安装 ADB |
| `'grep' 不是内部或外部命令` | Windows 无 grep | 在本地端 pipe grep |
| 乱码输出 | Windows 编码问题 | 正常现象，不影响功能 |

---

## 辅助脚本命令

```bash
python3 <SKILL_PATH>/scripts/adb_helper.py list-profiles      # 列出配置
python3 <SKILL_PATH>/scripts/adb_helper.py get-profile        # 获取配置详情
python3 <SKILL_PATH>/scripts/adb_helper.py generate-wrapper   # 生成 wrapper
python3 <SKILL_PATH>/scripts/adb_helper.py test-ssh           # 测试 SSH
python3 <SKILL_PATH>/scripts/adb_helper.py discover-devices   # 发现设备
python3 <SKILL_PATH>/scripts/adb_helper.py test-adb           # 测试 ADB
python3 <SKILL_PATH>/scripts/adb_helper.py exec               # 执行命令
```

> 如需手动构造 SSH/ADB 命令，参见 [references/manual_commands.md](references/manual_commands.md)

---

## 配置文件格式

`~/.rk-adb/config.json`:

```json
{
  "last_used_profile": "lab-windows",
  "profiles": {
    "lab-windows": {
      "platform": "windows",
      "host": "172.16.21.200",
      "username": "admin",
      "password": "password123",
      "device_serial": "ABCD1234",
      "last_success": "2025-12-30T10:00:00+08:00"
    }
  }
}
```
