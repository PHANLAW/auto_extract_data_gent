"""
Demo Script: Test toàn bộ workflow từ đầu đến cuối
"""

import sys
import os
import time
import requests
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def check_server_running(api_url: str = "http://localhost:8000") -> bool:
    """Check if server is running"""
    try:
        response = requests.get(f"{api_url}/", timeout=5)
        return response.status_code == 200
    except:
        return False


def demo_full_workflow(folder_path: str, api_url: str = "http://localhost:8000"):
    """
    Demo toàn bộ workflow:
    1. Check server running
    2. Prepare data
    3. Process folder
    4. Show results
    """
    print("=" * 80)
    print("DEMO: Full Workflow Test")
    print("=" * 80)
    print()
    
    # Step 1: Check server
    print("[STEP 1] Checking server...")
    if not check_server_running(api_url):
        print(f"[ERROR] Server không chạy tại {api_url}")
        print("Hãy chạy server trước:")
        print("  python start_server.bat")
        print("  hoặc")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    
    print(f"[SUCCESS] Server đang chạy tại {api_url}")
    print()
    
    # Step 2: Check folder
    print("[STEP 2] Checking folder...")
    if not os.path.exists(folder_path):
        print(f"[ERROR] Folder không tồn tại: {folder_path}")
        return False
    
    if not os.path.isdir(folder_path):
        print(f"[ERROR] Path phải là folder: {folder_path}")
        return False
    
    folder_name = os.path.basename(folder_path)
    print(f"[SUCCESS] Folder: {folder_name}")
    
    # Count images
    folder = Path(folder_path)
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    image_files = []
    for ext in image_extensions:
        image_files.extend(folder.glob(f"*{ext}"))
        image_files.extend(folder.glob(f"*{ext.upper()}"))
    
    # Remove duplicates
    seen = set()
    unique_images = []
    for img in image_files:
        img_str = str(img.resolve())
        if img_str not in seen:
            seen.add(img_str)
            unique_images.append(img)
    
    print(f"[INFO] Tìm thấy {len(unique_images)} ảnh")
    print()
    
    # Step 3: Process folder
    print("[STEP 3] Processing folder...")
    print("-" * 80)
    
    process_url = f"{api_url}/api/v1/process-folder"
    payload = {"folder_path": folder_path}
    
    try:
        print(f"Calling API: POST {process_url}")
        print(f"Payload: {payload}")
        print()
        
        response = requests.post(process_url, json=payload, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            
            print("[SUCCESS] Processing completed!")
            print()
            print("=" * 80)
            print("RESULTS")
            print("=" * 80)
            print(f"Folder: {result.get('folder')}")
            print(f"Success: {result.get('success')}")
            
            if result.get('success'):
                print(f"\nMatch Info:")
                print(f"  Match Name: {result.get('match_name')}")
                print(f"  League: {result.get('league')}")
                print(f"  Start Time: {result.get('start_time')}")
                print(f"  Sport ID: {result.get('sport_id')}")
                
                print(f"\nImages:")
                print(f"  Processed: {result.get('images_processed', 0)}")
                print(f"  Success: {result.get('images_success', 0)}")
                print(f"  Failed: {result.get('images_failed', 0)}")
                
                image_results = result.get('image_results', [])
                if image_results:
                    print(f"\nDetails:")
                    for img_result in image_results:
                        status = "[SUCCESS]" if img_result.get('success') else "[FAILED]"
                        print(f"  {status} {img_result.get('image')}")
                        if img_result.get('url'):
                            print(f"    URL: {img_result.get('url')}")
                        if img_result.get('detected_link_id'):
                            print(f"    Detected Link ID: {img_result.get('detected_link_id')}")
                        if img_result.get('error'):
                            print(f"    Error: {img_result.get('error')}")
            else:
                print(f"\nError: {result.get('error')}")
            
            return True
        else:
            print(f"[ERROR] API error {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python demo_full_workflow.py <folder_path> [api_url]")
        print()
        print("Example:")
        print('  python demo_full_workflow.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"')
        print('  python demo_full_workflow.py "data/folder" http://localhost:8000')
        print()
        print("Note: Server phải đang chạy trước khi chạy script này!")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    demo_full_workflow(folder_path, api_url)


if __name__ == "__main__":
    main()
