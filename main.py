import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
                             QLineEdit, QMessageBox, QTextEdit, QLabel, QProgressBar, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
import requests
from io import BytesIO
import webbrowser
import os
import yt_dlp

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('YouTube Downloader')
        self.setGeometry(100, 100, 600, 400)

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

        self.play_button = QPushButton('Play Preview', self)
        self.play_button.setVisible(False)
        self.play_button.clicked.connect(self.play_preview)
        self.layout.addWidget(self.play_button)

        self.download_button = QPushButton('Download', self)
        self.download_button.setVisible(False)
        self.download_button.clicked.connect(self.download_video)
        self.layout.addWidget(self.download_button)

        self.batch_download_button = QPushButton('Batch Download', self)
        self.batch_download_button.setVisible(False)
        self.batch_download_button.clicked.connect(self.batch_download)
        self.layout.addWidget(self.batch_download_button)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.video_urls = []
        self.current_video_url = ''

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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
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
        self.console_output.clear()
        self.thumbnail_label.clear()
        self.play_button.setVisible(False)
        self.download_button.setVisible(False)
        self.batch_download_button.setVisible(False)
        self.video_urls.clear()

        if 'entries' in info_dict:
            self.console_output.append('Playlist detected:')
            for entry in info_dict['entries']:
                self.video_urls.append(entry['url'])
                self.console_output.append(entry['url'])
            self.batch_download_button.setVisible(True)
        elif 'short' in info_dict.get('id', ''):
            QMessageBox.critical(self, 'Error', 'Death to all Shorts')
            sys.exit(1)
        else:
            self.console_output.append(f"Video detected: {info_dict['title']}")
            self.thumbnail_label.setPixmap(self.fetch_thumbnail(info_dict['thumbnail']))
            self.play_button.setVisible(True)
            self.download_button.setVisible(True)
            self.current_video_url = info_dict['webpage_url']
            self.video_urls.append(info_dict['webpage_url'])

    def fetch_thumbnail(self, url):
        response = requests.get(url)
        image = QPixmap()
        image.loadFromData(BytesIO(response.content).getvalue())
        return image.scaled(320, 180, Qt.KeepAspectRatio)

    def play_preview(self):
        webbrowser.open(self.current_video_url)

    def download_video(self):
        if self.video_urls:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "", "Video Files (*.mp4 *.mkv *.avi)")
            if save_path:
                self.start_download(self.video_urls[0], save_path)

    def batch_download(self):
        if self.video_urls:
            save_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
            if save_dir:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.thread = BatchDownloadThread(self.video_urls, save_dir)
                self.thread.console_update.connect(self.update_console)
                self.thread.progress_update.connect(self.update_progress)
                self.thread.finished.connect(self.download_finished)
                self.thread.start()

    def start_download(self, url, save_path):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.thread = DownloadThread(url, save_path)
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
        else:
            QMessageBox.critical(self, 'Error', f'Download failed: {message}')


class DownloadThread(QThread):
    console_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        command = ['yt-dlp', '-f', 'best', '-o', self.save_path, self.url]
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

    def __init__(self, urls, save_dir):
        super().__init__()
        self.urls = urls
        self.save_dir = save_dir

    def run(self):
        for i, url in enumerate(self.urls):
            command = ['yt-dlp', '-f', 'best', '-o', os.path.join(self.save_dir, '%(title)s.%(ext)s'), url]
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
