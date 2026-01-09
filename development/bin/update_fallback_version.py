"""Update the fallback version in ai_ops/__init__.py to match the version from pyproject.toml.

This script is automatically called by `invoke generate-release-notes` to ensure that the
fallback version strings in ai_ops/__init__.py stay in sync with the actual package version.

The fallback version is used when:
1. The package is not installed via pip (development environment)
2. The pyproject.toml file cannot be found or parsed

Example:
    $ python update_fallback_version.py --version '1.0.2'
"""

import argparse
import re
from pathlib import Path

# Semantic versioning pattern: X.Y.Z or X.Y.ZbN (for beta/alpha)
VERSION_PATTERN = r'^\d+\.\d+\.\d+([ab]\d+)?$'


def update_fallback_version(version):
    """Update the fallback version strings in ai_ops/__init__.py to match the given version.
    
    Args:
        version: The version string to set (e.g., '1.0.2')
    
    Returns:
        bool: True if the update was successful or version was already correct, False otherwise.
    """
    # Validate version format (semantic versioning: X.Y.Z or X.Y.ZbN for beta)
    if not re.match(VERSION_PATTERN, version):
        print(f"Error: Invalid version format '{version}'. Expected format: X.Y.Z or X.Y.ZbN")
        return False
    
    init_file = Path(__file__).parent.parent.parent / "ai_ops" / "__init__.py"
    if not init_file.exists():
        print(f"Error: {init_file} not found")
        return False
    
    content = init_file.read_text(encoding='utf-8')
    
    # Pattern to match the fallback version assignments
    # Matches lines like: __version__ = "1.0.1"  # Ultimate fallback
    # The comment is required to ensure we only match the fallback assignments
    # and not other version assignments in the file
    pattern = r'(__version__ = )"(\d+\.\d+\.\d+(?:[ab]\d+)?)"(\s*# Ultimate fallback)'
    
    # Count how many replacements we'll make
    matches = list(re.finditer(pattern, content))
    if not matches:
        print(f"Warning: No fallback version patterns found in {init_file}")
        return False
    
    # Replace all occurrences - group 1 is prefix, group 2 is old version, group 3 is comment
    updated_content = re.sub(pattern, rf'\1"{version}"\3', content)
    
    if updated_content == content:
        print(f"Fallback version in {init_file} is already {version}")
        return True
    
    init_file.write_text(updated_content, encoding='utf-8')
    print(f"Updated {len(matches)} fallback version(s) in {init_file} to {version}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update the fallback version in ai_ops/__init__.py to match the package version."
    )
    parser.add_argument("--version", required=True, help="The version string (e.g., 1.0.2)")
    args = parser.parse_args()
    
    success = update_fallback_version(args.version)
    exit(0 if success else 1)
