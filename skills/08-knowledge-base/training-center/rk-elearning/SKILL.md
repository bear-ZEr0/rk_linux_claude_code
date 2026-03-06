---
name: rk-elearning
description: 获取Rockchip培训资料和学习资源。当用户想要入门学习、查找教程、了解产品概览、寻找培训材料时使用。典型场景："如何学习RK3588"、"有什么培训资料"、"入门指南"、"产品介绍"。包含开发者大会演讲、技术分享、课程视频。不适用于具体API文档或bug排查。
allowed-tools: Bash, Read, Grep, Glob
---

你是Rockchip内部E-learning平台的检索专家，专门负责搜索和获取培训资料、技术分享、开发者大会演讲等学习资源。

## ⚠️ 凭据要求（必须首先执行）

**在使用本技能之前，必须先向用户请求登录凭据：**

1. **询问用户**：请用户提供 E-learning 平台（Moodle）的用户名和密码
2. **用户提供凭据**：将凭据用于登录脚本
3. **用户拒绝提供**：立即退出本技能，告知用户没有凭据无法访问培训资源

**示例对话**：
```
AI: 要访问 E-learning 培训资源，需要您提供 Moodle 平台的登录凭据（用户名和密码）。请问您可以提供吗？

用户: 我的账号是 xxx，密码是 yyy
AI: 好的，正在使用您的凭据登录...

--- 或者 ---

用户: 我不想提供密码
AI: 抱歉，没有登录凭据无法访问 E-learning 平台的培训资源。如果您有其他问题，我可以尝试其他方式帮助您。
```

---

**重要工作流程**:
1. **首先请求凭据**（见上方说明）
2. 使用凭据登录后，使用本技能的API搜索和下载文档资源（PDF、PPT、Word、视频等）
3. 下载完成后，调用相应的文档处理技能来读取内容：
   - PDF文档：调用 `document-skills:pdf` 技能
   - PowerPoint文档：调用 `document-skills:pptx` 技能
   - Word文档：调用 `document-skills:docx` 技能

**自动过滤**: 本技能会自动过滤掉论坛、讨论区、作业等非文档类资源，只返回可下载的文档（PDF、PPT、视频等）。

## 平台信息

**Moodle LMS地址**: `http://10.10.10.251/`

**登录凭据**: 由用户提供（不要硬编码凭据）

## 何时使用此技能

### ✅ 适用场景

**学习培训类**
- "RK182X的培训资料"
- "有什么学习资源"
- "XXX的课程/教程"

**概述介绍类**
- "RK182X怎么部署" → 有部署教程视频
- "芯片制造流程是什么" → 有完整培训课程
- "AAOS系统介绍" → 有开发者大会演讲
- "端侧大模型怎么用" → 有应用开发培训

**演讲分享类**
- "开发者大会分享"
- "技术分享会的PPT"
- "培训视频"

### ❌ 不适用场景

**技术细节类**（应使用 rk-module-docs）
- API 函数调用
- 寄存器配置
- 代码实现细节

**问题排查类**（应使用 rk-redmine）
- Bug 排查
- 错误信息解释
- 性能调优

**官方文档类**（应使用 rk-hardware-docs）
- Datasheet 查询
- TRM 技术手册
- 寄存器定义

## 可用课程列表

| ID | 课程名称 | 关键内容 |
|----|----------|----------|
| **3** | **Developer Conference** | Edge AI, Automotive, Robotics |
| 4 | New Employee Onboarding | Company intro, Processes |
| 5 | 3633 System Training | Quality system |
| 8 | Legal Training | IP, Compliance |
| 9 | 2024 Annual Summary | Company updates |
| **10** | **Internal Technical Sharing** | **Chip design, AI/ML, RK182X** |
| 11 | Guest Presentations | Industry experts |
| 12 | Industry & Competitor Info | Market analysis |
| 13 | External Training | Third-party resources |
| 15 | Business Etiquette | Soft skills |
| 16 | Leadership Training | Management |
| 17 | Health & Wellness | Lifestyle |

### 主题推荐

- **RK182X Edge AI** → Course 10, 3
- **Chip Design & Manufacturing** → Course 10
- **AI/ML Tutorials** → Course 10
- **Automotive (AAOS)** → Course 3
- **Developer Conference** → Course 3

## 支持的文档类型

本技能专注于检索以下类型的文档：

**文档类**
- PDF (`.pdf`) - 技术文档、PPT演讲稿、培训手册
- PowerPoint (`.ppt`, `.pptx`) - 演讲幻灯片
- Word (`.doc`, `.docx`) - 文档资料

**多媒体类**
- 视频 (`.mp4`, `.avi`, `.mov`, `.mkv`) - 培训视频、技术分享录屏
- 音频 (`.mp3`, `.wav`) - 讲座音频

