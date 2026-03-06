# 详细工作流程示例

## ECC支持查询完整流程

### RK3568 ECC支持查询
```bash
# 1. 使用Python API客户端搜索和下载
python3 scripts/nas_api.py RK3568 --download --output-dir /tmp/docs

# 2. 切换到PDF处理技能进行内容分析
# 使用 dev-utilities:pdf 技能提取文本并搜索ECC相关信息
# pdf:extract_text /tmp/docs/Rockchip_RK3568_Datasheet_V1.2-20210601.pdf | grep -i "ECC" -B 3 -A 3

# 3. 搜索DDR和ECC配置信息
# pdf:extract_text /tmp/docs/Rockchip_RK3568_Datasheet_V1.2-20210601.pdf | grep -E "DDR3|DDR4|LPDDR|ECC" -i -B 2 -A 2
```

### RK3576 Link ECC支持查询
```bash
# 1. 使用Python API客户端搜索并下载
python3 scripts/nas_api.py RK3576 --download --output-dir /tmp/docs

# 2. 切换到PDF处理技能分析Hardware Design Guide
# 使用 dev-utilities:pdf 技能提取文本
# pdf:extract_text /tmp/docs/RK3576_Hardware_Design_Guide_V1.3_20250331_EN.pdf | grep -E "LPDDR5|JEDEC|standard" -i -B 2 -A 2

# 3. 补充Web搜索确认JEDEC标准支持
# 搜索："LPDDR5 Link ECC JEDEC JESD209-5B RK3576"
```

## 接口复用分析流程

### RK3588 SATA和PCIe复用分析
```bash
# 1. 下载RK3588文档
python3 scripts/nas_api.py RK3588 --download --output-dir /tmp/docs

# 2. 切换到PDF处理技能进行接口分析
# 查找Block Diagram（通常在前30页）
# pdf:extract_text_pages /tmp/docs/Rockchip_RK3588_Datasheet_V1.2.pdf 1-30 | grep -i "block diagram" -A 30

# 3. 搜索Combo PHY配置信息
# pdf:search_text /tmp/docs/Rockchip_RK3588_Datasheet_V1.2.pdf "combo.*phy|SATA.*PCIe|multiplex" -i -B 5 -A 5

# 4. 确认Features描述
# pdf:search_text /tmp/docs/Rockchip_RK3588_Datasheet_V1.2.pdf "SATA|PCIe" -i -A 5 | head -50
```

## 使用建议

### 文档分析工作流
```bash
# 1. 下载文档到本地
python3 scripts/nas_api.py <芯片型号> --download --output-dir /tmp/work_docs

# 2. 切换到相应的文档处理技能：
#    - dev-utilities:pdf 用于PDF文档分析
#    - dev-utilities:docx 用于Word文档分析
#    - dev-utilities:pptx 用于PowerPoint文档分析

# 3. 使用文档处理技能的搜索和分析功能提取所需信息

# 4. 需要内部技术细节时，切换到 rk-module-docs 技能进行交叉验证
```

### 高级搜索技巧
```bash
# 当标准搜索无结果时，尝试：
python3 scripts/nas_api.py <芯片型号前缀>  # 如：RK35 而非 RK3588

# 使用模糊搜索发现相关芯片系列
python3 scripts/nas_api.py RK3*  # 需要修改脚本支持通配符
```