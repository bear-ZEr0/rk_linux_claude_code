---
name: rk-serial
description: Rockchip 设备串口调试技能。当需要查看串口日志、抓取 kernel log、启动日志分析、FIQ 调试、串口交互命令时，使用此技能通过 SSH 连接远程 Windows/Linux PC 访问串口。支持发送命令并获取输出、后台监听设备启动、FIQ 内核调试等功能。
---

# Rockchip 串口调试

此技能提供通过 SSH 连接远程 PC（Windows 或 Linux）访问 Rockchip 设备串口的完整工作流。

## 何时激活

检测到以下关键词或需求时触发：
- 串口日志 / serial log / uart log
- kernel log / dmesg / boot log
- 串口交互 / serial console
- FIQ 调试 / 内核调试
- U-Boot / bootloader 调试

> [!IMPORTANT]
> **工作目录规则**: 所有辅助脚本必须在**用户的工作目录**执行，使用脚本的**绝对路径**调用。
> - 不要 `cd` 到技能目录执行脚本。

---

## 使用流程

> ⚠️ **重要**：每次使用此技能时，必须先检查是否有已保存的配置！

### Step 0: 检查已保存配置（必须执行）

```bash
python3 <SKILL_PATH>/scripts/serial_helper.py list-profiles
```

**如果有配置**：
1. 向用户展示可用配置列表
2. 询问用户是否使用已有配置
3. 如果用户确认使用，用 `get-profile` 获取配置详情
4. **Windows 平台**：即使使用已有配置，也需询问当前的 COM 端口号（因为 COM 端口经常变化）
5. 使用配置中的 IP/用户名/密码 执行后续操作

**如果没有配置或用户选择新建**：
→ 进入下方的「首次使用引导」流程

---

## 首次使用引导

> 当没有配置或配置失效时，执行此引导流程

### Step 1: 询问平台类型

向用户询问：
> 您连接串口的 PC 是什么操作系统？
> - **Windows** (使用 USB 转串口，端口形如 COM64)
> - **Linux** (使用 USB 转串口，端口形如 /dev/ttyUSB0)

**如果用户选择 Windows**，在收集 SSH 信息之前，必须先询问：

> ⚠️ **Windows SSH 服务确认**
>
> 串口调试需要通过 SSH 连接到 Windows PC。请确认：
> 1. 您的 Windows PC 是否已安装并启动 **OpenSSH 服务器**？
>    - 如果不确定，请打开 **服务管理器**（Win+R 输入 services.msc），查找 "OpenSSH SSH Server" 是否存在且正在运行
>
> 如果尚未开启，请按以下步骤操作：
> 1. 打开 **设置 > 应用 > 可选功能 > 添加功能**
> 2. 搜索并安装 **OpenSSH 服务器**
> 3. 在服务管理器中启动 **OpenSSH SSH Server** 并设置为自动启动
> 4. 确保防火墙允许 22 端口
>
> 或使用 PowerShell（管理员）一键开启：
> ```powershell
> Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
> Start-Service sshd
> Set-Service -Name sshd -StartupType 'Automatic'
> # 如果 SSH 连接超时，请尝试关闭防火墙：
> Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
> ```
>
> **请问您是否已开启 SSH 服务？**

等待用户确认后，再继续 Step 2。

### Step 2: 收集 SSH 连接信息

向用户询问：
> 请提供远程 PC 的 SSH 连接信息：
> 1. IP 地址
> 2. SSH 用户名
> 3. SSH 密码

### Step 3: 测试 SSH 连接

```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 用户名@IP "echo 'SSH connected'"
```

- ✓ 成功 → 继续下一步
- ✗ 失败 → 检查网络连通性、凭证或防火墙拦截

### Step 4: 发现可用串口

**Linux 平台**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null; ls -la /dev/serial/by-id/ 2>/dev/null || echo '未发现串口设备'"
```

**Windows 平台**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"[System.IO.Ports.SerialPort]::GetPortNames()\""
```

列出发现的串口，让用户确认要使用哪个。

### Step 5: 测试串口通信

**Linux 平台**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "python3 -c \"
import serial, time
p = serial.Serial('串口', 1500000, timeout=3)
p.reset_input_buffer()
p.write(b'\r\n')
time.sleep(1)
print(p.read(p.in_waiting or 1024).decode('utf-8', errors='replace'))
p.close()
\""
```

**Windows 平台**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"\& { try { \$p = New-Object System.IO.Ports.SerialPort 串口,1500000,None,8,One; \$p.Open(); \$p.DiscardInBuffer(); \$p.WriteLine(''); Start-Sleep -Seconds 1; Write-Host \$p.ReadExisting() } finally { if(\$p.IsOpen) { \$p.Close() } } }\""
```

