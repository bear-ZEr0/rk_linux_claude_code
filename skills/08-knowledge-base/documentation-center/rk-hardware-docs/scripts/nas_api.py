#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rockchip NAS API Python工具
提供经过验证的标准NAS API操作，避免重复试错
"""

import json
import sys
import subprocess
import urllib.parse
import requests
from typing import List, Dict, Optional, Tuple
import tempfile
import os


def safe_print(msg):
    """Print with encoding error handling for Windows"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


class RockchipNASAPI:
    """Rockchip NAS API 客户端"""

    def __init__(self, nas_server: str = "http://10.10.10.79:5000"):
        self.nas_server = nas_server
        self.sid = ""
        self.session = requests.Session()

        # 标准API参数（经过验证可用的配置）
        self.auth_config = {
            "api": "SYNO.API.Auth",
            "version": "3",  # 关键：必须使用version=3
            "method": "login",
            "account": "肖小霞",
            "passwd": "123456",
            "session": "FileStation",  # 关键：必须使用FileStation
            "format": "cookie"  # 关键：必须使用format=cookie
        }

        # 文件列表API配置
        self.list_config = {
            "api": "SYNO.FileStation.List",
            "version": "2",
            "method": "list"
        }

        # 下载API配置
        self.download_config = {
            "api": "SYNO.FileStation.Download",
            "version": "2",
            "method": "download",
            "mode": "download"
        }

    def authenticate(self) -> bool:
        """
        认证NAS服务器
        使用经过验证的标准参数，避免试错

        Returns:
            认证是否成功
        """
        safe_print("[AUTH] 正在认证NAS服务器...")

        try:
            # 构造认证URL
            auth_url = f"{self.nas_server}/webapi/auth.cgi"
            params = self.auth_config.copy()

            # 发送认证请求
            response = self.session.get(auth_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("success"):
                self.sid = data["data"]["sid"]
                safe_print(f"[OK] 认证成功，SID: {self.sid}")
                return True
            else:
                error_code = data.get("error", {}).get("code", "unknown")
                safe_print(f"[ERROR] 认证失败，错误代码: {error_code}")
                self._print_auth_error_solution(error_code)
                return False

        except requests.exceptions.RequestException as e:
            safe_print(f"[ERROR] 网络请求失败: {e}")
            return False
        except json.JSONDecodeError as e:
            safe_print(f"[ERROR] 响应解析失败: {e}")
            return False

    def _print_auth_error_solution(self, error_code: str) -> None:
        """打印认证错误解决方案"""
        solutions = {
            "119": "权限不足 - 联系管理员配置FileStation访问权限",
            "400": "认证失败 - 检查用户名密码",
            "403": "访问被拒绝 - 检查账户权限",
            "404": "API不存在 - 检查NAS服务器配置",
            "500": "服务器内部错误 - 联系管理员"
        }

        solution = solutions.get(error_code, "未知错误 - 联系管理员")
        safe_print(f"[TIP] 解决方案: {solution}")

    def check_permissions(self) -> bool:
        """
        检查文件访问权限

        Returns:
            权限是否正常
        """
        if not self.sid:
            safe_print("[ERROR] 未认证，请先调用authenticate()")
            return False

        safe_print("[CHECK] 验证文件访问权限...")

        try:
            # 使用shares方法检查共享文件夹权限
            list_url = f"{self.nas_server}/webapi/entry.cgi"
            params = {
                "api": "SYNO.FileStation.List",
                "version": "2",
                "method": "list_share",
                "_sid": self.sid
            }

            response = self.session.get(list_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("success"):
                safe_print("[OK] 文件访问权限验证通过")
                return True
            else:
                error_code = data.get("error", {}).get("code", "unknown")
                safe_print(f"[ERROR] 权限验证失败 (错误代码: {error_code})")
                return False

        except requests.exceptions.RequestException as e:
            safe_print(f"[ERROR] 权限检查失败: {e}")
            return False

    def list_files(self, folder_path: str, keyword: str = "") -> List[Dict]:
        """
        列出目录中的文件

        Args:
            folder_path: 目录路径
            keyword: 搜索关键词（可选）

        Returns:
            文件列表
        """
        if not self.sid:
            safe_print("[ERROR] 未认证，请先调用authenticate()")
            return []

        try:
            list_url = f"{self.nas_server}/webapi/entry.cgi"
            params = {
                **self.list_config,
                "folder_path": folder_path,
                "_sid": self.sid
            }

            response = self.session.get(list_url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                return []

            files = data.get("data", {}).get("files", [])
            dirs = data.get("data", {}).get("dirs", [])
            all_items = files + dirs

            # 关键词过滤
            if keyword:
                all_items = [item for item in all_items
                           if keyword.upper() in item.get("name", "").upper()]

            return all_items

        except requests.exceptions.RequestException:
            return []

    def search_chip_documents(self, chip_model: str) -> Dict[str, List[Dict]]:
        """
        搜索特定芯片文档（标准3位置搜索）

        Args:
            chip_model: 芯片型号（如 "RK3588"）

        Returns:
            按目录分类的搜索结果
        """
        results = {}

        safe_print(f"[SEARCH] 搜索 {chip_model} 相关文档...")

        # 1. 搜索芯片专用目录
        chip_path = f"/03_对外发布文件/{chip_model}"
        chip_files = self.list_files(chip_path)
        if chip_files:
            results["芯片专用目录"] = chip_files
            safe_print(f"  [OK] 芯片目录: 找到 {len(chip_files)} 个文件")

        # 2. 搜索Datasheet目录
        datasheet_path = "/03_对外发布文件/01_Datasheet"
        datasheet_files = self.list_files(datasheet_path, chip_model)
        if datasheet_files:
            results["Datasheet目录"] = datasheet_files
            safe_print(f"  [OK] Datasheet: 找到 {len(datasheet_files)} 个文件")

        # 3. 搜索TRM目录
        trm_path = "/03_对外发布文件/02_TRM"
        trm_files = self.list_files(trm_path, chip_model)
        if trm_files:
            results["TRM目录"] = trm_files
            safe_print(f"  [OK] TRM目录: 找到 {len(trm_files)} 个文件")

        return results

    def download_file(self, file_path: str, output_path: str = "/tmp/") -> bool:
        """
        下载文件

        Args:
            file_path: 文件路径
            output_path: 输出目录

        Returns:
            下载是否成功
        """
        if not self.sid:
            return False

        try:
            # 构造下载URL（直接在URL中传递参数，避免双重编码）
            encoded_path = urllib.parse.quote(file_path, safe='')

            download_url = (
                f"{self.nas_server}/webapi/entry.cgi"
                f"?api=SYNO.FileStation.Download"
                f"&version=2"
                f"&method=download"
                f"&path={encoded_path}"
                f"&mode=download"
                f"&_sid={self.sid}"
            )

            response = self.session.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # 构造输出文件路径
            filename = os.path.basename(file_path)
            output_file = os.path.join(output_path.rstrip('/'), filename)

            # 写入文件
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(output_file)
            safe_print(f"[OK] 下载成功: {filename} ({file_size} bytes)")
            return True

        except requests.exceptions.RequestException as e:
            safe_print(f"[ERROR] 下载失败: {e}")
            return False
        except OSError as e:
            safe_print(f"[ERROR] 文件写入失败: {e}")
            return False

    def search_and_download(self, chip_model: str, download_dir: str = "/tmp/") -> List[str]:
        """
        搜索并下载芯片文档

        Args:
            chip_model: 芯片型号
            download_dir: 下载目录

        Returns:
            下载成功的文件列表
        """
        # 搜索文档
        results = self.search_chip_documents(chip_model)

        if not results:
            safe_print("[ERROR] 未找到相关文档")
            return []

        downloaded_files = []
        total_files = 0

        for category, files in results.items():
            safe_print(f"\n[DIR] {category}:")

            for file_info in files:
                if not file_info.get("isdir", False):  # 只下载文件
                    total_files += 1
                    file_path = file_info.get("path", "")
                    filename = file_info.get("name", "")

                    # 只下载PDF、DOC、PPT文件
                    if filename.lower().endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx')):
                        safe_print(f"  [DOWNLOAD] 下载中: {filename}")
                        if self.download_file(file_path, download_dir):
                            downloaded_files.append(filename)
                        else:
                            safe_print(f"  [ERROR] 下载失败: {filename}")
                    else:
                        safe_print(f"  [SKIP] 跳过: {filename}")

        safe_print(f"\n[STAT] 下载统计: 成功 {len(downloaded_files)}/{total_files} 个文件")
        return downloaded_files

    def logout(self) -> None:
        """登出NAS服务器"""
        if self.sid:
            try:
                logout_url = f"{self.nas_server}/webapi/auth.cgi"
                params = {
                    "api": "SYNO.API.Auth",
                    "version": "1",
                    "method": "logout",
                    "session": "FileStation",
                    "_sid": self.sid
                }

                self.session.get(logout_url, params=params, timeout=5)
                safe_print("[OK] 已登出")
            except Exception:
                pass  # 登出失败不影响程序执行
            finally:
                self.sid = ""

    def __enter__(self):
        """上下文管理器入口"""
        if self.authenticate():
            if self.check_permissions():
                return self
            else:
                raise PermissionError("权限验证失败")
        else:
            raise ConnectionError("认证失败")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.logout()

def main():
    """命令行主函数"""
    if len(sys.argv) < 2:
        safe_print("用法: python3 nas_api.py <芯片型号> [--download] [--output-dir <目录>]")
        safe_print("示例: python3 nas_api.py RK3588")
        safe_print("      python3 nas_api.py RK3588 --download --output-dir ./downloads")
        sys.exit(1)

    chip_model = sys.argv[1]
    should_download = "--download" in sys.argv
    output_dir = "/tmp/"

    # 提取输出目录
    if "--output-dir" in sys.argv:
        output_dir_index = sys.argv.index("--output-dir")
        if output_dir_index + 1 < len(sys.argv):
            output_dir = sys.argv[output_dir_index + 1]
        else:
            safe_print("[ERROR] --output-dir 需要指定目录")
            sys.exit(1)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 使用上下文管理器
    try:
        with RockchipNASAPI() as nas:
            if should_download:
                downloaded_files = nas.search_and_download(chip_model, output_dir)
                if downloaded_files:
                    safe_print(f"\n[DIR] 所有文件已下载到: {output_dir}")
                    for filename in downloaded_files:
                        safe_print(f"  [OK] {filename}")
            else:
                results = nas.search_chip_documents(chip_model)

                if results:
                    safe_print(f"\n[SEARCH] 搜索结果: {chip_model}")
                    safe_print("=" * 50)

                    for category, files in results.items():
                        safe_print(f"\n[DIR] {category}:")
                        for file_info in files:
                            name = file_info.get("name", "")
                            is_dir = file_info.get("isdir", False)
                            icon = "[D]" if is_dir else "[F]"
                            safe_print(f"  {icon} {name}")
                else:
                    safe_print("[ERROR] 未找到相关文档")

    except (ConnectionError, PermissionError) as e:
        safe_print(f"[ERROR] 操作失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        safe_print("\n[WARN] 用户中断操作")

if __name__ == "__main__":
    main()