# TokGrabber 🚀🎥

![Repo Size](https://img.shields.io/github/repo-size/xHaMMaDy/TokGrabber?style=for-the-badge)
![GitHub Stars](https://img.shields.io/github/stars/xHaMMaDy/TokGrabber?style=for-the-badge)
![License](https://img.shields.io/github/license/xHaMMaDy/TokGrabber?style=for-the-badge)

TokGrabber is a feature-rich, modern GUI application for downloading TikTok videos, cover images, and music. Built with PyQt5 and styled with [QDarkStyleSheet](https://github.com/ColinDuquesnoy/QDarkStyleSheet), TokGrabber delivers an elegant and powerful experience for content retrieval.

## Features ✨

- **Custom Title Bar:**  
  - Frameless window with a sleek custom title bar featuring a TikTok logo and the name **TokGrabber**.
  - Menu options for **Settings**, **Export Logs**, and **About** directly in the title bar.

- **Single Download Mode:**  
  - Fetch video info (title, region, duration) and preview the thumbnail.
  - Choose from Standard Video, HD Video, Cover Image, or Music.
  - Check for file existence (prompt to overwrite if exists) with a real-time progress bar and detailed logs.

- **Batch Download Mode:**  
  - Download multiple TikTok videos by supplying a text file with URLs.
  - Global progress bar tracks overall download progress.
  - Skips already existing files and logs errors for individual URLs.

- **Download History Tab:**  
  - View a history table populated from a CSV file.
  - Right-click on any history entry to get a "Show in Folder" option.

- **Robust Error Handling:**  
  - Built-in retry logic and detailed logging for both single and batch operations.

- **User Settings Panel:**  
  - Configure default output directory, network timeout, verbose logging, and theme preference via a settings dialog.

- **Modern Dark Theme:**  
  - Uses QDarkStyleSheet for a stunning dark appearance (with a fallback if not installed).

- **About Dialog:**  
  - Provides information about the project and the creator: **Ibrahim Hammad (HaMMaDy)**.  
  - Visit my GitHub: [https://github.com/xHaMMaDy](https://github.com/xHaMMaDy)
  
  ## Screenshots

Here are some snapshots of TokGrabber in action:

**Before Fetching Info:**
![TokGrabber Screenshot Before](https://i.imgur.com/jKoerkK.png)

**After Fetching Info:**
![TokGrabber Screenshot After](https://i.imgur.com/VgLExpQ.png)


## Installation 🛠️

1. **Clone the repository:**
   ```bash
   git clone https://github.com/xHaMMaDy/TokGrabber.git
   cd TokGrabber
	```
2. **Install dependencies:**
   ```bash
	pip install PyQt5 requests tqdm qdarkstyle
	```
3. **Assets:**
	Ensure `tiktok_logo.png` is located in the project directory.

## Usage ▶️
	Run the application with:
   ```bash
	python TokGrabber.py```
	
	
### Single Download Mode
- **Enter TikTok URL:** Paste a valid TikTok URL.
- **Fetch Info:** Retrieve video details (title, region, duration) and view the thumbnail.
- **Download:** Select your desired download type and output directory, then click **Download**. If the file exists, you’ll be prompted to overwrite it.
- **Pause/Resume:** Control the download process using the **Pause/Resume** button.
- **Logs & Progress:** Monitor download progress and view detailed logs in real time.

### Batch Download Mode
- **URLs File:** Provide a text file containing TikTok URLs (one per line).
- **Download Type:** Choose the media type for all URLs.
- **Output Directory:** Specify the output directory.
- **Start Batch Download:** Click **Start Batch Download** to process all URLs. A global progress bar and log updates will keep you informed.
- **Error Handling:** Invalid URLs and download errors are logged, and the process continues for remaining URLs.

### Download History Tab
- **View History:** Browse your past downloads displayed in a table.
- **Context Menu:** Right-click on any history entry to bring up a context menu with a **"Show in Folder"** option, which opens the folder containing the downloaded file.
- **Refresh:** Click the **Refresh History** button to update the history view.

## Disclaimer ⚠️

**TokGrabber** is provided for **educational purposes only**.  
This project is not affiliated with, endorsed by, or approved by TikTok Inc.  
Use of this tool to download content may violate TikTok’s Terms of Service.  
It is the user's responsibility to ensure compliance with local laws and TikTok policies.

## License 📄

This project is licensed under the [MIT License](LICENSE).

## Contributing 🤝

Contributions are welcome! Feel free to fork the repository and submit pull requests.  
Please follow the guidelines outlined in our [Contributing Guide](CONTRIBUTING.md).


### About & Contact
- **About TokGrabber:**  
  Created by **Ibrahim Hammad (HaMMaDy)**.  
  GitHub: [https://github.com/xHaMMaDy](https://github.com/xHaMMaDy)
  
- **Contact:**  
  Feel free to reach out via email: [xhammady@gmail.com](mailto:xhammady@gmail.com)

*Happy Downloading! 🎉*
