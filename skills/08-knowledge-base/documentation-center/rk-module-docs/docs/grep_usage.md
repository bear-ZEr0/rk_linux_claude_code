# Grep工具使用规范

## 两阶段搜索模式

### 阶段1: 文件定位

**目标**: 找到包含相关信息的文档文件

**命令格式**:
```
Grep -pattern "关键词1.*关键词2"
     -path /data/rk-tech-kb/documents/internal-docs/模块目录
     -output_mode files_with_matches
     -i true
     -head_limit 20
```

**参数说明**:
- `pattern`: 使用正则表达式组合多个关键词
- `path`: 指定搜索目录
- `output_mode: files_with_matches`: 只返回文件路径，不显示内容
- `i: true`: 忽略大小写（必须使用）
- `head_limit`: 限制返回文件数量

**示例**:
```bash
# 搜索UBOOT目录下包含"logo"和"memory"的文档
Grep -pattern "logo.*memory|logo.*内存"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode files_with_matches
     -i true
```

### 阶段2: 内容查看

**目标**: 查看具体文档中的相关内容和上下文

**命令格式**:
```
Grep -pattern "配置项名称|关键词"
     -path /data/rk-tech-kb/documents/internal-docs/相关目录
     -output_mode content
     -n true
     -C 10
     -head_limit 20
```

**参数说明**:
- `output_mode: content`: 显示匹配的内容行
- `n: true`: 显示行号（便于引用）
- `C: 5-10`: 显示上下文5-10行（理解完整配置）
- `head_limit`: 限制输出行数避免过多

**示例**:
```bash
# 查看CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES的具体配置
Grep -pattern "CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode content
     -n true
     -C 10
```

## 参数详解

### pattern (必需)

支持ripgrep正则表达式语法：

**基本字符串匹配**:
```
pattern: "logo"  # 简单字符串
```

**OR组合 (|)**:
```
pattern: "logo|LOGO|标志"  # 匹配任意一个
```

**AND组合 (.*)**:
```
pattern: "logo.*memory"  # logo后面跟着memory
pattern: "logo.*memory|logo.*内存"  # 中英文都匹配
```

**标题匹配**:
```
pattern: "^#{1,3}\s.*FAQ"  # 匹配1-3级标题包含FAQ的
```

**配置项匹配**:
```
pattern: "CONFIG_[A-Z_]+"  # 匹配所有CONFIG开头的配置项
```

**路径匹配**:
```
pattern: "include/configs/.*\.h"  # 匹配配置文件路径
```

### path (可选)

指定搜索目录，默认为当前工作目录。

**最佳实践**:
```
# 优先使用具体模块目录
path: "/data/rk-tech-kb/documents/internal-docs/UBOOT/"

# 相关模块目录
path: "/data/rk-tech-kb/documents/internal-docs/DISPLAY/"

# 全局搜索（最后手段）
path: "/data/rk-tech-kb/documents/internal-docs/"
```

### output_mode

三种输出模式：

**files_with_matches** (文件定位阶段):
- 只返回包含匹配的文件路径
- 不显示具体内容
- 适合第一阶段：找到相关文档

**content** (内容查看阶段):
- 返回匹配的具体内容行
- 配合 -C 参数显示上下文
- 适合第二阶段：查看详细信息

**count** (统计模式):
- 返回每个文件的匹配次数
- 用于评估相关性

### i (忽略大小写)

**必须使用**: `i: true`

原因：
- 配置项可能大小写混合 (Config vs CONFIG)
- 中英文混合搜索
- 提高召回率

### n (显示行号)

**推荐使用**: `n: true` (在 output_mode=content 时)

原因：
- 便于引用文档位置 (file_path:line_number)
- 帮助用户快速定位

### -C (上下文行数)

**推荐值**: 5-10

```
C: 5   # 前后各5行，适合简短配置
C: 10  # 前后各10行，适合复杂配置或代码片段
```

**使用场景**:
- 理解配置项的完整说明
- 查看代码示例的完整上下文
- 了解配置的前置条件和后续步骤

### head_limit

**文件定位阶段**: 20
```
head_limit: 20  # 限制返回20个文件
```

**内容查看阶段**: 50-100
```
head_limit: 100  # 限制返回100行内容
```

## 常见搜索模式

### 模式1: 配置项搜索

```bash
# 第一步: 找到包含配置项的文档
Grep -pattern "CONFIG_XXX"
     -path /data/rk-tech-kb/documents/internal-docs/相关模块/
     -output_mode files_with_matches
     -i true

# 第二步: 查看具体配置说明
Grep -pattern "CONFIG_XXX"
     -path 找到的文档路径
     -output_mode content
     -n true
     -C 10
```

### 模式2: FAQ章节搜索

```bash
# 搜索FAQ章节
Grep -pattern "^#{1,3}\s.*(FAQ|常见问题)"
     -path /data/rk-tech-kb/documents/internal-docs/模块/
     -output_mode content
     -n true
     -C 5
```

### 模式3: 错误信息搜索

```bash
# 搜索错误信息
Grep -pattern "error.*message|错误.*信息"
     -path /data/rk-tech-kb/documents/internal-docs/
     -output_mode content
     -n true
     -C 10
     -head_limit 50
```

### 模式4: 多语言组合搜索

```bash
# 中英文混合搜索
Grep -pattern "logo.*memory|logo.*内存|标志.*内存"
     -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
     -output_mode files_with_matches
     -i true
```

### 模式5: 并行多目录搜索

```bash
# 在单次响应中发起多个并行搜索
Grep -pattern "关键词" -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
Grep -pattern "关键词" -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
Grep -pattern "关键词" -path /data/rk-tech-kb/documents/internal-docs/KERNEL/
```

## 结果过滤技巧

### 避免过多结果

**使用head_limit**:
```
head_limit: 20  # 限制最多返回20条
```

**缩小搜索范围**:
```
# 不好: 全局搜索
path: "/data/rk-tech-kb/documents/internal-docs/"

# 好: 指定模块
path: "/data/rk-tech-kb/documents/internal-docs/UBOOT/"
```

**使用更精确的关键词**:
```
# 不好: 单一通用词
pattern: "config"

# 好: 具体配置项
pattern: "CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES"
```

### 提高匹配相关性

**使用组合关键词**:
```
pattern: "logo.*memory|logo.*内存"  # AND逻辑
```

**使用文档类型筛选**:
```
pattern: "(FAQ|常见问题).*logo"  # 优先FAQ章节
```

**使用文件类型筛选**:
```
glob: "*.md"  # 只搜索Markdown文档
type: "markdown"  # 使用文件类型过滤
```

## 最佳实践总结

1. **两阶段搜索**: 先定位文件 (files_with_matches)，再查看内容 (content)
2. **从小到大**: 从具体模块目录开始，逐步扩大范围
3. **忽略大小写**: 始终使用 `i: true`
4. **显示行号**: 内容查看时使用 `n: true`
5. **足够上下文**: 使用 `-C 5-10` 获取完整信息
6. **限制输出**: 使用 `head_limit` 避免过多结果
7. **并行搜索**: 在多个目录并行搜索提高效率
8. **精确关键词**: 使用具体的配置项名称而非通用词