- ✓ 看到设备响应（如 `shell@rk3228a_box:/ $`）→ 连接成功，保存配置
- ⚠ 无输出 → 设备可能休眠，尝试多发几次换行
- ✗ 错误 → 检查串口权限、波特率

### Step 6: 保存配置（成功后）

使用辅助脚本保存配置：
```bash
python3 <SKILL_PATH>/scripts/serial_helper.py save-profile \
  --name "profile-name" \
  --host IP \
  --user 用户名 \
  --password "密码" \
  --platform linux/windows \
  --port 串口
```

配置将保存到 `~/.rk-serial/config.json`。

---

## 已有配置使用

### 检查已保存的配置

```bash
python3 <SKILL_PATH>/scripts/serial_helper.py list-profiles
```

### 使用已有配置

1. 从配置获取连接信息
2. **Windows 用户**：因为 COM 端口号经常变化，需要询问当前的端口号
3. 使用对应平台的命令模板执行操作

---

## 必须遵守的规则

### 规则 1：使用 sshpass 进行 SSH 连接

禁止使用普通 `ssh` 命令（会要求交互式输入密码），必须使用 `sshpass -p '密码' ssh ...` 格式。

### 规则 2：Windows 用户名格式

Windows 用户名格式通常为 `COMPUTER\username`，SSH 连接时只使用用户名部分。

例如：`desktop-m1lb8ea\steven` → SSH 用户名为 `steven`

### 规则 3：波特率

Rockchip 设备默认波特率为 `1500000`（150 万，不是 115200）。

### 规则 4：串口资源释放

串口是独占资源，使用后必须释放。所有命令模板都包含资源释放机制。
遇到 `Access Denied` 或 `PermissionError` 时，先执行清理命令释放串口。

### 规则 5：获取 root 权限

每次串口会话开始时，先尝试执行 `su` 获取 root 权限。`reboot` 等命令需要 root 权限才能执行。

### 规则 6：临时文件位置

- **Windows**：使用 `$env:TEMP` 目录（通常为 `C:\Users\<用户名>\AppData\Local\Temp`）
- **Linux**：使用 `/tmp` 目录

---

## Linux 平台命令模板

### 模板 L1：执行命令并获取输出

适用于：`ls`、`dumpsys`、`getprop`、`cat` 等命令

**第一步**：尝试 su 获取 root（失败无影响）
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "python3 -c \"
import serial, time
p = serial.Serial('串口', 1500000, timeout=3)
p.reset_input_buffer()
p.write(b'su\r\n')
time.sleep(2)
print(p.read(p.in_waiting or 1024).decode('utf-8', errors='replace'))
p.close()
\""
```

**第二步**：执行目标命令
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "python3 -c \"
import serial, time
p = serial.Serial('串口', 1500000, timeout=3)
p.reset_input_buffer()
p.write(b'命令\r\n')
time.sleep(3)
print(p.read(p.in_waiting or 4096).decode('utf-8', errors='replace'))
p.close()
\""
```

---

### 模板 L2：捕获开机日志

适用于捕获设备重启/开机的完整日志。

```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "python3 << 'EOF'
import serial
import time

p = serial.Serial('串口', 1500000, timeout=1)
p.reset_input_buffer()

log = ''
start = time.time()
duration = 60  # 监听 60 秒

print('开始捕获日志，持续 60 秒...')
while time.time() - start < duration:
    if p.in_waiting:
        log += p.read(p.in_waiting).decode('utf-8', errors='replace')
    time.sleep(0.05)

p.close()

# 保存日志
with open('/tmp/serial_boot_log.txt', 'w') as f:
    f.write(log)
print(f'日志已保存到 /tmp/serial_boot_log.txt，共 {len(log)} 字符')
EOF"

# 传回本地
sshpass -p '密码' scp -o StrictHostKeyChecking=no 用户名@IP:/tmp/serial_boot_log.txt /tmp/serial_boot_log.txt
cat /tmp/serial_boot_log.txt
```

---

### 模板 L3：发送 reboot 并捕获启动日志

> ⚠️ reboot 需要 root 权限，必须先执行 `su` 再执行 `reboot`

