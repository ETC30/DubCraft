from TTS.api import TTS
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx
import os
from PySide6.QtCore import QThread, Signal
from gui.interface import MainWindow

class Generator(QThread):
    finished_signal = Signal(bool)
    def __init__(self, model, segment_lists, output_path, sample_path, to_lang, maintain_speed_of, generate_AV, video_path ):
        super().__init__()
        self.tts = TTS(model, gpu=True)
        self.segment_lists = segment_lists
        self.output_path = output_path
        self.sample_path = sample_path
        self.to_lang = to_lang
        self.maintain_speed_of = maintain_speed_of
        self.generate_AV = generate_AV
        self.video_path = video_path
    
    def adjust_audio_speed(self, audio_segment, speed_factor):
        
        adjusted_audio = audio_segment._spawn(audio_segment.raw_data, overrides={
        "frame_rate": int(audio_segment.frame_rate * speed_factor)}) # Tiene error puesto que se convierte en un int

        # Cambiar el frame_rate del audio ajustado
        adjusted_audio = adjusted_audio.set_frame_rate(audio_segment.frame_rate)

        return adjusted_audio
    
    def adjust_video_speed(self, video_path, output_path, start_seconds_list, end_seconds_list, speed_factor_list):
        video = VideoFileClip(video_path)
        clips = []
        for start, end, speed_factor in zip(start_seconds_list, end_seconds_list, speed_factor_list):
            clip_segmento = video.subclip(start, end)
            clip_segmento = clip_segmento.fx(vfx.speedx, 1/speed_factor)
            clips.append(clip_segmento)
        final_video = concatenate_videoclips(clips)
        self.video_path = f"{output_path}/adjusted_video.mp4"
        final_video.write_videofile(self.video_path)

    def combine_AV(self, video_path, audio_path, output_path):
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        video_and_audio = video.set_audio(audio)
        video_and_audio.write_videofile(f"{output_path}/final_video.mp4", codec="libx264", audio_codec="aac")
        
    def run(self):
        path = f"{self.output_path}/Output"
        os.mkdir(path)
        # Dobla cada segmento de texto
        for i, text in enumerate(self.segment_lists[1]):
            self.tts.tts_to_file(text=text,
                    file_path = f"{path}/output_{i}.wav",
                    speaker_wav=self.sample_path,
                    language=self.to_lang)
        
        final_audio = AudioSegment.silent(duration=0) # Crear un segmento de silencio como base
        
        speed_factor_list = []
        start_seconds_list = []
        end_seconds_list = []
        # Bucle para medir la duración de cada segmento
        for i, time in enumerate(self.segment_lists[0]):
            time_splited =time.split()
            # Tiempo incial a milisengundos
            start_time_splited = time_splited[0].split(":")
                                #Horas                               #Minutos                           #Segundos                                  #Milisegundos
            start_miliseconds = int(start_time_splited[0])*3600000 + int(start_time_splited[1])*60000 + int(start_time_splited[2].split(",")[0])*1000 + int(start_time_splited[2].split(",")[1])
            start_seconds_list.append(start_miliseconds / 1000)

            # Tiempo final a milisegundos
            end_time_splited = time_splited[2].split(":")
            end_miliseconds = int(end_time_splited[0])*3600000 + int(end_time_splited[1])*60000 + int(end_time_splited[2].split(",")[0])*1000 + int(end_time_splited[2].split(",")[1])
            end_seconds_list.append(end_miliseconds / 1000)
            original_duration = end_miliseconds - start_miliseconds
        
            # Selecciona cada segmento de los generados anteriormente
            segment = AudioSegment.from_wav(f"{path}/output_{i}.wav")

            segment_duration = len(segment)
            speed_factor = segment_duration / original_duration
            speed_factor_list.append(speed_factor)

            if self.maintain_speed_of == 0: # Varía la velocidad del video, mantiene el audio
                segment = AudioSegment.from_wav(f"{path}/output_{i}.wav")
                final_audio += segment
            
            else: # Varía la velocidad del audio, mantiene el video
                # Ajusta la velocidad del segmento para que coincida con la duración del subtítulo
                adjusted_segment = self.adjust_audio_speed(segment, speed_factor)
                final_audio += adjusted_segment

        audio_path = f"{self.output_path}/final_audio.wav"        
        final_audio.export(audio_path, format="wav")
        
        if self.generate_AV:
            if self.maintain_speed_of == 0:
                self.adjust_video_speed(self.video_path, self.output_path, start_seconds_list, end_seconds_list, speed_factor_list)
            self.combine_AV(self.video_path, audio_path, self.output_path)

        self.finished_signal.emit(True)
