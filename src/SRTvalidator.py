import re
from PySide6.QtCore import QThread, Signal

class SRTvalidator(QThread):
    is_valid = Signal(bool, tuple)
    error_signal = Signal(str)  # Signal para enviar errores a la GUI
    
    def __init__(self, srt_text):
        super().__init__()
        self.srt_text = srt_text
        
    def run(self):
        time_format = re.compile(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}")
        blocks = self.srt_text.strip().split("\n\n")
        segments_time = []
        segments_text = []

        for i, block in enumerate(blocks):
            lines = block.splitlines()
            
            if len(lines) < 3:
                self.error_signal.emit(f"Error in block {i}: there are not enough lines.")
                self.is_valid.emit(False, None)
                return
            
            if not lines[0].isdigit():
                self.error_signal.emit(f"Error in block {i}: the identification number is not valid.")
                self.is_valid.emit(False, None)
                return
            
            if not time_format.match(lines[1]):
                self.error_signal.emit(f"Error in block {i}: time format is not valid.")
                self.is_valid.emit(False, None)
                return
            else:
                segments_time.append(lines[1])
            
            if len(lines[2]) == 0:
                self.error_signal.emit(f"Error in block {i}: text format is not correct.")
                self.is_valid.emit(False, None)
                return
            else:
                segments_text.append(lines[2])

        segments = (segments_time, segments_text)
        self.is_valid.emit(True, segments)
