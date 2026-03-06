# SDK下载指南

本指南说明如何获取和下载不在sdk-mount中的SDK，包括从Wiki文档查询和从Samba服务器获取对外SDK。

## ⚠️ 重要：PDF文件读取方法

**当需要读取PDF文档时，必须使用 `dev-utilities:pdf` 技能，不要直接使用 Read 工具读取PDF文件。**

PDF文档的正确读取方式：
```bash
# 使用 pdf 技能读取
Skill pdf
```

**禁止使用**：
```bash
# ❌ 错误：不要直接读取PDF文件
Read /path/to/document.pdf
```

PDF技能能够正确处理PDF格式、提取文本、表格和图像内容，而直接读取PDF文件会得到乱码或无法解析的内容。

## 何时使用此方法

在以下情况使用此方法：
- SDK不在 `sdk-mount -L` 列表中
- 用户请求挂载列表中没有的特定SDK变体
- 用户需要较旧或专用的SDK版本
- 用户提到sdk-mount未覆盖的特定项目名称
- 用户明确要求**对外发布**的SDK版本
- 需要从PDF文档中获取精确的repo init命令

## 方法选择

### Wiki文档查询（内部SDK）
适用于：
- 新型号芯片（RK3588、RK3576、RK356x等）
- 高版本Android（12.0、13.0、14.0等）
- 用户未明确指定对外版本

### Samba服务器查询（对外SDK）
适用于：
- 用户明确提到"对外SDK"
- 芯片型号为RK3128、RK3328等较老型号
- 明确的BOX版本（RK3128 BOX 7.1）

---

## 方法1: Wiki文档查询（内部SDK）

### Wiki SDK文档位置

所有SDK文档位于：
```
/data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects/
```

主索引文件：
```
/data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects.md
```

### 查找正确的SDK

#### 步骤1: 识别SDK文档文件

根据用户的芯片和操作系统请求，搜索相关文档：

```bash
grep -r "repo init" /data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects/ | grep -i "{芯片}" | grep -i "{系统版本}"
```

**文件命名规则**:
- Android: `rockchip_android{版本}_sdk_developer_guide_cn.md`
- 特定芯片Android: `rockchip_{芯片}_android{版本}_*_sdk_cn.md`
- Linux: `rockchip_{芯片}_linux_sdk_cn.md` 或 `rockchip_{芯片}_linux_{内核版本}_sdk_release_cn.md`
- 特殊变体: 查找关键词如 `ipc`、`nvr`、`clouddesk`、`box` 等

**示例**:
- Android 14: `rockchip_android14_0_sdk_developer_guide_cn.md`
- Android 14 MS: `rockchip_android14_0_ms_sdk_developer_guide_cn.md`
- RK3588 Linux: `rockchip_rk3588_linux_sdk_cn.md`
- RK3576 NVR: `rockchip_rk3576_nvr_sdk_cn.md`
- RV1106 IPC: 查看 `server_management/RV1106_IPC_SDK_Release.md`

#### 步骤2: 读取文档文件

读取匹配的文件以查找 `repo init` 命令：

```bash
# Android 14示例
Read /data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects/rockchip_android14_0_sdk_developer_guide_cn.md
```

查找以下部分：
- "内部开发" - 用于内部SDK
- "对外发布" - 用于对外SDK
- 通常在文档顶部附近

#### 步骤3: 提取repo init命令

文档通常包含：

**内部SDK格式**:
```bash
repo init --repo-url ssh://10.10.10.29:29418/android/tools/repo \
  -u ssh://10.10.10.29:29418/android/platform/manifest \
  -b {分支} -m {manifest.xml}
```

**对外SDK格式**:
```bash
repo init --repo-url https://gerrit.rock-chips.com:8443/repo-release/tools/repo \
  -u https://gerrit.rock-chips.com:8443/{项目}/manifests.git \
  -m {manifest.xml}
```

**Linux SDK格式**:
```bash
repo init --repo-url ssh://10.10.10.29:29418/linux/tools/repo \
  -u ssh://10.10.10.29:29418/linux/rockchip/platform/manifests \
  -b {分支} -m {manifest.xml}
```

### 常用内部SDK Repo命令

#### Android 14 内部版
```bash
repo init --repo-url ssh://10.10.10.29:29418/android/tools/repo \
  -u ssh://10.10.10.29:29418/android/platform/manifest \
  -b rk35/mid/14.0/develop -m Android14.xml
```

#### Android 13 内部版
```bash
repo init --repo-url ssh://10.10.10.29:29418/android/tools/repo \
  -u ssh://10.10.10.29:29418/android/platform/manifest \
  -b rk33/mid/13.0/develop -m rockchip-13.xml
```

