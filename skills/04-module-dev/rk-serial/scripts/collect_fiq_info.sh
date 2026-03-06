#!/bin/bash
#
# Rockchip FIQ Diagnostic Information Collection Script (Linux)
# 
# Upload PowerShell script to Windows PC, execute it, and retrieve the log
#
# Usage:
#   ./collect_fiq_info.sh -i <windows_ip> -u <username> -p <password> -c <com_port>
#   ./collect_fiq_info.sh -i 172.16.21.12 -u steven -p password123 -c COM64
#   ./collect_fiq_info.sh -i 172.16.21.12 -u steven -p password123 -c COM64 -n 8  # 8-core CPU
#
# Output:
#   /tmp/fiq_debug_<timestamp>.txt

set -e

# Default values
WINDOWS_IP=""
USERNAME=""
PASSWORD=""
COM_PORT=""
CPU_COUNT=0  # 0 means auto-detect
OUTPUT_DIR="/tmp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS_SCRIPT="$SCRIPT_DIR/collect_fiq_info.ps1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_usage() {
    echo "Usage: $0 -i <windows_ip> -u <username> -p <password> -c <com_port>"
    echo ""
    echo "Parameters:"
    echo "  -i  Windows PC IP address"
    echo "  -u  SSH username"
    echo "  -p  SSH password"
    echo "  -c  Serial port (e.g. COM64)"
    echo "  -n  CPU count (default: auto-detect)"
    echo "  -o  Output directory (default: /tmp)"
    echo "  -h  Show help"
    echo ""
    echo "Examples:"
    echo "  $0 -i 172.16.21.12 -u steven -p mypassword -c COM64"
    echo "  $0 -i 172.16.21.12 -u steven -p mypassword -c COM64 -n 8  # 8-core CPU"
}

# Parse arguments
while getopts "i:u:p:c:n:o:h" opt; do
    case $opt in
        i) WINDOWS_IP="$OPTARG" ;;
        u) USERNAME="$OPTARG" ;;
        p) PASSWORD="$OPTARG" ;;
        c) COM_PORT="$OPTARG" ;;
        n) CPU_COUNT="$OPTARG" ;;
        o) OUTPUT_DIR="$OPTARG" ;;
        h) print_usage; exit 0 ;;
        *) print_usage; exit 1 ;;
    esac
done

# Check required parameters
if [ -z "$WINDOWS_IP" ] || [ -z "$USERNAME" ] || [ -z "$PASSWORD" ] || [ -z "$COM_PORT" ]; then
    echo -e "${RED}Error: Missing required parameters${NC}"
    print_usage
    exit 1
fi

# Check sshpass
if ! command -v sshpass &> /dev/null; then
    echo -e "${RED}Error: sshpass is required${NC}"
    echo "Ubuntu/Debian: sudo apt install sshpass"
    exit 1
fi

# Check PowerShell script exists
if [ ! -f "$PS_SCRIPT" ]; then
    echo -e "${RED}Error: PowerShell script not found: $PS_SCRIPT${NC}"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_OUTPUT="$OUTPUT_DIR/fiq_debug_$TIMESTAMP.txt"
REMOTE_PS_SCRIPT="C:\\Users\\$USERNAME\\collect_fiq_info.ps1"

echo -e "${CYAN}=== Rockchip FIQ Diagnostic Collection ===${NC}"
echo "Windows PC: $WINDOWS_IP"
echo "Username: $USERNAME"
echo "Serial Port: $COM_PORT"
echo "CPU Count: $([ $CPU_COUNT -eq 0 ] && echo 'auto-detect' || echo $CPU_COUNT)"
echo "Local Output: $LOCAL_OUTPUT"
echo ""

# Test SSH connection
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ! timeout 10 sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$USERNAME@$WINDOWS_IP" "echo connected" > /dev/null 2>&1; then
    echo -e "${RED}Error: SSH connection failed${NC}"
    exit 1
fi
echo -e "${GREEN}SSH connection OK${NC}"

# Upload PowerShell script
echo -e "${YELLOW}Uploading PowerShell script...${NC}"
if ! sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$PS_SCRIPT" "$USERNAME@$WINDOWS_IP:$REMOTE_PS_SCRIPT" 2>/dev/null; then
    echo -e "${RED}Error: Failed to upload script${NC}"
    exit 1
fi
echo -e "${GREEN}Script uploaded${NC}"

# Build PowerShell command
PS_ARGS="-ComPort $COM_PORT"
if [ "$CPU_COUNT" -gt 0 ]; then
    PS_ARGS="$PS_ARGS -CpuCount $CPU_COUNT"
fi

# Execute PowerShell script
echo -e "${YELLOW}Collecting FIQ diagnostic info (this may take 2-3 minutes)...${NC}"
echo ""

RESULT=$(timeout 180 sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$USERNAME@$WINDOWS_IP" \
    "powershell -ExecutionPolicy Bypass -File '$REMOTE_PS_SCRIPT' $PS_ARGS" 2>&1) || true

echo "$RESULT"
echo ""

# Extract output file path from result
WIN_OUTPUT=$(echo "$RESULT" | grep -oP 'Saved to: \K.*' | tr -d '\r')

if [ -z "$WIN_OUTPUT" ]; then
    echo -e "${RED}Error: Could not determine output file path${NC}"
    echo -e "${YELLOW}Trying default TEMP path...${NC}"
    WIN_TEMP=$(timeout 10 sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$USERNAME@$WINDOWS_IP" 'echo %TEMP%' 2>/dev/null | tr -d '\r')
    WIN_OUTPUT=$(ls -t "$WIN_TEMP/fiq_debug_"*.txt 2>/dev/null | head -1 || echo "")
fi

if [ -z "$WIN_OUTPUT" ]; then
    echo -e "${RED}Error: Failed to collect FIQ info${NC}"
    exit 1
fi

# Download log file
echo -e "${YELLOW}Downloading log file...${NC}"
# Convert Windows path for scp (backslash to forward slash)
WIN_OUTPUT_SCP=$(echo "$WIN_OUTPUT" | sed 's/\\/\//g')

if sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$USERNAME@$WINDOWS_IP:$WIN_OUTPUT_SCP" "$LOCAL_OUTPUT" 2>/dev/null; then
    echo -e "${GREEN}Log saved to: $LOCAL_OUTPUT${NC}"
    
    # File stats
    FILE_SIZE=$(stat -c%s "$LOCAL_OUTPUT" 2>/dev/null || stat -f%z "$LOCAL_OUTPUT" 2>/dev/null)
    LINE_COUNT=$(wc -l < "$LOCAL_OUTPUT")
    echo "File size: $FILE_SIZE bytes"
    echo "Lines: $LINE_COUNT"
    
    echo ""
    echo -e "${CYAN}=== Log Preview (first 50 lines) ===${NC}"
    head -50 "$LOCAL_OUTPUT"
    echo ""
    echo -e "${CYAN}... (use 'cat $LOCAL_OUTPUT' for full content)${NC}"
else
    echo -e "${RED}Error: Failed to download log file${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Collection Complete ===${NC}"
