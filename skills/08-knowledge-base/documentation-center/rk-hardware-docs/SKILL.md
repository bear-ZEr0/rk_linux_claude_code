---
name: rk-hardware-docs
description: 查询芯片硬件规格和官方技术文档。当用户需要芯片数据手册(Datasheet)、技术参考手册(TRM)、寄存器详情、接口电气特性、管脚复用、硬件设计参考时使用。典型场景："RK3588数据手册"、"GPIO复用关系"、"接口电气特性"、"芯片Block Diagram"、"EOL停产信息"。覆盖40+芯片平台官方文档。
allowed-tools: Bash, Read, Grep, Glob
license: Rockchip Internal Use Only
color: #FF6B35
---

# 瑞芯微硬件文档检索技能

## 技能用途

提供瑞芯微官方硬件文档的检索、下载和分析能力。访问NAS文档服务器获取权威的芯片技术资料，包括数据手册、技术参考手册和硬件设计指南。

## 使用场景

在以下场景中使用此技能：

### 芯片规格查询
- 查询特定芯片数据手册和规格参数
- 查找芯片电气特性和引脚定义
- 检查芯片版本差异和更新信息

### 技术参考手册查询
- 访问寄存器定义和编程指南
- 查询芯片内部模块和功能描述
- 搜索技术参考手册（TRM）相关内容

### 硬件设计参考
- 查询原理图参考设计和PCB设计指南
- 检查接口复用关系和配置方法
- 分析硬件设计兼容性问题

### 接口分析需求
- **接口复用分析**：分析接口冲突，如SATA和PCIe同时使用
- **Block Diagram查询**：分析芯片内部结构和接口连接
- **ECC支持查询**：检查特定芯片型号是否支持ECC功能

### 技术信息查询
- 芯片EOL（停产）信息和技术简报
- 芯片选型比较和替代方案
- 官方设计考虑和最佳实践

## 核心工作流程

### 快速开始（渐进式披露 - 第1层）

执行快速查询的标准NAS API方法：

```bash
# 1. 认证并获取Session ID
echo "正在认证NAS服务器..."
AUTH_RESPONSE=$(curl -s "http://10.10.10.79:5000/webapi/auth.cgi?api=SYNO.API.Auth&version=3&method=login&account=肖小霞&passwd=123456&session=FileStation&format=cookie")

# 2. 验证认证结果
if echo "$AUTH_RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); exit(0 if data.get('success') else 1)" 2>/dev/null; then
    SID=$(echo "$AUTH_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['sid'])")
    echo "认证成功，SID: $SID"
else
    echo "认证失败，检查网络连接或凭据"
    exit 1
fi

# 3. 执行搜索任务（替换目标芯片型号）
CHIP_MODEL="RK3588"

# 搜索3个标准位置
echo "搜索芯片专用目录..."
curl -s "http://10.10.10.79:5000/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&folder_path=/03_对外发布文件/$CHIP_MODEL&_sid=$SID" 2>/dev/null | python3 -c "
import sys,json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        for f in data.get('data', {}).get('files', []) + data.get('data', {}).get('dirs', []):
            if '$CHIP_MODEL' in f['name'].upper():
                print(f'  {f[\"name\"]}')
except:
    pass
"

echo "搜索Datasheet目录..."
curl -s "http://10.10.10.79:5000/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&folder_path=/03_对外发布文件/01_Datasheet&_sid=$SID" 2>/dev/null | python3 -c "
import sys,json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        for f in data.get('data', {}).get('files', []):
            if '$CHIP_MODEL' in f['name'].upper():
                print(f'  {f[\"name\"]}')
except:
    pass
"

echo "搜索TRM目录..."
curl -s "http://10.10.10.79:5000/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&folder_path=/03_对外发布文件/02_TRM&_sid=$SID" 2>/dev/null | python3 -c "
import sys,json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        for f in data.get('data', {}).get('files', []):
            if '$CHIP_MODEL' in f['name'].upper():
                print(f'  {f[\"name\"]}')
except:
    pass
"

# 4. 清理Session
curl -s "http://10.10.10.79:5000/webapi/auth.cgi?api=SYNO.API.Auth&version=1&method=logout&session=FileStation&_sid=$SID" > /dev/null
echo "搜索完成"
```

### 详细检索流程（渐进式披露 - 第2层）

当需要深入文档分析时，加载详细工作流程指导：

