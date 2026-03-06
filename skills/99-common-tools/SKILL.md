---
name: common-tools
description: 常用工具集 - 通用辅助功能
---

# 常用工具集

## 何时激活

- 用户需要通用辅助功能
- 用户说"格式化"、"转换"、"生成"等通用操作

## 包含的技能

| 技能 | 说明 | 触发关键词 |
|------|------|-----------|
| [doc-translate](doc-translate/SKILL.md) | 文档翻译（中英互译） | 翻译, translate |
| [doc-writer](doc-writer/SKILL.md) | Rockchip 标准文档编写 | 文档模板, 技术文档 |
| [rk-email](rk-email/SKILL.md) | 内部邮件发送 | 发邮件, send email |
| [rk-gerrit](rk-gerrit/SKILL.md) | Gerrit API 客户端（认证、查询、Review） | Gerrit, 提交记录, code review |
| [rk-oa](rk-oa/SKILL.md) | OA 客户端（登录、打卡、工时） | OA, 考勤, 打卡, 工时 |
| [skill-creator](skill-creator/SKILL.md) | 技能创建、验证、打包 | 创建技能, new skill |
| [document-processor/docx](document-processor/docx/SKILL.md) | Word 文档处理 | Word, .docx |
| [document-processor/xlsx](document-processor/xlsx/SKILL.md) | Excel 表格处理 | Excel, .xlsx |
| [document-processor/pptx](document-processor/pptx/SKILL.md) | PPT 演示文稿处理 | PPT, .pptx |
| [document-processor/pdf](document-processor/pdf/SKILL.md) | PDF 文档处理 | PDF, .pdf |

## 最佳实践

### DO
- ✅ 使用工具简化重复操作
- ✅ 批量处理时使用脚本

### DON'T
- ❌ 不要手动计算可自动化的内容
