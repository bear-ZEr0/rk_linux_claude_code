# 串口调试详细设置指南

本文档提供 Windows 和 Linux PC 上配置串口调试环境的详细步骤。

## Windows PC 设置

### 1. 检查并安装 SSH 服务

```powershell
# 检查 SSH 服务状态
Get-Service sshd

# 如果提示找不到服务，安装 OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# 启动 SSH 服务
Start-Service sshd

# 设置开机自启
Set-Service -Name sshd -StartupType 'Automatic'
```

### 2. 配置防火墙

```powershell
netsh advfirewall firewall add rule name="OpenSSH" dir=in action=allow protocol=TCP localport=22
```

### 3. 获取连接信息

```powershell
# IP 地址
ipconfig

# 用户名（取反斜杠后面的部分）
whoami
```

### 4. 查找串口

```powershell
# 列出所有串口
mode

# 或使用 PowerShell
[System.IO.Ports.SerialPort]::GetPortNames()
```

### 5. 设置中文 UTF-8 编码

```powershell
chcp 65001
```

## Linux PC 设置

### 1. 检查 SSH 服务

```bash
# 检查状态
systemctl status sshd

# 启动服务
sudo systemctl start sshd

# 设置开机自启
sudo systemctl enable sshd
```

### 2. 获取连接信息

```bash
# IP 地址
ip addr
# 或
hostname -I

# 用户名
whoami
```

### 3. 查找串口

```bash
# 列出 USB 串口
ls /dev/ttyUSB*

# 或查看内核日志
dmesg | grep tty
```

### 4. 串口权限

```bash
# 添加用户到 dialout 组
sudo usermod -a -G dialout $USER

# 重新登录后生效
```

## 常用串口工具

### Windows

- **PowerShell + System.IO.Ports.SerialPort**（推荐，无需安装）
- **PuTTY**
- **SecureCRT**

### Linux

- **minicom**（推荐，支持交互）
  ```bash
  minicom -D /dev/ttyUSB0 -b 1500000
  ```
- **screen**
  ```bash
  screen /dev/ttyUSB0 1500000
  ```
- **cat**（只读）
  ```bash
  cat /dev/ttyUSB0
  ```

## 故障排除

### SSH 连接失败

1. 检查网络连通性：`ping <ip>`
2. 检查 SSH 服务：`systemctl status sshd`（Linux）或 `Get-Service sshd`（Windows）
3. 检查防火墙规则

### 串口找不到

1. 确认 USB 转串口线已插入
2. 检查驱动是否安装（Windows 设备管理器）
3. 检查 USB 供电是否正常

### 串口被占用

Windows:
```powershell
# 查看占用串口的进程
tasklist | findstr powershell

# 强制结束
taskkill /F /IM powershell.exe
```

Linux:
```bash
# 查看占用串口的进程
fuser /dev/ttyUSB0

# 强制结束
sudo kill -9 <pid>
```

### 乱码问题

1. 确认波特率正确（Rockchip 默认 1500000）
2. Windows 运行 `chcp 65001` 设置 UTF-8
3. 检查数据位（8）、停止位（1）、校验（None）
