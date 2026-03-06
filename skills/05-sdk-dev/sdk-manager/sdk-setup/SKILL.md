---
name: sdk-setup
description: 准备Rockchip SDK开发环境。当用户提到需要在RK芯片(RK3588/RK3568/RK3576等)上工作，使用某个操作系统版本(Android/Linux/RTOS等)调试问题时使用。提供SDK下载地址或者自动创建工作空间并挂载或下载SDK。
allowed-tools: Read, Write, Bash, Glob, Grep, AskUserQuestion
---

# SDK环境准备技能

根据芯片型号和操作系统需求，提供Rockchip SDK下载地址查询和代码下载功能。

## 何时使用

当用户提到以下内容时激活：

### 下载地址查询
- "告诉我RK3128 BOX 7.1对外SDK地址"
- "RK3328 Android 10.0的repo命令是什么"
- "哪里可以下载RK3588 Android 12.0 SDK"
- "Rockchip_RK3576_Android11_CloudDesk_SDK_Release的下载信息"

### SDK代码下载
- "我要下载RK3328 Android 10.0 SDK"
- "帮我设置RK3588 Android 12.0开发环境"
- "下载并准备RK3128 BOX 7.1 SDK"
- "我要在RK3588 A14 SDK上看媒体播放的问题"

**关键词识别**:
- **查询类**: 告诉我、下载地址、repo命令、哪里下载、SDK信息
- **下载类**: 下载、设置、准备、开发环境、查看代码、编译SDK

## 核心流程

### 步骤1: 解析需求

从用户请求中提取：
- **请求类型**: 查询地址 vs 下载SDK
- **芯片型号**: RK3588、RK3576、RK3568、RK3562、RK3399、RK3128、RK3328 等
- **操作系统类型**: Android、Linux、RTOS 等
- **操作系统版本**: Android的14/13/12/11/10/9/8/7, Linux的内核版本
- **发布类型**: internal/release（从请求词判断，默认：internal）
- **SDK类型**: BOX、Tablet、NVR、IPC、CloudDesk等
- **问题领域**: media、camera、display 等（仅用于下载时的工作空间命名）

**查询vs下载判断**:
- **查询类词汇**: "告诉我"、"地址"、"repo命令"、"哪里下载"、"SDK信息" → 只提供下载地址
- **下载类词汇**: "下载"、"设置"、"准备"、"开发环境"、"查看代码" → 提供下载并询问是否执行

如果缺少关键信息（芯片或操作系统），使用 **AskUserQuestion** 询问用户。

### 步骤2: 确定SDK来源

#### 对外SDK (release) → Samba扫描
判断条件：
- 用户明确提到"对外SDK"
- 芯片型号为RK3128、RK3328等较老型号
- 明确的BOX版本（RK3128 BOX 7.1）

#### 内部SDK (internal) → Wiki查询
判断条件：
- 新型号芯片（RK3588、RK3576、RK356x等）
- 高版本Android（12.0、13.0、14.0等）
- 用户未明确指定对外版本

### 步骤3: 执行相应操作

#### 流程A: 仅查询下载地址

如果用户请求类型为查询，执行以下步骤：

1. **对外SDK → 使用 rk-samba-share 技能查询**:

   **SDK 存储位置**: `//10.10.10.164/Common_Repository/RK_SDK/`

   ```bash
   # 方法1: 直接列出 SDK 目录
   python3 /path/to/rk-samba-share/scripts/samba_browser.py --list Common_Repository RK_SDK

   # 方法2: 使用 --path 参数在 RK_SDK 目录下搜索特定芯片（推荐，更快）
   python3 /path/to/rk-samba-share/scripts/samba_browser.py --search "{芯片}" --share Common_Repository --path RK_SDK --max-depth 1
   ```
   - 使用 samba_browser.py 查询 Samba 服务器
   - 过滤和识别匹配的 SDK（格式：`{芯片}_ANDROID{版本}_SDK_{日期}`）
   - 下载相关 PDF 文档提取 repo init 命令

2. **内部SDK → Wiki查询**:
   ```bash
   grep -r "repo init" /data/rk-tech-kb/documents/wiki/developer_guide/sdk_development/sdk_projects/
   ```
   - 查找匹配的wiki文档
   - 提取repo init命令和下载信息

3. **格式化输出**:
   - 清晰展示SDK信息（芯片、版本、类型）
   - 提供完整的repo init命令
   - 说明下载方法和注意事项
   - **询问用户是否需要执行下载**

#### 流程B: 执行SDK下载

如果用户请求类型为下载，执行以下步骤：

1. **优先检查sdk-mount**:
   ```bash
   sdk-mount -L | grep -i "{芯片}" | grep -i "{系统}"
   ```
   - 如果找到匹配项 → 使用sdk-mount快速挂载
   - 注意:MS(MediaStreaming) SDK适用于RK3518/RK3528/RK3576/RK3562/RK3588/RK3538等用于OTT BOX、投影等产品线，如果符合这类产品线优先选择这个MS SDK

2. **对外SDK → 使用 rk-samba-share 技能获取 repo 命令**:

   **SDK 存储位置**: `//10.10.10.164/Common_Repository/RK_SDK/`

   ```bash
   # 使用 --path 参数搜索 SDK（推荐，更快）
   python3 /path/to/rk-samba-share/scripts/samba_browser.py --search "{芯片}" --share Common_Repository --path RK_SDK --max-depth 1

   # 下载 SDK 说明文档（指定完整路径）
   python3 /path/to/rk-samba-share/scripts/samba_browser.py --download Common_Repository "RK_SDK/{SDK目录名}"
   ```
   - 使用 samba_browser.py 查询和下载
   - 从 PDF 文档提取 repo init 命令
   - 创建工作空间并执行下载

