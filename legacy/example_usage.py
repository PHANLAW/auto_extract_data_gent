"""
Example Usage: Demonstrate how to use the AI Agent workflow
"""

from folder_parser import parse_folder_name
from sport_api import SportAPIClient
from url_extractor import URLExtractor
from error_handler import ErrorHandler
from agent import ImageProcessingAgent
from openai import AzureOpenAI

# ============================================
# EXAMPLE 1: Parse Folder Name
# ============================================
def example_parse_folder():
    """Example: Parse folder name"""
    print("=" * 60)
    print("EXAMPLE 1: Parse Folder Name")
    print("=" * 60)
    
    folder_name = "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
    start_time, league, match_name, original = parse_folder_name(folder_name)
    
    print(f"Folder: {folder_name}")
    print(f"  Start Time: {start_time}")
    print(f"  League: {league}")
    print(f"  Match Name: {match_name}")
    print(f"  Original: {original}")
    print()


# ============================================
# EXAMPLE 2: Get Sport ID
# ============================================
def example_get_sport_id():
    """Example: Get sport_id from API"""
    print("=" * 60)
    print("EXAMPLE 2: Get Sport ID")
    print("=" * 60)
    
    # Initialize API client (update with your actual API details)
    api_client = SportAPIClient(
        base_url="https://your-api.com",
        api_key="YOUR_API_KEY"
    )
    
    # Get sport_id
    sport_id, error = api_client.get_sport_id(
        match_name="Crystal Palace - Fulham",
        start_time="2026-01-02 00:30",
        league="PL 25_26"
    )
    
    if error:
        print(f"Error: {error}")
    else:
        print(f"Sport ID: {sport_id}")
    print()


# ============================================
# EXAMPLE 3: Extract URL from Image
# ============================================
def example_extract_url():
    """Example: Extract URL from image"""
    print("=" * 60)
    print("EXAMPLE 3: Extract URL from Image")
    print("=" * 60)
    
    # Initialize Azure OpenAI client (update with your credentials)
    azure_client = AzureOpenAI(
        api_key="YOUR_AZURE_OPENAI_KEY",
        api_version="2024-02-15-preview",
        azure_endpoint="https://YOUR_RESOURCE_NAME.openai.azure.com"
    )
    
    # Initialize URL extractor
    url_extractor = URLExtractor(
        client=azure_client,
        deployment_name="gpt-4o-mini"
    )
    
    # Extract URL
    url, error = url_extractor.extract_url("image.png")
    
    if error:
        print(f"Error: {error}")
    else:
        print(f"Extracted URL: {url}")
    print()


# ============================================
# EXAMPLE 4: Process Image with Agent
# ============================================
def example_process_image():
    """Example: Process image using agent"""
    print("=" * 60)
    print("EXAMPLE 4: Process Image with Agent")
    print("=" * 60)
    
    # Initialize Azure OpenAI client
    azure_client = AzureOpenAI(
        api_key="YOUR_AZURE_OPENAI_KEY",
        api_version="2024-02-15-preview",
        azure_endpoint="https://YOUR_RESOURCE_NAME.openai.azure.com"
    )
    
    # Initialize components
    url_extractor = URLExtractor(
        client=azure_client,
        deployment_name="gpt-4o-mini"
    )
    
    api_client = SportAPIClient(
        base_url="https://your-api.com",
        api_key="YOUR_API_KEY"
    )
    
    error_handler = ErrorHandler(
        retry_file="retry_failed.json",
        file_format="json"
    )
    
    # Initialize agent
    agent = ImageProcessingAgent(
        url_extractor=url_extractor,
        api_client=api_client,
        error_handler=error_handler
    )
    
    # Process image
    result = agent.process_image(
        image_path="image.png",
        match_name="Crystal Palace - Fulham",
        sport_id=123
    )
    
    print(f"Success: {result['success']}")
    print(f"URL: {result.get('url')}")
    print(f"Detected Link ID: {result.get('detected_link_id')}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print()


# ============================================
# EXAMPLE 5: Error Handling
# ============================================
def example_error_handling():
    """Example: Write failed URL to retry file"""
    print("=" * 60)
    print("EXAMPLE 5: Error Handling")
    print("=" * 60)
    
    error_handler = ErrorHandler(
        retry_file="retry_failed.json",
        file_format="json"
    )
    
    # Write failed URL
    error_handler.write_failed_url(
        match_name="Crystal Palace - Fulham",
        image_name="image1.png",
        url="https://b5.thapcam73.life/example",
        error="No detected_link_id in response"
    )
    
    print("Failed URL written to retry_failed.json")
    
    # Read failed URLs
    failed_urls = error_handler.read_failed_urls()
    print(f"Total failed URLs: {len(failed_urls)}")
    for entry in failed_urls:
        print(f"  - {entry['match_name']}: {entry['image_name']} - {entry['url']}")
    print()


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("\nAI Agent Workflow - Example Usage\n")
    
    # Run examples (comment out ones that require API credentials)
    example_parse_folder()
    # example_get_sport_id()  # Requires API credentials
    # example_extract_url()  # Requires Azure OpenAI credentials
    # example_process_image()  # Requires all credentials
    example_error_handling()
    
    print("=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNote: Some examples require API credentials to run.")
    print("Update the configuration in each function before running.")