#### Linux 内部版 (RK3588)
```bash
repo init --repo-url ssh://10.10.10.29:29418/linux/tools/repo \
  -u ssh://10.10.10.29:29418/linux/rockchip/platform/manifests \
  -b linux -m rk3588_linux_release.xml
```

---

## 方法2: Samba服务器查询（对外SDK）

### 概述

Samba SDK扫描器位于 `//10.10.10.164/Common_Repository/RK_SDK/`，包含Rockchip对外发布的所有SDK。使用smbclient可以手动访问和查询。

### 访问凭证

Samba服务器使用以下凭证：
- 服务器：`//10.10.10.164/Common_Repository`
- 用户名：`rkguest` (只读账号)
- 密码：`rk839919`
- SDK路径：`RK_SDK/`

### 使用smbclient查询SDK

#### 1. 连接到Samba服务器

```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919
```

#### 2. 列出所有SDK

连接后执行：
```bash
cd RK_SDK
ls
```

或者一次性执行：
```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls"
```

#### 3. 按芯片型号搜索

使用grep过滤输出：
```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3588"
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3328"
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3566"
```

#### 4. 按Android版本搜索

```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "android10"
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "android12"
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "android11"
```

#### 5. 组合条件搜索

```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3588.*android12"
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3328.*android10"
```

### 获取SDK详细信息

#### 1. 进入SDK目录

```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK/Rockchip_Android_RK3328_10.0_BOX_SDK_v1.0_Release_20191125; ls"
```

#### 2. 下载PDF文档获取repo命令

```bash
# 退出smbclient或使用新连接下载文件
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK/Rockchip_Android_RK3328_10.0_BOX_SDK_v1.0_Release_20191125; get Rockchip_RK3328_Android10.0_Box_SDK_Release_Alpha_20191125_CN&EN.pdf /tmp/sdk_info.pdf"
```

#### 3. 分析PDF获取repo init命令

**使用 pdf 技能读取PDF文档**，提取其中的repo init命令：
```bash
Skill pdf
```

在pdf技能中打开下载的PDF文件，查找包含"repo init"的部分，复制完整的命令。

### 常用搜索命令示例

#### 热门芯片+版本
```bash
# RK3588系列
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3588"

# RK356x系列
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK356"

# RK3328系列
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3328"
```

#### 特殊用途SDK
```bash
# NVR SDK
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i nvr

# IPC SDK
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i ipc

# 云桌面SDK
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i clouddesk
```

### 典型SDK命名规则

#### Android SDK
- **Box SDK**: 电视盒子设备 (`BOX`)
- **Tablet SDK**: 平板设备 (`TABLET`)
- **MID SDK**: 移动互联网设备 (`MID`)
- **CloudDesk SDK**: 云桌面设备 (`CloudDesk`)

#### Linux SDK
- **通用SDK**: 标准Linux系统
- **NVR SDK**: 网络视频录像机 (`NVR`)
- **IPC SDK**: 网络摄像机 (`IPC`)
- **CVR SDK**: 中央视频录像机 (`CVR`)

#### 专用SDK
- **RKNN SDK**: 神经网络推理
- **RKNPU SDK**: 神经网络处理器
- **RKLLM SDK**: 大语言模型
- **Face SDK**: 人脸识别

### 压缩包处理

某些SDK提供压缩包格式：
- **tar.gz/zip**: 完整SDK压缩包
- **分片压缩**: 大文件分割 (如 .tar.gz.001, .tar.gz.002)
- 需要先合并分片，再解压

#### 处理分片压缩包
```bash
# 下载所有分片文件
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK/Rockchip_Android14.0_Express_SDK_Release; mget *.tar.gz.*"

# 合并分片
cat Rockchip_Android14.0_Express_SDK_Release.tar.gz.* > Rockchip_Android14.0_Express_SDK_Release.tar.gz

# 解压
tar -xzf Rockchip_Android14.0_Express_SDK_Release.tar.gz
```

### 常见对外SDK Repo命令格式

#### 标准对外SDK格式
```bash
repo init --repo-url ssh://git@www.rockchip.com.cn/repo/rk/tools/repo \
  -u ssh://git@www.rockchip.com.cn/gerrit/rk/platform/manifest \
  -b android-10.0 -m rk3328_box_android10_release.xml
```

#### Mirror版本命令
```bash
repo init --mirror --repo-url ssh://git@www.rockchip.com.cn/repo/rk/tools/repo \
  -u ssh://git@www.rockchip.com.cn/gerrit/rk/platform/manifest
```

---

## 实施流程

### 1. 创建工作空间
```bash
mkdir -p ./{芯片}-{系统}{版本}-{问题}-{日期}/sdk
cd ./{芯片}-{系统}{版本}-{问题}-{日期}/sdk
```

### 2. 执行repo init

从相应方法复制确切的命令：

