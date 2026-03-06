# Redmine 搜索指南和项目映射

本文档提供完整的搜索策略、关键词模式和Redmine项目映射信息，用于高效查找相关技术问题。

## 核心搜索策略

### 1. 基础搜索模式

#### 芯片特定搜索
- **移除RK前缀**：`rk3568` → `3568`，`rk3588` → `3588`
- **结合技术术语**：`3568 HDMI`，`3588 camera`

#### 问题特定搜索
- **包含错误症状**：`"green screen"`、`"no signal"`、`"i2c timeout"`
- **添加上下文**：`"HDMI display"`、`"camera focus"`、`"boot fail"`

### 2. 项目映射搜索

基于问题类型的专门项目搜索，提高搜索精度：

| 问题类型 | 推荐关键词 | 对应项目ID |
|---------|-----------|-----------|
| 显示问题 | `hdmi`, `屏幕`, `绿屏`, `花屏`, `mipi`, `dsi` | 1178, 1177, 572 |
| Camera问题 | `camera`, `摄像头`, `isp`, `预览`, `拍照` | 1188, 572 |
| 视频编解码 | `video`, `视频`, `编码`, `解码`, `mpp`, `codec` | 1189, 572 |
| 音频问题 | `audio`, `音频`, `声音`, `alsa`, `播放` | 1190, 572 |
| 底层问题 | `kernel`, `uboot`, `boot`, `panic`, `ddr` | 1191, 572 |
| 性能优化 | `bandwidth`, `带宽`, `性能`, `performance` | 1191, 572 |
| 网络问题 | `wifi`, `bluetooth`, `网络`, `蓝牙` | 1187, 572 |
| 应用框架 | `framework`, `app`, `应用`, `android` | 1186, 572 |


## 搜索结果分析策略

### 结果优先级评估
1. **状态优先级**：Resolved > Confirmed > New > Feedback
2. **优先级排序**：High/Urgent > Normal > Low
3. **项目相关性**：优先查看专门项目的结果
4. **附件重要性**：包含补丁、日志、截图的问题优先

### 附件类型分析
- **截图文件**：用于问题对比分析
- **日志文件**：包含错误信息和调试线索
- **补丁文件**：直接的解决方案
- **配置文件**：工作配置示例

## 高级搜索技巧

### 布尔搜索组合
```bash
# HDMI相关问题，排除测试环境
python3 scripts/search_by_keyword.py "HDMI AND signal AND NOT test" 30

# Camera问题，包括预览和拍照
python3 scripts/search_by_keyword.py "camera AND (preview OR capture)" 40

# 音频问题，播放或录音
python3 scripts/search_by_keyword.py "audio AND (playback OR recording)" 35
```

### 版本特定搜索
```bash
# Android版本相关问题
python3 scripts/search_by_keyword.py "3568 Android 11 display" 25
```

## Grep模式用于下载后分析

下载问题后，使用这些grep模式进行深度分析：

```bash
# 查找所有补丁文件
grep -r "patch\|\.diff\|\.patch" ./redmine_issues_*/

# 查找内核相关问题
grep -r "kernel\|dts\|driver" ./redmine_issues_*/

# 查找网络相关问题
grep -r "wifi\|ethernet\|bluetooth\|BT" ./redmine_issues_*/
```

## 常见搜索错误避免

### 不要使用的搜索词
- 过于通用的术语：`"problem"`, `"error"`, `"issue"`
- 带RK前缀的芯片名：`"RK3568"` (应该用 `3568`)
- 过于宽泛的组合：`"device driver"`, `"system issue"`

### 推荐的搜索词
- 具体技术术语：`HDMI`, `camera`, `kernel`, `codec`
- 明确的问题描述：`"green screen"`, `"i2c timeout"`
- 芯片型号+问题：`"3568 HDMI"`, `"3588 camera"`
- 补丁简报专用：`"补丁"`, `"patch"`, `"FIX"`, Change-Id

使用这个搜索指南可以大大提高在Rockchip Redmine系统中找到相关技术问题的效率和准确性。
