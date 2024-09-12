from transformers import MarianMTModel, MarianTokenizer
import os
from PySide6.QtCore import QThread, Signal

class Translator(QThread):
    finished_signal = Signal(tuple)
    def __init__(self, segment_lists, output_path, src_lang,tgt_lang):
        super().__init__()
        model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        self.model = MarianMTModel.from_pretrained(model_name)
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.segment_lists = segment_lists
        self.output_path = output_path

    def run(self):
        #Lista de tokens del texto completo
        srt_translated=""

        for i, text in enumerate(self.segment_lists[1]):
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            segment_translated = self.model.generate(**inputs)
            # Sobreescribe el texto original de cada segmento con el texto traducido
            self.segment_lists[1][i] = self.tokenizer.decode(segment_translated[0],skip_special_tokens=True)
            srt_translated += f"{i+1}\n{self.segment_lists[0][i]}\n{self.segment_lists[1][i]}\n\n"

        complete_path = os.path.join(self.output_path, "Translated_transcript.srt")
        with open(complete_path, "w", encoding="utf-8") as f:
            f.write(srt_translated)

        self.finished_signal.emit(self.segment_lists) # Emite las listas de segmentos traducidos