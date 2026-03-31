---
name: fix-commit-files
description: Use when committing files, checking code before commit, or running pre-commit checks
---

# Fix Commit Files

## Overview

Before committing, check and fix three things: trailing spaces, incorrect file permissions, and mixed/inconsistent indentation.

## When to Use

- Before running `git commit` or creating a pull request
- After editing files, before marking a task complete
- When the skill is invoked explicitly

## Trailing Space Check

**Check:** Does any line in any file end with a space character (` ` before newline)?

```bash
grep -rn ' $' --include='*.sh' --include='*.bash' \
  --include='CMakeLists.txt' --include='*.cmake' \
  --include='*.cpp' --include='*.h' --include='*.c' \
  --include='*.hpp' --include='*.cc' \
  --include='*.py' --include='*.js' --include='*.ts' --include='*.tsx' \
  --include='*.go' --include='*.md' --include='*.txt' \
  --include='*.yaml' --include='*.yml' --include='*.json' \
  --include='*.toml' --include='*.cfg' --include='*.ini' --include='*.conf' .
```

**Fix:** Remove trailing whitespace from all matching lines.

```bash
find . -type f \( \
  -name '*.sh' -o -name '*.bash' \
  -name 'CMakeLists.txt' -name '*.cmake' \
  -name '*.cpp' -name '*.h' -name '*.hpp' -name '*.cc' -name '*.c' \
  -name '*.py' -name '*.js' -name '*.ts' -name '*.tsx' \
  -name '*.go' -name '*.md' -name '*.txt' \
  -name '*.yaml' -name '*.yml' -name '*.json' \
  -name '*.toml' -name '*.cfg' -name '*.ini' -name '*.conf' \
\) ! -path '*/\.*' | while read -r f; do
  sed -i 's/[[:space:]]*$//' "$f"
done
```

**Why:** Trailing spaces cause spurious diff noise in commits, waste storage, and indicate sloppiness in code quality checks.

## File Permission Check

**Check:** Are any regular files set to executable (755, 775, etc.) when they should be 644?

```bash
find . -type f ! -path '*/\.*' -perm -111 | grep -v '\.sh$' | grep -v '/bin/'
```

**Fix:** Set non-script regular files to 644.

```bash
find . -type f ! -path '*/\.*' \
  ! -name '*.sh' ! -name '*.bash' ! -name '*.py' ! -name '*.rb' \
  ! -name '*.js' ! -name '*.ts' \
  ! -name 'node' ! -name 'npm' ! -name 'yarn' ! -name 'cargo' \
  ! -name '*.so' ! -name '*.a' ! -name '*.o' \
  ! -path '*/bin/*' ! -path '*/scripts/*' \
  -executable -exec chmod 644 {} +
```

## Indentation Check

**Scope:** `.sh`, `.bash`, `CMakeLists.txt`, `*.cmake`, `*.cpp`, `*.h`, `*.hpp`, `*.cc`, `*.c`

### Check 1: Mixed tabs and spaces

If a file uses spaces for indentation, tabs are forbidden (and vice versa). Mixing both is a violation.

```bash
# Detect files with mixed tabs and spaces in leading whitespace
python3 -c "
import sys, os, re

TARGET_EXTS = {'.sh', '.bash', '.cpp', '.h', '.hpp', '.cc', '.c', '.cmake', ''}
TARGET_NAMES = {'CMakeLists.txt'}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fn in files:
        fpath = os.path.join(root, fn)
        if fn in TARGET_NAMES or any(fn.endswith(e) for e in TARGET_EXTS):
            with open(fpath, 'rb') as f:
                lines = f.read().splitlines()
            has_tab, has_space = False, False
            for i, line in enumerate(lines, 1):
                stripped = line.lstrip()
                lead = line[:len(line) - len(stripped)]
                if b'\t' in lead:
                    has_tab = True
                if b' ' in lead:
                    has_space = True
                if has_tab and has_space:
                    print(f'{fpath}:{i}: mixed tabs and spaces')
                    break
"
```

### Check 2: Inconsistent indentation depth

Detect two types of indentation issues:

1. **Mixed tabs and spaces** (same as above)
2. **Missing indent on continuation lines** — multi-line commands (`set(...)`, `add_executable(...)`, `target_link_libraries(...)`, `include_directories(`, etc.) must indent their content rows relative to the opening line

