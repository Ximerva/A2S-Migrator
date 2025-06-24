# Anghami to Spotify Playlist Migrator

This tool allows you to migrate your liked songs or any public playlist from Anghami to a new playlist in your Spotify account. It uses a Selenium-based extractor to fetch song data directly from the Anghami web player and a smart matching algorithm to find the corresponding tracks on Spotify.


## Features

-   **Live Extraction:** No need to manually download HTML files. The tool controls a web browser to extract data live.
-   **Smart Song Matching:** Uses multiple strategies and a similarity algorithm to find the correct songs, even with variations in titles (e.g., "Live", "Remix", "feat.").
-   **Detailed Reporting:** Generates both a `JSON` and a readable `TXT` report detailing which songs were found and which were not.
-   **Interactive CLI:** A simple and clean menu-driven interface to guide you through the process.
-   **Cross-Platform:** Works with Chrome, Firefox, and Edge on any OS that supports them.

## Prerequisites

-   Python 3.7+
-   One of the following web browsers installed:
    -   Google Chrome (or any Chromium-based browser)
    -   Mozilla Firefox
    -   Microsoft Edge
-   A Spotify account with a new App created to get API credentials.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/PierreRamez/A2S-Migrator.git
    cd "A2S-Migrator"
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    # On Windows, use: .venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Spotify API Credentials:**
    -   Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
    -   Click **"Create app"**.
    -   Give it a name (e.g., "Anghami Migrator") and a description.
    -   Once created, you will see your **Client ID** and you can click to show your **Client Secret**.
    -   Now, go to **"Edit Settings"**.
    -   In the **"Redirect URIs"** field, add `http://127.0.0.1:8080`. Click **Save**.
    -   Rename the `config.ini.example` file to `config.ini`.
    -   Open `config.ini` and paste your credentials:
        ```ini
        [Spotify]
        client_id = YOUR_SPOTIFY_CLIENT_ID
        client_secret = YOUR_SPOTIFY_CLIENT_SECRET
        redirect_url = http://127.0.0.1:8080
        ```

## How to Use

Simply run the main script to start the interactive menu:

```bash
python3 main.py
```

You will be presented with the following options:

-   **1. Run the full process (Extract -> Migrate):** This will first launch the song extractor and then immediately run the migrator.
-   **2. Run only the Song Extractor:** This is useful if you just want to get your Anghami playlist data into the `anghami_extracted_data.json` file.
-   **3. Run only the Playlist Migrator:** Use this if you have already run the extractor and want to re-run the migration to Spotify.

### First-Time Run

When you run a process that uses the Spotify API for the first time, a browser window will open asking you to authorize the application. After you approve, you will be redirected to a blank page. **Copy the full URL of this page** and paste it back into the terminal when prompted.

## Project Structure

```
.
├── main.py           # The main entry point with the user menu
├── extractor.py      # Script to extract songs from Anghami using Selenium
├── migration.py      # Script to find songs on Spotify and create the playlist
├── requirements.txt  # Project dependencies
├── config.ini        # Template for the configuration file
├── config.ini        # Template for the configuration file
└── README.md         # This file
```

## Contributing

Contributions are welcome! If you have ideas for improvements or find any bugs, feel free to open an issue or submit a pull request.

## Supported Browsers

- **Google Chrome** (or Chromium)
- **Microsoft Edge**
- **Mozilla Firefox**
- **Other Chromium-based browsers** (Brave, Vivaldi, Opera, etc.)

When running the extractor, you can now choose "Other Chromium-based browser" and enter the full path to your browser's executable (e.g., `/usr/bin/brave-browser`).

To find the path to your browser, you can use:
```bash
which brave-browser
which vivaldi
which opera
which chromium
```

---

Made with ❤️ by Pierre Ramez Francis
