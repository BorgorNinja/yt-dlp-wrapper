#!/usr/bin/python3

import sys
import subprocess
import os
import json
import requests

from io import BytesIO

import yt_dlp

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLineEdit, QMessageBox, QLabel, QProgressBar,
    QFileDialog, QComboBox, QAction, QSystemTrayIcon, QHBoxLayout,
    QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView


class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('YouTube Downloader')
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # URL input
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Enter YouTube URL')
        self.layout.addWidget(self.url_input)

        # Check URL button
        self.check_button = QPushButton('Check URL', self)
        self.check_button.clicked.connect(self.check_url)
        self.layout.addWidget(self.check_button)

        # Thumbnail (small)
        self.thumbnail_label = QLabel(self)
        self.layout.addWidget(self.thumbnail_label)

        # Embedded WebView for preview, set it to expand with window
        self.web_view = QWebEngineView(self)
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.web_view.setVisible(False)
        self.layout.addWidget(self.web_view)

        # Download (video) button
        self.download_button = QPushButton('Download Video', self)
        self.download_button.setEnabled(False)
        self.download_button.setVisible(False)
        self.download_button.clicked.connect(self.download_video)
        self.layout.addWidget(self.download_button)

        # Download (audio) button
        self.audio_download_button = QPushButton('Download Audio', self)
        self.audio_download_button.setEnabled(False)
        self.audio_download_button.setVisible(False)
        self.audio_download_button.clicked.connect(self.download_audio)
        self.layout.addWidget(self.audio_download_button)

        # Batch download buttons
        self.batch_download_button = QPushButton('Batch Download Videos', self)
        self.batch_download_button.setVisible(False)
        self.batch_download_button.clicked.connect(self.batch_download_videos)
        self.layout.addWidget(self.batch_download_button)

        self.batch_audio_download_button = QPushButton('Batch Download Audios', self)
        self.batch_audio_download_button.setVisible(False)
        self.batch_audio_download_button.clicked.connect(self.batch_download_audios)
        self.layout.addWidget(self.batch_audio_download_button)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        # Quality combo (will be populated dynamically for single videos)
        self.quality_combo = QComboBox(self)
        self.quality_combo.setVisible(False)
        self.quality_combo.addItem("-- None --")  # Default
        self.quality_combo.setCurrentIndex(0)
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        self.layout.addWidget(self.quality_combo)

        # Store video URLs and info
        self.video_urls = []
        self.current_video_url = ''
        self.current_video_title = ''
        self.video_formats = []

        self.init_menu()

        # Tray icon
        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.show()

    def init_menu(self):
        menubar = self.menuBar()

        settings_menu = menubar.addMenu('Settings')
        default_dir_action = QAction('Set Default Download Directory', self)
        default_dir_action.triggered.connect(self.set_default_directory)
        settings_menu.addAction(default_dir_action)

        material_action = QAction('Apply Material Design', self)
        material_action.triggered.connect(self.apply_material_design)
        settings_menu.addAction(material_action)

    def apply_material_design(self):
        material_stylesheet = """
        QWidget {
            background-color: #fafafa;
            font-family: Roboto, sans-serif;
            color: #212121;
        }
        QPushButton {
            background-color: #6200ee;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #3700b3;
        }
        QLineEdit {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px;
            background-color: white;
        }
        QProgressBar {
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #eeeeee;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #6200ee;
            width: 20px;
        }
        QComboBox {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px;
            background-color: white;
        }
        QMenuBar {
            background-color: #6200ee;
            color: white;
        }
        QMenuBar::item {
            background-color: #6200ee;
            color: white;
            padding: 5px 10px;
        }
        QMenuBar::item:selected {
            background-color: #3700b3;
        }
        QMenu {
            background-color: white;
            color: #212121;
        }
        QMenu::item:selected {
            background-color: #eeeeee;
        }
        """
        app = QApplication.instance()
        app.setStyleSheet(material_stylesheet)
        QMessageBox.information(self, "Material Design", "Material Design applied.")

    def set_default_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Default Download Directory")
        if directory:
            with open('settings.json', 'w') as f:
                json.dump({'default_directory': directory}, f)

    def get_default_directory(self):
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                return settings.get('default_directory', '')
        return ''

    def check_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, 'Error', 'Please enter a valid YouTube URL')
            return

        ydl_opts = {
            'quiet': True,
            'dump_single_json': True,
            'extract_flat': True,
            'headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                )
            }
        }

        try:
            info_dict = self.extract_info(url, ydl_opts)
            self.handle_url_info(info_dict)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to extract info: {str(e)}')

    def extract_info(self, url, ydl_opts):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def handle_url_info(self, info_dict):
        self.thumbnail_label.clear()
        self.web_view.setVisible(False)
        self.download_button.setVisible(False)
        self.download_button.setEnabled(False)
        self.audio_download_button.setVisible(False)
        self.audio_download_button.setEnabled(False)
        self.batch_download_button.setVisible(False)
        self.batch_audio_download_button.setVisible(False)
        self.quality_combo.setVisible(False)
        self.quality_combo.clear()
        self.quality_combo.addItem("-- None --")
        self.quality_combo.setCurrentIndex(0)
        self.video_urls.clear()
        self.video_formats = []

        # Check if playlist
        if 'entries' in info_dict:
            for entry in info_dict['entries']:
                video_url = entry['url']
                if not video_url.startswith("http"):
                    video_url = "https://www.youtube.com/watch?v=" + video_url
                self.video_urls.append(video_url)
            self.batch_download_button.setVisible(True)
            self.batch_audio_download_button.setVisible(True)
        else:
            # Single video
            self.current_video_title = info_dict.get('title', 'untitled')
            thumbnail = info_dict.get('thumbnail')
            if thumbnail:
                self.thumbnail_label.setPixmap(self.fetch_thumbnail(thumbnail))

            self.current_video_url = info_dict.get('webpage_url', '')
            self.video_urls.append(self.current_video_url)

            # Populate available video formats
            if 'formats' in info_dict:
                for f in info_dict['formats']:
                    if f.get('vcodec') != 'none':  # Only video
                        height = f.get('height', 'Unknown')
                        ext = f.get('ext', 'Unknown')
                        format_id = f.get('format_id', 'Unknown')
                        label = f"{height}p ({ext}) [ID: {format_id}]"
                        self.video_formats.append((label, format_id, ext))

                # Sort by resolution descending
                self.video_formats.sort(
                    key=lambda x: int(x[0].split('p')[0]) if x[0].split('p')[0].isdigit() else 0,
                    reverse=True
                )
                for label, format_id, ext in self.video_formats:
                    self.quality_combo.addItem(label, (format_id, ext))

            self.quality_combo.setVisible(True)
            self.download_button.setVisible(True)
            self.audio_download_button.setVisible(True)
            self.audio_download_button.setEnabled(True)

            # Embed video in QWebEngineView
            video_id = info_dict.get('id', '')
            if video_id:
                embed_url = f"https://www.youtube.com/embed/{video_id}"
                self.web_view.setUrl(QUrl(embed_url))
                self.web_view.setVisible(True)

    def fetch_thumbnail(self, url):
        response = requests.get(url)
        image = QPixmap()
        image.loadFromData(BytesIO(response.content).getvalue())
        # Scale the thumbnail to a smaller size
        return image.scaled(120, 90, Qt.KeepAspectRatio)

    def on_quality_changed(self, index):
        if index == 0:  # "-- None --"
            self.download_button.setEnabled(False)
        else:
            self.download_button.setEnabled(True)

    def download_video(self):
        if not self.video_urls:
            return
        if self.quality_combo.currentIndex() <= 0:
            QMessageBox.warning(self, 'Error', 'Please select a valid video quality.')
            return

        # Get chosen format
        format_id, ext = self.quality_combo.itemData(self.quality_combo.currentIndex())

        save_path = self.get_default_directory()
        if not save_path:
            save_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if save_path:
            final_path = os.path.join(save_path, f"{self.current_video_title}.mp4")
            self.start_download(
                url=self.video_urls[0],
                save_path=final_path,
                video=True,
                format_id=format_id
            )

    def download_audio(self):
        if not self.video_urls:
            return

        save_path = self.get_default_directory()
        if not save_path:
            save_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if save_path:
            final_path = os.path.join(save_path, f"{self.current_video_title}.mp3")
            self.start_download(
                url=self.video_urls[0],
                save_path=final_path,
                video=False,
                format_id=None
            )

    def batch_download_videos(self):
        if self.video_urls:
            save_dir = self.get_default_directory()
            if not save_dir:
                save_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
            if save_dir:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.thread = BatchDownloadThread(
                    self.video_urls,
                    save_dir,
                    self.quality_combo.currentText(),  # Old approach for batch
                    video=True
                )
                self.thread.progress_update.connect(self.update_progress)
                self.thread.finished.connect(self.download_finished)
                self.thread.start()

    def batch_download_audios(self):
        if self.video_urls:
            save_dir = self.get_default_directory()
            if not save_dir:
                save_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
            if save_dir:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.thread = BatchDownloadThread(
                    self.video_urls,
                    save_dir,
                    self.quality_combo.currentText(),  # Old approach for batch
                    video=False
                )
                self.thread.progress_update.connect(self.update_progress)
                self.thread.finished.connect(self.download_finished)
                self.thread.start()

    def start_download(self, url, save_path, video, format_id):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.thread = DownloadThread(
            url=url,
            save_path=save_path,
            video=video,
            format_id=format_id
        )
        self.thread.progress_update.connect(self.update_progress)
        self.thread.finished.connect(self.download_finished)
        self.thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, success, message):
        self.progress_bar.setVisible(False)
        if success:
            if "Skipped private/unavailable video." in message:
                QMessageBox.information(self, "Info", "Skipped private/unavailable video.")
            else:
                QMessageBox.information(self, 'Success', 'Download completed successfully')
                self.tray_icon.showMessage(
                    "YouTube Downloader",
                    "Download completed successfully",
                    QSystemTrayIcon.Information
                )
        else:
            QMessageBox.critical(self, 'Error', f'Download failed: {message}')
            self.tray_icon.showMessage(
                "YouTube Downloader",
                f"Download failed: {message}",
                QSystemTrayIcon.Critical
            )


