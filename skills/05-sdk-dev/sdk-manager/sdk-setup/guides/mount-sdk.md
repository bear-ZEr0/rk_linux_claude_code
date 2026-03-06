# 使用sdk-mount设置SDK

本指南详细说明如何使用 `sdk-mount` 工具快速挂载已有的SDK仓库。

## 什么是sdk-mount？

`sdk-mount` 是一个使用overlayfs挂载预下载SDK仓库的工具，它可以：
- 无需完整下载即可快速访问SDK代码
- 拥有具有写入能力的隔离工作空间
- 通过共享只读基础SDK节省磁盘空间

## 可用的SDK

运行 `sdk-mount -L` 可查看所有59个可用SDK，包括：

**Android SDK**:
- 内部版本：`internal_android_9_RK3528`、`internal_android_10`、`internal_android_11`、`internal_android_12`、`internal_android_13`、`internal_android_14`、`internal_android_ms_14`
- 对外版本：`release_android_10_*`、`release_android_11_*`、`release_android_12_*`、`release_android_13`、`release_android_14_*`

**Linux SDK**:
- 内部版本：`internal_linux_RK3308`、`internal_linux_RK3528`、`internal_linux_RK356X`、`internal_linux_RK3576`、`internal_linux_RK3588`、`internal_linux_RV1103B` 等
- 对外版本：`release_linux_RK3308_5.10`、`release_linux_RK3399`、`release_linux_RK3528`、`release_linux_RK356X_5.10`、`release_linux_RK3576`、`release_linux_RK3588` 等

**RTOS SDK**:
- 内部版本：`internal_rtt_RK2118`
- 对外版本：`release_rtt_RK2116`、`release_rtt_RK2118`

## 使用命令

### 交互模式（推荐首次使用）
```bash
sdk-mount
```
显示菜单供选择可用SDK。

### 列出可用SDK
```bash
sdk-mount -L
```

### 非交互式挂载（最新版本）
```bash
sdk-mount -n <显示名称>
```
示例：
```bash
sdk-mount -n internal_android_14
```

### 挂载特定版本
```bash
sdk-mount -n <显示名称> -v <完整版本名>
```
示例：
```bash
sdk-mount -n internal_android_ms_14 -v internal_android_ms_14_20251022_0003
```

### 自定义工作目录
```bash
sdk-mount -n <显示名称> -t <目标目录>
```
在目标目录中创建 `upper/`、`work/` 和 `workspace/` 子目录。

### 卸载
```bash
# 卸载默认workspace
sdk-mount -u

# 卸载指定workspace
sdk-mount -U <workspace路径>
```

## 分步操作流程

### 1. 创建工作空间目录
```bash
mkdir -p ~/workspace/{芯片}-{系统}-{问题}-{日期}/sdk
cd ~/workspace/{芯片}-{系统}-{问题}-{日期}/sdk
```

### 2. 挂载SDK
```bash
sdk-mount -n <匹配的项目名>
```

工具将会：
- 创建 `upper/`、`work/`、`workspace/` 目录
- 使用overlayfs挂载SDK
- 实际工作目录是 `workspace/`

### 3. 在工作空间中工作
```bash
cd workspace/
source build/envsetup.sh  # Android使用
# 或
./build.sh  # Linux使用
```

### 4. 完成工作后
删除工作空间之前：
```bash
cd ~/workspace/{芯片}-{系统}-{问题}-{日期}/sdk
sdk-mount -u  # 或 sdk-mount -U $(pwd)/workspace
```

## 将用户需求匹配到SDK名称

### Android内部SDK

| 用户请求 | sdk-mount名称 |
|---------|--------------|
| RK3588 A14、RK3568 A14、Android 14 | `internal_android_14` |
| RK3588 A14 Media Streaming | `internal_android_ms_14` |
| RK3588 A13、Android 13 | `internal_android_13` |
| RK3588 A12、Android 12 | `internal_android_12` |
| RK3588 A11、Android 11 | `internal_android_11` |
| RK3588 A10、Android 10 | `internal_android_10` |
| RK3528 A9、RK3566 A9 | `internal_android_9_RK3528` 或 `internal_android_9_RK3566` |
| RK3576 CloudDesk A11 | `internal_android_clouddesk_11_RK3576` |

### Android对外SDK

| 用户请求 | sdk-mount名称 |
|---------|--------------|
| RK3576 A14 对外版 | `release_android_14_RK3576` |
| Android 14 All 对外版 | `release_android_14_all` |
| Android 14 Media Streaming 对外版 | `release_android_14_media_streaming` |
| Android 13 对外版 | `release_android_13` |
| RK3588 A12 对外版 | `release_android_12_RK3588` |
| Android 12 Common 对外版 | `release_android_12_COMMON` |

### Linux SDK

| 用户请求 | sdk-mount名称 |
|---------|--------------|
| RK3588 Linux | `internal_linux_RK3588` 或 `release_linux_RK3588` |
| RK3576 Linux | `internal_linux_RK3576` 或 `release_linux_RK3576` |
| RK356X Linux (RK3568/3566) | `internal_linux_RK356X` 或 `release_linux_RK356X_5.10` |
| RK3528 Linux | `internal_linux_RK3528` 或 `release_linux_RK3528` |
| RK3588 NVR | `internal_linux_RK3588_NVR` 或 `release_linux_RK3588_NVR` |
| RK3576 NVR | `internal_linux_RK3576_NVR` 或 `release_linux_RK3576_NVR` |

### RTOS SDK

| 用户请求 | sdk-mount名称 |
|---------|--------------|
| RK2118 RTOS | `internal_rtt_RK2118` 或 `release_rtt_RK2118` |
| RK2116 RTOS | `release_rtt_RK2116` |

## 实现指南

使用sdk-mount实现SDK设置时：

1. **解析用户请求** 提取芯片型号、操作系统类型、版本
2. **映射到sdk-mount名称** 使用上面的表格
3. **运行 `sdk-mount -L`** 验证SDK存在
4. **如果有多个匹配**，使用AskUserQuestion让用户选择（例如内部版vs对外版）
5. **先创建工作空间目录**
6. **进入workspace/sdk目录**
7. **执行 `sdk-mount -n <名称>`**
8. **验证挂载** 检查 `workspace/` 子目录是否已填充
9. **向用户报告** 工作空间路径和后续步骤

## 错误处理

如果 `sdk-mount` 失败：
- 检查SDK名称是否完全匹配（区分大小写）
- 确保该位置没有已存在的挂载
- 先尝试 `sdk-mount -u` 清理任何陈旧的挂载
- 检查用户主目录的磁盘空间
- 如果持续出现问题，回退到wiki下载方法

## 注意事项

- sdk-mount使用overlayfs，因此基础SDK是只读的
- 你的修改存储在 `upper/` 目录中
- `workspace/` 是你工作的叠加视图
- 删除工作空间目录前务必先卸载
- 如果不指定 `-t`，默认workspace位置是当前目录