```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "python3 << 'EOF'
import serial
import time

p = serial.Serial('串口', 1500000, timeout=1)
p.reset_input_buffer()

# su 获取 root
p.write(b'su\r\n')
time.sleep(1)

# 发送 reboot
p.write(b'reboot\r\n')
print('已发送 reboot，开始捕获启动日志...')

# 监听 70 秒
log = ''
start = time.time()
while time.time() - start < 70:
    if p.in_waiting:
        log += p.read(p.in_waiting).decode('utf-8', errors='replace')
    time.sleep(0.05)

p.close()

with open('/tmp/serial_reboot_log.txt', 'w') as f:
    f.write(log)
print(f'日志已保存，共 {len(log)} 字符')
EOF"

# 传回分析
sshpass -p '密码' scp -o StrictHostKeyChecking=no 用户名@IP:/tmp/serial_reboot_log.txt /tmp/serial_reboot_log.txt
cat /tmp/serial_reboot_log.txt
```

---

### 模板 L4：FIQ 内核调试

FIQ 是系统最高优先级中断，即使系统死锁也能响应，用于诊断严重故障。

> 📖 完整 FIQ 命令参考见 [fiq_debug_guide.md](references/fiq_debug_guide.md)

**快速诊断**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "python3 << 'EOF'
import serial
import time

p = serial.Serial('串口', 1500000, timeout=3)
p.reset_input_buffer()

# 进入 FIQ 模式
p.write(b'fiq')
time.sleep(0.5)
p.write(b'\r\n')
time.sleep(1)
print(p.read(p.in_waiting or 4096).decode('utf-8', errors='replace'))

# 执行调试命令
for cmd in ['bt', 'regs', 'irqs']:
    p.write(f'{cmd}\r\n'.encode())
    time.sleep(2)
    print(f'=== {cmd} ===')
    print(p.read(p.in_waiting or 8192).decode('utf-8', errors='replace'))

# 退出 FIQ
p.write(b'console\r\n')
time.sleep(1)
print(p.read(p.in_waiting or 1024).decode('utf-8', errors='replace'))

p.close()
EOF"
```

---

## Windows 平台命令模板

### 模板 W1：执行命令并获取输出

**第一步**：尝试 su 获取 root
```bash
timeout 10 sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"\& { try { \$p = New-Object System.IO.Ports.SerialPort 串口,1500000,None,8,One; \$p.Open(); \$p.DiscardInBuffer(); \$p.WriteLine('su'); Start-Sleep -Seconds 2; Write-Host \$p.ReadExisting() } finally { if(\$p.IsOpen) { \$p.Close() } } }\""
```

**第二步**：执行目标命令
```bash
timeout 15 sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"\& { try { \$p = New-Object System.IO.Ports.SerialPort 串口,1500000,None,8,One; \$p.Open(); \$p.DiscardInBuffer(); \$p.WriteLine('命令'); Start-Sleep -Seconds 5; Write-Host \$p.ReadExisting() } finally { if(\$p.IsOpen) { \$p.Close() } } }\""
```

---

### 模板 W2：捕获开机日志

```bash
timeout 70 sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"\& { try { \$p = New-Object System.IO.Ports.SerialPort 串口,1500000,None,8,One; \$p.Open(); \$p.DiscardInBuffer(); \$log = ''; \$start = Get-Date; while(((Get-Date) - \$start).TotalSeconds -lt 60) { if(\$p.BytesToRead -gt 0) { \$log += \$p.ReadExisting() }; Start-Sleep -Milliseconds 50 }; \$log | Out-File -FilePath \$env:TEMP\\serial_boot_log.txt -Encoding UTF8 } finally { if(\$p.IsOpen) { \$p.Close() } }; Write-Host 'Log saved' }\""

# 传回分析
WIN_TEMP=$(sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP 'echo %TEMP%' | tr -d '\r' | tr '\\' '/')
sshpass -p '密码' scp -o StrictHostKeyChecking=no "用户名@IP:${WIN_TEMP}/serial_boot_log.txt" /tmp/serial_boot_log.txt
cat /tmp/serial_boot_log.txt
```

---

### 模板 W3：发送 reboot 并捕获启动日志

```bash
timeout 90 sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"\& { try { \$p = New-Object System.IO.Ports.SerialPort 串口,1500000,None,8,One; \$p.Open(); \$p.DiscardInBuffer(); \$p.WriteLine('su'); Start-Sleep -Seconds 1; \$p.WriteLine('reboot'); \$log = ''; \$start = Get-Date; while(((Get-Date) - \$start).TotalSeconds -lt 70) { if(\$p.BytesToRead -gt 0) { \$log += \$p.ReadExisting() }; Start-Sleep -Milliseconds 50 }; \$log | Out-File -FilePath \$env:TEMP\\serial_reboot_log.txt -Encoding UTF8 } finally { if(\$p.IsOpen) { \$p.Close() } }; Write-Host 'Log saved' }\""

