#!/usr/bin/env python3
"""
Anghami to Spotify Playlist Migrator - Enhanced Version
This script migrates songs from Anghami to Spotify with smart matching and detailed reporting.
"""

import json
import logging
import sys
import os
import re
import time
from typing import List, Tuple, Optional, Dict
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import configparser
from difflib import SequenceMatcher
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()


def load_config() -> Tuple[str, str, str]:
    """Load configuration from config.ini"""
    config = configparser.ConfigParser()

    if not os.path.exists('config.ini'):
        logger.error("Error: config.ini not found.")
        logger.error(
            "Please ensure the config.ini file exists and contains your Spotify API credentials.")
        sys.exit(1)

    config.read('config.ini')

    try:
        client_id = config.get('Spotify', 'client_id')
        client_secret = config.get('Spotify', 'client_secret')
        redirect_uri = config.get('Spotify', 'redirect_url')

        # Check if the user has replaced the placeholder values
        if 'YOUR_SPOTIFY_CLIENT_ID' in client_id or 'YOUR_SPOTIFY_CLIENT_SECRET' in client_secret:
            logger.error(
                "Error: Default placeholder values found in config.ini.")
            logger.error(
                "Please edit the config.ini file and replace the placeholder values with your actual Spotify API credentials.")
            sys.exit(1)

        return client_id, client_secret, redirect_uri
    except (configparser.Error, KeyError) as e:
        logger.error(f"Error reading config.ini: {e}")
        sys.exit(1)


def load_extracted_data(data_file: str = "anghami_extracted_data.json") -> Tuple[List[str], List[str]]:
    """Load songs and artists from the extracted data file"""
    if not os.path.exists(data_file):
        logger.error(
            f"Data file {data_file} not found. Please run selenium_extractor.py first.")
        sys.exit(1)

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        songs = data.get('songs', [])
        artists = data.get('artists', [])

        logger.info(f"Loaded {len(songs)} songs from {data_file}")
        return songs, artists

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error reading data file: {e}")
        sys.exit(1)


def setup_spotify_client(client_id: str, client_secret: str, redirect_uri: str) -> spotipy.Spotify:
    """Setup and authenticate Spotify client"""
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public playlist-modify-private"
        ))

        # Test the connection
        user = sp.current_user()
        if not user:
            logger.error(
                "Could not retrieve user info. Please check your authentication.")
            sys.exit(1)

        display_name = user.get('display_name', 'Unknown User')
        logger.info(f"Connected to Spotify as: {display_name}")
        return sp

    except Exception as e:
        logger.error(f"Failed to authenticate with Spotify: {e}")
        sys.exit(1)