```python
# 加载详细工作流程参考
import os
with open('references/detailed_workflow.md', 'r', encoding='utf-8') as f:
    workflow_content = f.read()
    # 按需读取高级工作流程内容
```

### 高级分析技术（渐进式披露 - 第3层）

对于复杂接口分析场景，加载专业分析方法：

```python
# 加载接口分析指南
import os
with open('references/interface_analysis_guide.md', 'r', encoding='utf-8') as f:
    analysis_guide = f.read()
    # 按需读取高级分析技术内容
```

## 系统配置

### 访问凭据
- **服务器**: NAS文档服务器 (http://10.10.10.79:5000)
- **用户名**: `肖小霞`
- **密码**: `123456`
- **文档根目录**: `/03_对外发布文件/`

### API认证要求
- **认证版本**: `version=3` (关键参数)
- **Session类型**: `FileStation` (不是Core或其他)
- **格式参数**: `format=cookie` (必需)
- **参数名称**: 使用`_sid`而不是`sid` (重要)

### 权限要求
- 需要FileStation访问权限
- 遇到错误代码119时联系管理员配置权限

## 常见查询模式

### 接口复用分析（关键原则）
分析芯片接口时遵循以下原则：

1. **优先查找Block Diagram** - 这是接口复用关系的权威来源
2. **不依赖Features描述** - Features只列举功能，不说明复用冲突
3. **用Block Diagram验证** - 确保所有方案没有接口冲突
4. **区分独立和复用接口** - Combo PHY同一时间只能选择一种模式

### 芯片型号匹配策略
- 用户指定RK3588C就精确搜索RK3588C
- 未找到结果时列出相似型号供选择
- 注意区分：RK3588 ≠ RK3588S ≠ RK3588C

### 文档类型优先级
1. **芯片专用目录** - `/03_对外发布文件/{芯片型号}/`
2. **Datasheet目录** - `/03_对外发布文件/01_Datasheet/`
3. **TRM目录** - `/03_对外发布文件/02_TRM/`

## 错误处理和故障排除

### 认证失败处理
```bash
# 诊断认证问题
echo "诊断NAS连接..."
ping -c 2 10.10.10.79 && echo "网络连接正常" || echo "网络连接失败"

# 测试API可用性
curl -s "http://10.10.10.79:5000/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query" | python3 -c "import sys,json; data=json.load(sys.stdin); print('API可用' if data.get('success') else 'API不可用')"
```

### 搜索失败处理
当标准搜索失败时：
1. 使用更短的关键词（如"3588"而非完整文件名）
2. 检查芯片型号拼写是否正确，356X包括3566/3568/3566PRO，182X包括1820/1828
3. 浏览根目录结构确认文档位置
4. 查看已验证的芯片支持列表

## 资源引用

### 脚本资源
- `scripts/nas_api.py` - Python NAS API客户端

### 参考文档
- `references/detailed_workflow.md` - 详细工作流程和最佳实践
- `references/interface_analysis_guide.md` - 接口分析专业方法

## 与其他技能的协作

### 文档内容分析流程
1. 使用本技能下载PDF/PPT/DOCX文档
2. 切换到通用文档处理技能：`dev-utilities:pdf`、`dev-utilities:pptx`、`dev-utilities:docx`
3. 使用文档处理技能读取内容并搜索关键词
4. 需要内部文档交叉验证时切换到`rk-module-docs`技能

### 典型协作场景
```bash
# 1. 下载文档到本地
python3 scripts/nas_api.py RK3588C --download --output-dir /tmp/docs

# 2. 切换到PDF分析技能
# 使用 dev-utilities:pdf 技能提取和分析内容
# pdf:extract_text /tmp/docs/RK3588C_Datasheet.pdf | grep -i -A 5 -B 5 "Block Diagram"
```

## 最佳实践

### 效率优化
- 使用标准化API参数避免重试
- 优先使用3位置标准搜索流程
- 大文件处理时使用页数范围限制
- 搜索Block Diagram通常在前20页

### 准确性保证
- 接口分析务必参考Block Diagram
- 多文档交叉验证（Datasheet + Hardware Design Guide）
- 注意芯片型号和版本的区别
- 优先使用最新版本的官方文档

### 用户体验
- 提供具体的文件路径和下载方法
- 给出明确的文档分析建议
- 提供备选方案和错误处理指导
- 与通用文档处理技能无缝衔接

通过这个技能，用户可以快速获取权威的瑞芯微官方硬件文档，避免设计错误，提高开发效率。