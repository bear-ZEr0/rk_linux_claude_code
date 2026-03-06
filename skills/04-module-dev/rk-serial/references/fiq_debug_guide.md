# FIQ 调试命令参考

本文档详细说明 Rockchip 设备 FIQ（快速中断请求）调试器的所有可用命令。

## 进入/退出 FIQ 模式

- **进入**：发送 `fiq` 字符串（不换行），然后回车
- **退出**：执行 `console` 命令返回正常控制台

---

## 基础调试命令

### 帮助
```
help    显示所有可用命令
?       同 help
```

### CPU 信息
```
cpu            显示当前 CPU 编号
cpu <number>   切换到指定 CPU（如 cpu 0, cpu 1）
```
**用途**：在多核系统中，可以切换到不同 CPU 查看各核心的状态。这对于诊断多核死锁特别有用。

### 系统版本
```
version        显示内核版本信息
```
**示例输出**：
```
Linux version 3.10.0 (huangjc@RD-DEP1-SERVER-163) (gcc version 4.6.x-google 20120106)
```

---

## 寄存器与栈跟踪

### 寄存器
```
regs           显示当前 CPU 的基本寄存器
allregs        显示扩展寄存器（包括各模式下的寄存器）
```

**regs 示例**：
```
 r0 00000000  r1 00000000  r2 01287000  r3 00000000
 r4 c0d28000  r5 c0d28000  r6 00000000  r7 c0923060
 r8 6000406a  r9 410fc075 r10 00000000 r11 00000000  mode SVC
 ip 00000000  sp c0d29fa0  lr c000e874  pc c0031a5c cpsr 000001d3
```

**allregs 示例**（额外显示各模式下的寄存器）：
```
*svc: sp c0d29eb0  lr c06a72d0  spsr 600f0013
 abt: sp c0e451cc  lr c000d840  spsr 600d0193
 und: sp c0e451d8  lr c000d8e0  spsr a00d0093
 irq: sp c0e451c0  lr c000d6c0  spsr 600f0193
 fiq: r8 c359309a  r9 994f9e22  r10 f246bb7d  r11 b39c5be2  r12 5a16992c
```

### 栈跟踪
```
bt             显示当前 CPU 的调用栈（backtrace）
pc             显示 PC 寄存器状态
```

---

## 进程与中断

### 进程列表
```
ps             显示所有进程的简要列表
```
**输出格式**：`pid  ppid  prio  task  state  pc`

### 中断状态
```
irqs           显示中断统计信息
```

---

## 内核日志

### 当前内核日志
```
kmsg           显示当前内核消息缓冲区
```

### 上次内核日志
```
last_kmsg      显示上次重启前的内核日志（需要 pstore 支持）
```
**用途**：查看系统崩溃/重启前的最后日志，对于定位死机原因非常重要。

---

## 系统控制

### 重启/复位
```
reboot [<c>]   软重启，可选参数 c 指定重启命令
reset [<c>]    硬件复位
```

### 休眠控制
```
sleep          允许系统在 FIQ 模式下进入休眠
nosleep        禁止系统在 FIQ 模式下进入休眠（默认）
```

---

## SysRq 魔术键

通过 `sysrq <参数>` 执行 Linux 魔术键功能。

### 查看帮助
```
sysrq          显示所有 SysRq 选项
```

### 常用 SysRq 参数

| 参数 | 功能 | 说明 |
|------|------|------|
| `m` | Show Memory | 显示内存使用情况 |
| `t` | Show Task States | 显示所有任务状态及调用栈 |
| `l` | Show Backtrace All CPUs | 显示所有 CPU 的调用栈 |
| `w` | Show Blocked Tasks | 显示被阻塞的任务（D状态） |
| `p` | Show Registers | 显示寄存器 |
| `q` | Show All Timers | 显示所有定时器 |
| `b` | Reboot | 立即重启 |
| `c` | Crash | 触发系统崩溃（生成 crash dump） |
| `s` | Sync | 同步所有文件系统 |
| `u` | Unmount | 只读挂载所有文件系统 |
| `e` | Terminate All | 向所有进程发送 SIGTERM |
| `i` | Kill All | 向所有进程发送 SIGKILL |
| `n` | Nice All RT | 降低实时任务优先级 |
| `f` | OOM Kill | 触发 OOM killer |
| `o` | Power Off | 关机 |
| `j` | Thaw Filesystems | 解冻文件系统 |
| `z` | Dump Ftrace | 输出 ftrace 缓冲区 |

### SysRq 使用示例

**查看内存**：
```
sysrq m
# 输出包括：各 CPU 页面分配、活跃/非活跃页面、slab 信息等
```

**显示所有任务状态**：
```
sysrq t
# 输出所有进程的状态和调用栈
```

**显示所有 CPU 调用栈**：
```
sysrq l
# 对于诊断多核死锁特别有用
```

**显示阻塞任务**：
```
sysrq w
# 显示 D 状态（不可中断睡眠）的任务
# 对于诊断 I/O 阻塞问题很有用
```

---

## 系统异常时的完整诊断流程

当系统出现卡死/异常时，按以下顺序收集信息：

### 第一步：进入 FIQ 并收集基础信息
```
fiq<回车>
version
cpu
regs
allregs
bt
```

### 第二步：遍历所有 CPU
```
cpu 0
regs
bt
cpu 1
regs
bt
cpu 2
regs
bt
cpu 3
regs
bt
```

### 第三步：收集系统状态
```
ps
irqs
```

### 第四步：使用 SysRq 收集详细信息
```
sysrq m     # 内存信息
sysrq l     # 所有 CPU 调用栈
sysrq t     # 所有任务状态
sysrq w     # 阻塞任务
```

### 第五步：查看内核日志
```
kmsg
last_kmsg
```

### 第六步：退出或重启
```
console     # 返回正常控制台
# 或
reboot      # 重启系统
```

---

## 注意事项

1. **FIQ 是最高优先级中断**：即使系统已经死锁，FIQ 通常仍然可以响应
2. **某些命令输出很长**：建议将输出保存到文件后分析
3. **last_kmsg 依赖 pstore**：需要内核配置支持才能使用
4. **SysRq b/c 会导致系统重启/崩溃**：谨慎使用
