"""
install_dependencies.py
Quick dependency installer for PC Workman v1.4.0
Installs all required packages and checks for errors
"""

import subprocess
import sys

def install_package(package):
    """Install a single package using pip"""
    print(f"\n📦 Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    print("╔══════════════════════════════════════════════╗")
    print("║   PC Workman v1.4.0 - Dependency Installer   ║")
    print("╚══════════════════════════════════════════════╝\n")

    # Core dependencies
    dependencies = [
        "psutil>=5.9.0",
        "matplotlib>=3.7.0",
        "gputil>=1.4.0",
        "pandas>=2.0.0",
        "pillow>=10.0.0",
        "pystray>=0.19.0"
    ]

    print(f"Installing {len(dependencies)} packages...\n")

    success_count = 0
    failed = []

    for dep in dependencies:
        if install_package(dep):
            success_count += 1
        else:
            failed.append(dep)

    print("\n" + "="*50)
    print("Installation Summary")
    print("="*50)
    print(f"✅ Successful: {success_count}/{len(dependencies)}")

    if failed:
        print(f"❌ Failed: {len(failed)}")
        print("\nFailed packages:")
        for pkg in failed:
            print(f"  - {pkg}")
        print("\nTry installing failed packages manually:")
        print(f"  pip install {' '.join(failed)}")
        return 1
    else:
        print("\n🎉 All dependencies installed successfully!")
        print("\nYou can now run PC Workman:")
        print("  python startup.py")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
