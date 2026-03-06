#!/bin/bash
# Moodle E-learning Platform API 访问脚本

# 配置信息
MOODLE_URL="http://10.10.10.251"
# 从环境变量获取凭据（由用户提供）
# 使用方式: export MOODLE_USERNAME="用户名" MOODLE_PASSWORD="密码"
USERNAME="${MOODLE_USERNAME:-}"
PASSWORD="${MOODLE_PASSWORD:-}"
COOKIE_FILE="/tmp/moodle_session.txt"

# 1. 登录 Moodle 平台
login() {
    # 检查凭据是否已设置
    if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
        echo "❌ 错误: 未设置登录凭据" >&2
        echo "请设置环境变量后重试:" >&2
        echo "  export MOODLE_USERNAME=\"你的用户名\"" >&2
        echo "  export MOODLE_PASSWORD=\"你的密码\"" >&2
        return 1
    fi

    echo "🔐 正在登录 E-learning 平台 (用户: $USERNAME)..." >&2

    # 清理旧的 cookie
    rm -f "$COOKIE_FILE"

    # 获取登录 token
    local logintoken=$(curl -s --noproxy '*' --max-time 5 -c "$COOKIE_FILE" \
        "${MOODLE_URL}/login/index.php" | \
        grep -oP 'logintoken" value="\K[^"]+' | head -1)

    if [ -z "$logintoken" ]; then
        echo "❌ 获取登录token失败" >&2
        return 1
    fi

    echo "✓ 获取登录token: $logintoken" >&2

    # 执行登录
    curl -s --noproxy '*' --max-time 5 \
        -b "$COOKIE_FILE" -c "$COOKIE_FILE" \
        -d "username=$USERNAME" \
        -d "password=$PASSWORD" \
        -d "logintoken=$logintoken" \
        -d "anchor=" \
        -L "${MOODLE_URL}/login/index.php" > /tmp/moodle_login_result.html

    # 验证登录状态
    if grep -q "个人主页\|Dashboard\|logout.php" /tmp/moodle_login_result.html; then
        echo "✓ 登录成功" >&2
        return 0
    else
        echo "❌ 登录失败 (用户名或密码错误)" >&2
        return 1
    fi
}

# 2. 获取课程页面内容
get_course() {
    local course_id=$1
    local output_file=${2:-/tmp/course_${course_id}.html}

    echo "📚 获取 Course $course_id 内容..." >&2

    # 使用 curl 保持 session 一致性
    curl -s --noproxy '*' --max-time 5 -b "$COOKIE_FILE" -c "$COOKIE_FILE" \
        "${MOODLE_URL}/course/view.php?id=$course_id" \
        -o "$output_file"

    if [ -f "$output_file" ] && [ -s "$output_file" ]; then
        # 检查是否需要重新登录
        if grep -q "登录本网站\|Log in to" "$output_file"; then
            echo "⚠ Session 过期，需要重新登录" >&2
            return 2
        fi

        local file_size=$(stat -c%s "$output_file" 2>/dev/null || stat -f%z "$output_file" 2>/dev/null)
        echo "✓ 成功获取课程内容: $output_file ($file_size bytes)" >&2
        echo "$output_file"
        return 0
    else
        echo "❌ 获取课程内容失败" >&2
        return 1
    fi
}

# 3. 在课程页面中搜索关键词（支持文档类型过滤）
search_in_course() {
    local course_file=$1
    local keyword=$2
    local filter_type=${3:-"all"}  # 可选参数: "doc"=只显示文档, "all"=显示全部

    echo "🔍 在课程中搜索: $keyword ${filter_type:+(过滤: $filter_type)}" >&2

    if [ ! -f "$course_file" ]; then
        echo "❌ 课程文件不存在: $course_file" >&2
        return 1
    fi

    # 文档类型扩展名列表
    local doc_extensions="pdf|ppt|pptx|doc|docx|mp4|avi|mov|mkv|mp3|wav|zip|tar\.gz"

    # 提取包含关键词的资源名称
    # Moodle 的资源通常在 class="instancename" 中
    local results=$(grep -i "$keyword" "$course_file" | \
        grep -oP 'class="instancename"[^>]*>.*?<span' | \
        sed 's/<[^>]*>//g' | \
        sed 's/&nbsp;/ /g' | \
        grep -i "$keyword")

    # 根据过滤类型处理结果
    if [ "$filter_type" = "doc" ]; then
        # 只显示文档类资源（包含文件扩展名或明确的资源类型）
        echo "$results" | grep -iE "\.(${doc_extensions})|文件|File|视频|Video|PPT|PDF|文档|Document" | nl
    else
        # 显示所有结果
        echo "$results" | nl
    fi
}

