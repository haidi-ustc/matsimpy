#!/usr/bin/env python3
"""
Script to remove sys.path.insert lines from test files.

This script removes the redundant sys.path.insert lines from test files
since conftest.py now handles the path setup centrally.
"""
import os
import re
from pathlib import Path

# Pattern to match sys.path.insert lines
PATH_INSERT_PATTERN = re.compile(
    r'^\s*sys\.path\.insert\s*\(\s*0\s*,\s*os\.path\.abspath\s*\(\s*os\.path\.join\s*\(\s*os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*["\']\.\.["\']\s*\)\s*\)\s*\)\s*$',
    re.MULTILINE
)

# Pattern to match import sys and import os lines (if only used for path setup)
IMPORT_PATTERN = re.compile(
    r'^import\s+(sys|os)\s*$',
    re.MULTILINE
)

def cleanup_test_file(file_path: Path) -> bool:
    """
    Remove sys.path.insert lines from a test file.
    
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove sys.path.insert lines
        content = PATH_INSERT_PATTERN.sub('', content)
        
        # Remove standalone import sys/os if they're not used elsewhere
        # (This is a simple check - might need refinement)
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if it's a standalone import sys or os
            if re.match(r'^import\s+(sys|os)\s*$', line):
                # Check if sys or os is used later in the file
                var_name = re.match(r'^import\s+(sys|os)\s*$', line).group(1)
                remaining_content = '\n'.join(lines[i+1:])
                # Simple check: if variable is used, keep the import
                if f'{var_name}.' in remaining_content or f' {var_name}' in remaining_content:
                    new_lines.append(line)
                # Otherwise, skip it (conftest.py handles it)
            else:
                new_lines.append(line)
            i += 1
        
        content = '\n'.join(new_lines)
        
        # Clean up multiple blank lines
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to clean up all test files."""
    tests_dir = Path('tests')
    
    if not tests_dir.exists():
        print("Error: tests directory not found")
        return
    
    test_files = list(tests_dir.glob('test_*.py'))
    
    print(f"Found {len(test_files)} test files")
    print("Cleaning up sys.path.insert lines...")
    
    modified_count = 0
    for test_file in sorted(test_files):
        if cleanup_test_file(test_file):
            print(f"  Modified: {test_file}")
            modified_count += 1
    
    print(f"\n✓ Cleaned up {modified_count} files")
    print("Note: conftest.py now handles path setup centrally")

if __name__ == '__main__':
    main()

