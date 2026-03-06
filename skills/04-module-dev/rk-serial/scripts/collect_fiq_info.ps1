<#
.SYNOPSIS
    Rockchip FIQ Diagnostic Information Collection Script (Windows PowerShell)
.DESCRIPTION
    Collect all diagnostic information from FIQ debugger via serial port and save to file.
    Uses idle detection: waits until no output for IdleTimeout seconds before proceeding.
.PARAMETER ComPort
    Serial port, e.g. COM64
.PARAMETER OutputFile
    Output file path, default: $env:TEMP\fiq_debug_<timestamp>.txt
.PARAMETER BaudRate
    Baud rate, default: 1500000
.PARAMETER CpuCount
    Number of CPUs (default: auto-detect, fallback to 4)
.PARAMETER IdleTimeout
    Seconds of no output before considering command complete (default: 3)
.PARAMETER MaxCmdTimeout
    Maximum wait time per command in seconds (default: 30)
.EXAMPLE
    .\collect_fiq_info.ps1 -ComPort COM64
    .\collect_fiq_info.ps1 -ComPort COM64 -CpuCount 8 -IdleTimeout 5
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ComPort,
    
    [string]$OutputFile = "",
    
    [int]$BaudRate = 1500000,
    
    [int]$CpuCount = 0,  # 0 means auto-detect
    
    [int]$IdleTimeout = 3,  # Seconds of idle before moving on
    
    [int]$MaxCmdTimeout = 30  # Max wait per command
)

# Use temp directory with timestamp if no output file specified
if ([string]::IsNullOrEmpty($OutputFile)) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputFile = Join-Path $env:TEMP "fiq_debug_$timestamp.txt"
}

$ErrorActionPreference = "Stop"

Write-Host "=== Rockchip FIQ Diagnostic Collection ===" -ForegroundColor Cyan
Write-Host "SerialPort: $ComPort, BaudRate: $BaudRate"
Write-Host "IdleTimeout: ${IdleTimeout}s, MaxTimeout: ${MaxCmdTimeout}s"
Write-Host "OutputFile: $OutputFile"
Write-Host ""

