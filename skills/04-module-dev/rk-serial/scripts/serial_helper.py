#!/usr/bin/env python3
"""
Rockchip Serial Port Helper Script

Provides utilities for:
- Configuration management (read/write ~/.rk-serial/config.json)
- SSH connection testing
- Serial port discovery (Linux/Windows)
- Basic serial operations

Usage:
    # Test SSH connection
    python3 serial_helper.py test-ssh --host 172.16.21.161 --user cw --password " "
    
    # Discover serial ports
    python3 serial_helper.py discover-ports --host 172.16.21.161 --user cw --password " " --platform linux
    
    # Test serial communication
    python3 serial_helper.py test-serial --host 172.16.21.161 --user cw --password " " --platform linux --port /dev/ttyUSB0
    
    # Save profile
    python3 serial_helper.py save-profile --name "linux-dev" --host 172.16.21.161 --user cw --password " " --platform linux --port /dev/ttyUSB0
    
    # List profiles
    python3 serial_helper.py list-profiles
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration file path
CONFIG_DIR = Path.home() / ".rk-serial"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from file."""
    if not CONFIG_FILE.exists():
        return {"last_used_profile": None, "profiles": {}}
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"Configuration saved to {CONFIG_FILE}")


def safe_print(msg):
    """Print with encoding error handling for Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def test_ssh(host: str, user: str, password: str, timeout: int = 10) -> bool:
    """Test SSH connection to remote host."""
    cmd = [
        'sshpass', '-p', password,
        'ssh', '-o', 'StrictHostKeyChecking=no', '-o', f'ConnectTimeout={timeout}',
        f'{user}@{host}', 'echo connected'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if 'connected' in result.stdout:
            safe_print(f"[OK] SSH connection successful: {user}@{host}")
            return True
        else:
            safe_print(f"[ERROR] SSH connection failed: {result.stderr or result.stdout}")
            print("\n[Tip] If connecting to Windows, Firewall might be blocking port 22.")
            print("      Try disabling firewall temporarily via PowerShell (Admin):")
            print("      Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False")
            return False
    except subprocess.TimeoutExpired:
        safe_print(f"[ERROR] SSH connection timeout after {timeout}s")
        print("\n[Tip] If connecting to Windows, Firewall might be blocking port 22.")
        print("      Try disabling firewall temporarily via PowerShell (Admin):")
        print("      Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False")
        return False
    except FileNotFoundError:
        safe_print("[ERROR] sshpass not found. Install with: sudo apt install sshpass")
        return False


def discover_ports_linux(host: str, user: str, password: str) -> list:
    """Discover serial ports on remote Linux host."""
    cmd = [
        'sshpass', '-p', password,
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f'{user}@{host}',
        'ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null; ls -la /dev/serial/by-id/ 2>/dev/null || true'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ports = []
        for line in result.stdout.strip().split('\n'):
            if '/dev/tty' in line:
                # Extract device path
                parts = line.split()
                if parts:
                    dev = parts[-1] if '->' in line else [p for p in parts if '/dev/tty' in p]
                    if isinstance(dev, list) and dev:
                        dev = dev[0]
                    if '/dev/tty' in str(dev):
                        ports.append(dev)
        return list(set(ports))
    except Exception as e:
        print(f"Error discovering ports: {e}")
        return []


def discover_ports_windows(host: str, user: str, password: str) -> list:
    """Discover serial ports on remote Windows host."""
    cmd = [
        'sshpass', '-p', password,
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f'{user}@{host}',
        'powershell -Command "[System.IO.Ports.SerialPort]::GetPortNames()"'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ports = [p.strip() for p in result.stdout.strip().split('\n') if p.strip().startswith('COM')]
        return ports
    except Exception as e:
        print(f"Error discovering ports: {e}")
        return []


def discover_ports(host: str, user: str, password: str, platform: str) -> list:
    """Discover serial ports on remote host."""
    if platform == 'linux':
        ports = discover_ports_linux(host, user, password)
    else:
        ports = discover_ports_windows(host, user, password)
    
    if ports:
        print(f"Found serial ports on {host}:")
        for p in ports:
            print(f"  - {p}")
    else:
        print(f"No serial ports found on {host}")
    
    return ports


def test_serial_linux(host: str, user: str, password: str, port: str, baud: int = 1500000) -> bool:
    """Test serial communication on remote Linux host."""
    python_code = f'''
import serial
import time

try:
    p = serial.Serial('{port}', {baud}, timeout=3)
    p.reset_input_buffer()
    p.write(b'\\r\\n')
    time.sleep(1)
    output = p.read(p.in_waiting or 1024)
    p.close()
    text = output.decode('utf-8', errors='replace')
    if text.strip():
        print('SERIAL_OK')
        print(text)
    else:
        print('SERIAL_EMPTY')
except Exception as e:
    print(f'SERIAL_ERROR: {{e}}')
'''
    
    cmd = [
        'sshpass', '-p', password,
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f'{user}@{host}',
        f'python3 -c "{python_code}"'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = result.stdout + result.stderr
        
        if 'SERIAL_OK' in output:
            safe_print(f"[OK] Serial port {port} is responsive")
            # Print device output
            lines = output.split('\n')
            for line in lines[1:]:  # Skip SERIAL_OK line
                if line.strip():
                    safe_print(f"  Device: {line}")
            return True
        elif 'SERIAL_EMPTY' in output:
            safe_print(f"[WARN] Serial port {port} opened but no device response (device may be idle)")
            return True
        else:
            safe_print(f"[ERROR] Serial port test failed: {output}")
            return False
    except Exception as e:
        safe_print(f"[ERROR] Error testing serial: {e}")
        return False


def test_serial_windows(host: str, user: str, password: str, port: str, baud: int = 1500000) -> bool:
    """Test serial communication on remote Windows host."""
    ps_cmd = f'''
try {{
    $p = New-Object System.IO.Ports.SerialPort {port},{baud},None,8,One
    $p.Open()
    $p.DiscardInBuffer()
    $p.WriteLine('')
    Start-Sleep -Seconds 1
    $output = $p.ReadExisting()
    $p.Close()
    if ($output) {{
        Write-Host 'SERIAL_OK'
        Write-Host $output
    }} else {{
        Write-Host 'SERIAL_EMPTY'
    }}
}} catch {{
    Write-Host "SERIAL_ERROR: $_"
}}
'''
    
    cmd = [
        'sshpass', '-p', password,
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f'{user}@{host}',
        f'powershell -Command "{ps_cmd}"'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = result.stdout + result.stderr
        
        if 'SERIAL_OK' in output:
            safe_print(f"[OK] Serial port {port} is responsive")
            return True
        elif 'SERIAL_EMPTY' in output:
            safe_print(f"[WARN] Serial port {port} opened but no device response")
            return True
        else:
            safe_print(f"[ERROR] Serial port test failed: {output}")
            return False
    except Exception as e:
        safe_print(f"[ERROR] Error testing serial: {e}")
        return False


def test_serial(host: str, user: str, password: str, platform: str, port: str, baud: int = 1500000) -> bool:
    """Test serial communication on remote host."""
    if platform == 'linux':
        return test_serial_linux(host, user, password, port, baud)
    else:
        return test_serial_windows(host, user, password, port, baud)


def save_profile(name: str, host: str, user: str, password: str, platform: str, 
                 port: str = None, baud: int = 1500000) -> None:
    """Save a connection profile."""
    config = load_config()
    
    profile = {
        "platform": platform,
        "host": host,
        "username": user,
        "password": password,
        "baud_rate": baud,
        "last_success": datetime.now().isoformat()
    }
    
    # Save port for Linux (stable), skip for Windows (changes frequently)
    if platform == 'linux' and port:
        profile["serial_port"] = port
    
    config["profiles"][name] = profile
    config["last_used_profile"] = name
    
    save_config(config)
    print(f"Profile '{name}' saved successfully")


def list_profiles() -> None:
    """List all saved profiles."""
    config = load_config()
    profiles = config.get("profiles", {})
    
    if not profiles:
        print("No saved profiles found.")
        print(f"Configuration file location: {CONFIG_FILE}")
        return
    
    print(f"Saved profiles ({CONFIG_FILE}):")
    print("-" * 60)
    
    last_used = config.get("last_used_profile")
    
    for name, profile in profiles.items():
        marker = " (last used)" if name == last_used else ""
        platform = profile.get("platform", "unknown")
        host = profile.get("host", "")
        user = profile.get("username", "")
        port = profile.get("serial_port", "N/A (ask user)" if platform == "windows" else "not set")
        
        print(f"\n[{name}]{marker}")
        print(f"  Platform: {platform}")
        print(f"  Host: {user}@{host}")
        print(f"  Serial Port: {port}")
        print(f"  Baud Rate: {profile.get('baud_rate', 1500000)}")
        if profile.get("last_success"):
            print(f"  Last Success: {profile.get('last_success')}")


def get_profile(name: str = None) -> dict:
    """Get a profile by name, or the last used profile."""
    config = load_config()
    
    if name is None:
        name = config.get("last_used_profile")
    
    if name is None:
        return None
    
    return config.get("profiles", {}).get(name)


def main():
    parser = argparse.ArgumentParser(description='Rockchip Serial Port Helper')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # test-ssh command
    ssh_parser = subparsers.add_parser('test-ssh', help='Test SSH connection')
    ssh_parser.add_argument('--host', required=True, help='Remote host IP')
    ssh_parser.add_argument('--user', required=True, help='SSH username')
    ssh_parser.add_argument('--password', required=True, help='SSH password')
    
    # discover-ports command
    discover_parser = subparsers.add_parser('discover-ports', help='Discover serial ports')
    discover_parser.add_argument('--host', required=True, help='Remote host IP')
    discover_parser.add_argument('--user', required=True, help='SSH username')
    discover_parser.add_argument('--password', required=True, help='SSH password')
    discover_parser.add_argument('--platform', required=True, choices=['linux', 'windows'], help='Remote platform')
    
    # test-serial command
    serial_parser = subparsers.add_parser('test-serial', help='Test serial communication')
    serial_parser.add_argument('--host', required=True, help='Remote host IP')
    serial_parser.add_argument('--user', required=True, help='SSH username')
    serial_parser.add_argument('--password', required=True, help='SSH password')
    serial_parser.add_argument('--platform', required=True, choices=['linux', 'windows'], help='Remote platform')
    serial_parser.add_argument('--port', required=True, help='Serial port (e.g., /dev/ttyUSB0 or COM64)')
    serial_parser.add_argument('--baud', type=int, default=1500000, help='Baud rate (default: 1500000)')
    
    # save-profile command
    save_parser = subparsers.add_parser('save-profile', help='Save a connection profile')
    save_parser.add_argument('--name', required=True, help='Profile name')
    save_parser.add_argument('--host', required=True, help='Remote host IP')
    save_parser.add_argument('--user', required=True, help='SSH username')
    save_parser.add_argument('--password', required=True, help='SSH password')
    save_parser.add_argument('--platform', required=True, choices=['linux', 'windows'], help='Remote platform')
    save_parser.add_argument('--port', help='Serial port (saved for Linux, skipped for Windows)')
    save_parser.add_argument('--baud', type=int, default=1500000, help='Baud rate')
    
    # list-profiles command
    subparsers.add_parser('list-profiles', help='List saved profiles')
    
    # get-profile command
    get_parser = subparsers.add_parser('get-profile', help='Get profile details')
    get_parser.add_argument('--name', help='Profile name (default: last used)')
    
    args = parser.parse_args()
    
    if args.command == 'test-ssh':
        success = test_ssh(args.host, args.user, args.password)
        sys.exit(0 if success else 1)
    
    elif args.command == 'discover-ports':
        ports = discover_ports(args.host, args.user, args.password, args.platform)
        sys.exit(0 if ports else 1)
    
    elif args.command == 'test-serial':
        success = test_serial(args.host, args.user, args.password, args.platform, args.port, args.baud)
        sys.exit(0 if success else 1)
    
    elif args.command == 'save-profile':
        save_profile(args.name, args.host, args.user, args.password, args.platform, args.port, args.baud)
    
    elif args.command == 'list-profiles':
        list_profiles()
    
    elif args.command == 'get-profile':
        profile = get_profile(args.name)
        if profile:
            print(json.dumps(profile, indent=2, ensure_ascii=False))
        else:
            print("Profile not found")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
