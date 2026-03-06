# Samba 目录结构参考

本文档提供 10.10.10.164 Samba 服务器的详细目录结构，帮助快速定位资源。

## Android SDK 存储区

### V_Repository (Android 15)

```
V_Repository/
├── RK3588/          # RK3588 Android 15 SDK
├── RK3576/          # RK3576 Android 15 SDK
├── RK356X/          # RK3566/RK3568 SDK
├── RK3562/          # RK3562 SDK
├── RK3399/          # RK3399 SDK
└── RK3326/          # RK3326 SDK
```

### U_Repository (Android 14)

```
U_Repository/
├── RK3588/          # RK3588 SDK、固件
├── RK3576/          # RK3576 SDK、固件
├── RK356X/          # RK3566/RK3568 SDK
├── RK3562/          # RK3562 SDK
├── RK3528/          # RK3528 SDK
├── RK751/           # RK751 相关
├── GMS/             # GMS 认证资料
├── VTS/             # VTS 测试资料
└── 补丁集/          # 补丁包合集
```

### R_Repository (Android 11)

```
R_Repository/
├── RK3588/          # RK3588 SDK
├── RK3576/          # RK3576 SDK
├── RK356X/          # RK356X SDK
│   └── 云终端/云终端补丁集  # 运营商补丁
├── RK3399/          # RK3399 SDK
├── RK3328/          # RK3328 SDK
├── RK3326/          # RK3326 SDK
├── RK3288/          # RK3288 SDK
├── RV1126_1109/     # RV1126/RV1109 SDK
└── widevine/        # DRM 相关
```

---

## Linux_Repository

```
Linux_Repository/
├── 0_Release-Images/     # 发布固件
├── RK3588/
│   ├── 1_竞品分析/       # 竞品分析资料
│   ├── 2_项目/           # 项目相关
│   ├── 3_固件/           # 固件镜像
│   ├── 4_工具/           # 工具
│   └── 5_品测/           # 品测资料
├── RK3576/               # RK3576 Linux
├── RK3566_RK3568/        # RK356X Linux
├── RK3562/               # RK3562 Linux
├── RK3528/               # RK3528 Linux
├── RK3358/RK3358M/       # RK3358 系列
├── RK3308/               # RK3308 (音频芯片)
├── RV1106/               # RV1106 IPC
├── RV1126B/              # RV1126B
├── AI/                   # AI 相关资源
├── LLM/                  # 大语言模型相关
├── ROS/                  # ROS 机器人系统
├── Openharmony/          # OpenHarmony
├── Debian/               # Debian 发行版
├── Ubuntu/               # Ubuntu 发行版
├── docker-images/        # Docker 镜像
└── toolchain/            # 工具链
```

---

## Common_Repository

```
Common_Repository/
├── RK_SDK/               # 所有历史 SDK 存档
│   ├── RK3288_ANDROID*.tar.gz
│   ├── RK3399_ANDROID*.tar.gz
│   └── ...
├── RK_SDK_NEW/           # 新 SDK
├── rknn/                 # RKNN AI 工具包
│   ├── rknn-toolkit/     # RKNN Toolkit 1
│   ├── rknn-toolkit2/    # RKNN Toolkit 2
│   ├── rockface/         # 人脸识别
│   └── rockx/            # RockX AI SDK
├── Audio/                # 音频相关
├── DDR相关工具/          # DDR 调试工具
├── DDR颗粒兼容性验证/    # DDR 兼容性测试
├── EMMC颗粒兼容性验证/   # EMMC 兼容性测试
├── GMS-Materials/        # GMS 认证材料
├── toolchain/            # 编译工具链
├── USB_Tool/             # USB 相关工具
├── PATCHSETS/            # 补丁集合
└── 编译环境/             # 编译环境配置
```

---

## TOOLS_Repository

