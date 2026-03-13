#!/usr/bin/env python3
"""
Quick Initialization Wrapper
Checks if system is initialized and runs init if needed
"""

import sys
from pathlib import Path

def main():
    # Check if search index exists
    index_path = Path('data/index/search_index.pkl')
    
    if not index_path.exists():
        print("=" * 64)
        print("WARNING: Search index not found!")
        print("=" * 64)
        print()
        print("You must run initialization first:")
        print("   python init_kse.py")
        print()
        print("This will take 2-4 hours but only needs to be done once.")
        print()
        
        response = input("Do you want to initialize now? (y/n): ").strip().lower()
        
        if response in ['y', 'yes']:
            print("\nStarting initialization...")
            print("-" * 64)
            
            # Import and run init_kse
            try:
                import init_kse
                init_kse.main()
                
                print("\n" + "=" * 64)
                print("✅ Initialization complete!")
                print("=" * 64)
                print("\nYou can now start the server:")
                print("   python start_server.py")
                
            except Exception as e:
                print(f"\n❌ Initialization failed: {e}")
                print("\nPlease run manually:")
                print("   python init_kse.py")
                return 1
        else:
            print("\nExiting. Please run init_kse.py when ready.")
            return 0
    else:
        print("✅ Search index found!")
        print("\nSystem is initialized. You can:")
        print("   python start_server.py    # Start the server")
        print("   python health_check.py    # Verify system health")
        return 0

if __name__ == '__main__':
    sys.exit(main())