def clean_song_title(title: str) -> str:
    """Clean song title by removing version indicators from parentheses or trailing hyphens."""

    cleaned_title = title

    # Define patterns for content within parentheses, like (feat. ...), (Live), (Remix)
    # The 'feat', 'ft', 'with', and 'featuring' patterns are more robust to consume everything until the closing parenthesis.
    paren_patterns = [
        # Feature patterns (already robust)
        r'\s*\(feat\.[^)]*\)', r'\s*\(ft\.[^)]*\)',
        r'\s*\(with[^)]*\)', r'\s*\(featuring[^)]*\)',
        
        # General version patterns - making them more robust
        r'\s*\(live[^)]*\)', r'\s*\(acoustic[^)]*\)', r'\s*\(remix[^)]*\)',
        r'\s*\(remastered[^)]*\)', r'\s*\(anniversary[^)]*\)',
        r'\s*\(deluxe[^)]*\)', r'\s*\(explicit\)', r'\s*\(clean\)',
        r'\s*\(radio\sedit[^)]*\)', r'\s*\(album\sversion[^)]*\)', r'\s*\(single\sversion[^)]*\)',
        r'\s*\(original\smix[^)]*\)', r'\s*\(extended\smix[^)]*\)',
        r'\s*\(instrumental\)', r'\s*\(karaoke\)', r'\s*\(cover\)',
        r'\s*\(bonus[^)]*\)', r'\s*\(demo\)', r'\s*\(edit\)',
        r'\s*\(version\)', r'\s*\(mix\)', r'\s*\(cut\)', r'\s*\(take\)',
        
        # Newly added precise patterns
        r'\s*\(from [^)]*\)',       # Catches (from "Movie"), (from the album), etc.
        r'\s*\(session[^)]*\)',     # Catches (BBC Session), etc.
        r'\s*\(unplugged[^)]*\)',   # Catches (MTV Unplugged), etc.
        r'\s*\(stripped\)',
        r'\s*\(edition[^)]*\)',
        r'\s*\(stereo\)', r'\s*\(mono\)',
        r'\s*\(reprise\)', r'\s*\(interlude\)',
        r'\s*\(soundtrack\)', r'\s*\(OST\)'
    ]

    for pattern in paren_patterns:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)

    # Define keywords for trailing hyphenated versions, like " - Live", " - Remix"
    # The `$` anchor ensures we only match at the end of the string, protecting titles like "We Live".
    hyphen_keywords = [
        'live', 'remix', 'acoustic', 'radio edit', 'album version', 'single version',
        'extended', 'studio version', 'original mix', 'club mix', 'radio mix',
        'main mix', 'extended mix', 'short mix', 'instrumental', 'karaoke',
        'cover', 'remastered', 'remaster', 'edit', 'mix', 'cut', 'take',
        # Newly added keywords
        'session', 'unplugged', 'stripped', 'edition', 'stereo', 'mono',
        'reprise', 'interlude', 'soundtrack'
    ]
    # Create a regex pattern like: \s+-\s+(live|remix|...)$
    hyphen_pattern = r'\s+-\s+(' + '|'.join(re.escape(k)
                                            for k in hyphen_keywords) + r')\s*$'
    cleaned_title = re.sub(
        hyphen_pattern, '', cleaned_title, flags=re.IGNORECASE)

    # Remove any empty parentheses that might be left over
    cleaned_title = re.sub(r'\s*\(\s*\)\s*', '', cleaned_title)

    # Remove extra spaces and trim
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    return cleaned_title