# 4. 提取课程中的所有资源链接
list_course_resources() {
    local course_file=$1

    echo "📋 提取课程资源列表..." >&2

    if [ ! -f "$course_file" ]; then
        echo "❌ 课程文件不存在: $course_file" >&2
        return 1
    fi

    # 使用 Python 解析 HTML 会更可靠
    python3 << 'PYTHON_SCRIPT' "$course_file"
import sys
import re
from html.parser import HTMLParser

course_file = sys.argv[1] if len(sys.argv) > 1 else sys.stdin

try:
    with open(course_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有活动资源
    # Moodle 资源通常在 <li class="activity ..."> 中

    # 提取资源 ID 和名称
    pattern = r'data-activityname="([^"]*)"[^>]*>.*?href="([^"]*)"'
    matches = re.findall(pattern, content, re.DOTALL)

    if matches:
        for idx, (name, url) in enumerate(matches, 1):
            # 清理名称中的HTML实体
            name = name.replace('&nbsp;', ' ').replace('&amp;', '&')
            print(f"{idx}. {name}")
            print(f"   URL: {url}")
    else:
        # 尝试另一种匹配模式
        pattern2 = r'class="instancename">([^<]+)<'
        matches2 = re.findall(pattern2, content)
        if matches2:
            for idx, name in enumerate(matches2, 1):
                name = name.strip()
                if name:
                    print(f"{idx}. {name}")
        else:
            print("❌ 未找到资源", file=sys.stderr)

except Exception as e:
    print(f"❌ 解析错误: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
}

# 5. 获取资源下载链接
get_resource_download_url() {
    local resource_id=$1
    local output_file="/tmp/resource_${resource_id}.html"

    echo "🔗 获取资源 $resource_id 的下载链接..." >&2

    # 获取资源页面
    curl -s --noproxy '*' --max-time 5 -b "$COOKIE_FILE" \
        "${MOODLE_URL}/mod/resource/view.php?id=$resource_id" \
        > "$output_file"

    # 提取下载链接 - 尝试多种模式
    # 模式1: 直接的 pluginfile.php 链接
    local download_url=$(grep -oP 'href="http://10\.10\.10\.251/pluginfile\.php/[^"]*"' \
        "$output_file" | head -1 | sed 's/href="//;s/"//')

    # 模式2: pdfjs viewer 中的文件链接
    if [ -z "$download_url" ]; then
        download_url=$(grep -oP 'file=http://10\.10\.10\.251/pluginfile\.php/[^"&]*' \
            "$output_file" | head -1 | sed 's/file=//')
    fi

    # 模式3: 任何包含 pluginfile.php 的链接
    if [ -z "$download_url" ]; then
        download_url=$(grep -oP 'http://10\.10\.10\.251/pluginfile\.php/[^"&\s]*' \
            "$output_file" | head -1)
    fi

    if [ -n "$download_url" ]; then
        echo "✓ 下载链接: $download_url" >&2
        echo "$download_url"
        return 0
    else
        echo "❌ 未找到下载链接" >&2
        echo "调试信息: 查看 $output_file" >&2
        return 1
    fi
}

# 6. 下载资源文件
download_resource() {
    local download_url=$1
    local output_file=$2

    echo "📥 下载资源..." >&2
    echo "   URL: $download_url" >&2
    echo "   保存到: $output_file" >&2

    # 下载文件
    local http_code=$(curl -s --noproxy '*' -w "%{http_code}" -o "$output_file" \
        --max-time 60 -b "$COOKIE_FILE" "$download_url")

    if [ "$http_code" != "200" ]; then
        echo "❌ 下载失败 (HTTP $http_code)" >&2
        rm -f "$output_file"
        return 1
    fi

    # 检查文件大小
    local file_size=$(stat -c%s "$output_file" 2>/dev/null || stat -f%z "$output_file" 2>/dev/null)

    if [ "$file_size" -lt 100 ]; then
        echo "❌ 下载的文件太小，可能是错误" >&2
        return 1
    fi

    echo "✓ 下载成功: $output_file ($(numfmt --to=iec-i --suffix=B $file_size 2>/dev/null || echo $file_size bytes))" >&2
    return 0
}

# 7. 搜索多个课程中的关键词（默认只显示文档类资源）
search_courses() {
    local keyword=$1
    shift
    local courses=("$@")

    echo "🔍 在 ${#courses[@]} 个课程中搜索: $keyword (只显示文档类资源)" >&2
    echo "" >&2

    for course_id in "${courses[@]}"; do
        echo "=== Course $course_id ===" >&2

        local course_file=$(get_course "$course_id")
        local status=$?

        if [ $status -eq 2 ]; then
            # Session 过期，重新登录
            echo "重新登录..." >&2
            login
            course_file=$(get_course "$course_id")
        fi

        if [ -f "$course_file" ]; then
            # 默认使用"doc"过滤，只显示文档类资源
            search_in_course "$course_file" "$keyword" "doc"
        fi

        echo "" >&2
    done
}

# 使用示例
# login
# get_course 10
# search_courses "RK182X" 10 3
# get_resource_download_url 123
# download_resource "http://10.10.10.251/pluginfile.php/..." "/tmp/resource.pdf"
