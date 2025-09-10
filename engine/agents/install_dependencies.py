#!/usr/bin/env python3
"""
Install missing dependencies for the Planning Agent System.

This script checks for missing dependencies and provides instructions
to install them from the comprehensive requirements.txt.
"""

import subprocess
import sys
import pkg_resources
from packaging import version

def check_package(package_name, min_version=None):
    """Check if a package is installed with optional version check."""
    try:
        installed_version = pkg_resources.get_distribution(package_name).version
        if min_version and version.parse(installed_version) < version.parse(min_version):
            return False, installed_version
        return True, installed_version
    except pkg_resources.DistributionNotFound:
        return False, None

def main():
    """Check and install dependencies."""
    print("🔍 Checking Planning Agent dependencies...")
    print("=" * 50)
    
    # Critical dependencies needed for the planning agent
    critical_deps = [
        ("fastapi", "0.104.1"),
        ("uvicorn", "0.24.0"),
        ("pydantic", "2.4.2"),
        ("tensorflow", "2.13.0"),
        ("matplotlib", "3.7.0"),
        ("opencv-python", "4.8.0"),
        ("numpy", "1.24.0"),
        ("langchain", "0.1.0"),
        ("langchain-community", "0.0.10"),
        ("pandas", "2.0.0"),
        ("python-dotenv", "1.0.0"),
    ]
    
    missing_packages = []
    outdated_packages = []
    
    for package, min_ver in critical_deps:
        is_installed, current_ver = check_package(package, min_ver)
        
        if not is_installed and current_ver is None:
            print(f"❌ {package} - NOT INSTALLED")
            missing_packages.append(package)
        elif not is_installed and current_ver:
            print(f"⚠️  {package} - OUTDATED (have {current_ver}, need {min_ver}+)")
            outdated_packages.append(package)
        else:
            print(f"✅ {package} - OK ({current_ver})")
    
    print("\n" + "=" * 50)
    
    if missing_packages or outdated_packages:
        print(f"📦 Found {len(missing_packages)} missing and {len(outdated_packages)} outdated packages")
        print("\n🚀 To install/update all dependencies, run:")
        print("   pip install -r requirements.txt")
        print("\n🔧 Or install specific packages:")
        
        all_problematic = missing_packages + outdated_packages
        if len(all_problematic) <= 5:
            cmd = "pip install " + " ".join(f'"{pkg}"' for pkg in all_problematic)
            print(f"   {cmd}")
        
        print("\n💡 Recommended: Use a virtual environment:")
        print("   python -m venv planning_agent_env")
        print("   source planning_agent_env/bin/activate  # On Windows: planning_agent_env\\Scripts\\activate")
        print("   pip install -r requirements.txt")
        
        return False
    else:
        print("🎉 All critical dependencies are satisfied!")
        print("✅ Planning Agent is ready to run!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