def clean_artist_name(artist: str) -> str:
    """Clean artist name by removing featuring artists and common variations"""
    # Remove featuring artists
    artist = re.sub(r'\s*feat\.?\s*.*$', '', artist, flags=re.IGNORECASE)
    artist = re.sub(r'\s*ft\.?\s*.*$', '', artist, flags=re.IGNORECASE)
    artist = re.sub(r'\s*featuring\s*.*$', '', artist, flags=re.IGNORECASE)
    artist = re.sub(r'\s*with\s*.*$', '', artist, flags=re.IGNORECASE)
    artist = re.sub(r'\s*&\s*.*$', '', artist, flags=re.IGNORECASE)
    artist = re.sub(r'\s*and\s*.*$', '', artist, flags=re.IGNORECASE)

    # Remove "The" prefix for matching
    artist = re.sub(r'^the\s+', '', artist, flags=re.IGNORECASE)

    return artist.strip()


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def search_song_on_spotify_enhanced(sp: spotipy.Spotify, song_title: str, artist_name: str) -> Tuple[Optional[str], str, Dict]:
    """Enhanced search for a song on Spotify with multiple strategies"""
    original_song = song_title
    original_artist = artist_name

    # Clean the inputs
    clean_song = clean_song_title(song_title)
    clean_artist = clean_artist_name(artist_name)

    search_results = {
        'original_song': original_song,
        'original_artist': original_artist,
        'clean_song': clean_song,
        'clean_artist': clean_artist,
        'match_type': 'not_found',
        'confidence': 0.0,
        'spotify_title': '',
        'spotify_artist': '',
        'search_queries': []
    }

    # Strategy 1: Exact match with original names
    query1 = f"{original_song} {original_artist}"
    search_results['search_queries'].append(query1)
    results = sp.search(q=query1, type='track', limit=5)

    if results and results['tracks']['items']:
        track = results['tracks']['items'][0]
        if track:
            track_title = track.get('name', '').lower()
            spotify_artists = track.get('artists', [])
            track_artist = spotify_artists[0].get(
                'name', '').lower() if spotify_artists else ""

            # Check if it's a very close match
            song_similarity = calculate_similarity(original_song, track_title)
            artist_similarity = calculate_similarity(
                original_artist, track_artist)

            if song_similarity > 0.8 and artist_similarity > 0.7:
                search_results.update({
                    'match_type': 'exact_match',
                    'confidence': min(song_similarity, artist_similarity),
                    'spotify_title': track.get('name', 'Unknown Title'),
                    'spotify_artist': spotify_artists[0].get('name', 'Unknown Artist') if spotify_artists else "Unknown Artist",
                    'track_uri': track.get('uri')
                })
                return track.get('uri'), f"Exact match: {track.get('name', 'Unknown Title')} - {spotify_artists[0].get('name', 'Unknown Artist') if spotify_artists else 'Unknown'}", search_results

    # Strategy 2: Clean version matching
    query2 = f"{clean_song} {clean_artist}"
    search_results['search_queries'].append(query2)
    results = sp.search(q=query2, type='track', limit=5)

    if results and results['tracks']['items']:
        track = results['tracks']['items'][0]
        if track:
            track_title = track.get('name', '').lower()
            spotify_artists = track.get('artists', [])
            track_artist = spotify_artists[0].get(
                'name', '').lower() if spotify_artists else ""

            song_similarity = calculate_similarity(clean_song, track_title)
            artist_similarity = calculate_similarity(
                clean_artist, track_artist)

            if song_similarity > 0.7 and artist_similarity > 0.6:
                search_results.update({
                    'match_type': 'version_match',
                    'confidence': min(song_similarity, artist_similarity),
                    'spotify_title': track.get('name', 'Unknown Title'),
                    'spotify_artist': spotify_artists[0].get('name', 'Unknown Artist') if spotify_artists else "Unknown Artist",
                    'track_uri': track.get('uri')
                })
                return track.get('uri'), f"Version match: {track.get('name', 'Unknown Title')} - {spotify_artists[0].get('name', 'Unknown Artist') if spotify_artists else 'Unknown'}", search_results

    # Strategy 3: Search by artist name to find similar songs
    query3 = f"artist:{clean_artist}"
    search_results['search_queries'].append(query3)
    results = sp.search(q=query3, type='track', limit=10)

    if results and results['tracks']['items']:
        best_match = None
        best_similarity = 0

        for track in results['tracks']['items']:
            if not track:
                continue
            track_title = track.get('name', '').lower()
            spotify_artists = track.get('artists', [])
            track_artist = spotify_artists[0].get(
                'name', '').lower() if spotify_artists else ""

            song_similarity = calculate_similarity(clean_song, track_title)
            artist_similarity = calculate_similarity(
                clean_artist, track_artist)

            # Combined similarity score
            combined_similarity = (song_similarity * 0.7) + \
                (artist_similarity * 0.3)

            if combined_similarity > best_similarity and combined_similarity > 0.6:
                best_similarity = combined_similarity
                best_match = track

        if best_match:
            best_match_artists = best_match.get('artists', [])
            search_results.update({
                'match_type': 'artist_search_match',
                'confidence': best_similarity,
                'spotify_title': best_match.get('name', 'Unknown Title'),
                'spotify_artist': best_match_artists[0].get('name', 'Unknown Artist') if best_match_artists else "Unknown Artist",
                'track_uri': best_match.get('uri')
            })
            return best_match.get('uri'), f"Artist search match: {best_match.get('name', 'Unknown Title')} - {best_match_artists[0].get('name', 'Unknown Artist') if best_match_artists else 'Unknown'}", search_results

    # Strategy 4: Search by song title only (last resort)
    query4 = f"{clean_song}"
    search_results['search_queries'].append(query4)
    results = sp.search(q=query4, type='track', limit=5)

    if results and results['tracks']['items']:
        track = results['tracks']['items'][0]
        if track:
            track_title = track.get('name', '').lower()
            spotify_artists = track.get('artists', [])
            track_artist = spotify_artists[0].get(
                'name', '').lower() if spotify_artists else ""

            song_similarity = calculate_similarity(clean_song, track_title)
            artist_similarity = calculate_similarity(
                clean_artist, track_artist)

            # Very strict matching for title-only search
            if song_similarity > 0.9 and artist_similarity > 0.5:
                search_results.update({
                    'match_type': 'title_only_match',
                    'confidence': song_similarity,
                    'spotify_title': track.get('name', 'Unknown Title'),
                    'spotify_artist': spotify_artists[0].get('name', 'Unknown Artist') if spotify_artists else "Unknown Artist",
                    'track_uri': track.get('uri')
                })
                return track.get('uri'), f"Title-only match: {track.get('name', 'Unknown Title')} - {spotify_artists[0].get('name', 'Unknown Artist') if spotify_artists else 'Unknown'}", search_results

    return None, "Not found", search_results


