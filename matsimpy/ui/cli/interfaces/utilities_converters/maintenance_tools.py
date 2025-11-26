"""
Automated Maintenance Tools Interface Implementation
Provides automated maintenance and cleanup operations for MatSimPy
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import glob
import json

from matsimpy.ui.cli.parameter_manager import CLIParameterManager


def automated_maintenance(style: Optional[str] = None) -> Dict[str, Any]:
    """
    Automated maintenance interface for MatSimPy.
    
    Provides various maintenance operations including:
    - Cleanup temporary files
    - Archive old output files
    - System optimization
    - Log rotation
    - Cache cleanup
    
    Args:
        style: Optional style parameter for parameter manager
        
    Returns:
        Dict with status, message, and operation results
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)
        
        # Define parameters
        param_manager.define_parameter(
            name="maintenance_type",
            description="Type of maintenance operation",
            param_type=str,
            required=True,
            default="cleanup",
            validator=lambda x: x in ["cleanup", "archive", "optimize", "logs", "cache", "all"]
        )
        
        param_manager.define_parameter(
            name="target_directory",
            description="Target directory for maintenance (default: current directory)",
            param_type=str,
            required=False,
            default=".",
            validator=lambda x: Path(x).exists()
        )
        
        param_manager.define_parameter(
            name="days_old",
            description="Age threshold in days for cleanup/archive operations",
            param_type=int,
            required=False,
            default=30,
            validator=lambda x: x > 0
        )
        
        param_manager.define_parameter(
            name="dry_run",
            description="Perform dry run without actual changes",
            param_type=bool,
            required=False,
            default=True
        )
        
        param_manager.define_parameter(
            name="create_backup",
            description="Create backup before maintenance operations",
            param_type=bool,
            required=False,
            default=True
        )
        
        # Get parameters from user
        params = param_manager.get_parameters()
        if not params:
            return {"status": False, "message": "No parameters provided"}
        
        # Extract parameters
        maintenance_type = params.get("maintenance_type", "cleanup")
        target_dir = Path(params.get("target_directory", "."))
        days_old = int(params.get("days_old", 30))
        dry_run = bool(params.get("dry_run", True))
        create_backup = bool(params.get("create_backup", True))
        
        print(f"\n=== Automated Maintenance Operation ===")
        print(f"Type: {maintenance_type}")
        print(f"Target Directory: {target_dir.absolute()}")
        print(f"Age Threshold: {days_old} days")
        print(f"Dry Run: {dry_run}")
        print(f"Create Backup: {create_backup}")
        print("=" * 40)
        
        # Initialize results
        results = {
            "operation_type": maintenance_type,
            "target_directory": str(target_dir.absolute()),
            "dry_run": dry_run,
            "operations_performed": [],
            "files_processed": 0,
            "space_freed": 0,
            "errors": []
        }
        
        # Create backup if requested and not dry run
        backup_path = None
        if create_backup and not dry_run:
            backup_path = create_maintenance_backup(target_dir)
            if backup_path:
                results["backup_created"] = str(backup_path)
                print(f"✓ Backup created: {backup_path}")
        
        # Perform maintenance operations
        if maintenance_type == "cleanup" or maintenance_type == "all":
            cleanup_result = perform_cleanup(target_dir, days_old, dry_run)
            results["operations_performed"].append("cleanup")
            results["files_processed"] += cleanup_result["files_processed"]
            results["space_freed"] += cleanup_result["space_freed"]
            results["errors"].extend(cleanup_result["errors"])
        
        if maintenance_type == "archive" or maintenance_type == "all":
            archive_result = perform_archive(target_dir, days_old, dry_run)
            results["operations_performed"].append("archive")
            results["files_processed"] += archive_result["files_processed"]
            results["errors"].extend(archive_result["errors"])
        
        if maintenance_type == "optimize" or maintenance_type == "all":
            optimize_result = perform_optimization(target_dir, dry_run)
            results["operations_performed"].append("optimize")
            results["files_processed"] += optimize_result["files_processed"]
            results["space_freed"] += optimize_result["space_freed"]
            results["errors"].extend(optimize_result["errors"])
        
        if maintenance_type == "logs" or maintenance_type == "all":
            logs_result = perform_log_rotation(target_dir, days_old, dry_run)
            results["operations_performed"].append("log_rotation")
            results["files_processed"] += logs_result["files_processed"]
            results["space_freed"] += logs_result["space_freed"]
            results["errors"].extend(logs_result["errors"])
        
        if maintenance_type == "cache" or maintenance_type == "all":
            cache_result = perform_cache_cleanup(target_dir, dry_run)
            results["operations_performed"].append("cache_cleanup")
            results["files_processed"] += cache_result["files_processed"]
            results["space_freed"] += cache_result["space_freed"]
            results["errors"].extend(cache_result["errors"])
        
        # Generate summary report
        generate_maintenance_report(results, target_dir)
        
        # Final summary
        print(f"\n=== Maintenance Summary ===")
        print(f"Operations: {', '.join(results['operations_performed'])}")
        print(f"Files Processed: {results['files_processed']}")
        print(f"Space Freed: {format_size(results['space_freed'])}")
        
        if results["errors"]:
            print(f"Errors Encountered: {len(results['errors'])}")
            for error in results["errors"][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(results["errors"]) > 5:
                print(f"  ... and {len(results['errors']) - 5} more errors")
        
        if dry_run:
            print("\n⚠ This was a DRY RUN - no actual changes were made")
            print("Set dry_run=False to perform actual maintenance")
        else:
            print("\n✓ Maintenance operations completed successfully")
        
        status_message = f"Maintenance completed: {results['files_processed']} files processed"
        if results['space_freed'] > 0:
            status_message += f", {format_size(results['space_freed'])} freed"
        
        return {
            "status": True,
            "message": status_message,
            "data": results
        }
        
    except Exception as e:
        return {"status": False, "message": f"Error in automated maintenance: {str(e)}"}


def create_maintenance_backup(target_dir: Path) -> Optional[Path]:
    """Create backup before maintenance operations"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = target_dir.parent / f"backup_maintenance_{timestamp}"
        
        # Create selective backup (only important files)
        important_patterns = ["*.json", "*.py", "*.yaml", "*.yml", "*.conf", "*.cfg"]
        
        backup_dir.mkdir(exist_ok=True)
        
        for pattern in important_patterns:
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    backup_file = backup_dir / file_path.name
                    shutil.copy2(file_path, backup_file)
        
        return backup_dir
        
    except Exception as e:
        print(f"Warning: Failed to create backup: {e}")
        return None


def perform_cleanup(target_dir: Path, days_old: int, dry_run: bool) -> Dict[str, Any]:
    """Perform cleanup of temporary and old files"""
    result = {"files_processed": 0, "space_freed": 0, "errors": []}
    
    # Define cleanup patterns
    cleanup_patterns = [
        "*.tmp", "*.temp", "*~", "*.bak", "*.old",
        "*.log.*", "core.*", "*.pyc", "__pycache__",
        ".DS_Store", "Thumbs.db", "*.swp", "*.swo"
    ]
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    print(f"\n--- Cleanup Operation ---")
    
    try:
        for pattern in cleanup_patterns:
            for file_path in target_dir.rglob(pattern):
                try:
                    if file_path.is_file():
                        file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_age < cutoff_date:
                            file_size = file_path.stat().st_size
                            
                            if dry_run:
                                print(f"Would delete: {file_path} ({format_size(file_size)})")
                            else:
                                file_path.unlink()
                                print(f"Deleted: {file_path} ({format_size(file_size)})")
                            
                            result["files_processed"] += 1
                            result["space_freed"] += file_size
                            
                    elif file_path.is_dir() and file_path.name == "__pycache__":
                        if not dry_run:
                            shutil.rmtree(file_path)
                        print(f"{'Would remove' if dry_run else 'Removed'} directory: {file_path}")
                        result["files_processed"] += 1
                        
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {e}"
                    result["errors"].append(error_msg)
                    
    except Exception as e:
        result["errors"].append(f"Cleanup operation error: {e}")
    
    return result


def perform_archive(target_dir: Path, days_old: int, dry_run: bool) -> Dict[str, Any]:
    """Archive old output files"""
    result = {"files_processed": 0, "errors": []}
    
    # Define archivable patterns
    archive_patterns = ["*.out", "*.output", "*.result", "*.data"]
    archive_dir = target_dir / "archive"
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    print(f"\n--- Archive Operation ---")
    
    try:
        if not dry_run:
            archive_dir.mkdir(exist_ok=True)
        
        for pattern in archive_patterns:
            for file_path in target_dir.glob(pattern):
                try:
                    if file_path.is_file():
                        file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_age < cutoff_date:
                            archive_path = archive_dir / file_path.name
                            
                            if dry_run:
                                print(f"Would archive: {file_path} -> {archive_path}")
                            else:
                                shutil.move(str(file_path), str(archive_path))
                                print(f"Archived: {file_path} -> {archive_path}")
                            
                            result["files_processed"] += 1
                            
                except Exception as e:
                    error_msg = f"Error archiving {file_path}: {e}"
                    result["errors"].append(error_msg)
                    
    except Exception as e:
        result["errors"].append(f"Archive operation error: {e}")
    
    return result


def perform_optimization(target_dir: Path, dry_run: bool) -> Dict[str, Any]:
    """Perform system optimization tasks"""
    result = {"files_processed": 0, "space_freed": 0, "errors": []}
    
    print(f"\n--- Optimization Operation ---")
    
    try:
        # Remove empty directories
        for dir_path in target_dir.rglob("*"):
            if dir_path.is_dir():
                try:
                    if not any(dir_path.iterdir()):  # Empty directory
                        if dry_run:
                            print(f"Would remove empty directory: {dir_path}")
                        else:
                            dir_path.rmdir()
                            print(f"Removed empty directory: {dir_path}")
                        result["files_processed"] += 1
                except Exception as e:
                    result["errors"].append(f"Error removing directory {dir_path}: {e}")
        
        # Optimize JSON files (pretty print)
        for json_file in target_dir.glob("*.json"):
            try:
                if json_file.is_file():
                    original_size = json_file.stat().st_size
                    
                    if not dry_run:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                        
                        with open(json_file, 'w') as f:
                            json.dump(data, f, indent=2)
                    
                    new_size = json_file.stat().st_size if not dry_run else original_size
                    size_diff = original_size - new_size
                    
                    print(f"{'Would optimize' if dry_run else 'Optimized'} JSON: {json_file}")
                    result["files_processed"] += 1
                    result["space_freed"] += max(0, size_diff)
                    
            except Exception as e:
                result["errors"].append(f"Error optimizing {json_file}: {e}")
                
    except Exception as e:
        result["errors"].append(f"Optimization error: {e}")
    
    return result


def perform_log_rotation(target_dir: Path, days_old: int, dry_run: bool) -> Dict[str, Any]:
    """Perform log file rotation and cleanup"""
    result = {"files_processed": 0, "space_freed": 0, "errors": []}
    
    log_patterns = ["*.log", "*.out", "matsimpy.log*"]
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    print(f"\n--- Log Rotation Operation ---")
    
    try:
        for pattern in log_patterns:
            for log_file in target_dir.glob(pattern):
                try:
                    if log_file.is_file():
                        file_age = datetime.fromtimestamp(log_file.stat().st_mtime)
                        file_size = log_file.stat().st_size
                        
                        if file_age < cutoff_date:
                            if dry_run:
                                print(f"Would rotate/compress: {log_file} ({format_size(file_size)})")
                            else:
                                # Compress old log files
                                import gzip
                                compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                                
                                with open(log_file, 'rb') as f_in:
                                    with gzip.open(compressed_file, 'wb') as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                
                                log_file.unlink()  # Remove original
                                
                                compressed_size = compressed_file.stat().st_size
                                space_saved = file_size - compressed_size
                                
                                print(f"Compressed: {log_file} -> {compressed_file}")
                                print(f"  Size reduction: {format_size(space_saved)}")
                                
                                result["space_freed"] += space_saved
                            
                            result["files_processed"] += 1
                            
                except Exception as e:
                    result["errors"].append(f"Error rotating log {log_file}: {e}")
                    
    except Exception as e:
        result["errors"].append(f"Log rotation error: {e}")
    
    return result


def perform_cache_cleanup(target_dir: Path, dry_run: bool) -> Dict[str, Any]:
    """Clean up cache directories and files"""
    result = {"files_processed": 0, "space_freed": 0, "errors": []}
    
    cache_patterns = [".cache", "__pycache__", "*.cache", ".pytest_cache"]
    
    print(f"\n--- Cache Cleanup Operation ---")
    
    try:
        for pattern in cache_patterns:
            for cache_path in target_dir.rglob(pattern):
                try:
                    if cache_path.is_dir():
                        # Calculate directory size
                        dir_size = sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file())
                        
                        if dry_run:
                            print(f"Would remove cache directory: {cache_path} ({format_size(dir_size)})")
                        else:
                            shutil.rmtree(cache_path)
                            print(f"Removed cache directory: {cache_path} ({format_size(dir_size)})")
                        
                        result["files_processed"] += 1
                        result["space_freed"] += dir_size
                        
                    elif cache_path.is_file():
                        file_size = cache_path.stat().st_size
                        
                        if dry_run:
                            print(f"Would remove cache file: {cache_path} ({format_size(file_size)})")
                        else:
                            cache_path.unlink()
                            print(f"Removed cache file: {cache_path} ({format_size(file_size)})")
                        
                        result["files_processed"] += 1
                        result["space_freed"] += file_size
                        
                except Exception as e:
                    result["errors"].append(f"Error cleaning cache {cache_path}: {e}")
                    
    except Exception as e:
        result["errors"].append(f"Cache cleanup error: {e}")
    
    return result


def generate_maintenance_report(results: Dict[str, Any], target_dir: Path):
    """Generate maintenance report"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = target_dir / f"maintenance_report_{timestamp}.json"
        
        # Add timestamp to results
        results["timestamp"] = timestamp
        results["report_generated"] = datetime.now().isoformat()
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✓ Maintenance report saved: {report_file}")
        
    except Exception as e:
        print(f"Warning: Could not generate report: {e}")


def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


# Additional utility functions for specific maintenance tasks
def check_disk_space(target_dir: Path) -> Dict[str, Any]:
    """Check available disk space"""
    try:
        statvfs = os.statvfs(target_dir)
        total_space = statvfs.f_frsize * statvfs.f_blocks
        available_space = statvfs.f_frsize * statvfs.f_available
        used_space = total_space - available_space
        
        return {
            "total": total_space,
            "available": available_space,
            "used": used_space,
            "usage_percent": (used_space / total_space) * 100
        }
    except Exception as e:
        return {"error": str(e)}


def find_large_files(target_dir: Path, size_threshold_mb: int = 100) -> List[Dict[str, Any]]:
    """Find large files above threshold"""
    large_files = []
    threshold_bytes = size_threshold_mb * 1024 * 1024
    
    try:
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    if file_size > threshold_bytes:
                        large_files.append({
                            "path": str(file_path),
                            "size": file_size,
                            "size_formatted": format_size(file_size),
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        })
                except Exception:
                    continue
                    
        # Sort by size (largest first)
        large_files.sort(key=lambda x: x["size"], reverse=True)
        
    except Exception as e:
        print(f"Error finding large files: {e}")
    
    return large_files
