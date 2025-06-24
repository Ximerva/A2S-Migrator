#!/usr/bin/env python3
"""
Anghami Playlist Extractor - Enhanced Version
This script tries harder to extract ALL songs from any Anghami playlist.
"""

import time
import json
import logging
import sys
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

def ask_for_browser_choice() -> str:
    """Ask the user to choose a browser."""
    print("Please choose your browser:")
    print("1. Google Chrome (or Chromium)")
    print("2. Microsoft Edge")
    print("3. Mozilla Firefox")
    print("4. Other Chromium-based browser (Brave, Vivaldi, Opera, etc.)")
    
    while True:
        choice = input("Enter the number of your choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            return choice
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

def setup_driver(browser_choice: str):
    """Setup the selected browser driver with appropriate options"""
    try:
        if browser_choice == '3':
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            options = FirefoxOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Firefox(options=options)
            return driver
        elif browser_choice == '2':
            from selenium.webdriver.edge.options import Options as EdgeOptions
            options = EdgeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Edge(options=options)
            return driver
        elif browser_choice == '1':
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            options = ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=options)
            return driver
        elif browser_choice == '4':
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            options = ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            custom_path = input("Enter the full path to your browser executable (e.g., /usr/bin/brave-browser): ").strip()
            options.binary_location = custom_path
            driver = webdriver.Chrome(options=options)
            return driver
        else:
            # This case should not be hit if input is validated, but it's good practice.
            logger.error(f"Invalid browser choice '{browser_choice}'. Exiting.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to start browser driver: {e}")
        sys.exit(1)

def extract_songs_from_page(driver):
    """
    Extracts songs and artists by iterating through each song row to ensure correct pairing.
    This is much more robust than grabbing all titles and artists in separate lists.
    """
    songs = []
    artists = []
    try:
        # This XPath finds a common ancestor (like <article> or <div>) that contains both a title and an artist.
        # This ensures we process each song as a self-contained unit.
        song_rows = driver.find_elements(By.XPATH, "//*[.//div[contains(@class, 'cell-title')] and .//div[contains(@class, 'cell-artist')]]")
        
        logger.info(f"Found {len(song_rows)} potential song rows to process.")

        for row in song_rows:
            try:
                # Find the title and artist WITHIN this specific row.
                song_elem = row.find_element(By.CSS_SELECTOR, "[class*='cell-title']")
                artist_elem = row.find_element(By.CSS_SELECTOR, "[class*='cell-artist']")
                
                song_text = song_elem.text.strip()
                artist_text = artist_elem.text.strip()

                # Only add if we have a valid song title.
                if song_text and song_text not in songs:
                    songs.append(song_text)
                    artists.append(artist_text)
            except NoSuchElementException:
                # This "row" might be a header or something else without a song, so we skip it.
                continue
    except Exception as e:
        logger.warning(f"An error occurred during row-by-row extraction: {e}")
        
    logger.info(f"Successfully extracted {len(songs)} unique song/artist pairs.")
    return songs, artists

