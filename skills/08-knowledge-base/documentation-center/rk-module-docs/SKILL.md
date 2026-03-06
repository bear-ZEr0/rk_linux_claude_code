---
name: rk-module-docs
description: 查询软件模块开发文档和调试指南。当用户需要模块开发方法、配置步骤、FAQ问题、故障排查、API说明时使用。覆盖DDR、显示(HDMI/MIPI/LVDS)、USB、AUDIO、CAMERA、PCIe、GMAC、UBOOT、MCU/AMP等67个模块。典型场景："DDR ECC配置"、"HDMI开发指南"、"USB性能分析"、"MIPI屏适配"、"UBOOT logo配置"。1280+技术文档。
allowed-tools: Bash, Read, Grep, Glob
---

# 瑞芯微软件模块文档检索技能

## 技能用途

提供瑞芯微软件模块技术文档的检索能力。基于1280+ Markdown文档，覆盖67个软硬件模块的开发指南、配置说明、FAQ和故障排查文档。

## 使用场景

### 模块开发问题
- DDR内存配置、调试、ECC设置
- DISPLAY显示开发：HDMI、DP、MIPI DSI、LVDS、eDP
- USB开发：性能分析、UVC、UAC、合规测试
- AUDIO音频：驱动开发、PulseAudio配置
- CAMERA摄像头：ISP调试、VICAP配置

### 启动和系统问题
- UBOOT配置：logo、启动流程、SPL/TPL、FIT镜像
- 电源管理：PMIC配置、DVFS调频、THERMAL温控
- 安全加密：CRYPTO、TRUST、SECURITY配置

### 通信接口问题
- PCIe/GMAC/CAN/UART/I2C/SPI配置
- 接口驱动开发和调试

### 多核和MCU开发
- AMP非对称多核：Linux+RTOS混合部署
- MCU开发：RT-Thread、FreeRTOS

## 环境设置

**文档来源（按优先级）**：
1. **本地预下载**：`/data/rk-tech-kb/documents/internal-docs/`
2. **Gerrit克隆**（若本地不存在）：
   ```bash
   git clone ssh://10.10.10.29:29418/rk/internal-docs ./internal-docs
   ```

**使用前检查**：
```bash
ls /data/rk-tech-kb/documents/internal-docs/ | head -5
# 或：ls ./internal-docs/ | head -5
```

## 核心工作流程

### 第1步：确定模块目录

根据用户问题定位目标模块目录：

| 问题类型 | 模块目录 |
|---------|---------|
| DDR/内存 | `DDR/` |
| 显示/HDMI/MIPI/LVDS | `DISPLAY/` |
| USB | `USB/` |
| 音频 | `AUDIO/` |
| 摄像头 | `CAMERA/` |
| 启动/UBOOT | `UBOOT/` |
| 电源/PMIC | `POWER/`, `PMIC/`, `DVFS/` |
| 网络/以太网 | `GMAC/` |
| PCIe | `PCIe/` |
| MCU/RTOS | `MCU/` |
| 多核AMP | `AMP/` |

### 第2步：文件定位搜索

```bash
grep -r -l -i "关键词" /data/rk-tech-kb/documents/internal-docs/模块目录/ --include="*.md" | head -20
```

### 第3步：内容检索

```bash
grep -r -n -i -C 10 "关键词" /data/rk-tech-kb/documents/internal-docs/模块目录/ --include="*.md" | head -100
```

### 第4步：读取文档

```bash
cat /data/rk-tech-kb/documents/internal-docs/模块目录/文档名.md
```

## 文档目录结构

```
internal-docs/
├── DDR/          # DDR开发指南、FAQ、调试工具
├── DISPLAY/      # HDMI、DP、MIPI、LVDS、eDP开发指南
├── USB/          # USB开发、性能分析、UVC/UAC
├── AUDIO/        # 音频驱动、PulseAudio
├── CAMERA/       # 摄像头、ISP、VICAP
├── UBOOT/        # 启动流程、SPL、FIT
├── MCU/          # MCU开发、RT-Thread
├── AMP/          # 多核混合部署
├── GMAC/         # 以太网开发
├── PCIe/         # PCIe配置
├── POWER/        # 电源管理
├── PMIC/         # PMIC配置
├── DVFS/         # 动态调频
├── THERMAL/      # 温控
├── CRYPTO/       # 加密
├── SECURITY/     # 安全
├── TRUST/        # 可信执行
├── CLK/          # 时钟配置
├── GPIO/         # GPIO、PINCTRL
├── I2C/, SPI/, UART/, CAN/  # 通信接口
└── DEBUG/, PERF/, TOOL/     # 调试工具
```

## 搜索技巧

### 关键词组合
```bash
# 中英文混合搜索
grep -r -i "logo.*memory\|logo.*内存" UBOOT/

# FAQ章节定位
grep -r -i "FAQ\|常见问题" DDR/

# 配置项搜索
grep -r -i "CONFIG_" DISPLAY/
```

### 文档类型优先级
1. `*_FAQ_*.md` - FAQ文档
2. `*Trouble_Shooting*.md` - 故障排查
3. `*Developer_Guide*.md` - 开发指南
4. `*User_Guide*.md` - 用户指南

## 输出规范

回答时包含以下信息：
1. **搜索过程**：使用的关键词和目录
2. **答案内容**：配置方法、代码示例
3. **文档引用**：`文件路径:行号` 格式
4. **置信度说明**：高/中/低

## 参考文档

详细搜索策略和特殊场景处理见：
- `docs/search_strategy.md` - 搜索策略
- `docs/grep_usage.md` - Grep工具使用
- `docs/special_scenarios.md` - 特殊场景处理