# 传回分析
WIN_TEMP=$(sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP 'echo %TEMP%' | tr -d '\r' | tr '\\' '/')
sshpass -p '密码' scp -o StrictHostKeyChecking=no "用户名@IP:${WIN_TEMP}/serial_reboot_log.txt" /tmp/serial_reboot_log.txt
cat /tmp/serial_reboot_log.txt
```

---

### 模板 W4：FIQ 快速诊断

```bash
timeout 25 sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"\& { try { \$p = New-Object System.IO.Ports.SerialPort 串口,1500000,None,8,One; \$p.Open(); \$p.DiscardInBuffer(); \$p.Write('fiq'); Start-Sleep -Milliseconds 500; \$p.WriteLine(''); \$p.WriteLine('bt'); \$p.WriteLine('regs'); \$p.WriteLine('irqs'); \$p.WriteLine('console'); Start-Sleep -Seconds 10; Write-Host \$p.ReadExisting() } finally { if(\$p.IsOpen) { \$p.Close() } } }\""
```

---

## 故障排除

### 串口被占用

**Linux**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "fuser -k 串口"
```

**Windows**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "taskkill /F /IM powershell.exe"
```

### 查看可用串口

**Linux**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "ls -la /dev/ttyUSB* /dev/ttyACM* /dev/serial/by-id/ 2>/dev/null"
```

**Windows**：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "powershell -Command \"[System.IO.Ports.SerialPort]::GetPortNames()\""
```

### 测试 SSH 连接

```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "echo SSH connected"
```

### Linux 串口权限问题

确保用户在 `dialout` 组：
```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@IP "groups"
# 如果没有 dialout，需要添加：sudo usermod -aG dialout 用户名
```

---

## 常见错误

| 错误信息 | 原因 | 解决方法 |
|---------|------|----------|
| `Access Denied` | 串口被占用 (Windows) | 执行 `taskkill /F /IM powershell.exe` |
| `PermissionError` | 串口被占用/无权限 (Linux) | `fuser -k 串口` 或检查 dialout 组 |
| `Permission denied` | SSH 密码错误 | 确认密码，使用 `sshpass -p` |
| 乱码输出 | 波特率错误 | 确认使用 `1500000` |
| 输出为空 | 设备无输出或等待时间不足 | 增加等待时间 |
| `reboot` 不执行 | 缺少 root 权限 | 先执行 `su` 获取 root |
| `pyserial not found` | Linux 未安装 pyserial | `pip3 install pyserial` |

---

## 配置管理

### 配置文件位置

`~/.rk-serial/config.json`

### 配置格式

```json
{
  "last_used_profile": "linux-dev",
  "profiles": {
    "linux-dev": {
      "platform": "linux",
      "host": "172.16.21.161",
      "username": "cw",
      "password": " ",
      "serial_port": "/dev/ttyUSB0",
      "baud_rate": 1500000,
      "last_success": "2025-12-20T10:40:00+08:00"
    }
  }
}
```

> **注意**：Windows 的 COM 端口号不保存，因为经常变化，每次使用时询问用户。

### 辅助脚本

```bash
# 列出所有配置
python3 <SKILL_PATH>/scripts/serial_helper.py list-profiles

# 测试 SSH 连接
python3 <SKILL_PATH>/scripts/serial_helper.py test-ssh --host IP --user 用户名 --password "密码"

# 发现串口
python3 <SKILL_PATH>/scripts/serial_helper.py discover-ports --host IP --user 用户名 --password "密码" --platform linux

# 测试串口通信
python3 <SKILL_PATH>/scripts/serial_helper.py test-serial --host IP --user 用户名 --password "密码" --platform linux --port /dev/ttyUSB0

# 保存配置
python3 <SKILL_PATH>/scripts/serial_helper.py save-profile --name "my-profile" --host IP --user 用户名 --password "密码" --platform linux --port /dev/ttyUSB0
```

---

## 参数替换说明

执行命令前，替换以下占位符：
- `密码` → SSH 密码
- `用户名` → SSH 用户名
- `IP` → 远程 PC IP 地址
- `串口` → 串口路径（Linux: `/dev/ttyUSB0`，Windows: `COM64`）
- `命令` → 要在设备上执行的命令

---

## 最佳实践

1. **先尝试 su** - 每次会话开始先尝试获取 root
2. **用完释放** - 每个命令都有资源释放机制
3. **长日志保存文件** - 长时间捕获保存到临时目录，再传回分析
4. **遇到占用** - 先清理再重试
5. **保存配置** - 成功连接后保存配置，下次直接复用
6. **Windows COM 端口** - 每次使用时确认当前端口号
