# Dept3 Skills 插件安装记录

## 安装信息

- **仓库**: ssh://10.10.10.29:29418/linux/dept3-skills
- **版本**: v0.3.0
- **安装日期**: 2026-03-06
- **安装位置**: `/home/lht/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/dept3-skills/`

## 项目简介

系统产品三部开发团队工作流程与 AI 深度集成，覆盖从需求到交付的全流程。

### 核心价值
- **周报自动生成**：自动收集 Gerrit/Redmine/邮件/OA 数据，减少手工整理
- **知识库检索**：快速查找芯片规格书、FAE 文档、培训资料
- **文档处理**：Word/Excel/PPT/PDF 一站式处理
- **内部邮件**：直接发送邮件，无需切换工具

## 功能模块

### 01 - 工作总结
- 周报生成
- AI 优化描述
- 工时校验

### 02 - 会议纪要
- 拜访纪要
- 工作会议纪要

### 03 - 产品需求
- 需求收集
- PRD
- 竞品分析

### 04 - 模块开发
- **c-code-review** - C 代码审核
- **cpp-testing** - C++ 测试驱动开发
- **rk-adb** - Android ADB 调试工具
- **rk-serial** - 串口调试工具
- **rk-dts-from-schematic** - 从原理图生成 DTS

### 05 - SDK 开发
- **sdk-diff** - SDK 差异对比
- **sdk-setup** - SDK 环境搭建

### 06 - SDK 发布
- 发布检查
- 环境部署

### 07 - 客户支持
- **rk-redmine** - Redmine 问题跟踪系统集成
  - 问题查询
  - 补丁简报
  - 回复模板
  - 工时统计

### 08 - 知识库
- **documentation-center** - 文档中心
  - redmine-fae-docs - FAE 文档查询
  - rk-hardware-docs - 硬件文档查询
  - rk-module-docs - 模块文档查询
- **rk-samba-share** - Samba 共享浏览
- **training-center** - 培训中心
  - rk-elearning - 在线学习平台

### 99 - 通用工具
- **doc-translate** - 文档翻译
- **document-processor** - 文档处理
  - DOCX 处理（修订、批注）
  - PDF 处理（表单填写、字段提取）
  - PPTX 处理（幻灯片编辑）
  - XLSX 处理（重新计算）
- **doc-writer** - 文档编写助手
- **rk-email** - 邮件发送
- **rk-gerrit** - Gerrit 客户端
- **rk-oa** - OA 系统集成（考勤、工时）
- **skill-creator** - 技能创建工具

## 可用的 Agents

1. **planner** - 开发计划制定
2. **code-reviewer** - 代码审核
3. **tdd-guide** - TDD 指导
4. **doc-writer** - 文档编写
5. **translator** - 翻译助手
6. **security-reviewer** - 安全审计

## 已安装依赖

### Python 依赖
```bash
pip install openpyxl pypdf pdfplumber reportlab markitdown Pillow requests
```

### 可选依赖（OA 工时统计）
```bash
pip install cryptography        # RSA 加密登录
pip install ddddocr             # 验证码 OCR 识别
```

### 可选依赖（Word/PPT 创建）
```bash
npm install -g docx pptxgenjs
```

## 配置说明

需要创建 `settings.json` 配置文件（参考 `settings.example.json`）：

```json
{
  "redmine": {
    "url": "http://redmine.example.com",
    "api_key": "YOUR_API_KEY"
  },
  "gerrit": {
    "url": "http://10.10.10.29:29418",
    "username": "YOUR_USERNAME"
  },
  "email": {
    "smtp_server": "smtp.example.com",
    "smtp_port": 25,
    "from_email": "your@email.com"
  },
  "oa": {
    "url": "http://oa.example.com",
    "username": "YOUR_USERNAME"
  }
}
```

## 更新

手动更新：
```bash
cd /tmp
git clone ssh://10.10.10.29:29418/linux/dept3-skills
cp -r dept3-skills /home/lht/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/
```

## 参考资料

- 插件配置：`~/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/dept3-skills/`
- Skills 源码：`~/.claude/my-custom/skills/01-work-summary` 等
- README：`~/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/dept3-skills/README.md`
