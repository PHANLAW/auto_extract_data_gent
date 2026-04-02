"""
Script: Upload folder to Azure Blob Storage and trigger processing
"""

import sys
import requests
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def upload_and_trigger(folder_path: str, api_base_url: str = "http://localhost:8000"):
    """
    Upload folder to blob storage and trigger processing
    
    Args:
        folder_path: Path to folder to upload
        api_base_url: Base URL of the API server
    """
    print("=" * 80)
    print("Upload Folder and Trigger Processing")
    print("=" * 80)
    
    if not os.path.exists(folder_path):
        print(f"[ERROR] Folder khong ton tai: {folder_path}")
        return False
    
    if not os.path.isdir(folder_path):
        print(f"[ERROR] Path phai la folder: {folder_path}")
        return False
    
    folder_name = os.path.basename(folder_path)
    print(f"\nFolder: {folder_name}")
    print(f"Path: {folder_path}")
    print("-" * 80)
    
    # Step 1: Upload folder
    print("\n[STEP 1] Uploading folder to Azure Blob Storage...")
    upload_url = f"{api_base_url}/api/v1/upload-and-process"
    
    payload = {
        "folder_path": folder_path
    }
    
    try:
        response = requests.post(upload_url, json=payload, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                print("[SUCCESS] Folder uploaded successfully!")
                print(f"  Folder name: {result.get('folder_name')}")
                print(f"  Uploaded: {result.get('uploaded')}")
                print(f"  Processed: {result.get('processed')}")
                
                processing_result = result.get("processing_result")
                if processing_result:
                    print(f"\n[PROCESSING RESULT]")
                    print(f"  Success: {processing_result.get('success')}")
                    print(f"  Images processed: {processing_result.get('images_processed', 0)}")
                    print(f"  Images success: {processing_result.get('images_success', 0)}")
                    print(f"  Images failed: {processing_result.get('images_failed', 0)}")
                
                return True
            else:
                print(f"[ERROR] Upload failed: {result.get('error')}")
                return False
        else:
            print(f"[ERROR] API error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def upload_only(folder_path: str, api_base_url: str = "http://localhost:8000"):
    """
    Upload folder only (without triggering processing)
    
    Args:
        folder_path: Path to folder to upload
        api_base_url: Base URL of the API server
    """
    print("=" * 80)
    print("Upload Folder to Azure Blob Storage")
    print("=" * 80)
    
    if not os.path.exists(folder_path):
        print(f"[ERROR] Folder khong ton tai: {folder_path}")
        return False
    
    folder_name = os.path.basename(folder_path)
    print(f"\nFolder: {folder_name}")
    print("-" * 80)
    
    upload_url = f"{api_base_url}/api/v1/upload-folder"
    payload = {"folder_path": folder_path}
    
    try:
        response = requests.post(upload_url, json=payload, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"[SUCCESS] {result.get('message')}")
                return True
            else:
                print(f"[ERROR] {result.get('error')}")
                return False
        else:
            print(f"[ERROR] API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def trigger_processing(api_base_url: str = "http://localhost:8000"):
    """
    Trigger processing of new folders in blob storage
    
    Args:
        api_base_url: Base URL of the API server
    """
    print("=" * 80)
    print("Trigger Blob Check and Processing")
    print("=" * 80)
    
    trigger_url = f"{api_base_url}/api/v1/trigger-blob-check"
    
    try:
        response = requests.post(trigger_url, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            print(f"[SUCCESS] Check completed")
            print(f"  Checked folders: {result.get('checked', 0)}")
            print(f"  New folders: {result.get('new_folders', 0)}")
            print(f"  Processed: {result.get('processed', 0)}")
            
            results = result.get("results", [])
            if results:
                print(f"\n[RESULTS]")
                for r in results:
                    status = "[SUCCESS]" if r.get("success") else "[FAILED]"
                    print(f"  {status} {r.get('folder')}")
                    if r.get("images_processed"):
                        print(f"    Images: {r.get('images_success', 0)}/{r.get('images_processed', 0)} success")
            
            return True
        else:
            print(f"[ERROR] API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload folder and trigger processing")
    parser.add_argument("folder_path", nargs="?", help="Path to folder to upload")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--upload-only", action="store_true", help="Upload only, don't trigger processing")
    parser.add_argument("--trigger-only", action="store_true", help="Trigger processing only (no upload)")
    
    args = parser.parse_args()
    
    if args.trigger_only:
        trigger_processing(args.api_url)
    elif args.folder_path:
        if args.upload_only:
            upload_only(args.folder_path, args.api_url)
        else:
            upload_and_trigger(args.folder_path, args.api_url)
    else:
        print("Usage:")
        print("  python upload_and_trigger.py <folder_path>                    # Upload and trigger")
        print("  python upload_and_trigger.py <folder_path> --upload-only      # Upload only")
        print("  python upload_and_trigger.py --trigger-only                  # Trigger only")
        print()
        print("Examples:")
        print('  python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"')
        print('  python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham" --upload-only')
        print("  python upload_and_trigger.py --trigger-only")
        print("  python upload_and_trigger.py <folder_path> --api-url http://your-server.com")


if __name__ == "__main__":
    main()