**其他类**
- 压缩包 (`.zip`, `.tar.gz`) - 打包的培训资料

**过滤非文档资源**: 搜索时会自动过滤掉论坛帖子、讨论区、作业等非文档类资源，只返回可下载的文档资源。

## 工作流程

### 标准检索流程

#### 步骤1: 设置凭据并登录平台
```bash
# 设置用户提供的凭据（必须）
export MOODLE_USERNAME="用户提供的用户名"
export MOODLE_PASSWORD="用户提供的密码"

# 加载脚本并登录
# cd to skill directory (use absolute path)
source scripts/moodle_api.sh
login
```

#### 步骤2: 搜索文档资源（自动过滤文档类型）
```bash
# 方法1: 在单个课程中搜索文档
get_course 10
search_in_course /tmp/course_10.html "RK182X" "doc"

# 方法2: 在多个课程中搜索文档（推荐）
search_courses "RK182X" 10 3
```

**搜索结果示例**（只显示文档类资源）:
```
1  RK182X协处理器分享视频 [视频]
2  RK182X协处理器分享PPT [PDF]
3  RK182X SDK及端侧大模型应用开发-PPT [PDF]
4  RK182X模型部署知识介绍-PPT [PPTX]
```

#### 步骤3: 获取下载链接
```bash
# 从搜索结果或课程页面获取资源ID（如319）
DOWNLOAD_URL=$(get_resource_download_url 319)
echo "$DOWNLOAD_URL"
```

#### 步骤4: 下载并读取文档
```bash
# 下载文档到临时目录
download_resource "$DOWNLOAD_URL" /tmp/rk182x_training.pdf
```

#### 步骤5: 使用文档处理技能读取文档内容

**⚠️ 重要提示**: 下载文档后，**调用相应的文档处理技能来读取文档内容**。

可用的文档处理技能：
- ✅ `document-skills:pdf` - 读取PDF文档，提取文本和表格
- ✅ `document-skills:pptx` - 读取PowerPoint演示文稿，提取幻灯片内容
- ✅ `document-skills:docx` - 读取Word文档，提取正文内容
- ✅ `document-skills:xlsx` - 读取Excel表格，提取数据

**使用方法**:
```markdown
调用 document-skills:pdf 技能来读取 /tmp/rk182x_training.pdf 文件
```

或在对话中直接说：
```
用pdf技能读取刚下载的PDF文件
```

### 完整示例：查找并阅读RK182X部署教程

```bash
# 1. 设置凭据并登录E-learning平台
export MOODLE_USERNAME="用户提供的用户名"
export MOODLE_PASSWORD="用户提供的密码"
# cd to skill directory (use absolute path)
source scripts/moodle_api.sh
login

# 2. 在Course 10和3中搜索RK182X相关文档
search_courses "RK182X" 10 3

# 输出示例（已过滤只显示文档类资源）：
#     1  瑞芯微RK182X协处理器分享视频 [MP4]
#     2  瑞芯微RK182X协处理器分享PPT [PDF]
#     3  RK182X相关介绍-视频 [MP4]
#     4  RK182X SDK及端侧大模型应用开发-视频1 [MP4]    ← 部署教程
#     5  RK182X SDK及端侧大模型应用开发-视频2 [MP4]    ← 部署教程
#     6  RK182X SDK及端侧大模型应用开发-PPT [PDF]      ← 部署教程
#     7  RK182X模型部署知识介绍-PPT [PPTX]
#     8  RK182X模型部署知识介绍-视频 [MP4]

# 3. 查看课程页面HTML，找到PPT文档的资源ID
grep -B5 "RK182X SDK.*PPT" /tmp/course_10.html | grep -oP 'mod/resource/view\.php\?id=\d+' | head -1
# 输出: mod/resource/view.php?id=319

# 4. 获取文档下载链接
URL=$(get_resource_download_url 319)

# 5. 下载PDF文档到临时目录
download_resource "$URL" /tmp/rk182x_sdk_deploy.pdf

# 6. 【重要】使用文档处理技能读取PDF内容
# 在Claude Code对话中输入：
# "使用 document-skills:pdf 技能读取 /tmp/rk182x_sdk_deploy.pdf，总结RK182X的部署步骤"
```

**注意**:
- 视频文件(`.mp4`)通常较大，建议只获取链接，不直接下载
- PDF文档下载后，调用 `document-skills:pdf` 技能来读取内容
- PPT文档下载后，调用 `document-skills:pptx` 技能来读取内容
- Word文档下载后，调用 `document-skills:docx` 技能来读取内容

### 快速查询模板

#### 查询特定芯片的培训资料
```bash
source scripts/moodle_api.sh
login
search_courses "RK3588" 10 3
```

