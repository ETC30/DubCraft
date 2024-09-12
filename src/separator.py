from PySide6.QtCore import QThread, Signal
from moviepy.editor import VideoFileClip

class Separator(QThread):
    
    finished_signal = Signal(str, str)
    
    def __init__(self, video_path, output_path):
        super().__init__()
        self.video_path = video_path
        self.output_path = output_path
    
    def run(self):
        try:
            video = VideoFileClip(self.video_path)
            audio = video.audio
            title = self.video_path.split("/")[-1]
            title = title.split(".")[0]
            audio_output_path = f"{self.output_path}/audio_{title}.mp3"
            audio.write_audiofile(audio_output_path)
            only_video = video.without_audio()
            video_output_path = f"{self.output_path}/video_{title}.mp4"
            only_video.write_videofile(video_output_path, codec="libx264")
            
            self.finished_signal.emit(audio_output_path, video_output_path)
        
        except Exception as e:
            print(f"Error during processing: {e}")