def create_playlist(sp: spotipy.Spotify, playlist_name: str, description: str = "") -> str:
    """Create a new playlist on Spotify"""
    try:
        user = sp.current_user()
        if not user or 'id' not in user:
            logger.error(
                "Could not get user ID from Spotify. Cannot create playlist.")
            sys.exit(1)
        user_id = user['id']

        playlist = sp.user_playlist_create(
            user=user_id, name=playlist_name, public=True, description=description)

        if not playlist or 'id' not in playlist:
            logger.error("Failed to create playlist on Spotify.")
            sys.exit(1)

        logger.info(
            f"Playlist '{playlist.get('name', 'Unknown Playlist')}' created successfully.")
        return playlist['id']
    except Exception as e:
        logger.error(f"Failed to create playlist: {e}")
        sys.exit(1)


def add_tracks_to_playlist(sp: spotipy.Spotify, playlist_id: str, track_uris: List[str]) -> None:
    """Add tracks to the playlist"""
    if not track_uris:
        logger.warning("No tracks to add to playlist")
        return

    try:
        # Spotify allows max 100 tracks per request
        batch_size = 100
        for i in range(0, len(track_uris), batch_size):
            batch = track_uris[i:i + batch_size]
            sp.playlist_add_items(playlist_id, batch)
            logger.info(
                f"Added batch {i//batch_size + 1}: {len(batch)} tracks")

        logger.info(f"Successfully added {len(track_uris)} tracks to playlist")

    except Exception as e:
        logger.error(f"Error adding tracks to playlist: {e}")


def save_detailed_report(found_tracks: List[Dict], not_found_tracks: List[Dict], playlist_name: str, total_songs: int):
    """Save a detailed migration report in both JSON and TXT formats."""

    # Generate timestamp for filenames and report header
    timestamp = datetime.now()
    file_timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
    report_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # Define filenames
    json_filename = f"migration_report_{file_timestamp}.json"
    txt_filename = f"migration_report_{file_timestamp}.txt"

    # --- Create JSON Report ---
    report_data = {
        'playlist_name': playlist_name,
        'report_generated_at': report_timestamp,
        'summary': {
            'total_songs_in_source': total_songs,
            'songs_found_on_spotify': len(found_tracks),
            'songs_not_found': len(not_found_tracks)
        },
        'found_tracks': found_tracks,
        'not_found_tracks': not_found_tracks
    }

    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved detailed JSON report to {json_filename}")
    except IOError as e:
        logger.error(f"Failed to write JSON report: {e}")

    # --- Create TXT Summary Report ---
    try:
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write("========================================\n")
            f.write("      Anghami to Spotify Migration      \n")
            f.write("========================================\n\n")
            f.write(f"Playlist Name: {playlist_name}\n")
            f.write(f"Report Generated On: {report_timestamp}\n\n")
            f.write("--- Migration Summary ---\n")
            f.write(f"Total Songs to Migrate: {total_songs}\n")
            f.write(f"Songs Found on Spotify: {len(found_tracks)}\n")
            f.write(f"Songs Not Found: {len(not_found_tracks)}\n\n")

            f.write("--- Found Tracks ---\n")
            if found_tracks:
                for i, track in enumerate(found_tracks, 1):
                    f.write(
                        f"{i}. ANGHAMI: {track['original_song']} - {track['original_artist']}\n"
                        f"   SPOTIFY: {track['spotify_title']} - {track['spotify_artist']} "
                        f"(Match: {track['match_type']}, Confidence: {track['confidence']:.2f})\n\n"
                    )
            else:
                f.write("No tracks were successfully found on Spotify.\n\n")

            # Add section for not-found tracks
            f.write("--- Songs Not Found on Spotify ---\n")
            if not_found_tracks:
                f.write(f"Total songs not found: {len(not_found_tracks)}\n\n")
                for i, track in enumerate(not_found_tracks, 1):
                    f.write(
                        f"{i}. Song: {track['original_song']}, Artist: {track['original_artist']}\n")
            else:
                f.write("Excellent! All songs were found on Spotify.\n")

            f.write("\n========================================\n")
            f.write("              End of Report             \n")
            f.write("========================================\n")

        logger.info(f"Saved summary TXT report to {txt_filename}")
    except IOError as e:
        logger.error(f"Failed to write TXT report: {e}")