```bash
# 如需要配置git
git config --global user.email "your.email@rock-chips.com"
git config --global user.name "Your Name"

# 执行获得的repo init命令
repo init --repo-url {url} -u {manifest_url} -b {branch} -m {manifest}
```

### 3. 同步仓库

```bash
# 对于内部仓库，可能需要特殊repo路径
/home/repohub/repo/repo sync -c

# 或标准repo sync
.repo/repo/repo sync -c
```

**注意**: 同步时间取决于SDK大小和网络速度，可能需要较长时间。

### 4. 验证下载

检查关键目录是否存在：
```bash
ls -la
# 应该看到类似目录：kernel-5.10, u-boot, device, vendor 等
```

## 搜索策略

### 1. 按芯片+操作系统搜索
```bash
# Wiki方法
grep -l "repo init" /data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects/*.md | xargs grep -l "RK3588" | xargs grep -l "Android 14"

# Samba方法
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i "RK3588.*android14"
```

### 2. 按SDK类型搜索
```bash
# IPC SDK (Wiki)
ls /data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/server_management/*IPC*.md

# NVR SDK (Wiki + Samba)
grep -l "nvr" /data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects/*.md
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i nvr
```

### 3. 阅读主索引
阅读 `/data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects.md` 查找特定SDK文档的链接。

## 特殊情况

### IPC/相机SDK
**Wiki方法**：
```
/data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/server_management/
```
如文件：
- `RV1106_IPC_SDK_Release.md`
- `RV1103B_Linux_IPC_SDK_Release.md`
- `RK3588_IPC_SDK_Release.md`

**Samba方法**：
```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i ipc
```

### NVR SDK
**Wiki方法**：查找名称中包含"nvr"的文件：
- `rockchip_rk3588_nvr_sdk_cn.md`
- `rockchip_rk3576_nvr_sdk_cn.md`

**Samba方法**：
```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i nvr
```

### RTOS SDK
**Wiki方法**：查找"rtt"或"rt-thread"：
- `sdk_development/rk1820/` 或类似目录中的文件

**Samba方法**：
```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i rtos
```

### 车载SDK
**Wiki方法**：查找"vehicle"或特定提及：
- `vehicle-sdk.md`

**Samba方法**：
```bash
smbclient '//10.10.10.164/Common_Repository' -U rkguest%rk839919 -c "cd RK_SDK; ls" | grep -i vehicle
```

## 错误处理

### Samba连接问题
1. **SMB连接失败**
   - 检查网络连接到10.10.10.164
   - 确认用户名密码正确：rkguest/rk839919
   - 确认有Samba访问权限
   - 检查防火墙设置

2. **权限问题**
   - rkguest是只读账号，只能下载不能上传
   - 确认路径正确：`RK_SDK/`

### Wiki查询问题
1. **repo init失败**
   - 检查网络连接
   - 验证SSH密钥已配置（内部仓库）
   - 检查用户是否有访问权限
   - 尝试替代repo URL

2. **repo sync失败**
   - 使用 `-j4` 限制并行任务：`repo sync -c -j4`
   - 先尝试同步特定项目
   - 检查磁盘空间
   - 对于内部仓库，使用：`/home/repohub/repo/repo sync -c`

3. **权限被拒**
   - 对外仓库，用户可能需要通过OA申请访问权限
   - 提供wiki中关于如何申请访问权限的说明
   - 对于内部仓库，检查SSH密钥配置

### PDF相关问题

1. **PDF读取失败**
   - 某些PDF可能使用特殊编码或受保护
   - 确保使用 `Skill pdf` 而不是直接Read工具
   - 如果pdf技能无法读取，尝试重新下载文件

2. **无Repo命令**
   - 不是所有SDK都有repo init命令
   - 某些SDK仅提供压缩包格式
   - 在这种情况下查找压缩包下载链接

## 提示

1. **优先选择方法**:
   - 新芯片/高版本 → 优先Wiki
   - 老芯片/明确对外 → 优先Samba
   - 始终先查sdk-mount

2. **使用精确命令**: 除非必要，不要修改URL或分支

3. **注意下载时间**: 告知用户完整SDK下载可能需要30分钟-2小时

4. **同步后验证**: 检查关键目录是否存在

5. **记录来源**: 在README.md中注明使用了哪个wiki页面或Samba路径

## 下载后

repo sync完成后：

1. **验证编译环境**
   ```bash
   source build/envsetup.sh  # Android
   # 或
   cat README.md  # Linux - 通常有编译说明
   ```

2. **在工作空间README中记录**
   - 使用的wiki页面或Samba路径
   - Repo init命令
   - 同步日期
   - 任何特殊注意事项

3. **通知用户**
   - 下载完成
   - SDK大小
   - 构建的后续步骤