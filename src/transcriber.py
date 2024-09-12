import whisper
import torch
import os
from PySide6.QtCore import QThread, Signal

class Transcriber(QThread):
    finished_signal = Signal(tuple)
    transcription_progress = Signal(int)
    #modelos disponibles: "tiny","base", "small", "medium", "large"
    def __init__(self, model, audio_path, output_path, language):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model, self.device)
        self.audio_path = audio_path
        self.output_path = output_path
        self.language = language
        self.segments_time = []
        self.segments_texts = []
        
    def run(self):
        # Transcribir el archivo de audio
        result = self.model.transcribe(self.audio_path, language=self.language)
        
        # Crear el contenido en formato SRT
        srt_content = ""
        total = len(result['segments'])
        
        for i, segment in enumerate(result['segments']):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()
            # Convertir el tiempo a formato SRT (HH:MM:SS,mmm)
            start_time_srt = self.time_format_srt(start_time)
            end_time_srt = self.time_format_srt(end_time)
            # Añadir el string de tiempo a la lista de tiempos
            self.segments_time.append(f"{start_time_srt} --> {end_time_srt}")
            # Añadir el string de texto a la lista de textos
            self.segments_texts.append(text)
            # Añadir el segmento al contenido SRT
            srt_content += f"{i+1}\n{self.segments_time[i]}\n{text}\n\n"
            self.transcription_progress.emit((i+1)/total)

        # Guardar la transcripción en formato SRT
        complete_path = os.path.join(self.output_path, "Original_transcription.srt")
        with open(complete_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        segment_list = self.segments_time, self.segments_texts
        self.finished_signal.emit(segment_list)
        
    def time_format_srt(self,seconds):
        """Convierte el tiempo en segundos al formato SRT: HH:MM:SS,mmm"""
        hours = int (seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"
        