# 特殊场景处理策略

## 场景1: 配置项查找

### 问题特征
用户需要找到某个配置项的具体配置方法、位置、参数说明。

### 处理步骤
```
步骤1: 搜索配置项名称
  - 使用 CONFIG_XXX, DT属性名等精确名称
  - 如果用户未提供，从问题中推断可能的配置项

步骤2: 查找配置文件路径
  - 搜索 include/configs/
  - 搜索 *.dts, defconfig
  - 搜索 Kconfig, Makefile

步骤3: 寻找配置示例
  - 查找 diff补丁格式的示例
  - 查找代码片段
  - 查找配置步骤说明

步骤4: 理解配置原因
  - 优先查找 FAQ 章节
  - 查看配置说明文档
  - 理解配置的影响范围
```

### 示例

**用户问题**: "如何配置UBOOT logo占用的内存大小？"

```bash
# 第一步: 广泛搜索
Grep -pattern "logo.*memory|logo.*内存|logo.*size"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode files_with_matches

# 假设找到文档包含 CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES

# 第二步: 精确搜索配置项
Grep -pattern "CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode content
     -n true
     -C 10

# 第三步: 查找配置文件路径
Grep -pattern "include/configs.*\.h"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode content
```

## 场景2: 错误信息定位

### 问题特征
用户遇到错误信息，需要找到原因和解决方法。

### 处理步骤
```
步骤1: 搜索错误信息原文或关键部分
  - 使用错误信息的核心关键词
  - 去除变量部分（如地址、数值）

步骤2: 搜索错误相关的函数名或模块名
  - 从错误栈中提取函数名
  - 识别相关模块

步骤3: 优先查找FAQ或故障排查章节
  - 搜索 "FAQ.*错误关键词"
  - 搜索 "Troubleshooting.*错误关键词"

步骤4: 查找相关的日志输出和调试方法
  - 搜索调试开关
  - 搜索日志分析方法
```

### 示例

**用户问题**: "启动时出现 'drm: failed to allocate buffer' 错误"

```bash
# 第一步: 搜索错误信息
Grep -pattern "failed to allocate buffer"
     -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
     -output_mode files_with_matches

# 第二步: 搜索FAQ章节
Grep -pattern "FAQ.*(allocate|内存|buffer)"
     -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
     -output_mode content
     -C 10

# 第三步: 搜索调试方法
Grep -pattern "debug|调试|log|日志"
     -path 找到的文档
     -output_mode content
```

## 场景3: API/接口查找

### 问题特征
用户需要了解某个API的使用方法、参数说明、返回值等。

### 处理步骤
```
步骤1: 搜索函数名或接口名
  - 使用精确的函数名
  - 使用接口名称

步骤2: 查找头文件定义或接口文档
  - 搜索函数声明
  - 搜索参数说明

步骤3: 寻找使用示例和最佳实践
  - 搜索代码示例
  - 搜索示例程序

步骤4: 阅读相关模块的开发指南
  - 查看模块整体架构
  - 理解API在整体中的作用
```

### 示例

**用户问题**: "如何使用RGA接口进行图像旋转？"

```bash
# 第一步: 搜索API名称
Grep -pattern "rga.*rotate|RGA.*旋转|im.*rotate"
     -path /data/rk-tech-kb/documents/internal-docs/RGA/
     -output_mode files_with_matches

# 第二步: 查找使用示例
Grep -pattern "示例|example|sample.*rotate"
     -path /data/rk-tech-kb/documents/internal-docs/RGA/
     -output_mode content
     -C 15

# 第三步: 查找参数说明
Grep -pattern "参数|parameter.*rotate"
     -path 找到的文档
     -output_mode content
```

## 场景4: 跨模块问题

### 问题特征
问题涉及多个模块的协同工作。

### 处理策略
```
策略: 在多个相关模块目录中并行搜索
  - 识别涉及的所有模块
  - 在每个模块目录中搜索
  - 综合多个模块的信息

验证: 交叉对比不同模块文档中的信息一致性
```

### 示例

**用户问题**: "UBOOT显示logo时屏幕花屏"

```bash
# 识别涉及模块: UBOOT + DISPLAY

# 并行搜索
Grep -pattern "logo.*(花屏|artifact|corrupt)"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode files_with_matches

Grep -pattern "logo.*(花屏|artifact|corrupt)"
     -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
     -output_mode files_with_matches

Grep -pattern "logo.*timing|logo.*配置"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode content
     -C 10

Grep -pattern "timing|时序"
     -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
     -output_mode content
     -C 10
```

## 场景5: 缺失文档

### 问题特征
在相关模块目录中找不到所需信息。

### 降级策略
```
1. 搜索相关模块的通用配置
   - 扩大搜索范围到相关模块

2. 查找类似芯片平台的文档
   - 在 Socs/ 目录下查找其他平台文档
   - 参考相似平台的配置

3. 搜索相关的代码注释和示例
   - 查找代码示例
   - 查看源码注释

4. 建议用户查看源代码或提交工单
   - 明确告知文档缺失
   - 提供替代方案
```

### 示例

**用户问题**: "RK3562的某个新功能配置方法"

```bash
# 第一步: 在RK3562目录搜索
Grep -pattern "新功能关键词"
     -path /data/rk-tech-kb/documents/internal-docs/Dept*/*/Socs/RK3562/
     -output_mode files_with_matches

# 未找到，第二步: 查找相似平台
Grep -pattern "新功能关键词"
     -path /data/rk-tech-kb/documents/internal-docs/Dept*/*/Socs/RK3568/
     -output_mode files_with_matches

# 第三步: 全局搜索
Grep -pattern "新功能关键词"
     -path /data/rk-tech-kb/documents/internal-docs/
     -output_mode files_with_matches
     -head_limit 30
```

## 场景6: 模糊查询

### 问题特征
用户问题不明确，不确定具体要找什么。

### 处理策略
```
优先行动:
1. 提取问题中的所有可能关键词
   - 模块名称
   - 功能描述
   - 问题现象

2. 使用多个关键词组合并行搜索
   - 尝试不同的关键词组合
   - 使用中英文双语搜索

3. 列出找到的多个候选结果
   - 显示所有相关文档
   - 提供简要说明

4. 向用户确认具体需求
   - 询问更具体的信息
   - 根据反馈缩小范围
```

### 示例

**用户问题**: "显示有问题"（非常模糊）

```bash
# 第一步: 广泛搜索显示相关问题
Grep -pattern "FAQ.*(显示|display|屏幕|screen)"
     -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
     -output_mode files_with_matches

# 第二步: 搜索常见显示问题
Grep -pattern "花屏|绿屏|黑屏|不显示|闪烁"
     -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
     -output_mode files_with_matches

# 第三步: 列出常见问题清单
Read 找到的FAQ文档

# 第四步: 向用户确认
# "我在文档中找到以下几种常见显示问题，请问您遇到的是哪一种？
#  1. 启动黑屏
#  2. 显示花屏
#  3. HDMI不显示
#  4. ..."
```

## 通用处理原则

### 1. 渐进式搜索
- 从具体到一般
- 从精确到模糊
- 从单一到组合

### 2. 多层验证
- 在多个文档中确认
- 对比中英文文档
- 检查版本差异

### 3. 上下文完整
- 使用足够的上下文行数
- 理解完整的配置流程
- 注意前置条件和后续步骤

### 4. 透明沟通
- 明确说明搜索过程
- 标注置信度
- 指出不确定的地方

### 5. 提供替代方案
- 文档缺失时提供替代途径
- 建议相关的文档资源
- 必要时建议查看源码
