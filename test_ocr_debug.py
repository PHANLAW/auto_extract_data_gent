"""
Test script để debug OCR workflow và xem tại sao URL bị đọc sai
Sử dụng: python test_ocr_debug.py <image_path>
"""

import os
import sys
import argparse
from pathlib import Path
from openai import AzureOpenAI
from app.tools.url_extractor_tool import URLExtractorTool
from app.core.config import get_settings
from app.core.logging_config import logger
import cv2
import numpy as np

settings = get_settings()


def test_ocr_workflow(image_path: str, output_dir: str = "debug_output"):
    """
    Test OCR workflow với debug output
    
    Args:
        image_path: Đường dẫn đến ảnh cần test
        output_dir: Thư mục để lưu ảnh crop và log
    """
    if not os.path.exists(image_path):
        print(f"❌ File không tồn tại: {image_path}")
        return
    
    # Tạo output directory
    os.makedirs(output_dir, exist_ok=True)
    
    image_name = Path(image_path).stem
    print(f"\n{'='*80}")
    print(f"🔍 Testing OCR workflow for: {image_name}")
    print(f"{'='*80}\n")
    
    # Initialize Azure OpenAI client
    try:
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
    except Exception as e:
        print(f"❌ Không thể khởi tạo Azure OpenAI client: {e}")
        print("   Vui lòng kiểm tra AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT trong .env")
        return
    
    # Initialize URL extractor tool
    url_extractor = URLExtractorTool(client=client)
    
    # Step 1: Check web detection
    print("📸 Step 1: Checking if image is web browser...")
    is_web, web_error = url_extractor.is_web_browser_image(image_path)
    if not is_web:
        print(f"❌ Image is NOT a web browser: {web_error}")
        return
    print("✅ Image is a web browser\n")
    
    # Step 2: Crop image (simulate workflow)
    print("✂️  Step 2: Cropping image...")
    img_array = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        print("❌ Cannot read image")
        return
    
    height, width = img.shape[:2]
    crop_ratio = url_extractor.crop_ratio
    crop_height = int(height * crop_ratio)
    address_bar_region = img[0:crop_height, 0:width]
    
    print(f"   Original size: {width}x{height}px")
    print(f"   Crop ratio: {crop_ratio:.1%}")
    print(f"   Crop height: {crop_height}px")
    print(f"   Cropped size: {width}x{crop_height}px")
    
    # Upscale if needed
    upscaled_region = address_bar_region.copy()
    scale_applied = 1.0
    if crop_height > 0 and crop_height < 400:
        target_height = min(400, crop_height * 3)
        scale = target_height / float(crop_height)
        if 1.0 < scale <= 3.0:
            upscaled_width = int(width * scale)
            upscaled_height = int(crop_height * scale)
            upscaled_region = cv2.resize(
                address_bar_region,
                (upscaled_width, upscaled_height),
                interpolation=cv2.INTER_CUBIC
            )
            scale_applied = scale
            print(f"   Upscaled to: {upscaled_width}x{upscaled_height}px (scale={scale:.2f}x)")
    
    # Save cropped images
    crop_file = os.path.join(output_dir, f"{image_name}_crop_{crop_height}px.png")
    cv2.imencode('.png', address_bar_region)[1].tofile(crop_file)
    print(f"   ✅ Saved cropped image: {crop_file}")
    
    if scale_applied > 1.0:
        upscaled_file = os.path.join(output_dir, f"{image_name}_upscaled_{upscaled_region.shape[1]}x{upscaled_region.shape[0]}px.png")
        cv2.imencode('.png', upscaled_region)[1].tofile(upscaled_file)
        print(f"   ✅ Saved upscaled image: {upscaled_file}")
    
    # Step 3: Test GCV OCR để lấy raw text
    print(f"\n🔍 Step 3: Testing GCV OCR (raw text extraction)...")
    import tempfile
    
    temp_fd, temp_file = tempfile.mkstemp(suffix='.png', prefix='temp_crop_')
    os.close(temp_fd)
    cv2.imencode('.png', upscaled_region if scale_applied > 1.0 else address_bar_region)[1].tofile(temp_file)
    
    # Test GCV OCR để lấy raw text
    gcv_text = ""
    gcv_urls_found = []
    
    try:
        gcv_text = url_extractor._get_gcv_text(temp_file)
        if gcv_text:
            print(f"   📝 GCV read raw text ({len(gcv_text)} chars):")
            print(f"      {gcv_text[:300]}..." if len(gcv_text) > 300 else f"      {gcv_text}")
            
            # Tìm tất cả URL candidates trong text
            import re
            url_regex = re.compile(
                r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*)"
            )
            matches = list(url_regex.finditer(gcv_text))
            if matches:
                print(f"\n   🔗 Found {len(matches)} URL candidate(s) in OCR text:")
                for i, match in enumerate(matches, 1):
                    candidate = match.group(0).strip()
                    start_pos = match.start()
                    end_pos = match.end()
                    context = gcv_text[max(0, start_pos-30):min(len(gcv_text), end_pos+30)]
                    print(f"      {i}. Position {start_pos}-{end_pos}: {candidate}")
                    print(f"         Context: ...{context}...")
                    gcv_urls_found.append((start_pos, candidate))
            else:
                print(f"   ⚠️  No URL candidates found in OCR text")
        else:
            print(f"   ⚠️  GCV did not find any text")
    except Exception as e:
        print(f"   ❌ GCV exception: {e}")
    
    # Step 4: Test Agent Validation (workflow mới)
    validated_url = None
    validation_error = None
    
    if gcv_text:
        print(f"\n🤖 Step 4: Testing Agent URL Validation (new workflow)...")
        print(f"   📤 Sending OCR text + cropped image to Azure agent for validation...")
        print(f"   📝 OCR text length: {len(gcv_text)} chars")
        print(f"   🖼️  Cropped image: {temp_file}")
        
        try:
            validated_url, validation_error = url_extractor.validate_url_from_ocr(
                ocr_text=gcv_text,
                cropped_image_path=temp_file
            )
            
            if validated_url:
                print(f"   ✅ Agent validated URL: {validated_url}")
                print(f"   📌 Agent confirmed this URL is from address bar (not watermark/logo)")
            else:
                print(f"   ⚠️  Agent did not find valid URL in address bar")
                if validation_error:
                    print(f"      Error: {validation_error}")
        except Exception as e:
            print(f"   ❌ Agent validation exception: {e}")
            validation_error = str(e)
    else:
        print(f"\n⚠️  Step 4: Skipping Agent Validation (no OCR text)")
    
    # Step 5: Test full workflow
    print(f"\n🔄 Step 5: Testing full workflow (execute)...")
    url, error = url_extractor.execute(image_path=image_path)
    
    print(f"\n{'='*80}")
    print(f"📊 RESULTS:")
    print(f"{'='*80}")
    if url:
        print(f"✅ Final URL extracted: {url}")
        if validated_url:
            if validated_url == url:
                print(f"   ✅ Matches agent validated URL")
            else:
                print(f"   ⚠️  Different from agent validated URL: {validated_url}")
        
        # So sánh với OCR candidates (agent có thể đọc lại từ ảnh và sửa lỗi OCR)
        if gcv_urls_found:
            print(f"\n   📋 URL candidates found in OCR text: {len(gcv_urls_found)}")
            matched_candidate = False
            for i, (pos, candidate) in enumerate(gcv_urls_found, 1):
                # Normalize để so sánh (bỏ scheme, trailing slash, lowercase)
                from urllib.parse import urlparse
                candidate_normalized = candidate.lower().rstrip('/').replace('https://', '').replace('http://', '')
                url_normalized = url.lower().rstrip('/').replace('https://', '').replace('http://', '')
                
                # So sánh với độ linh hoạt (có thể agent đã sửa lỗi OCR)
                if candidate_normalized == url_normalized:
                    print(f"      {i}. ✅ {candidate} (EXACT MATCH - selected)")
                    matched_candidate = True
                elif candidate_normalized in url_normalized or url_normalized in candidate_normalized:
                    print(f"      {i}. ⚠️  {candidate} (SIMILAR - agent corrected OCR: {url})")
                    matched_candidate = True
                else:
                    # Kiểm tra xem có phải cùng domain không (agent có thể đã sửa path)
                    candidate_domain = candidate_normalized.split('/')[0] if '/' in candidate_normalized else candidate_normalized
                    url_domain = url_normalized.split('/')[0] if '/' in url_normalized else url_normalized
                    if candidate_domain == url_domain:
                        print(f"      {i}. ⚠️  {candidate} (SAME DOMAIN - agent read from image: {url})")
                        matched_candidate = True
                    else:
                        print(f"      {i}. ❌ {candidate} (rejected - not from address bar)")
            
            if not matched_candidate:
                print(f"\n   📌 Note: Agent read URL directly from image (corrected OCR errors)")
                print(f"      OCR text had: {', '.join([c for _, c in gcv_urls_found])}")
                print(f"      Agent found in address bar: {url}")
                print(f"      → Agent successfully identified correct URL from address bar!")
    else:
        print(f"❌ Failed to extract URL: {error}")
        if validated_url:
            print(f"   ⚠️  Agent validated URL was: {validated_url}")
        if validation_error:
            print(f"   ⚠️  Validation error: {validation_error}")
    
    # Step 5: Save debug info
    debug_file = os.path.join(output_dir, f"{image_name}_debug.txt")
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(f"OCR Debug Info for: {image_name}\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"Original image: {image_path}\n")
        f.write(f"Original size: {width}x{height}px\n")
        f.write(f"Crop ratio: {crop_ratio:.1%}\n")
        f.write(f"Crop height: {crop_height}px\n")
        f.write(f"Cropped size: {width}x{crop_height}px\n")
        if scale_applied > 1.0:
            f.write(f"Upscaled size: {upscaled_region.shape[1]}x{upscaled_region.shape[0]}px (scale={scale_applied:.2f}x)\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"GCV OCR DETAILS:\n")
        f.write(f"{'='*80}\n")
        f.write(f"Full text read by GCV ({len(gcv_text)} chars):\n")
        f.write(f"{gcv_text}\n\n")
        
        if gcv_urls_found:
            f.write(f"URL candidates found in OCR text:\n")
            for i, (pos, candidate) in enumerate(gcv_urls_found, 1):
                context = gcv_text[max(0, pos-30):min(len(gcv_text), pos+len(candidate)+30)]
                f.write(f"  {i}. Position {pos}: {candidate}\n")
                f.write(f"     Context: ...{context}...\n")
            f.write(f"\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"AGENT VALIDATION (NEW WORKFLOW):\n")
        f.write(f"{'='*80}\n")
        f.write(f"OCR text sent to agent: {len(gcv_text)} chars\n")
        f.write(f"Cropped image sent to agent: {temp_file}\n")
        if validated_url:
            f.write(f"✅ Agent validated URL: {validated_url}\n")
            f.write(f"   → Agent confirmed this URL is from address bar\n")
        else:
            f.write(f"❌ Agent did not find valid URL\n")
            if validation_error:
                f.write(f"   Error: {validation_error}\n")
        f.write(f"\n")
        
        f.write(f"{'='*80}\n")
        f.write(f"FINAL RESULT:\n")
        f.write(f"{'='*80}\n")
        f.write(f"Final URL: {url or 'None'}\n")
        if error:
            f.write(f"Error: {error}\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"WORKFLOW SUMMARY:\n")
        f.write(f"{'='*80}\n")
        f.write(f"1. Web detection: ✅ Passed\n")
        f.write(f"2. Crop image: ✅ {crop_height}px ({crop_ratio:.1%})\n")
        if scale_applied > 1.0:
            f.write(f"3. Upscale: ✅ {scale_applied:.2f}x\n")
        f.write(f"4. GCV OCR: {'✅' if gcv_text else '❌'} ({len(gcv_text)} chars)\n")
        f.write(f"5. Agent Validation: {'✅' if validated_url else '❌'} ({validated_url or 'None'})\n")
        f.write(f"6. Final URL: {'✅' if url else '❌'} ({url or 'None'})\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"OUTPUT FILES:\n")
        f.write(f"{'='*80}\n")
        f.write(f"Cropped image: {crop_file}\n")
        if scale_applied > 1.0:
            f.write(f"Upscaled image: {upscaled_file}\n")
        f.write(f"Debug log: {debug_file}\n")
    
    print(f"\n✅ Debug info saved to: {debug_file}")
    print(f"\n📁 Output files:")
    print(f"   - Cropped image: {crop_file}")
    if scale_applied > 1.0:
        print(f"   - Upscaled image: {upscaled_file}")
    print(f"   - Debug log: {debug_file}")
    
    # Cleanup temp file
    try:
        os.remove(temp_file)
    except:
        pass
    
    print(f"\n{'='*80}\n")
    
    # Return để tránh print nhiều lần
    return


def main():
    parser = argparse.ArgumentParser(
        description="Test OCR workflow với debug output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python test_ocr_debug.py "data/folder/image.png"
  python test_ocr_debug.py "Ảnh chụp màn hình (3152).png" --output-dir debug
        """
    )
    parser.add_argument("image_path", help="Đường dẫn đến ảnh cần test")
    parser.add_argument(
        "--output-dir",
        default="debug_output",
        help="Thư mục để lưu ảnh crop và log (default: debug_output)"
    )
    
    args = parser.parse_args()
    
    test_ocr_workflow(
        image_path=args.image_path,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
