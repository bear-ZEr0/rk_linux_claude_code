---
name: redmine-fae-docs
description: 查询器件兼容性和FAE技术资料。当用户需要DDR/eMMC/UFS/NAND/WiFi/Camera等器件支持列表(AVL)、芯片兼容性查询、硬件设计参考、EVB资料、芯片EOL/PCN通知时使用。典型场景："这个DDR颗粒支持RK3588吗"、"UFS AVL"、"芯片停产通知"。支持AVL文档智能解析。
allowed-tools: Bash, Read, Grep, Glob, Skill
---

# Rockchip Redmine FAE文档检索与存储器件分析

访问Rockchip内部FAE文档中心，检索技术文档并智能解析DDR/eMMC/UFS器件兼容性列表。

## 核心工作流程

### 1. 文档搜索
```bash
# 搜索FAE文档（自动登录认证）
python3 /path/to/skill/scripts/search_fae_docs.py "关键词" [--limit 10]

# 示例关键词
- "eMMC支持列表" - 查找eMC器件支持文档
- "UFS Approved Vendor List" - 查找UFS器件支持文档
- "DDR支持列表" - 查找DDR器件支持文档
- "硬件设计指南" - 查找硬件设计文档
- "RK3588" - 查找特定芯片平台文档
```

### 2. 文档下载
```bash
# 下载指定文档到工作目录
python3 /path/to/skill/scripts/download_fae_doc_auth.py <文档ID> --output-dir .

# 常用文档分类ID
- 49: DDR支持列表
- 50: eMMC和UFS支持列表
- 46: Nand flash支持列表
- 52: Wi-Fi/BT支持列表
- 53: Camera支持列表
```

### 3. 存储器件智能解析

#### DDR兼容性分析
```bash
# 解析DDR AVL文档，生成ddr_avl_data.json
python3 /path/to/skill/scripts/parse_ddr_avl.py

# 查询兼容性示例（使用生成的JSON数据）
# RK3576 + Samsung K4UCE3Q4AB-MGCL → 支持（S/A状态）
```

#### eMMC兼容性分析
```bash
# 解析eMMC AVL文档，生成emmc_avl_data.json
python3 /path/to/skill/scripts/parse_emmc_avl.py

# 查询示例：RK3588 + Samsung SDINBDG4-32GB → 支持（√状态）
```

#### UFS兼容性分析
```bash
# 解析UFS AVL文档，生成ufs_avl_data.json
python3 /path/to/skill/scripts/parse_ufs_avl.py

# 查询示例：RK3576 + KIOXIA THGJFGT2T85BAB5 → 支持（T/A状态）
```

### 4. JSON数据结构与查询

解析生成的JSON文件遵循统一的数据结构：

```json
{
  "metadata": { "source": "...", "version": "...", "total_parts": 63 },
  "chips": ["RK3576", "RK3588", ...],
  "parts": [
    {
      "manufacturer": "KIOXIA",
      "part_number": "THGJFGT2T85BAB5",
      "compatibility": {
        "RK3576": { "supported": true, "status": "T/A" },
        "RK3588": { "supported": true, "status": "√" }
      },
      "vcc": "2.5/3.3",
      "vccq": "1.2",
      "temp": "-40/105"
    }
  ]
}
```

#### 查询某个芯片支持的所有颗粒
```python
# 查询RK3576支持的所有UFS颗粒
import json
with open('ufs_avl_data.json', 'r') as f:
    data = json.load(f)

# 关键：使用 compatibility 字段，不是 supported_chips
for part in data['parts']:
    chip_compat = part.get('compatibility', {}).get('RK3576', {})
    if chip_compat.get('supported', False):
        print(f"{part['manufacturer']} {part['part_number']} - {chip_compat['status']}")
```

#### 查询某个颗粒支持的所有芯片
```python
# 脚本内置查询函数
from parse_ufs_avl import query_part_support
result = query_part_support(data, "THGJFGT2T85BAB5")
print(result['supported_chips'])  # ['RK3576', ...]
```

## 支持状态说明

- **√**: 完全支持，已批准量产
- **T/A**: 已测试，待批准量产
- **S/A**: 样品验证通过，需平台兼容性测试
- **D/A**: 数据表适用，需要样品测试
- **N/A**: 不适用

## 认证配置

技能使用Redmine用户名密码认证，配置信息查看`config/redmine_config.json`

Session自动保存1小时，过期后重新登录。

## 资源使用

### 核心脚本
- `scripts/search_fae_docs.py`: 文档搜索（集成登录认证）
- `scripts/download_fae_doc_auth.py`: 文档下载（支持认证）
- `scripts/parse_ddr_avl.py`: DDR AVL智能解析
- `scripts/parse_emmc_avl.py`: eMMC AVL智能解析
- `scripts/parse_ufs_avl.py`: UFS AVL智能解析
- `scripts/redmine_auth.py`: 独立认证工具

### 输出文件
- `ddr_avl_data.json`: DDR兼容性数据（798+颗粒，31制造商）
- `emmc_avl_data.json`: eMMC兼容性数据（20+芯片平台）
- `ufs_avl_data.json`: UFS兼容性数据（含电压、温度参数）

## 技能优势

- **自动认证**: 集成Redmine登录流程，解决HTML页面访问
- **智能解析**: 支持DDR/eMMC/UFS三大存储器件AVL文档
- **结构化输出**: 生成标准JSON格式，便于程序化查询
- **兼容性准确**: 自动识别制造商、支持状态和芯片平台
- **工作目录友好**: 所有中间文件生成在用户工作目录

## 注意事项

> [!IMPORTANT]
> **工作目录规则**: 所有脚本必须在**用户的工作目录**执行，不要切换到skill目录。
> - Skill目录是只读的，仅供读取脚本使用
> - 所有输出文件（JSON、下载的PDF等）都会生成在**当前工作目录**
> - 脚本会自动在工作目录和fae_doc_*子目录中查找PDF文件

1. **网络要求**: 需连接Rockchip内网（10.10.10.70）
2. **执行方式**: 始终使用绝对路径调用脚本，在用户工作目录执行
3. **文档版本**: AVL文档会定期更新，建议下载最新版本
4. **缓存管理**: 文档列表缓存24小时，可使用`--refresh`强制刷新