```
TOOLS_Repository/
├── windows/
│   ├── android_tool/         # Android 烧写工具
│   ├── upgrade_tool/         # 升级工具
│   ├── FactoryTool/          # 工厂测试工具
│   ├── driver_assistant/     # USB 驱动助手
│   ├── SocToolKit/           # SoC 工具包
│   ├── PinConfig/            # PIN 配置工具
│   ├── PinDebug/             # PIN 调试工具
│   ├── Efuse_tool/           # Efuse 烧写工具
│   ├── secureboot_tool/      # 安全启动工具
│   ├── rk_sign_tool/         # 签名工具
│   ├── programming_image_tool/ # 编程镜像工具
│   ├── sd_disk_tool/         # SD卡工具
│   ├── slt_tool/             # SLT 测试工具
│   ├── BoardProofTool/       # 板级验证工具
│   └── ClockHelper/          # 时钟配置工具
├── linux/                    # Linux 版工具
├── mac/                      # macOS 版工具
└── DDR相关工具/              # DDR 工具
```

---

## WIFI_BT_Repository

```
WIFI_BT_Repository/
├── Broadcom/             # Broadcom WiFi/BT
├── Realtek/              # Realtek WiFi/BT (RTL8822CS等)
├── Qualcomm/             # Qualcomm 驱动
├── MediaTek/             # MTK 驱动
├── Rockchip/             # RK 自研 WiFi
├── AIC/                  # AIC 芯片驱动
├── IOT WiFi MCU/         # IoT WiFi MCU
├── 乐鑫/                 # ESP 系列
├── 南方硅谷/             # SVW 驱动
├── 展锐/                 # 展锐驱动
└── RK WiFi BT相关问题排查文档/
```

---

## RTOS_Repository

```
RTOS_Repository/
├── RK2106-NanoD/         # RK2106 RTOS
├── RK2108-Pisces/        # RK2108 RTOS
├── RK2116/               # RK2116 RTOS
├── RK2118/               # RK2118 RTOS
├── RK2206-Canary/        # RK2206 RTOS
├── RK3308_AMP_Taurus/    # RK3308 AMP
├── RK3528_AMP_Bull/      # RK3528 AMP
├── RK3562_AMP_Snipe/     # RK3562 AMP
├── RK3568_AMP_Skylark/   # RK3568 AMP
├── RK3576_AMP_Heron/     # RK3576 AMP
├── RK3588_AMP_Orion/     # RK3588 AMP
├── RV1106_AMP_Puma/      # RV1106 AMP
├── Toolchain/            # RTOS 工具链
├── IDE/                  # IDE 工具
└── Swallow/              # Swallow 项目
```

---

## Pie_Repository (Android 9)

```
Pie_Repository/
├── RK3528/
│   └── 云电脑补丁/       # 运营商云电脑补丁
├── RK3326/               # RK3326 SDK
├── RK3399/               # RK3399 SDK
├── RK356X/               # RK356X SDK
├── PX30/                 # PX30 SDK
├── RK3576/               # RK3576 SDK
└── Express-Baseline/     # 快速基线
```

---

## 快速索引

### 按用途查找

| 需求 | 位置 |
|------|------|
| 烧写工具 | `TOOLS_Repository/windows/android_tool` |
| USB 驱动 | `TOOLS_Repository/windows/driver_assistant` |
| RKNN 模型转换 | `Common_Repository/rknn/rknn-toolkit2` |
| WiFi 驱动 | `WIFI_BT_Repository/<厂商>/` |
| Linux 固件 | `Linux_Repository/<芯片>/3_固件/` |
| 完整 SDK | `Common_Repository/RK_SDK/<芯片>_<版本>.tar.gz` |
| 补丁包 | `Common_Repository/PATCHSETS/` 或各仓库 `补丁集/` |

### 按芯片查找

| 芯片 | 主要位置 |
|------|---------|
| RK3588 | `U_Repository/RK3588`, `Linux_Repository/RK3588` |
| RK3576 | `U_Repository/RK3576`, `Linux_Repository/RK3576` |
| RK3568/66 | `U_Repository/RK356X`, `Linux_Repository/RK3566_RK3568` |
| RK3562 | `U_Repository/RK3562`, `Linux_Repository/RK3562` |
| RK3528 | `U_Repository/RK3528`, `Linux_Repository/RK3528` |
| RK3308 | `Linux_Repository/RK3308`, `RTOS_Repository/RK3308_AMP*` |
| RV1106 | `Linux_Repository/RV1106`, `RTOS_Repository/RV1106_AMP*` |
