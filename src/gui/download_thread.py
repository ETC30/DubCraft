from PySide6.QtCore import QThread, Signal
from pytube import YouTube
from pytube.innertube import _default_clients
from pytube import cipher
import re

from pytube.exceptions import RegexMatchError

#Código fix urls
_default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]



def get_throttling_function_name(js: str) -> str:
    """Extract the name of the function that computes the throttling parameter.

    :param str js:
        The contents of the base.js asset file.
    :rtype: str
    :returns:
        The name of the function used to compute the throttling parameter.
    """
    function_patterns = [
        r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&\s*'
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])\([a-z]\)',
    ]
    #logger.debug('Finding throttling function name')
    for pattern in function_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(js)
        if function_match:
            #logger.debug("finished regex search, matched: %s", pattern)
            if len(function_match.groups()) == 1:
                return function_match.group(1)
            idx = function_match.group(2)
            if idx:
                idx = idx.strip("[]")
                array = re.search(
                    r'var {nfunc}\s*=\s*(\[.+?\]);'.format(
                        nfunc=re.escape(function_match.group(1))),
                    js
                )
                if array:
                    array = array.group(1).strip("[]").split(",")
                    array = [x.strip() for x in array]
                    return array[int(idx)]

    raise RegexMatchError(
        caller="get_throttling_function_name", pattern="multiple"
    )

cipher.get_throttling_function_name = get_throttling_function_name
#Fin código fix urls

class DownloadVideoThread (QThread):
    progress = Signal(int)
    download_complete = Signal(bool)
    
    def __init__(self, url, output_path, resolution):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.resolution = resolution
        self.video_path=""

    def run (self):
        yt = YouTube(self.url, on_progress_callback=self.on_progress, on_complete_callback=self.on_complete)
        video_stream = yt.streams.filter(res=self.resolution, only_video=True).first()
        if video_stream:
            video_file_name = f"video_{yt.title}.mp4"
            self.video_path = video_stream.download(output_path=self.output_path, filename = video_file_name, max_retries=10)
        else:
            self.progress.emit(0)
            self.download_complete.emit(False)
            
    def on_progress(self, stream, chunk, bytes_remaining):
        total_size = stream.filesize
        percent_complete = int((1 - bytes_remaining / total_size) * 100)
        self.progress.emit(percent_complete)
    
    def on_complete(self, stream, file_path):
        self.progress.emit(100)
        self.download_complete.emit(True)

class DownloadAudioThread(QThread):
    progress = Signal(int)
    download_complete = Signal(bool)

    def __init__(self, url, output_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.output_path = output_path
        self.audio_path=""

    def run (self):
        yt = YouTube(self.url, on_progress_callback=self.on_progress, on_complete_callback=self.on_complete)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            audio_file_name = f"audio_{yt.title}.mp3"
            self.audio_path = audio_stream.download(output_path=self.output_path, filename=audio_file_name, max_retries=10)
        else:
            self.progress.emit(0)
            self.download_complete.emit(False)
    
    def on_progress(self, stream, chunk, bytes_remaining ):
        total_size = stream.filesize
        percent_complete = int((1 - bytes_remaining / total_size) * 100)
        self.progress.emit(percent_complete)

    def on_complete(self, stream, file_path):
        self.progress.emit(100)
        self.download_complete.emit(True)