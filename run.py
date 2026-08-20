import sys
import os
import subprocess

def main():
    print("==================================================")
    print("             VISIONGUARD EDGE INITIATOR           ")
    print("==================================================")
    
    # 1. Check workspace directories
    workspace_dirs = [
        "app",
        "data",
        os.path.join("data", "inspections"),
        os.path.join("data", "demo_samples"),
        "models",
        "reports",
        "static"
    ]
    
    for d in workspace_dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"Created workspace directory: {d}")
            
    # 2. Check Package Imports
    print("\nProbing dependencies...")
    missing_packages = []
    
    dependencies = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "cv2": "opencv-python",
        "PIL": "pillow",
        "pandas": "pandas",
        "reportlab": "reportlab",
        "ultralytics": "ultralytics"
    }
    
    for package, install_name in dependencies.items():
        try:
            __import__(package)
            print(f"  [OK] {package} - Available")
        except ImportError:
            print(f"  [ERR] {package} - MISSING")
            missing_packages.append(install_name)
            
    if missing_packages:
        print("\n[!] WARNING: Some required Python packages are missing.")
        print(f"Run: pip install {' '.join(missing_packages)}")
        sys.exit(1)
        
    print("\n[OK] Environment verification passed.")
    print("Launching FastAPI backend server...")
    
    # 3. Spawn Uvicorn
    try:
        # Run uvicorn server in current directory context
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8501"], check=True)
    except KeyboardInterrupt:
        print("\nVisionGuard Edge server stopped by user.")
    except Exception as e:
        print(f"\n[!] Failed to start Uvicorn server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
