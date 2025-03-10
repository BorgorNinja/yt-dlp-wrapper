#!/usr/bin/python3
import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
                             QLineEdit, QMessageBox, QTextEdit, QLabel, QProgressBar, QFileDialog, QComboBox, QAction, QMenu, QSystemTrayIcon, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
import requests
from io import BytesIO
import webbrowser
import os
import yt_dlp
import json
import asyncio

# --- New Helper Functions for Bypass Extraction ---

def get_cookies_headless(video_url):
    """
    Placeholder for headless cookie extraction.
    For a full implementation, you might use pyppeteer or Selenium to get valid cookies.
    """
    # For now, simply return an empty string.
    return ""

def save_cookies_to_file(cookies, path):
    with open(path, 'w') as f:
        f.write(cookies)

def extract_with_bypass(url):
    """
    Attempt a normal extraction first. If that fails, try using cookies.
    """
    ydl_opts = {
        'quiet': True,
        'dump_single_json': True,
        'extract_flat': True,
        'headers': {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/58.0.3029.110 Safari/537.3')
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return ("no_cookies", info)
    except Exception as e:
        print("Normal extraction failed, attempting fallback with cookies:", e)
        if not os.path.exists("cookies.txt"):
            cookies = asyncio.run(get_cookies_headless(url))
            save_cookies_to_file(cookies, "cookies.txt")
        ydl_opts['cookies'] = "cookies.txt"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return ("cookies", info)

# --- Main Application Code ---

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('YouTube Downloader')
        self.setGeometry(100, 100, 600, 500)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Enter YouTube URL')
        self.layout.addWidget(self.url_input)

        self.check_button = QPushButton('Check URL', self)
        self.check_button.clicked.connect(self.check_url)
        self.layout.addWidget(self.check_button)

        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.layout.addWidget(self.console_output)

        self.thumbnail_label = QLabel(self)
        self.layout.addWidget(self.thumbnail_label)

        self.video_length_label = QLabel(self)
        self.layout.addWidget(self.video_length_label)

        self.play_button = QPushButton('Play Preview', self)
        self.play_button.setVisible(False)
        self.play_button.clicked.connect(self.play_preview)
        self.layout.addWidget(self.play_button)

        self.download_button = QPushButton('Download', self)
        self.download_button.setVisible(False)
        self.download_button.clicked.connect(self.download_video)
        self.layout.addWidget(self.download_button)

        self.audio_download_button = QPushButton('Download Audio', self)
        self.audio_download_button.setVisible(False)
        self.audio_download_button.clicked.connect(self.download_audio)
        self.layout.addWidget(self.audio_download_button)

        self.batch_download_button = QPushButton('Batch Download Videos', self)
        self.batch_download_button.setVisible(False)
        self.batch_download_button.clicked.connect(self.batch_download_videos)
        self.layout.addWidget(self.batch_download_button)

        self.batch_audio_download_button = QPushButton('Batch Download Audios', self)
        self.batch_audio_download_button.setVisible(False)
        self.batch_audio_download_button.clicked.connect(self.batch_download_audios)
        self.layout.addWidget(self.batch_audio_download_button)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.quality_combo = QComboBox(self)
        self.quality_combo.setVisible(False)
        self.quality_combo.addItems(['Best', '1080p', '720p', '480p', '360p'])
        self.layout.addWidget(self.quality_combo)

        timestamp_layout = QHBoxLayout()
        self.start_time_input = QLineEdit(self)
        self.start_time_input.setPlaceholderText('Start (hh:mm:ss)')
        timestamp_layout.addWidget(self.start_time_input)

        self.end_time_input = QLineEdit(self)
        self.end_time_input.setPlaceholderText('End (hh:mm:ss)')
        timestamp_layout.addWidget(self.end_time_input)

        self.layout.addLayout(timestamp_layout)

        self.video_urls = []
        self.current_video_url = ''
        self.current_video_title = ''
        self.current_video_length = 0

        self.init_menu()

        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.show()

    def init_menu(self):
        menubar = self.menuBar()

        settings_menu = menubar.addMenu('Settings')
        default_dir_action = QAction('Set Default Download Directory', self)
        default_dir_action.triggered.connect(self.set_default_directory)
        settings_menu.addAction(default_dir_action)

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

        try:
            mode, info_dict = extract_with_bypass(url)
            self.handle_url_info(info_dict)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to extract info: {str(e)}')

    def handle_url_info(self, info_dict):
        self.console_output.clear()
        self.thumbnail_label.clear()
        self.video_length_label.clear()
        self.play_button.setVisible(False)
        self.download_button.setVisible(False)
        self.audio_download_button.setVisible(False)
        self.batch_download_button.setVisible(False)
        self.batch_audio_download_button.setVisible(False)
        self.quality_combo.setVisible(False)
        self.video_urls.clear()

        if 'entries' in info_dict:
            self.console_output.append('Playlist detected:')
            for entry in info_dict['entries']:
                self.video_urls.append(entry['url'])
                self.console_output.append(entry['url'])
            self.batch_download_button.setVisible(True)
            self.batch_audio_download_button.setVisible(True)
        else:
            self.console_output.append(f"Video detected: {info_dict['title']}")
            self.current_video_title = info_dict['title']
            self.thumbnail_label.setPixmap(self.fetch_thumbnail(info_dict['thumbnail']))
            self.video_length_label.setText(f"Length: {self.format_duration(info_dict['duration'])}")
            self.current_video_length = info_dict['duration']
            self.play_button.setVisible(True)
            self.download_button.setVisible(True)
            self.audio_download_button.setVisible(True)
            self.quality_combo.setVisible(True)
            self.current_video_url = info_dict['webpage_url']
            self.video_urls.append(info_dict['webpage_url'])

    def fetch_thumbnail(self, url):
        response = requests.get(url)
        image = QPixmap()
        image.loadFromData(BytesIO(response.content).getvalue())
        return image.scaled(320, 180, Qt.KeepAspectRatio)

    def format_duration(self, duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def play_preview(self):
        webbrowser.open(self.current_video_url)

    def download_video(self):
        if self.video_urls:
            save_path = self.get_default_directory()
            if not save_path:
                save_path = QFileDialog.getExistingDirectory(self, "Select Directory")
            if save_path:
                save_path = os.path.join(save_path, f"{self.current_video_title}.mp4")
                self.start_download(self.video_urls[0], save_path, video=True)

    def download_audio(self):
        if self.video_urls:
            save_path = self.get_default_directory()
            if not save_path:
                save_path = QFileDialog.getExistingDirectory(self, "Select Directory")
            if save_path:
                save_path = os.path.join(save_path, f"{self.current_video_title}.mp3")
                self.start_download(self.video_urls[0], save_path, video=False)

    def batch_download_videos(self):
        if self.video_urls:
            save_dir = self.get_default_directory()
            if not save_dir:
                save_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
            if save_dir:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.thread = BatchDownloadThread(self.video_urls, save_dir, self.quality_combo.currentText(), video=True)
                self.thread.console_update.connect(self.update_console)
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
                self.thread = BatchDownloadThread(self.video_urls, save_dir, self.quality_combo.currentText(), video=False)
                self.thread.console_update.connect(self.update_console)
                self.thread.progress_update.connect(self.update_progress)
                self.thread.finished.connect(self.download_finished)
                self.thread.start()

    def start_download(self, url, save_path, video=True):
        start_time = self.start_time_input.text().strip()
        end_time = self.end_time_input.text().strip()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.thread = DownloadThread(url, save_path, self.quality_combo.currentText(), video, start_time, end_time)
        self.thread.console_update.connect(self.update_console)
        self.thread.progress_update.connect(self.update_progress)
        self.thread.finished.connect(self.download_finished)
        self.thread.start()

    def update_console(self, text):
        self.console_output.append(text)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, success, message):
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, 'Success', 'Download completed successfully')
            self.tray_icon.showMessage("YouTube Downloader", "Download completed successfully", QSystemTrayIcon.Information)
        else:
            QMessageBox.critical(self, 'Error', f'Download failed: {message}')
            self.tray_icon.showMessage("YouTube Downloader", f"Download failed: {message}", QSystemTrayIcon.Critical)


class DownloadThread(QThread):
    console_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, save_path, quality, video, start_time=None, end_time=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.quality = quality
        self.video = video
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/58.0.3029.110 Safari/537.3')
        }
        quality_param = {
            'Best': 'best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best',
            '480p': 'bestvideo[height<=480]+bestaudio/best',
            '360p': 'bestvideo[height<=360]+bestaudio/best'
        }[self.quality]

        if self.video:
            command = [
                'yt-dlp',
                '--add-header', f'User-Agent: {headers["User-Agent"]}',
                '-f', quality_param,
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

        postprocessor_args = []
        if self.start_time:
            postprocessor_args.append(f"-ss {self.start_time}")
        if self.end_time:
            postprocessor_args.append(f"-to {self.end_time}")
        if postprocessor_args:
            command.extend(['--postprocessor-args', ' '.join(postprocessor_args)])

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in iter(process.stdout.readline, ''):
            self.console_update.emit(line.strip())
            if "frame=" in line:
                progress = self.extract_progress(line)
                self.progress_update.emit(progress)

        stdout, stderr = process.communicate()
        if process.returncode != 0:
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
    console_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, urls, save_dir, quality, video):
        super().__init__()
        self.urls = urls
        self.save_dir = save_dir
        self.quality = quality
        self.video = video

    def run(self):
        quality_param = {
            'Best': 'best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best',
            '480p': 'bestvideo[height<=480]+bestaudio/best',
            '360p': 'bestvideo[height<=360]+bestaudio/best'
        }[self.quality]

        for i, url in enumerate(self.urls):
            headers = {
                'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/58.0.3029.110 Safari/537.3')
            }
            if self.video:
                command = [
                    'yt-dlp',
                    '--add-header', f'User-Agent: {headers["User-Agent"]}',
                    '-f', quality_param,
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
                self.console_update.emit(line.strip())
                if "frame=" in line:
                    progress = self.extract_progress(line)
                    self.progress_update.emit(progress)

            stdout, stderr = process.communicate()
            if process.returncode != 0:
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
