# 渐进式搜索策略详解

## 5阶段搜索方法论

### 阶段1: 关键词提取与组合

从用户问题中提取核心术语，构建搜索关键词。

**多语言策略**:
```
核心概念: logo/LOGO/标志
功能描述: memory/内存/allocation/分配/buffer/缓冲区/reserved/预留
配置相关: config/配置/size/大小/length/长度
```

**正则表达式模式**:
```
组合搜索: logo.*memory|logo.*内存|logo.*allocation
标题匹配: ^#{1,3}\s.*关键词
配置项匹配: CONFIG_[A-Z_]+
文件路径匹配: include/configs/.*\.h
```

**渐进式关键词扩展**:
```
第一轮: 广泛搜索 → 核心概念组合（logo + memory）
第二轮: 精确定位 → 提取的配置项名称（CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES）
第三轮: 配置追踪 → 配置文件路径（include/configs/*.h）
```

### 阶段2: 目录定位与范围收缩

**搜索起点选择**:
1. 所有搜索必须在 `/data/rk-tech-kb/documents/internal-docs/` 目录下进行
2. 优先从用户明确提到的模块目录开始（如 /data/rk-tech-kb/documents/internal-docs/UBOOT）
3. 扩展到功能相关的模块目录
4. 最后才考虑在 /data/rk-tech-kb/documents/internal-docs/ 下全局搜索

**配置问题搜索路径**:
```
1. 明确指定模块 (如UBOOT/) - 用户提示或问题明确提到
2. 功能相关模块 (如DISPLAY/) - 与功能直接相关
3. 系统通用模块 (如MEMORY/, DEBUG/) - 通用配置
4. 全局搜索 (根目录) - 前述都未找到时
```

### 阶段3: 文档类型筛选

**文档章节优先级**:
```
1. FAQ/常见问题 (最高) - 包含具体配置示例和步骤
2. 故障排查/Troubleshooting - 包含问题解决方案
3. 配置说明/Configuration - 详细配置参数
4. 开发指南主体 - 系统性说明
```

**文档类型识别**:
- FAQ文档: 文件名包含 FAQ, 章节标题 "常见问题", "FAQ"
- 开发指南: Developer Guide, 开发指南
- 用户手册: User Manual, 用户手册
- 快速入门: Quick Start, 快速入门

### 阶段4: 配置项精确定位

当搜索到关键字后：

1. **提取配置项名称** - 识别 CONFIG_XXX, DT属性等
2. **二次精确搜索** - 使用配置项名称搜索
3. **查找配置文件路径** - include/configs/, defconfig, *.dts
4. **寻找配置示例** - diff补丁, 代码片段

**示例流程**:
```bash
# 第一次搜索: 找到关键词
Grep -pattern "logo.*memory" -path /data/rk-tech-kb/documents/internal-docs/UBOOT/

# 发现配置项: CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES

# 第二次搜索: 精确查找配置项
Grep -pattern "CONFIG_DRM_MEM_RESERVED_SIZE_MBYTES" -path /data/rk-tech-kb/documents/internal-docs/

# 第三次搜索: 查找配置文件路径
Grep -pattern "include/configs.*\.h" -path /data/rk-tech-kb/documents/internal-docs/
```

### 阶段5: 交叉验证

在多个相关文档中验证信息一致性：

1. **多文档确认** - 在至少2个相关文档中确认信息
2. **中英文对比** - 对比中英文文档 (_CN.md vs _EN.md)
3. **上下文理解** - 查看上下文理解修改原因和背景
4. **版本检查** - 注意不同版本或平台的差异

## 关键词选择技巧库

### 常见模块关键词

```
内存配置: memory|mem|内存|allocation|buffer|reserved|heap|malloc
大小配置: size|length|bytes|MB|大小|长度
驱动配置: driver|驱动|module|模块|device|设备
时钟电源: clock|clk|power|pmic|dvfs|时钟|电源
显示图形: display|显示|lcd|hdmi|mipi|drm|fb
音频: audio|音频|sound|alsa|codec|i2s
视频: video|视频|encoder|decoder|mpp|vpu
相机: camera|摄像头|isp|sensor|mipi-csi
存储: storage|存储|mmc|sd|emmc|nand|spi-nor
网络: network|网络|ethernet|gmac|wifi|bt
USB: usb|otg|host|device|gadget
安全: security|安全|trust|crypto|加密
启动: boot|启动|uboot|loader|spl
```

### 配置项模式

```
内核配置: CONFIG_[A-Z_]+
设备树属性: [a-z-]+,property
Kconfig: depends on|select|bool|tristate
Makefile: obj-y|obj-m|CFLAGS
```

### 文件路径模式

```
头文件: .*\.h|include/.*
配置文件: .*config.*|.*\.dts|.*defconfig
源代码: .*\.c|.*\.cpp|drivers/.*
文档: .*\.md|.*\.txt|Documentation/.*
```

## 目录搜索优先级详解

### 按问题类型选择目录

**启动配置问题** → UBOOT/, KERNEL/, BOOT/

**显示问题** → DISPLAY/, HDMI-IN/, RGA/

**音频问题** → AUDIO/

**视频问题** → VIDEO/, CAMERA/, VICAP/

**存储问题** → DDR/, MMC/, NVM/

**电源问题** → POWER/, PMIC/, CLK/

**网络问题** → GMAC/, WiFi/, BT/

**USB问题** → USB/

**安全问题** → SECURITY/, TRUST/, CRYPTO/

**性能调试** → PERF/, DEBUG/, TOOL/

### 跨模块问题处理

某些问题可能涉及多个模块，需要在多个目录中并行搜索：

**示例: LOGO显示问题**
```
涉及模块: UBOOT (启动logo) + DISPLAY (显示驱动)
搜索策略: 同时搜索 UBOOT/ 和 DISPLAY/ 目录
```

**示例: 性能优化问题**
```
涉及模块: DDR (内存带宽) + KERNEL (调度) + PERF (性能工具)
搜索策略: 在 DDR/, KERNEL/, PERF/ 中并行搜索
```

## 搜索范围控制技巧

### 从小到大原则

```
优先级1: 指定模块目录 (最小范围, 最快速度)
  示例: /data/rk-tech-kb/documents/internal-docs/UBOOT/

优先级2: 相关模块目录 (中等范围)
  示例: /data/rk-tech-kb/documents/internal-docs/DISPLAY/, /data/rk-tech-kb/documents/internal-docs/KERNEL/

优先级3: 全局根目录 (最大范围, 最慢速度)
  示例: /data/rk-tech-kb/documents/internal-docs/
```

### 并行搜索策略

当需要在多个位置搜索时，使用并行调用：

```bash
# 场景: 需要在多个目录搜索同一关键词
Grep -pattern "logo.*memory" -path /data/rk-tech-kb/documents/internal-docs/UBOOT/
Grep -pattern "logo.*memory" -path /data/rk-tech-kb/documents/internal-docs/DISPLAY/
Grep -pattern "CONFIG_DRM.*RESERVED" -path /data/rk-tech-kb/documents/internal-docs/

# 这三个搜索可以在单次响应中并行发起
```

## 结果验证清单

搜索完成后必须检查：

- [ ] 是否找到具体的配置项名称或修改方法
- [ ] 是否提供了代码示例或diff补丁
- [ ] 是否解释了修改原因和背景
- [ ] 是否在多个文档中交叉验证
- [ ] 是否记录了文档路径和行号(file_path:line_number)
- [ ] 是否注意了版本和平台差异