```bash
python3 -c "
import sys, os

TARGET_EXTS = {'.sh', '.bash', '.cpp', '.h', '.hpp', '.cc', '.c', '.cmake', ''}
TARGET_NAMES = {'CMakeLists.txt'}
MULTI_LINE_COMMANDS = {
    'set(', 'add_executable(', 'target_link_libraries(',
    'include_directories(', 'link_directories(',
    'add_definitions(', 'aux_source_directory(',
    'add_library(', 'target_include_directories(',
    'target_compile_options(', 'add_custom_command(',
    'target_sources(', 'set_target_properties(',
    'install(',
}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fn in files:
        fpath = os.path.join(root, fn)
        if fn in TARGET_NAMES or any(fn.endswith(e) for e in TARGET_EXTS):
            try:
                with open(fpath, 'rb') as f:
                    lines = f.read().splitlines()
            except:
                continue

            # Detect multi-line commands (opening line ends with '(' and is not a closing line)
            open_stack = []  # (line_index, indent_level)
            for i, raw in enumerate(lines):
                line = raw.lstrip()
                indent = len(raw) - len(line)
                stripped = line.decode('utf-8', errors='replace').strip()

                # Opening: non-empty, not closing ')', content starts with known multi-line cmd
                is_open = (
                    line and
                    not stripped.startswith('#') and
                    not stripped.startswith(')') and
                    not stripped.rstrip().endswith(')') and
                    any(stripped.startswith(cmd) for cmd in MULTI_LINE_COMMANDS)
                )
                if is_open:
                    open_stack.append((i, indent))
                elif stripped == ')' and open_stack:
                    # Closing ')', check indent matches opening
                    _, open_indent = open_stack.pop()
                    if indent != open_indent:
                        print(f'{fpath}:{i+1}: BAD_INDENT indent={indent} → should be {open_indent} (mismatches opening paren)')
                    elif indent == 0 and open_indent == 0:
                        # Content lines with same indent as opening (0) = missing indent
                        pass
                elif open_stack and line:
                    # Content line — must be indented more than the opening
                    _, open_indent = open_stack[-1]
                    if indent <= open_indent:
                        print(f'{fpath}:{i+1}: BAD_INDENT indent={indent} (content should be deeper than opening indent={open_indent})')
"
```

### Fix: Normalize indentation to 4 spaces

For space-based indentation: replace all leading spaces with multiples of 4. For tab-based: leave as-is (tabs are valid in Makefiles/CMake).

```bash
# Convert leading spaces to 4-space indent for the target file types
python3 -c "
import sys, os, re

TARGET_EXTS = {'.sh', '.bash', '.cpp', '.h', '.hpp', '.cc', '.c', '.cmake', ''}
TARGET_NAMES = {'CMakeLists.txt'}

def fix_indent(content):
    lines = content.splitlines(keepends=True)
    result = []
    tab_free = True
    for line in lines:
        if '\t' in line:
            tab_free = False
            break
    if not tab_free:
        return None  # leave tab-based files alone
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        lead = line[:len(line) - len(stripped)]
        if stripped:
            spaces = len(lead)
            # Normalize to nearest lower multiple of 4
            normalized = (spaces // 4) * 4
            new_lines.append(' ' * normalized + stripped)
        else:
            new_lines.append(line)
    return ''.join(new_lines)

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fn in files:
        fpath = os.path.join(root, fn)
        if fn in TARGET_NAMES or any(fn.endswith(e) for e in TARGET_EXTS):
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            fixed = fix_indent(content)
            if fixed is not None and fixed != content:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                print(f'fixed: {fpath}')
"
```

**Note on CMake:** CMake has its own conventions — prefer tabs in `CMakeLists.txt` unless the project enforces spaces. Check `.cmake-format.yaml` or project conventions first.

## Quick Reference

| Check | Command | Fix |
|-------|---------|-----|
| Trailing spaces | `grep -rn ' $' *.sh *.cpp *.h` | `sed -i 's/[[:space:]]*$//' file` |
| Wrong permissions | `find . -type f -executable` | `chmod 644 <file>` |
| Mixed tabs/spaces | Python detection script above | Python fix script above |
| Inconsistent indent | Python detection script above | Python fix script above |

## Common Mistakes

- **Fixing only staged files:** Run checks on the whole working directory, not just staged changes
- **Over-fixing permissions:** Scripts (`*.sh`, `*.bash`, `*.py`) and binaries should keep their executable bit
- **Skipping hidden files:** Some config files in `.git/` or project root need checking too (but skip `.git/` itself)
- **Converting CMake tabs to spaces:** CMake best practice is tabs. Only convert if the project explicitly uses spaces