def scroll_and_extract_all_songs(browser_choice: str, max_scrolls=200):
    """
    Loads the page fully, removes the recommended section via JavaScript,
    and then extracts the clean playlist data.
    """
    driver = setup_driver(browser_choice)
    
    try:
        # Login and navigation logic...
        # ... (same as before) ...
        logger.info("Opening Anghami login page...")
        driver.get("https://play.anghami.com/login")
        
        print("\n🔐 Please log in to your Anghami account in the browser window.")
        print("Once you're logged in, the script will automatically continue.")
        print("Waiting for login to complete...")
        
        input("Press Enter after you have successfully logged in to Anghami...")
        
        print("\n📋 Now please provide the Anghami playlist URL you want to extract songs from.")
        playlist_url = input("\nEnter the playlist URL: ").strip()
        
        if not playlist_url:
            logger.error("No playlist URL provided. Exiting.")
            return [], [], [], []
        
        logger.info(f"Navigating to playlist: {playlist_url}")
        driver.get(playlist_url)
        time.sleep(8)  # Wait for initial page load

        # --- Pass 1: The "Load Pass" - Scroll until all content is loaded ---
        logger.info("--- Starting Pass 1: Forcing all content to load by scrolling ---")

        scroll_count = 0
        while scroll_count < max_scrolls:
            # Get the current number of songs before scrolling
            last_song_count = len(driver.find_elements(By.CSS_SELECTOR, "[class*='cell-title']"))
            logger.info(f"Scroll attempt {scroll_count + 1}: Currently {last_song_count} songs visible.")

            # Scroll the last element into view to trigger loading
            try:
                song_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='cell-title']")
                if song_elements:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'end'});", song_elements[-1])
                else:  # Fallback for the very first scroll
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception as e:
                logger.warning(f"Could not scroll to last element, using generic scroll. Error: {e}")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Use an explicit wait to see if the number of songs increases
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "[class*='cell-title']")) > last_song_count
                )
            except TimeoutException:
                logger.info("Waited for 10 seconds, but no new songs loaded. Assuming end of playlist.")
                break  # Exit the loop, we're done scrolling

            scroll_count += 1

        logger.info("--- Pass 1 Complete: Page is fully scrolled. ---")
        
        # --- New Pass: Modify the DOM to remove the recommended section ---
        logger.info("--- Starting Pass 2: Removing 'Recommended' section from page via JavaScript ---")
        try:
            js_script = """
            const header = Array.from(document.querySelectorAll("h1, h2, h3, h4, [role='heading']"))
                               .find(el => el.textContent.includes('Recommended') || el.textContent.includes('مقترحة'));
            if (header) {
                let parent = header.parentElement;
                // Keep moving up to find a container that seems to hold the whole section
                for (let i = 0; i < 5 && parent; i++) {
                    if (parent.childElementCount > 1) {
                        break;
                    }
                    parent = parent.parentElement;
                }
                if (parent) {
                    parent.style.display = 'none';
                    return true;
                }
            }
            return false;
            """
            removed = driver.execute_script(js_script)
            if removed:
                logger.info("Successfully hid 'Recommended' section.")
            else:
                logger.warning("Could not find or hide 'Recommended' section. Extraction may include extra songs.")
            time.sleep(2) # Give DOM a moment to update
        except Exception as e:
            logger.error(f"Error executing JavaScript to remove recommended section: {e}")

        # --- Final Pass: The "Extract Pass" - Get all data from the clean page ---
        logger.info("--- Starting Pass 3: Extracting all songs from the clean page ---")
        playlist_songs, playlist_artists = extract_songs_from_page(driver)
        logger.info(f"Extracted a total of {len(playlist_songs)} songs.")

        # --- Final Verification Step ---
        logger.info("--- Final Verification ---")
        try:
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            match = re.search(r'(\d+)\s+songs', page_text, re.IGNORECASE)

            if match:
                expected_song_count = int(match.group(1))
                actual_song_count = len(playlist_songs)
                
                logger.info(f"Verification: Anghami page indicates {expected_song_count} songs in the playlist.")
                if expected_song_count == actual_song_count:
                    logger.info("✅ Success! The number of extracted songs matches the official count.")
                else:
                    logger.warning(f"⚠️ Warning: Mismatch! Extracted {actual_song_count} songs, but page says {expected_song_count}.")
            else:
                logger.info("Could not automatically verify the total song count from the page.")
        except Exception as e:
            logger.warning(f"Could not perform song count verification due to an error: {e}")

        # Since we removed the recommended section, we return the clean list directly.
        # We also return empty lists for the 'recommended' slots to match the save function's signature.
        return playlist_songs, playlist_artists, [], []
        
    except Exception as e:
        logger.error(f"An error occurred during the extraction process: {e}")
        return [], [], [], []
    
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def save_to_file(playlist_songs, playlist_artists, recommended_songs, recommended_artists):
    """
    Save extracted songs to a file.
    - The TXT file will be a full report for user review, including recommended songs.
    - The JSON file will contain only the clean playlist data for migration.
    """
    
    # --- Save TXT report for user review ---
    txt_filename = "anghami_extracted_songs.txt"
    try:
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write("--- Playlist Songs ---\n")
            if playlist_songs:
                for i, (song, artist) in enumerate(zip(playlist_songs, playlist_artists), 1):
                    f.write(f"{i}. {song} - {artist}\n")
            else:
                f.write("No playlist songs were extracted.\n")

            if recommended_songs:
                f.write("\n\n====================================================\n")
                f.write("--- RECOMMENDED SONGS (For Your Review) ---\n")
                f.write("--- These songs will NOT be migrated to Spotify ---\n")
                f.write("====================================================\n\n")
                for i, (song, artist) in enumerate(zip(recommended_songs, recommended_artists), 1):
                    f.write(f"{i}. {song} - {artist}\n")
        
        logger.info(f"Saved full report for your review to {txt_filename}")

    except IOError as e:
        logger.error(f"Failed to write TXT report: {e}")
    
    # --- Save JSON data for the migration script ---
    json_filename = "anghami_extracted_data.json"
    data = {
        'songs': playlist_songs,
        'artists': playlist_artists
    }
    
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved clean playlist data for migration to {json_filename}")
    except (IOError, TypeError) as e:
        logger.error(f"Failed to write JSON data: {e}")

def main():
    """Main function to run the extractor"""
    print("🚀 Starting Anghami Playlist Extractor...")
    
    # Let the user choose the browser
    browser = ask_for_browser_choice()

    # The script will ask for the playlist URL after login
    playlist_songs, playlist_artists, recommended_songs, recommended_artists = scroll_and_extract_all_songs(browser)
    
    if playlist_songs and playlist_artists:
        logger.info(f"Successfully extracted {len(playlist_songs)} songs to migrate.")
        
        # Save both the review file and the clean data file
        save_to_file(playlist_songs, playlist_artists, recommended_songs, recommended_artists)
        
    else:
        logger.warning("❌ No songs were extracted for the playlist. Please check the URL and try again.")

if __name__ == '__main__':
    main() 