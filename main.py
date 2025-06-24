#!/usr/bin/env python3
"""
Main entry point for the Anghami to Spotify Migration Tool.
This script provides a user-friendly menu to run the extractor and migrator.
"""

import subprocess
import sys
import os
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()


def run_script(script_name: str):
    """Runs a Python script as a subprocess and checks for errors."""
    try:
        logger.info(f"--- Running {script_name} ---")
        # Use sys.executable to ensure we use the same Python interpreter
        process = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,  # Set to False to see script's output in real-time
            text=True
        )
        logger.info(f"--- {script_name} finished successfully ---")
        return True
    except FileNotFoundError:
        logger.error(f"Error: The script '{script_name}' was not found.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: The script '{script_name}' failed with exit code {e.returncode}.")
        # The script's own error messages will be printed to the console.
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while running {script_name}: {e}")
        return False


def main_menu():
    """Displays the main menu and handles user input."""
    print("\n===============================================")
    print("🎵 Anghami to Spotify Migration Main Menu 🎵")
    print("===============================================")
    print("Please choose an option:")
    print("1. Run the full process (Extract -> Migrate)")
    print("2. Run only the Song Extractor (from Anghami)")
    print("3. Run only the Playlist Migrator (to Spotify)")
    print("4. Exit")
    print("-----------------------------------------------")

    while True:
        choice = input("Enter your choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            return choice
        else:
            print("❌ Invalid choice. Please enter a number between 1 and 4.")


def main():
    """Main function to orchestrate the migration process."""
    # Check for config file early
    if not os.path.exists('config.ini'):
        logger.warning("Warning: 'config.ini' not found.")
        logger.warning("Please copy 'config.ini.example' to 'config.ini' and fill in your credentials.")

    while True:
        choice = main_menu()

        if choice == '1':
            logger.info("Starting the full migration process...")
            # Step 1: Extract
            if run_script("extractor.py"):
                # Step 2: Migrate
                run_script("migration.py")
        elif choice == '2':
            run_script("extractor.py")
        elif choice == '3':
            # Check for data file before migrating
            if not os.path.exists('anghami_extracted_data.json'):
                logger.error("Error: 'anghami_extracted_data.json' not found.")
                logger.error("You must run the extractor (option 2) before you can run the migrator.")
            else:
                run_script("migration.py")
        elif choice == '4':
            print("👋 Exiting the program. Goodbye!")
            break


if __name__ == "__main__":
    main()
