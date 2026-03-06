#!/usr/bin/env python3
"""
Skill Packager - Creates a distributable zip file of a skill folder

Usage:
    python utils/package_skill.py <path/to/skill-folder> [output-directory]

Example:
    python utils/package_skill.py skills/public/my-skill
    python utils/package_skill.py skills/public/my-skill ./dist
"""

import sys
import os
import zipfile
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from quick_validate import validate_skill


def safe_print(msg):
    """Print with encoding error handling for Windows"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def package_skill(skill_path, output_dir=None):
    """
    Package a skill folder into a zip file.

    Args:
        skill_path: Path to the skill folder
        output_dir: Optional output directory for the zip file (defaults to current directory)

    Returns:
        Path to the created zip file, or None if error
    """
    skill_path = Path(skill_path).resolve()

    # Validate skill folder exists
    if not skill_path.exists():
        safe_print(f"[ERROR] Skill folder not found: {skill_path}")
        return None

    if not skill_path.is_dir():
        safe_print(f"[ERROR] Path is not a directory: {skill_path}")
        return None

    # Validate SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        safe_print(f"[ERROR] SKILL.md not found in {skill_path}")
        return None

    # Run validation before packaging
    safe_print("[INFO] Validating skill...")
    valid, message = validate_skill(skill_path)
    if not valid:
        safe_print(f"[ERROR] Validation failed: {message}")
        safe_print("   Please fix the validation errors before packaging.")
        return None
    safe_print(f"[OK] {message}\n")

    # Determine output location
    skill_name = skill_path.name
    if output_dir:
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()

    zip_filename = output_path / f"{skill_name}.zip"

    # Create the zip file
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the skill directory
            for file_path in skill_path.rglob('*'):
                if file_path.is_file():
                    # Calculate the relative path within the zip
                    arcname = file_path.relative_to(skill_path.parent)
                    zipf.write(file_path, arcname)
                    safe_print(f"  Added: {arcname}")

        safe_print(f"\n[OK] Successfully packaged skill to: {zip_filename}")
        return zip_filename

    except Exception as e:
        safe_print(f"[ERROR] Error creating zip file: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        safe_print("Usage: python utils/package_skill.py <path/to/skill-folder> [output-directory]")
        safe_print("\nExample:")
        safe_print("  python utils/package_skill.py skills/public/my-skill")
        safe_print("  python utils/package_skill.py skills/public/my-skill ./dist")
        sys.exit(1)

    skill_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    safe_print(f"[PACK] Packaging skill: {skill_path}")
    if output_dir:
        safe_print(f"   Output directory: {output_dir}")
    safe_print("")

    result = package_skill(skill_path, output_dir)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