try {
    # Create serial port object
    $port = New-Object System.IO.Ports.SerialPort $ComPort, $BaudRate, None, 8, One
    $port.ReadTimeout = 1000
    $port.WriteTimeout = 3000
    
    Write-Host "Opening serial port..." -ForegroundColor Yellow
    $port.Open()
    $port.DiscardInBuffer()
    
    $allOutput = ""
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $allOutput += "=== FIQ Diagnostic Collection ===`n"
    $allOutput += "Time: $timestamp`n"
    $allOutput += "SerialPort: $ComPort`n"
    $allOutput += "================================`n`n"
    
    # Helper function: Read until idle (no output for IdleTimeout seconds)
    function Read-UntilIdle {
        param(
            [int]$idleSeconds = $IdleTimeout,
            [int]$maxSeconds = $MaxCmdTimeout
        )
        
        $output = ""
        $lastDataTime = Get-Date
        $startTime = Get-Date
        
        while ($true) {
            # Check max timeout
            if (((Get-Date) - $startTime).TotalSeconds -ge $maxSeconds) {
                Write-Host "    (max timeout reached)" -ForegroundColor DarkYellow
                break
            }
            
            # Try to read data
            if ($port.BytesToRead -gt 0) {
                $chunk = $port.ReadExisting()
                $output += $chunk
                $lastDataTime = Get-Date  # Reset idle timer
            }
            
            # Check if idle for long enough
            $idleDuration = ((Get-Date) - $lastDataTime).TotalSeconds
            if ($idleDuration -ge $idleSeconds) {
                break
            }
            
            Start-Sleep -Milliseconds 100
        }
        
        return $output
    }
    
    # Helper function: Execute FIQ command with idle detection
    function Invoke-FiqCommand {
        param(
            [string]$cmd,
            [int]$idleSeconds = $IdleTimeout,
            [int]$maxSeconds = $MaxCmdTimeout,
            [bool]$showProgress = $true
        )
        
        if ($showProgress) {
            Write-Host "  Executing: $cmd" -ForegroundColor Green -NoNewline
        }
        
        $script:allOutput += "`n>>> $cmd <<<`n"
        $port.WriteLine($cmd)
        
        # Small initial delay to let command start
        Start-Sleep -Milliseconds 200
        
        # Read until idle
        $output = Read-UntilIdle -idleSeconds $idleSeconds -maxSeconds $maxSeconds
        $script:allOutput += $output
        
        if ($showProgress) {
            $lines = ($output -split "`n").Count
            Write-Host " ($lines lines)" -ForegroundColor Gray
        }
        
        return $output
    }
    
    # Enter FIQ mode
    Write-Host "Entering FIQ mode..." -ForegroundColor Yellow
    $port.Write("fiq")
    Start-Sleep -Milliseconds 500
    $port.WriteLine("")
    $welcome = Read-UntilIdle -idleSeconds 2 -maxSeconds 5
    $allOutput += $welcome
    Write-Host $welcome -ForegroundColor Gray
    
    # Auto-detect CPU count if not specified
    if ($CpuCount -le 0) {
        Write-Host "Auto-detecting CPU count..." -ForegroundColor Yellow
        
        # Default assumption (use 8 to cover most Rockchip SoCs)
        $CpuCount = 8
        
        # Try higher CPU numbers to detect actual count
        # We look for a response WITHOUT "offline" to confirm the CPU exists and is online
        foreach ($testCpu in @(7, 5, 3)) {
            $port.WriteLine("cpu $testCpu")
            Start-Sleep -Milliseconds 500
            if ($port.BytesToRead -gt 0) {
                $testOutput = $port.ReadExisting()
                # Check if CPU exists AND is not offline
                if ($testOutput -match "cpu $testCpu" -and $testOutput -notmatch "offline") {
                    $CpuCount = $testCpu + 1
                    break
                }
            }
        }
        
        # Return to CPU 0
        $port.WriteLine("cpu 0")
        Start-Sleep -Milliseconds 500
        if ($port.BytesToRead -gt 0) { $null = $port.ReadExisting() }
        
        Write-Host "Detected CPU count: $CpuCount" -ForegroundColor Cyan
    }
    
    $allOutput += "`nCPU Count: $CpuCount`n"
    
    # === Execute diagnostic commands ===
    
    # 1. Basic info
    Write-Host "[1/7] Basic info..." -ForegroundColor Cyan
    Invoke-FiqCommand "version"
    Invoke-FiqCommand "cpu"
    
    # 2. All CPUs registers and backtrace
    Write-Host "[2/7] CPU registers and backtrace ($CpuCount CPUs)..." -ForegroundColor Cyan
    for ($i = 0; $i -lt $CpuCount; $i++) {
        Invoke-FiqCommand "cpu $i"
        if ($i -eq 0) {
            Invoke-FiqCommand "allregs"
        } else {
            Invoke-FiqCommand "regs"
        }
        Invoke-FiqCommand "bt"
    }
    
    # 3. Process and interrupt
    Write-Host "[3/7] Process and interrupt info..." -ForegroundColor Cyan
    Invoke-FiqCommand "ps" -maxSeconds 60  # ps can take longer
    Invoke-FiqCommand "irqs"
    
    # 4. Kernel logs (capture before sysrq to avoid pollution)
    Write-Host "[4/7] Kernel logs..." -ForegroundColor Cyan
    Invoke-FiqCommand "kmsg" -maxSeconds 60
    Invoke-FiqCommand "last_kmsg" -maxSeconds 60
    
    # 5. SysRq diagnostics
    Write-Host "[5/7] SysRq diagnostics..." -ForegroundColor Cyan
    Invoke-FiqCommand "sysrq m" -maxSeconds 60  # Memory info
    Invoke-FiqCommand "sysrq l" -maxSeconds 60  # All CPU backtrace
    Invoke-FiqCommand "sysrq t" -maxSeconds 60  # Task states (can be large)
    Invoke-FiqCommand "sysrq w" -maxSeconds 60  # Blocked tasks
    Invoke-FiqCommand "sysrq q" -maxSeconds 60  # Timers
    
    # 6. Exit FIQ mode
    Write-Host "[6/6] Exiting FIQ mode..." -ForegroundColor Cyan
    $port.WriteLine("console")
    $exitOutput = Read-UntilIdle -idleSeconds 2 -maxSeconds 5
    $allOutput += $exitOutput
    
    # Save to file
    $allOutput | Out-File -FilePath $OutputFile -Encoding UTF8
    
    # Stats
    $lineCount = ($allOutput -split "`n").Count
    $fileSize = (Get-Item $OutputFile).Length
    
    Write-Host ""
    Write-Host "=== Collection Complete ===" -ForegroundColor Cyan
    Write-Host "Saved to: $OutputFile" -ForegroundColor Green
    Write-Host "File size: $fileSize bytes, Lines: $lineCount"
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    throw
} finally {
    if ($port -and $port.IsOpen) {
        $port.Close()
        Write-Host "Serial port closed" -ForegroundColor Yellow
    }
}
