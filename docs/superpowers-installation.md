# Superpowers 插件安装记录

## 安装信息

- **仓库**: https://github.com/obra/superpowers
- **版本**: 4.3.1
- **安装日期**: 2026-03-06
- **安装位置**: `/home/lht/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/superpowers/`

## Skills 列表

### 测试相关
- `test-driven-development` - 红-绿-重构 TDD 循环

### 调试相关
- `systematic-debugging` - 4阶段根因分析流程
- `verification-before-completion` - 完成前确保问题真正解决

### 协作相关
- `brainstorming` - 苏格拉底式设计细化
- `writing-plans` - 详细实施计划
- `executing-plans` - 批量执行带检查点
- `dispatching-parallel-agents` - 并发子代理工作流
- `requesting-code-review` - 预审查检查清单
- `receiving-code-review` - 响应反馈
- `using-git-worktrees` - 并行开发分支
- `finishing-a-development-branch` - 合并/PR 决策工作流
- `subagent-driven-development` - 快速迭代与两阶段审查

### 元技能
- `writing-skills` - 创建新技能遵循最佳实践
- `using-superpowers` - 技能系统介绍

## 核心工作流程

1. **brainstorming** - 写代码前激活，细化粗略想法
2. **using-git-worktrees** - 设计批准后，创建隔离工作空间
3. **writing-plans** - 将工作分解为小任务（2-5分钟）
4. **subagent-driven-development** - 每个任务分派新子代理并审查
5. **test-driven-development** - 实施期间强制 TDD
6. **requesting-code-review** - 任务间审查
7. **finishing-a-development-branch** - 任务完成后的收尾工作

## 哲学原则

- **测试驱动开发** - 先写测试
- **系统化而非临时** - 流程胜过猜测
- **降低复杂性** - 简单性为首要目标
- **证据胜于主张** - 验证后再宣布成功

## 更新

手动更新：
```bash
cd /tmp
git clone https://github.com/obra/superpowers.git
cp -r superpowers /home/lht/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/
```

## 参考资料

- 官方文档: https://github.com/obra/superpowers
- 博客文章: https://blog.fsck.com/2025/10/09/superpowers/