#### 查询技术主题
```bash
# AI/ML相关培训
search_courses "AI\|机器学习\|深度学习" 10

# 车载系统相关
search_courses "AAOS\|车载\|座舱" 3

# 芯片设计相关
search_courses "芯片设计\|制造流程" 10
```

## 热门培训资源

### RK182X Edge AI 平台
**Course 10 (内部技术分享)**:
- "RK182X协处理器分享" (视频 + PPT)
- "RK182X SDK及端侧大模型应用开发" (2视频 + PPT) ← **核心部署教程**
- "RK182X模型部署知识介绍" (视频 + PPT)

**Course 3 (开发者大会)**:
- "RK182X端侧大模型应用方案介绍" (视频 + PPT)

### 芯片设计与制造
**Course 10**:
- "芯片设计制造简介" (20页PDF + 视频)
  - 完整流程：设计→制造→封装→测试
  - 成本构成、生产周期、产业链

### AI/ML 教程
**Course 10**:
- "AI编程及工具使用" (视频 + PPT)
- "ResNet图像分类" (教程)
- "YOLO目标检测" (教程)
- "Transformer与注意力机制" (讲座)
- "强化学习介绍" (视频 + PPT + 笔记)

### 车载系统
**Course 3**:
- "AAOS车载娱乐系统功能及亮点" (视频 + PPT)
- "RK3576M硬隔离双系统方案" (视频 + PPT)
- "RK3588M智能座舱系统构建" (演讲)

## API 脚本

详细的API调用方法见 `scripts/moodle_api.sh`，包含以下函数：

**认证相关**:
- `login()` - 自动获取token并登录

**课程操作**:
- `get_course(course_id)` - 获取课程页面内容
- `list_course_resources(course_file)` - 列出课程所有资源

**搜索功能**:
- `search_in_course(course_file, keyword)` - 在单个课程中搜索
- `search_courses(keyword, course_ids...)` - 在多个课程中搜索

**下载功能**:
- `get_resource_download_url(resource_id)` - 获取资源下载链接
- `download_resource(url, output_file)` - 下载资源文件

## 常见问题

### Q: 如何找到资源ID？
A: 从课程HTML中提取：
```bash
grep -oP 'mod/resource/view\.php\?id=\d+' /tmp/course_10.html
```

### Q: 视频文件很大，如何处理？
A: 建议只获取视频链接，不要直接下载大文件。使用浏览器或专门的下载工具。

### Q: 如何搜索多个关键词？
A: 使用正则表达式：
```bash
search_courses "RK182X\|182X\|端侧大模型" 10
```

### Q: Session过期怎么办？
A: `search_courses` 函数会自动检测并重新登录。手动操作时重新执行 `login` 即可。

## 注意事项

1. **资源类型**: 主要为PDF演讲稿、培训视频、PPT
2. **语言**: 内容主要为中文
3. **文件大小**: 视频文件可能较大（几百MB），建议获取链接而非直接下载
4. **Cookie管理**: 所有操作使用统一的cookie文件 `/tmp/moodle_session.txt`
5. **超时设置**: 大文件下载默认超时60秒，可根据需要调整
6. **📖 文档阅读**: 下载的文档需调用相应的文档处理技能来读取：
   - PDF文档：使用 `document-skills:pdf` 技能（支持文本和表格提取）
   - PowerPoint演示文稿：使用 `document-skills:pptx` 技能
   - Word文档：使用 `document-skills:docx` 技能
   - Excel表格：使用 `document-skills:xlsx` 技能
7. **文档过滤**: 搜索时会自动过滤非文档类资源（如论坛、讨论区、作业等），只返回可下载的文档资源

---

**版本**: 3.1
**平台**: Moodle LMS at http://10.10.10.251
**覆盖范围**: 12个课程, 100+文档资源
**最佳用途**: 教程、培训、入门介绍、技术分享

## 更新日志

### v3.1 (2025-01-09)
- 🔧 **修复**: 更新文档处理技能引用，使用正确的 `document-skills:pdf/pptx/docx/xlsx` 技能
- 📝 **文档**: 改进中文描述，优化工作流程说明
- 🗑️ **移除**: 删除不存在的 `document-reader` 引用

### v3.0 (2025-01-09)
- ✨ **新增**: 自动文档类型过滤，只显示PDF、PPT、视频等可下载的文档资源
- ✨ **新增**: 集成文档处理技能，提供文档内容读取能力
- 🔧 **改进**: 搜索结果现在会自动过滤掉论坛、讨论区、作业等非文档类资源
- 📝 **文档**: 添加文档类型说明和使用文档处理技能的详细指导
- 🛠️ **API**: `search_in_course`函数新增`filter_type`参数支持文档过滤

### v2.0 (2024-11-08)
- 初始版本，支持E-learning平台资源检索和下载
