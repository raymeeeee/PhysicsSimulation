import sys
import pathlib

# add parent directory to path for imports
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from main_menu import main as main_menu_main


if __name__ == "__main__":
    print("=" * 60)
    print("Physics Simulations Suite")
    print("=" * 60)
    print()
    
    main_menu_main()
    
    print()
    print("Thank you for using Physics Simulations!")