def main():
    """Main function"""
    print("🎵 Anghami to Spotify Playlist Migrator - Enhanced Version")
    print("=" * 70)

    # Check if extracted data exists
    if not os.path.exists("anghami_extracted_data.json"):
        print("❌ No extracted data found!")
        print(
            "Please run selenium_extractor.py first to extract songs from your HTML file.")
        return

    # Load configuration
    print("Loading Spotify configuration...")
    client_id, client_secret, redirect_uri = load_config()

    # Load extracted data
    print("Loading extracted song data...")
    songs, artists = load_extracted_data()

    if not songs:
        print("❌ No songs found in the extracted data!")
        return

    print(f"Found {len(songs)} songs to migrate")

    # Setup Spotify client
    print("Connecting to Spotify...")
    sp = setup_spotify_client(client_id, client_secret, redirect_uri)

    total_songs_to_process = len(songs)
    logger.info(f"Attempting to migrate {total_songs_to_process} songs...")

    found_track_uris = []
    found_tracks_details = []
    not_found_tracks_details = []

    for i, (song, artist) in enumerate(zip(songs, artists), 1):
        logger.info(
            f"({i}/{total_songs_to_process}) Searching for: '{song}' by '{artist}'")
        uri, message, search_details = search_song_on_spotify_enhanced(
            sp, song, artist)

        if uri:
            logger.info(f"  -> Found: {message}")
            found_track_uris.append(uri)
            found_tracks_details.append(search_details)
        else:
            logger.warning(
                f"  -> Not Found: Could not find a suitable match for '{song}' by '{artist}'")
            not_found_tracks_details.append(search_details)

        time.sleep(0.5)  # Be respectful to Spotify's API rate limits

    if not found_track_uris:
        logger.warning(
            "No songs were found on Spotify. No playlist will be created.")
        save_detailed_report(found_tracks_details, not_found_tracks_details,
                             "No Playlist Created", total_songs_to_process)
        sys.exit(0)

    # Create a new playlist on Spotify
    playlist_name = input(
        "Enter the name for your new Spotify playlist: ").strip()
    if not playlist_name:
        playlist_name = "Anghami Liked Songs"
        logger.info(f"No name provided, using default: '{playlist_name}'")

    playlist_id = create_playlist(
        sp, playlist_name, "Migrated from Anghami using A2S-Migrator (https://github.com/PierreRamez/A2S-Migrator).")

    # Add songs to the playlist
    add_tracks_to_playlist(sp, playlist_id, found_track_uris)

    # Save the detailed migration report
    save_detailed_report(found_tracks_details, not_found_tracks_details,
                         playlist_name, total_songs_to_process)


if __name__ == "__main__":
    main()
