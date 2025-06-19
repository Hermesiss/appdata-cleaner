#!/usr/bin/env python3
"""
Build script for AppData Cleaner
Builds the application into a standalone executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def check_pyinstaller():
    """Check if PyInstaller is installed, install if not"""
    print("Checking PyInstaller...")
    result = run_command("pip show pyinstaller", check=False)
    if result.returncode != 0:
        print("PyInstaller not found. Installing...")
        run_command("pip install pyinstaller")
    else:
        print("PyInstaller is already installed.")


def clean_build_dirs():
    """Clean previous build directories"""
    print("Cleaning previous build files...")
    dirs_to_clean = ["dist", "build"]
    files_to_clean = ["*.spec"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name}/")
    
    for pattern in files_to_clean:
        for file_path in Path(".").glob(pattern):
            file_path.unlink()
            print(f"Removed {file_path}")


def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # Basic PyInstaller command
    cmd_parts = [
        "pyinstaller",
        "--onefile",           # Single executable file
        "--windowed",          # No console window
        "--name AppDataCleaner",  # Executable name
        "--clean",             # Clean cache
    ]
    
    # Add icon if exists
    if os.path.exists("icon.ico"):
        cmd_parts.append("--icon=icon.ico")
    
    # Add version info if exists
    if os.path.exists("version_info.txt"):
        cmd_parts.append("--version-file=version_info.txt")
    
    # Hidden imports for PySide6
    hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui", 
        "PySide6.QtWidgets",
        "humanize"
    ]
    
    for imp in hidden_imports:
        cmd_parts.append(f"--hidden-import={imp}")
    
    # Exclude unnecessary modules to reduce size
    excludes = [
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas"
    ]
    
    for exc in excludes:
        cmd_parts.append(f"--exclude-module={exc}")
    
    # Add the main script
    cmd_parts.append("appdata_cleaner.py")
    
    # Build command
    cmd = " ".join(cmd_parts)
    result = run_command(cmd)
    
    return result.returncode == 0


def main():
    """Main build function"""
    print("=" * 50)
    print("AppData Cleaner Build Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("appdata_cleaner.py"):
        print("Error: appdata_cleaner.py not found!")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    try:
        # Check and install PyInstaller
        check_pyinstaller()
        
        # Clean previous builds
        clean_build_dirs()
        
        # Build the executable
        success = build_executable()
        
        if success and os.path.exists("dist/AppDataCleaner.exe"):
            print("\n" + "=" * 50)
            print("✅ Build completed successfully!")
            print(f"📁 Executable: {os.path.abspath('dist/AppDataCleaner.exe')}")
            print(f"📦 Size: {os.path.getsize('dist/AppDataCleaner.exe') / (1024*1024):.1f} MB")
            print("=" * 50)
            
            # Optional: Open dist folder
            if sys.platform == "win32":
                os.startfile("dist")
        else:
            print("\n" + "=" * 50)
            print("❌ Build failed!")
            print("Check the output above for errors.")
            print("=" * 50)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Build cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 