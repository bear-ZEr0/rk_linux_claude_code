# Redmine 技能使用指南和最佳实践

本指南提供Redmine问题搜索和下载技能的详细使用示例、最佳实践和故障排除信息。

## 渐进式披露用法

### 初级用户（主要工作流程）

对于大多数用户，遵循这个简单的两步流程：

1. **搜索问题**：
   ```bash
   python3 scripts/search_by_keyword.py "HDMI green screen" 30
   ```

2. **获取详情并下载附件**（主要命令）：
   ```bash
   python3 scripts/get_issue_info.py 593691
   ```
   - 自动将所有附件下载到当前工作目录的 `./redmine_issues_593691/`
   - 图片可以直接查看
   - 使用文本编辑器查看日志文件
   - 使用 `git apply` 或 `patch` 命令应用补丁

### 中级用户（高级选项）

当用户需要更多控制时：

**仅查看不下载**：
```bash
python3 scripts/get_issue_info.py 593691 --no-download
```

**指定下载目录**：
```bash
# 工作目录
python3 scripts/get_issue_info.py 593691 --dir /home/cw/work

# 相对路径
python3 scripts/get_issue_info.py 593691 --dir ./downloads
```

## 搜索策略最佳实践

### 有效关键词

**芯片特定搜索**：
- 移除RK前缀：`rk3568` → `3568`，`rk3588` → `3588`
- 结合技术术语：`3568 HDMI`，`3588 camera`

**问题特定搜索**：
- 包含错误症状：`"green screen"`、`"no signal"`、`"i2c timeout"`
- 添加上下文：`"HDMI display"`、`"camera focus"`、`"boot fail"`

### 搜索结果优先级

1. **状态优先级**：Resolved > Confirmed > New
2. **优先级**：High > Normal > Low
3. **时效性**：最近的更新优先
4. **附件**：包含补丁、日志、截图的问题

## 附件类型处理

### 图片文件（PNG、JPG、GIF）
- **用途**：视觉问题对比、UI问题
- **查看**：`eog image.png`、`feh image.png`
- **分析**：与当前问题截图对比

### 日志文件（LOG、TXT）
- **用途**：调试信息、崩溃报告
- **查看**：`less log.txt`、`grep -i error log.txt`
- **分析**：查找错误模式、堆栈跟踪

### 补丁文件（PATCH、DIFF）
- **用途**：代码修复、驱动更新
- **应用**：`git apply fix.patch`、`patch -p1 < fix.patch`
- **验证**：检查补丁与当前代码库的相关性

### 压缩文件（ZIP、TAR.GZ）
- **用途**：完整的调试包
- **解压**：`unzip package.zip`、`tar -xzf package.tar.gz`
- **内容**：可能包含日志、补丁、配置文件

### 代码文件（C、H、CPP）
- **用途**：完整源码文件对比
- **查看**：`vim file.c`、`diff file.c original.c`
- **分析**：与本地实现对比

## 目录管理

### 默认下载结构
```
./redmine_issues_593691/
├── screenshot.png          # 截图
├── logcat.txt             # Android日志
├── fix.patch              # 补丁
└── debug_info.zip         # 压缩包
```

### 自定义目录结构
```
/projects/hdmi_debug/
└── redmine_issue_593691/  # 问题特定子目录
    ├── clipboard-*.png     # 截图
    ├── dw_hdmi.c          # 源文件
    └── *.patch            # 补丁
```

## 性能优化

### 网络考虑
- 使用稳定网络连接下载大文件
- 下载失败自动重试
- 文件完整性验证防止下载损坏文件

### 存储管理
- 监控大文件下载的磁盘空间
- 使用 `--dir` 参数组织存储
- 清理旧下载：`rm -rf ./redmine_issues_*`

### 批量处理
- 使用共同目录处理相关问题
- 使用脚本循环自动批量处理
- 完成后归档研究结果

## API配置

此技能使用以下Redmine API端点：
- **搜索**：`https://10.10.10.70/search.json`
- **问题详情**：`https://10.10.10.70/issues/{id}.json`
- **附件下载**：`https://10.10.10.70/attachments/download/{id}/{filename}`

API访问已在脚本中预配置身份验证令牌。