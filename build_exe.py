import os
import sys
import subprocess
import shutil

def build_executable():
    print("=== Building Standalone Windows Executable with PyInstaller ===")
    
    # Path verification
    base_dir = os.path.abspath(os.path.dirname(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    
    if not os.path.exists(assets_dir):
        print(f"Error: assets directory not found at {assets_dir}")
        return False
        
    index_html = os.path.join(assets_dir, "index.html")
    echarts_js = os.path.join(assets_dir, "echarts.min.js")
    
    if not os.path.exists(index_html) or not os.path.exists(echarts_js):
        print("Error: Missing index.html or echarts.min.js in assets/")
        return False

    # Clean old build/dist directories if existing
    for folder in ["build", "dist"]:
        folder_path = os.path.join(base_dir, folder)
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
                print(f"Cleaned old folder: {folder_path}")
            except Exception as e:
                print(f"Warning: Could not remove {folder_path}: {e}")

    # Build PyInstaller command
    # Using --onedir for fast startup and reliability with PyWebView on Windows
    add_data_param = f"{assets_dir};assets"
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=StockMaster",
        f"--add-data={add_data_param}",
        "app.py"
    ]
    
    print("Executing build command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=base_dir)
    
    if result.returncode == 0:
        exe_path = os.path.join(base_dir, "dist", "StockMaster", "StockMaster.exe")
        print("\n" + "=" * 50)
        print("BUILD SUCCESSFUL!")
        print(f"Executable generated at: {exe_path}")
        print("=" * 50 + "\n")
        return True
    else:
        print("\nBUILD FAILED with code:", result.returncode)
        return False

if __name__ == "__main__":
    success = build_executable()
    if not success:
        sys.exit(1)
