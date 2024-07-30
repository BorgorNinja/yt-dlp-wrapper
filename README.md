# yt-dlp wrapper

yt-dlp wrapper is a simple Video Downloader. The application uses `yt-dlp` to handle video downloading and provides options to select the save location for each video.

## Features

- Download individual videos.
- Batch download playlists.
- Select the save location for each video.
- View download progress and detailed logs in the console output.
- Play video previews directly from the application.

## Requirements

- Python 3.6+
- `yt-dlp`
- `requests`
- PyQt5

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/BorgorNinja/yt-dlp-wrapper.git
   cd yt-dlp-wrapper
   ```

2. **Install the required dependencies:**

   ```bash
   pip install yt-dlp requests pyqt5
   ```

3. **Ensure `yt-dlp` and `ffmpeg` are installed and available in your system's PATH:**

   - Install `yt-dlp` using pip:
     ```bash
     pip install yt-dlp
     ```

   - Install `ffmpeg` by following the instructions on the [official FFmpeg website](https://ffmpeg.org/download.html).

## Usage

1. **Run the application:**

   ```bash
   python yt-dlp-wrapper.py
   ```

2. **Enter the YouTube URL in the provided text box.**

3. **Click `Check URL` to verify the link.**

4. **If the link is a single video:**
   - Click `Download` to download the video.
   - Choose the save location for the video.

5. **If the link is a playlist:**
   - Click `Batch Download` to download all videos in the playlist.
   - Choose the directory where the videos should be saved. Each video will be saved with its title as the filename.

6. **Monitor the progress through the progress bar and console output.**

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This application uses the [yt-dlp](https://github.com/yt-dlp/yt-dlp) library for downloading videos.
- The GUI is built using [PyQt5](https://riverbankcomputing.com/software/pyqt/intro).
- Thanks to the developers of these libraries for their hard work.



Feel free to customize this README file as per your needs and update the repository URL and other specific details.