3. **内部SDK → Wiki获取repo命令**:
   - 查找wiki文档获取repo命令
   - 创建工作空间并执行下载

### 步骤4: 创建工作空间（仅下载流程）

```bash
# 创建工作空间
mkdir -p ./{芯片}-{系统}{版本}-{问题}-{年月日}/
cd ./{芯片}-{系统}{版本}-{问题}-{年月日}/
```

### 步骤5: 执行SDK下载

**如果使用sdk-mount**:
```bash
sdk-mount -n {项目名称}
```

**如果使用repo命令**:
```bash
# 配置git（如需要）
git config --global user.email "your.email@rock-chips.com"
git config --global user.name "Your Name"

# 执行repo init
repo init --repo-url {repo_url} -u {manifest_url} -b {branch} -m {manifest.xml}

# 同步代码
repo sync -c
```

### 步骤6: 提供总结

**查询结果总结**:
- SDK详细信息
- 完整的repo init命令
- 下载方法和步骤
- 询问是否需要执行下载

**下载结果总结**:
- 工作空间位置和状态
- SDK设置完成情况
- 快速开始命令
- 基于问题领域的后续建议

## 重要说明

1. **渐进式披露**: 仅在需要时才读取详细指南：
   - `guides/mount-sdk.md` - 使用sdk-mount方法时
   - `guides/download-sdk.md` - 从wiki搜索或Samba查询repo命令时
2. **用户选择**: 如果匹配多个SDK版本，使用AskUserQuestion让用户选择。
3. **错误处理**: 如果设置失败，提供清晰的错误信息和手动步骤。
4. **工作空间命名**: 包含日期以避免冲突。格式：`{芯片}-{系统}{版本}-{问题}-{日期}`
5. **SDK优先级**:
   - 首先尝试sdk-mount（快速，使用overlayfs）
   - 然后尝试wiki的repo命令（内部SDK）
   - 最后尝试Samba查询（对外SDK）
6. **无脚本依赖**: 本技能完全基于guides目录的手动操作，不依赖任何Python脚本
7. redmine客户问题，大概率是使用对外(release)的代码进行调试

## 使用示例

### 查询下载地址示例

**示例1**: 用户说"告诉我RK3128 BOX 7.1对外SDK地址"
- 解析：查询请求，RK3128，Android 7.1，对外SDK，BOX类型
- 判断：对外SDK → 使用 rk-samba-share 技能查询
- 执行：`python3 /path/to/rk-samba-share/scripts/samba_browser.py --search "RK3128" --share Common_Repository`
- 结果：返回SDK路径和repo init命令
- 后续：询问"需要我帮您下载这个SDK吗？"

**示例2**: 用户说"RK3328 Android 10.0的repo命令是什么"
- 解析：查询请求，RK3328，Android 10.0，获取repo命令
- 判断：对外SDK → 使用Samba手动查询
- 执行：查询Samba服务器，下载相关PDF，提取repo init命令
- 结果：
  ```bash
  repo init --repo-url ssh://git@www.rockchip.com.cn/repo/rk/tools/repo \
    -u ssh://git@www.rockchip.com.cn/gerrit/rk/platform/manifest \
    -b android-10.0 -m rk3328_box_android10_release.xml
  ```

**示例3**: 用户说"哪里可以下载RK3588 Android 12.0内部SDK"
- 解析：查询请求，RK3588，Android 12.0，内部SDK
- 判断：内部SDK → 使用Wiki查询
- 执行：搜索wiki文档中的repo init命令
- 结果：返回内部SDK的下载地址和方法

### SDK下载示例

**示例4**: 用户说"我要下载RK3328 Android 10.0对外SDK"
- 解析：下载请求，RK3328，Android 10.0，对外SDK
- 判断：对外SDK → 使用Samba手动查询获取repo命令
- 执行：
  1. 查询Samba服务器，下载PDF获取repo init命令
  2. 创建工作空间：`./rk3328-android10-20251124/`
  3. 执行：`repo init` + `repo sync -c`
- 结果：完成SDK下载并设置环境

**示例5**: 用户说"帮我设置RK3588 A14开发环境调试媒体问题"
- 解析：下载请求，RK3588，Android 14，媒体问题
- 检查：`sdk-mount -L` 显示有 `internal_android_14`
- 挂载：使用sdk-mount快速设置
- 工作空间：`./rk3588-a14-media-20251124/`

**示例6**: 用户说"需要RK3576 Linux 6.1内核代码调试相机"
- 解析：下载请求，RK3576，Linux 6.1，相机问题
- 检查：`sdk-mount -L` 显示有 `internal_linux_RK3576`
- 挂载：使用sdk-mount
- 工作空间：`./rk3576-linux-camera-20251124/`

## 典型交互流程

### 查询交互
1. **用户**: "告诉我RK3128 BOX 7.1对外SDK地址"
2. **系统**: 搜索并返回SDK信息和repo命令
3. **系统**: "需要我帮您下载这个SDK吗？"
4. **用户**: "需要" 或 "不需要"

### 下载交互
1. **用户**: "我要下载RK3328 Android 10.0 SDK"
2. **系统**: 获取下载信息
3. **系统**: 自动创建工作空间并执行下载
4. **系统**: 报告下载完成和使用方法
