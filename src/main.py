import sys
import os
import shutil
import time
from translator import Translator
from PySide6.QtWidgets import QApplication
from gui.interface import MainWindow
from transcriber import Transcriber
from generator import Generator

def emit_progress (progress):
    window.progress_bar.setValue(progress)

def start_process(isDownloaded):
    if isDownloaded:

        if window.current_mode == 0:
            try:   
                translate(window.segments)
            except Exception as e:
                window.switch_start_cancel()
                window.open_file_button.setEnabled(True)
                window.open_url_button.setEnabled(True)
                window.new_list_item("QLabel", f"An unexpected error occurred: {e}")

        if window.current_mode == 1 or window.current_mode == 2:
            try:
                transcribe()
            except Exception as e:
                window.switch_start_cancel()
                window.open_file_button.setEnabled(True)
                window.open_url_button.setEnabled(True)
                window.new_list_item("QLabel", f"An unexpected error occurred: {e}")

def transcribe():
    global transcriptor_thread
    transcriptor_thread = Transcriber(window.current_transcription_model, window.current_audio_path, window.current_inner_path, window.current_from_lang)
    transcriptor_thread.transcription_progress.connect(emit_progress)
    transcriptor_thread.finished_signal.connect(translate)
    window.new_list_item("QProgressBar")

    try:
        transcriptor_thread.start()
    except Exception as e:
        window.switch_start_cancel()
        window.open_file_button.setEnabled(True)
        window.open_url_button.setEnabled(True)
        window.new_list_item("QLabel", f"An unexpected error occurred: {e}")

def translate(segment_lists):
    global translator_thread
    translator_thread = Translator(segment_lists, window.current_inner_path, window.current_from_lang, window.current_to_lang)
    translator_thread.finished_signal.connect(generate_final_files)
    try:
        translator_thread.start()
    except Exception as e:
        window.switch_start_cancel()
        window.open_file_button.setEnabled(True)
        window.open_url_button.setEnabled(True)
        window.new_list_item("QLabel", f"An unexpected error occurred: {e}")
    
def generate_final_files(segment_lists):
    global generator_thread
    generator_thread = Generator(window.current_dubbing_model, segment_lists, window.current_inner_path, window.current_sample_path, window.current_to_lang, window.maintain_speed_of, window.generate_AV, window.current_video_path)
    generator_thread.finished_signal.connect(remove_files)  
    try:
        generator_thread.start()
    except Exception as e:
        window.switch_start_cancel()
        window.open_file_button.setEnabled(True)
        window.open_url_button.setEnabled(True)
        window.new_list_item("QLabel", f"An unexpected error occurred: {e}")
    
def remove_files(is_generated):
    if is_generated:
        shutil.rmtree(f"{window.current_inner_path}/Output")
        if window.current_mode == 0:
            if window.remove_TT: os.remove(f"{window.current_inner_path}/Translated_transcript.srt")
        else:
            if window.remove_OT: os.remove(f"{window.current_inner_path}/Original_transcription.srt")
            if window.remove_TT: os.remove(f"{window.current_inner_path}/Translated_transcript.srt")                       
            if window.remove_OA: os.remove(f"{window.current_inner_path}")
            #!!if window.remove_OV: os.remove(f"{window.current_video_path}")
            if not window.generate_A: os.remove(f"{window.current_inner_path}/final_audio.wav")
        finishing_actions()

def finishing_actions():
    window.new_list_item("QLabel", "The process has been completed successfully!")
    seconds = time.time() - window.init_time
    hours = int (seconds // 3600)
    mins = int ((seconds % 3600) // 60)
    rem_reconds = seconds % 60 
    window.new_list_item("QLabel", f"Total time was {hours}h:{mins}m:{rem_reconds}s")
    window.switch_start_cancel()
    window.open_file_button.setEnabled(True)
    window.open_url_button.setEnabled(True)

def stop_thread(state):
    if state:
        if transcriptor_thread in globals():
            if transcriptor_thread.isRunning(): transcriptor_thread.exit(0)
        if translator_thread in globals():
            if translator_thread.isRunning(): translator_thread.exit(0)
        if generator_thread in globals():
            if generator_thread.isRunning(): generator_thread.exit(0)

def main():
    global window
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.is_all_downloaded.connect(start_process)
    window.stop_process.connect(stop_thread)
    

    sys.exit(app.exec())


if __name__ == "__main__":
    main()