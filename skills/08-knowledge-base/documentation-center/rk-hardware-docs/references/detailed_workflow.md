# 详细工作流程和最佳实践

本文档提供Rockchip硬件文档检索的详细工作流程，适合需要深入了解和优化文档检索流程的用户。

## 1. 认证流程详解

### 1.1 标准认证参数

经过验证的可靠认证配置：

```python
# Python实现
auth_config = {
    "api": "SYNO.API.Auth",
    "version": "3",        # 关键参数，必须使用3
    "method": "login",
    "account": "肖小霞",
    "passwd": "123456",
    "session": "FileStation",  # 必须使用FileStation
    "format": "cookie"        # 必须使用cookie格式
}
```

```bash
# Bash实现
curl -s "http://10.10.10.79:5000/webapi/auth.cgi?api=SYNO.API.Auth&version=3&method=login&account=肖小霞&passwd=123456&session=FileStation&format=cookie"
```

### 1.2 认证失败处理

| 错误代码 | 原因 | 解决方案 |
|---------|------|---------|
| 119 | 权限不足 | 联系管理员配置FileStation权限 |
| 400 | 认证失败 | 检查用户名密码 |
| 403 | 访问拒绝 | 检查账户状态 |
| 500 | 服务器错误 | 联系NAS管理员 |

## 2. 搜索策略优化

### 2.1 三层搜索策略

#### 第一层：芯片专用目录
```
/03_对外发布文件/{CHIP_MODEL}/
```
- 优先级最高
- 通常包含该芯片的所有相关文档
- 搜索速度最快

#### 第二层：Datasheet目录
```
/03_对外发布文件/01_Datasheet/
```
- 包含所有芯片的数据手册
- 文档数量最多
- 需要关键词过滤

#### 第三层：TRM目录
```
/03_对外发布文件/02_TRM/
```
- 技术参考手册
- 包含详细的寄存器和功能描述
- 适合深度技术分析

### 2.2 关键词匹配策略

#### 精确匹配
- 用户指定"RK3588C" → 精确搜索"RK3588C"
- 避免返回"RK3588"或"RK3588S"的结果

#### 模糊匹配
- 当精确匹配无结果时，提供相似型号
- 按相似度排序推荐

#### 通配符匹配
- 支持"RK35*"格式
- 用于发现相关芯片系列

### 2.3 搜索优化技巧

```python
# 高效的文件过滤
def filter_documents(files, keyword, file_types=None):
    """
    高效文档过滤

    Args:
        files: 文件列表
        keyword: 搜索关键词
        file_types: 文件类型过滤（如['.pdf', '.doc']）
    """
    filtered = []
    for file in files:
        name = file.get('name', '').upper()

        # 关键词匹配
        if keyword.upper() in name:
            # 文件类型过滤
            if file_types:
                if any(name.endswith(ext.upper()) for ext in file_types):
                    filtered.append(file)
            else:
                filtered.append(file)

    return filtered
```

## 3. 文档下载最佳实践

### 3.1 批量下载策略

```python
def batch_download(nas_api, files, output_dir, max_concurrent=3):
    """
    批量下载文档

    Args:
        nas_api: NAS API客户端
        files: 文件列表
        output_dir: 输出目录
        max_concurrent: 最大并发数
    """
    import threading
    from queue import Queue

    download_queue = Queue()
    results = []

    def worker():
        while True:
            file_info = download_queue.get()
            if file_info is None:
                break

            success = nas_api.download_file(
                file_info['path'],
                output_dir
            )
            results.append((file_info['name'], success))
            download_queue.task_done()

    # 启动工作线程
    threads = []
    for i in range(max_concurrent):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    # 添加下载任务
    for file_info in files:
        download_queue.put(file_info)

    # 等待完成
    download_queue.join()

    # 停止工作线程
    for _ in range(max_concurrent):
        download_queue.put(None)

    for t in threads:
        t.join()

    return results
```

### 3.2 下载重试机制

```python
def download_with_retry(nas_api, file_path, output_dir, max_retries=3):
    """
    带重试的文件下载

    Args:
        nas_api: NAS API客户端
        file_path: 文件路径
        output_dir: 输出目录
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            success = nas_api.download_file(file_path, output_dir)
            if success:
                return True

            if attempt < max_retries - 1:
                print(f"下载失败，重试 {attempt + 1}/{max_retries}...")
                time.sleep(2 ** attempt)  # 指数退避

        except Exception as e:
            print(f"下载异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    return False
```

## 4. 性能优化

### 4.1 缓存机制

```python
import pickle
import hashlib
from datetime import datetime, timedelta

class CachedNASAPI(RockchipNASAPI):
    """带缓存的NAS API客户端"""

    def __init__(self, cache_dir="/tmp/nas_cache"):
        super().__init__()
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_ttl = timedelta(hours=1)  # 缓存1小时

    def _get_cache_key(self, method, *args):
        """生成缓存键"""
        key = f"{method}:{args}"
        return hashlib.md5(key.encode()).hexdigest()

    def _is_cache_valid(self, cache_file):
        """检查缓存是否有效"""
        if not os.path.exists(cache_file):
            return False

        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        return datetime.now() - file_time < self.cache_ttl

    def list_files_cached(self, folder_path, keyword=""):
        """带缓存的文件列表"""
        cache_key = self._get_cache_key("list_files", folder_path, keyword)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        # 检查缓存
        if self._is_cache_valid(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        # 获取新数据
        files = self.list_files(folder_path, keyword)

        # 保存缓存
        with open(cache_file, 'wb') as f:
            pickle.dump(files, f)

        return files
```

### 4.2 并发搜索

```python
import concurrent.futures
from typing import Dict, List

def concurrent_search(nas_api, chip_model, max_workers=5):
    """
    并发搜索多个位置

    Args:
        nas_api: NAS API客户端
        chip_model: 芯片型号
        max_workers: 最大并发数
    """
    search_paths = [
        (f"/03_对外发布文件/{chip_model}", ""),
        ("/03_对外发布文件/01_Datasheet", chip_model),
        ("/03_对外发布文件/02_TRM", chip_model),
    ]

    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交搜索任务
        future_to_path = {
            executor.submit(nas_api.list_files, path, keyword): path_name
            for (path, keyword), path_name in [
                ((search_paths[0][0], search_paths[0][1]), "芯片专用目录"),
                ((search_paths[1][0], search_paths[1][1]), "Datasheet目录"),
                ((search_paths[2][0], search_paths[2][1]), "TRM目录"),
            ]
        }

        # 收集结果
        for future in concurrent.futures.as_completed(future_to_path):
            path_name = future_to_path[future]
            try:
                files = future.result()
                if files:
                    results[path_name] = files
            except Exception as exc:
                print(f'{path_name} 搜索失败: {exc}')

    return results
```


## 5. 使用建议

### 5.1 小规模使用
- 直接使用基础API方法
- 无需复杂的缓存和并发
- 适合偶尔查询

### 5.2 中等规模使用
- 启用缓存机制
- 使用并发搜索

### 5.3 大规模使用
- 使用数据库存储索引
- 建立文档分析管道
- 考虑分布式架构

### 5.4 生产环境建议
- 添加日志记录
- 实现配置文件管理
- 定期备份重要文档

通过遵循这些最佳实践，可以构建一个稳定、高效的Rockchip硬件文档检索系统。