class DownloadThread(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, save_path, video, format_id=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.video = video
        self.format_id = format_id

    def run(self):
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            )
        }

        if self.video:
            command = [
                'yt-dlp',
                '--add-header', f'User-Agent: {headers["User-Agent"]}'
            ]
            if self.format_id:
                command += ['-f', self.format_id]
            command += [
                '--recode-video', 'mp4',
                '-o', self.save_path,
                self.url
            ]
        else:
            command = [
                'yt-dlp',
                '--add-header', f'User-Agent: {headers["User-Agent"]}',
                '-x', '--audio-format', 'mp3',
                '-o', self.save_path,
                self.url
            ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in iter(process.stdout.readline, ''):
            if "frame=" in line:
                progress = self.extract_progress(line)
                self.progress_update.emit(progress)

        stdout, stderr = process.communicate()
        if process.returncode != 0:
            err_lower = stderr.lower()
            if ("private" in err_lower or
                "not found" in err_lower or
                "extractorerror" in err_lower):
                self.finished.emit(True, "Skipped private/unavailable video.")
            else:
                self.finished.emit(False, stderr)
            return

        self.finished.emit(True, '')

    def extract_progress(self, line):
        if "%" in line:
            try:
                percent_str = line.split('%')[0].split()[-1]
                percent = float(percent_str)
                return int(percent)
            except (ValueError, IndexError):
                pass
        return 0


class BatchDownloadThread(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, urls, save_dir, quality, video):
        super().__init__()
        self.urls = urls
        self.save_dir = save_dir
        self.quality = quality
        self.video = video

    def run(self):
        # Old approach for batch: map textual choices to format strings
        quality_map = {
            'Best': 'best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best',
            '480p': 'bestvideo[height<=480]+bestaudio/best',
            '360p': 'bestvideo[height<=360]+bestaudio/best'
        }
        format_string = quality_map.get(self.quality, 'best')

        for i, url in enumerate(self.urls):
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                )
            }
            if self.video:
                command = [
                    'yt-dlp',
                    '--add-header', f'User-Agent: {headers["User-Agent"]}',
                    '-f', format_string,
                    '--recode-video', 'mp4',
                    '-o', os.path.join(self.save_dir, '%(title)s.%(ext)s'),
                    url
                ]
            else:
                command = [
                    'yt-dlp',
                    '--add-header', f'User-Agent: {headers["User-Agent"]}',
                    '-x', '--audio-format', 'mp3',
                    '-o', os.path.join(self.save_dir, '%(title)s.%(ext)s'),
                    url
                ]

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            for line in iter(process.stdout.readline, ''):
                if "frame=" in line:
                    progress = self.extract_progress(line)
                    self.progress_update.emit(progress)

            stdout, stderr = process.communicate()
            if process.returncode != 0:
                err_lower = stderr.lower()
                if ("private" in err_lower or
                    "not found" in err_lower or
                    "extractorerror" in err_lower):
                    self.progress_update.emit(int((i + 1) / len(self.urls) * 100))
                    continue
                else:
                    self.finished.emit(False, stderr)
                    return

            self.progress_update.emit(int((i + 1) / len(self.urls) * 100))

        self.finished.emit(True, '')

    def extract_progress(self, line):
        if "%" in line:
            try:
                percent_str = line.split('%')[0].split()[-1]
                percent = float(percent_str)
                return int(percent)
            except (ValueError, IndexError):
                pass
        return 0


if __name__ == '__main__':
    app = QApplication(sys.argv)
    downloader = YouTubeDownloader()
    downloader.show()
    sys.exit(app.exec_())
