"""
CLI Entry Point for Workflow Processing
"""

import sys
from pathlib import Path
from app.services.workflow_service import WorkflowService
from app.core.logging_config import logger, setup_logging
from app.core.config import get_settings

settings = get_settings()


def main():
    """Main entry point for workflow CLI"""
    setup_logging()
    
    print("=" * 80)
    print("IMAGE PROCESSING WORKFLOW CLI")
    print("=" * 80)
    print()
    
    # Get base folder from command line or use default
    if len(sys.argv) > 1:
        base_folder = sys.argv[1]
    else:
        base_folder = settings.LOCAL_DATA_PATH
        print(f"Using default data path: {base_folder}")
    
    base_folder = Path(base_folder).resolve()
    
    if not base_folder.exists():
        print(f"Error: Folder does not exist: {base_folder}")
        sys.exit(1)
    
    print(f"Processing folders in: {base_folder}")
    print()
    
    try:
        workflow_service = WorkflowService()
        results = workflow_service.process_all_folders(str(base_folder))
        
        # Save results
        if results:
            output_file = "workflow_results.json"
            workflow_service.save_results(results, output_file)
        
        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETED")
        print("=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        print("\nWorkflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
