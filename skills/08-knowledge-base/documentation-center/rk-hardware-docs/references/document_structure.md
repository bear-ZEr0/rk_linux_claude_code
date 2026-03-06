# 文档库结构和命名规范

## 通用文档类别
- **01_Datasheet**: 芯片数据手册（规格、引脚定义、电气特性）
- **02_支持列表**: 兼容性和支持列表
- **03_技术简报**: 技术亮点和应用简介
- **04_RK平台DDR测试工具**: DDR内存测试和调优工具
- **05_RK_Camera_AVL**: 摄像头兼容列表
- **06_TRM**: 技术参考手册（详细寄存器定义）

## 平台文档标准结构

以RK3588为例：
```
RK3588/
├── 01_Official Release/
│   ├── 01_Common Document/        # 通用文档
│   ├── 02_DDR Template/           # DDR配置模板
│   ├── 03_Product Line Branch_AIoT/
│   ├── 04_Product Line Branch_NVR/
│   ├── 05_Reference Demo EVB7/
│   └── 历史记录/
└── Release Note & File List
```

## 常见文档命名模式
- Datasheet: `Rockchip [芯片型号] Datasheet V[版本号]-[日期].pdf`
- Hardware Design Guide: `Rockchip_[芯片型号]_Hardware_Design_Guide_V[版本号]_[日期].pdf`
- EVB User Guide: `Rockchip_[芯片型号]_EVB[序号]_User_Guide_V[版本号]_[语言].pdf`
- Pin Out: `[芯片型号]_PinOut_V[版本号]_[日期].xlsx`

## 产品线分支说明
- **AIoT**: 人工智能物联网产品线
- **NVR**: 网络视频录像机产品线
- **Tablet**: 平板电脑产品线
- **EBOOK**: 电子书产品线