# 文档处理工具

处理 Office 文档和 PDF 文件的技能集合。

## 支持格式

| 格式 | 技能 | 创建 | 读取 | 编辑 |
|------|------|------|------|------|
| Word (.docx) | docx | ✅ | ✅ | ✅ |
| Excel (.xlsx) | xlsx | ✅ | ✅ | ✅ |
| PPT (.pptx) | pptx | ✅ | ✅ | ✅ |
| PDF (.pdf) | pdf | ✅ | ✅ | ✅ |

## 使用方式

直接描述需求，Claude 会自动识别并调用对应技能。无需手动指定命令。

### 触发示例

```
# Word 文档
"帮我写一份技术方案的 Word 文档"
"读取这个 docx 文件的内容"
"在这个 Word 文档里添加批注"

# Excel 表格
"创建一个销售数据的 Excel 表格"
"分析这个 xlsx 文件的数据"
"给这个表格添加公式"

# PPT 演示文稿
"做一个产品介绍的 PPT"
"提取这个 pptx 的文字内容"
"基于这个模板做一套新的 slides"

# PDF 文件
"把这几个 PDF 合并成一个"
"提取 PDF 中的表格数据"
"创建一份 PDF 报告"
```

## 依赖安装

### 必需依赖

```bash
# Python 依赖
pip install openpyxl pypdf pdfplumber reportlab markitdown Pillow

# Node.js 依赖
npm install -g docx pptxgenjs
```

### 可选依赖

用于格式转换和高级功能：

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| pandoc | 文档格式转换 | https://pandoc.org/installing.html |
| poppler | PDF 转图片 | https://github.com/oschwartz10612/poppler-windows/releases |
| LibreOffice | Office 格式转换 | https://www.libreoffice.org/download/download/ |

## 技能详情

### docx - Word 文档

**创建新文档**
- 使用 docx-js (Node.js)
- 支持：标题、段落、表格、图片、页眉页脚、目录、列表

**读取内容**
- 使用 markitdown 提取文本
- 或解压 XML 直接读取

**编辑现有文档**
- 解压 → 编辑 XML → 重新打包
- 支持：批注、跟踪修改、格式调整

详见 [docx/SKILL.md](docx/SKILL.md)

### xlsx - Excel 表格

**创建/编辑**
- 使用 openpyxl
- 支持：数据、公式、格式化、图表

**读取分析**
- 使用 pandas 或 openpyxl
- 支持：数据提取、统计分析

详见 [xlsx/SKILL.md](xlsx/SKILL.md)

### pptx - PPT 演示文稿

**创建新演示文稿**
- 使用 pptxgenjs (Node.js)
- 支持：幻灯片、文本、图片、图表

**读取内容**
- 使用 markitdown 提取文本

**编辑现有文件**
- 解压 → 编辑 XML → 重新打包

详见 [pptx/SKILL.md](pptx/SKILL.md)

### pdf - PDF 文件

**创建**
- 使用 reportlab
- 支持：文本、表格、图片

**读取**
- 使用 pdfplumber 提取文本和表格

**操作**
- 使用 pypdf
- 支持：合并、拆分、旋转、加密

详见 [pdf/SKILL.md](pdf/SKILL.md)

## 输出目录

生成的文档默认保存到 `output/` 目录：

```
output/
├── documents/      # Word 文档
├── spreadsheets/   # Excel 表格
├── presentations/  # PPT 演示文稿
└── pdfs/           # PDF 文件
```

## 注意事项

1. **编码问题**：Windows 终端可能显示乱码，但文件内容正确
2. **全局 npm 模块**：docx 和 pptxgenjs 需要全局安装 (`npm install -g`)
3. **格式转换**：需要安装可选依赖（pandoc、poppler、LibreOffice）
4. **中文支持**：创建 PDF 时需要注册中文字体
