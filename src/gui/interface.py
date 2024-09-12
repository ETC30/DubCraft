from PySide6.QtWidgets import (QFileDialog,QFrame,QMainWindow,QToolButton,QComboBox,QProgressBar, QPlainTextEdit,
                               QSpacerItem,QListWidgetItem, QCheckBox, QListWidget, QLineEdit,QLabel,
                               QHBoxLayout, QVBoxLayout, QPushButton, QWidget, QRadioButton, QMessageBox)
from PySide6.QtCore import  Qt, Signal, QSize
from PySide6.QtGui import QIcon, QAction
from separator import Separator
from pytube import YouTube
from pytube.exceptions import RegexMatchError, VideoUnavailable, AgeRestrictedError
from gui.download_thread import DownloadVideoThread, DownloadAudioThread
from SRTvalidator import SRTvalidator
from gui.icons import Icons
from languages import LANGUAGES
from models import TRANSCRIPTION_MODELS, DUBBING_MODELS
import webbrowser
import os
import uuid
import time

class MainWindow(QMainWindow):
    
    is_all_downloaded = Signal (bool, str, str, str, str, tuple)
    stop_process = Signal(bool)

    # Construye la ventana
    def __init__(self):
        super().__init__()
        self.current_version = "1.0.0"
        self.current_url=""
        self.current_output_path=""
        self.current_res=""
        self.current_title=""
        self.current_from_lang=""
        self.current_to_lang=""
        self.current_transcription_model = ""
        self.current_dubbing_model = ""
        self.current_inner_path=""
        self.current_sample_path=""
        self.current_video_path=""
        self.current_audio_path=""
        self.video_done = False
        self.audio_done = False
        self.remove_OT = True
        self.remove_TT = True
        self.remove_OV = True
        self.remove_OA = True
        self.generate_A = True
        self.generate_AV = True
        self.current_process_btn = True
        self.maintain_speed_of = 0
        self.current_mode = 2
        self.init_time = 0
        with open('resources\styles\styles.css','r') as file:
            style = file.read()
        self.inicializarUI()
        self.setStyleSheet(style)
        
    # Inicializa y carga todos los elementos iniciales de la ui
    def inicializarUI(self):
        self.setWindowTitle("DubCraft")
        self.setWindowIcon(QIcon(Icons.main_logo))
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        self.main_layout()
        self.showMaximized()
    
    # Busca la url y mira si es compatible, la guarda en una variable y llama a reset_res
    def search_url(self):
        if self.url_input.text():
            self.url = self.url_input.text()
            try:
                yt = YouTube(self.url)
                self.current_url=self.url
            # Aquí podrías proceder con la descarga o lo que necesites hacer con el video
            except RegexMatchError:
                self.new_list_item("QLabel", "The URL is not a valid YouTube URL.")
            except VideoUnavailable:
                self.new_list_item("QLabel","The video is not available (it may have been deleted, private, etc.).")
            except AgeRestrictedError:
                self.new_list_item("QLabel", "The video is age restricted and cannot be accessed without authentication.")
            except Exception as e:
                self.new_list_item("QLabel", f"An unexpected error occurred: {e}")
            self.current_title = yt.title
            self.video_title.setText(f"YouTube video: <b>{self.current_title}</b>")
            self.reset_res(yt.streams.filter(only_video=True))
            
    # Recibe los streams y crea un conjunto para almacenar las resoluciones, luego genera los items en el combobox
    def reset_res(self,streams):
        self.res_input.clear()
        res_set = set()
        for stream in streams:
            res_set.add(stream.resolution)
        for res in sorted(res_set, reverse=True):
            self.res_input.addItem(res)       
    
    # Actuliza la variable current_res con la resolución de la combobox
    def update_res(self):
        self.current_res = self.res_input.currentText()
        if (self.current_output_path !="") & (self.current_res !=""):
            self.update_main_notification(self.current_title,self.current_output_path,self.current_res)

    # Define la ruta en la que se guardará el video descargado en caso de haberlo
    def set_location_url(self):
            output_path = QFileDialog.getExistingDirectory()
            if output_path:
                self.current_output_path = output_path
                self.update_main_notification(self.current_output_path)

    # Genera la notificación principal
    def update_main_notification(self, location):
        self.new_list_item("QLabel", f"It will be processed in <a href=\"{location}\">{location}</a>")

    # Descarga el video y el audio de un link de YouTube
    def download_audio_video(self):
        if all([self.current_url, self.current_res]) and (self.generate_A_check.isChecked() or self.generate_AV_check.isChecked()):
            self.new_list_item("QLabel", "Downloading from YouTube:")
            self.new_list_item("QProgressBar")
            self.video_progress = 0
            self.audio_progress = 0
            self.video_thread = DownloadVideoThread(self.current_url, self.current_inner_path, self.current_res)
            self.video_thread.progress.connect(self.update_video_progress)
            self.video_thread.download_complete.connect(self.video_state)
            self.audio_thread = DownloadAudioThread(self.current_url,self.current_inner_path)
            self.audio_thread.progress.connect(self.update_audio_progress)
            self.audio_thread.download_complete.connect(self.audio_state)
            self.video_thread.start()
            self.audio_thread.start() 
        else:
            if not self.generate_A_check.isChecked() and not self.generate_AV_check.isChecked():
                self.new_list_item("QLabel","You must generate, at least, one audio file or one video file with audio.")
            else: self.new_list_item("QLabel","You need to enter a URL and a download resolution.") 
            self.switch_start_cancel()
            self.open_url_button.setEnabled(True)
            self.open_file_button.setEnabled(True)   
    
    # Separa el video del audio para comenzar el proceso con un archivo local
    def start_with_local(self):
        if all([self.import_local_text.text()]) and (self.generate_A_check.isChecked() or self.generate_AV_check.isChecked()):
            #separar el audio del video
            self.separator_thread = Separator(self.import_local_text.text(), self.current_inner_path)
            self.separator_thread.finished_signal.connect(self.on_start_with_local_finished)
            self.separator_thread.start()
        else:
            if not self.import_local_text.text(): self.new_list_item("QLabel","You need to enter a local video file.")
            else: self.new_list_item("QLabel","Choose a generate option.")
            self.switch_start_cancel()
            self.open_url_button.setEnabled(True)
            self.open_file_button.setEnabled(True)

    # 
    def on_start_with_local_finished(self, audio_output_path, video_output_path):
        self.current_audio_path = audio_output_path
        self.current_video_path = video_output_path
        self.emit_data()

    # Comprueba la validez del srt introducido
    def validated_srt(self, state, segments=None):
        if state:
            self.segments = segments
            self.emit_data()
        else:
            self.switch_start_cancel()
            self.open_url_button.setEnabled(True)
            self.open_file_button.setEnabled(True)
                                    
    # Analiza si el texto se encuentra en formato .srt y da comienzo al proceso
    def start_with_text(self):
        text = self.text_zone.toPlainText()
        self.srt_validator_thread = SRTvalidator(text)
        self.srt_validator_thread.is_valid.connect(self.validated_srt)
        self.srt_validator_thread.start()
    
    # Da comienzo a la descarga
    def start_process(self):
        if self.current_output_path and self.current_sample_path:
            self.init_time = time.time()
            self.new_list_item("QLabel", "The process has begun. The time depends on the performance of your computer. Be patient.")
            self.open_url_button.setEnabled(False)
            self.open_file_button.setEnabled(False)
            self.current_from_lang = LANGUAGES[self.from_language_combo.currentText()]
            self.current_to_lang = LANGUAGES[self.to_language_combo.currentText()]
            self.current_transcription_model = TRANSCRIPTION_MODELS[self.transcriber_combo.currentText()]
            self.current_dubbing_model = DUBBING_MODELS[self.dubbing_combo.currentText()]
            self.remove_OT = not self.preserve_OT_check.isChecked()
            self.remove_TT = not self.preserve_TT_check.isChecked()
            self.remove_OV = not self.preserve_OV_check.isChecked()
            self.remove_OA = not self.preserve_OA_check.isChecked()
            self.generate_A = self.generate_A_check.isChecked()
            self.generate_AV = self.generate_AV_check.isChecked()
            self.maintain_speed_of = self.speed_combo.currentIndex()
            if self.radio_text.isChecked(): self.current_mode = 0
            if self.radio_local.isChecked(): self.current_mode = 1
            if self.radio_url.isChecked(): self.current_mode = 2
            self.current_inner_path = self.current_output_path + "/" + "YouTranslator_" + str(uuid.uuid4()) 
            os.mkdir(self.current_inner_path)
            try:
                self.switch_start_cancel()
                match self.current_mode:
                    case 0: self.start_with_text()
                    case 1: self.start_with_local()
                    case 2: self.download_audio_video()

            except Exception as e:
                self.new_list_item("QLabel", f"An unexpected error occurred: {e}")
                self.switch_start_cancel()
                self.open_url_button.setEnabled(True)
                self.open_file_button.setEnabled(True)
        else:
            self.new_list_item("QLabel", "Please, choose an output folder and your sample voice.")
    
    # Cambia el botón de start a cancel y viceversa
    def switch_start_cancel(self):
        if self.current_process_btn == True:
            self.start_button.setIcon(QIcon(Icons.cancel_process))
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self.cancel_process)
            self.current_process_btn = False
        else:
            self.start_button.setIcon(QIcon(Icons.start_process))
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self.start_process)
            self.current_process_btn = True

    # Actualiza la variable que permite cancelar el proceso
    def cancel_process(self):
        self.stop_process.emit(True)
        print("Process cancelled!")

    # Comprobar si la descarga de video ha terminado
    def video_state(self,state):
        self.video_done = state
        self.emit_data()

    # Comprobar si la descarga de video ha terminado
    def audio_state(self,state):
        self.audio_done = state
        self.emit_data()

    # Se emite la información necesaria para comenzar el proceso
    def emit_data(self):
        if self.current_mode == 0:
            self.is_all_downloaded.emit(True, self.current_inner_path, self.current_sample_path, None, None, self.segments)

        if self.current_mode == 1:
            self.is_all_downloaded.emit(True, self.current_inner_path, self.current_sample_path, self.current_video_path, self.current_audio_path, None)

        if self.current_mode == 2 and self.video_done and self.audio_done:
            self.is_all_downloaded.emit(True, self.current_inner_path, self.current_sample_path, self.video_thread.video_path, self.audio_thread.audio_path, None)

    #Recibe el valor del signal y actualiza el progreso de la descarga del video
    def update_video_progress(self, value):
        self.video_progress = value
        self.update_progress_bar()

    #Recibe el valor del signal y actualiza el progreso de la descarga del audio
    def update_audio_progress(self, value):
        self.audio_progress = value
        self.update_progress_bar()

    #Recibe el progreso dd la descarga del audio y el video y hace su media para actualizar la progress_bar
    def update_progress_bar(self):
        if hasattr(self, 'progress_bar'):
            progress = (self.audio_progress + self.video_progress) / 2
            self.progress_bar.setValue(progress)

    # Abre el explorador de archivos para cargar la ruta del video o el texto del archivo srt
    def open_general_file(self):
        filters = "File (*.srt *.txt *.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.mpg *.mpeg *.3gp)"
        local_path, _ = QFileDialog.getOpenFileName(self,"","", filters)
        extension = local_path.rsplit(".", 1)[-1].lower()
        if extension == "srt" or extension == "txt":
            try:
                with open(local_path,'r', encoding='utf-8') as file:
                    self.text_zone.setPlainText(file.read())
            except Exception as e:
                self.new_list_item("QLabel", f"Error al leer el archivo: {e}")
        else:
            self.import_local_text.setText(local_path)

    # Abre el explorador de archivos para cargar la ruta del video
    def open_video_file(self):
        video_filters = "Video file (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.mpg *.mpeg *.3gp)"
        local_path,_ = QFileDialog.getOpenFileName(self,"","",video_filters)
        self.import_local_text.setText(local_path)

    #Abre el explorar de archivos para cargar la ruta de la muestra de audio
    def open_sample(self):
        self.current_sample_path,_ = QFileDialog.getOpenFileName(self,"","","Audio file (*.mp3 *.wav)")
        if self.current_sample_path != "": self.import_sample_line.setText(self.current_sample_path)

    #Añade items a la lista
    def new_list_item (self, widget_type, text=""):
        """
        Add a new item to the notification list

        widget_type (str): ""QLabel", "QProgressBar"

        text (str): Text to print if widget_type is a QLabel

        """
        #Nueva etiqueta
        if widget_type == "QLabel":
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("border: 1px solid black; padding: 2px; margin-bottom: 2px; margin-right: 1px")
            label.setOpenExternalLinks(False)
            label.linkActivated.connect(self.open_location)
            item = QListWidgetItem()
            item.setSizeHint(label.sizeHint())
            self.notification_zone.addItem(item)
            self.notification_zone.setItemWidget(item, label)
        #Nueva barra de progreso
        if widget_type == "QProgressBar":
            self.progress_bar = QProgressBar()
            item = QListWidgetItem()
            self.notification_zone.addItem(item)
            self.notification_zone.setItemWidget(item, self.progress_bar)
        self.notification_zone.scrollToBottom()

    #Cambia entre los idiomas de los combobox
    def swap_language(self):
        current_from_lang = self.from_language_combo.currentText()
        current_to_lang = self.to_language_combo.currentText()
        self.from_language_combo.setCurrentText(current_to_lang)  
        self.to_language_combo.setCurrentText(current_from_lang) 

    #Abre el explorador al pulsar sobre la dirección del label
    def open_location (self,path):
        webbrowser.open(path)

    # Define las acciones cuando se selecciona un radio button
    def on_radio_button_toggled(self):
        # Verificar cuál radio button está seleccionado
        if self.radio_text.isChecked():
            self.text_zone_title.setEnabled(True)
            self.import_local_title.setDisabled(True)
            self.video_title.setDisabled(True)

            self.preserve_OA_check.setDisabled(True)
            self.preserve_OV_check.setDisabled(True)
            self.preserve_OT_check.setDisabled(True)
            self.generate_AV_check.setDisabled(True)
            self.generate_A_check.setChecked(True)
            self.generate_A_check.setDisabled(True)
            self.transcriber_combo.setDisabled(True)
            self.speed_combo.setCurrentIndex(0)
            self.speed_combo.setDisabled(True)

        elif self.radio_local.isChecked():
            self.import_local_title.setEnabled(True)
            self.text_zone_title.setDisabled(True)
            self.video_title.setDisabled(True)

            self.preserve_OA_check.setDisabled(False)
            self.preserve_OV_check.setDisabled(False)
            self.preserve_OT_check.setDisabled(False)
            self.generate_AV_check.setDisabled(False)
            self.generate_A_check.setDisabled(False)
            self.transcriber_combo.setDisabled(False)
            self.speed_combo.setDisabled(False)

        elif self.radio_url.isChecked():
            self.video_title.setEnabled(True)
            self.import_local_title.setDisabled(True)
            self.text_zone_title.setDisabled(True)

            self.preserve_OA_check.setDisabled(False)
            self.preserve_OV_check.setDisabled(False)
            self.preserve_OT_check.setDisabled(False)
            self.generate_AV_check.setDisabled(False)
            self.generate_A_check.setDisabled(False)
            self.transcriber_combo.setDisabled(False)
            self.speed_combo.setDisabled(False)

    def show_about(self):
        QMessageBox.about(self, "About YouTranslator", 
            f"Version: {self.current_version}\n"
            "Autor: Enrique Tizón\n\n"
            "This application allows you to translate and dub videos entered from your computer or from a YouTube link, as well as translate and dub an SRT subtitle file. It has several models available and a lot of languages."
        )

    
    #Se definen todos lo widgets de la interfaz
    def main_layout(self):

        menu_bar = self.menuBar()
        # Añadir un menú a la barra de menú
        file_menu = menu_bar.addMenu("File")
        # Crear una acción para el menú
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_general_file)  # Conectar la acción a un método
        # Añadir la acción al menú
        file_menu.addAction(open_action)

        settings_action = QAction ("Settings", self)
        menu_bar.addAction(settings_action)
        
        help_menu = menu_bar.addMenu("Help")
        check_updates_action = QAction ("Check for updates", self)
        help_menu.addAction(check_updates_action)
        license_action = QAction ("License", self)
        help_menu.addAction(license_action)
        about_action = QAction ("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

            #Vertical Layout izquierdo
        left_Vlayout=QVBoxLayout()

        #Añade la zona de entrada de texto
        self.text_zone_title = QLabel("Text in .srt format")
        self.text_zone_title.setFixedHeight(24)
        self.text_zone_title.setStyleSheet("font-size: 20px;")
        left_Vlayout.addWidget(self.text_zone_title)

        self.text_zone = QPlainTextEdit()
        self.text_zone.setPlaceholderText("For example:\n1\n00:00:00,000 --> 00:00:06,200\nYour firts line\n\n2\n00:00:06,200 --> 00:00:10,500\nYour second line")
        self.text_zone.setFixedHeight(500)
        left_Vlayout.addWidget(self.text_zone)

        self.import_local_title = QLabel("Local video:")
        self.import_local_title.setAlignment(Qt.AlignVCenter)
        self.import_local_title.setFixedHeight(24)
        self.import_local_title.setStyleSheet("font-size: 20px;")
        left_Vlayout.addWidget( self.import_local_title)

        import_local_Hlayout = QHBoxLayout()

        import_local_info = QLabel("Import a local video file:")
        import_local_Hlayout.addWidget(import_local_info)

        self.import_local_text = QLineEdit()
        self.import_local_text.setReadOnly(True)
        import_local_Hlayout.addWidget(self.import_local_text)
        
                                       #Bóton
        #Añade el botón para abrir el archivo
        self.open_file_button = QPushButton()
        self.open_file_button.setIcon(QIcon(Icons.load_file))
        self.open_file_button.setIconSize(QSize(30, 30))
        self.open_file_button.setFixedHeight(35)
        self.open_file_button.clicked.connect(self.open_video_file)
        import_local_Hlayout.addWidget(self.open_file_button)
        
        import_local_container = QWidget()
        import_local_container.setLayout(import_local_Hlayout)
        left_Vlayout.addWidget(import_local_container)

        #Añade el título del video
        self.video_title = QLabel("YouTube video:")
        self.video_title.setAlignment(Qt.AlignVCenter)
        self.video_title.setFixedHeight(24)
        self.video_title.setStyleSheet("font-size: 20px;")
        #font-weight: bold;
        left_Vlayout.addWidget(self.video_title)

            #Layout url y calidad
        left_Hlayout = QHBoxLayout()

        #Añade textbox para la url
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URL from a YouTube video...")
        left_Hlayout.addWidget(self.url_input)

                                        #Bóton
        #Añade el botón de busqueda
        self.search_button=QPushButton()
        self.search_button.setIcon(QIcon(Icons.search_url))
        #self.search_button.setIconSize(QSize(25,25))
        #self.search_button.setFixedHeight(30)
        self.search_button.clicked.connect(self.search_url)
        left_Hlayout.addWidget(self.search_button)

        #Añade un combobox para la calidad
        self.res_input = QComboBox()
        self.res_input.currentIndexChanged.connect(self.update_res)
        left_Hlayout.addWidget(self.res_input)

        #Añade un contenedor para la url y la calidad
        left_Hlayout_container = QWidget()
        #left_Hlayout_container.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)
        left_Hlayout_container.setFixedHeight(40)
        left_Hlayout_container.setLayout(left_Hlayout)
        left_Vlayout.addWidget(left_Hlayout_container)

        #Genera el contenedor del layout izquierdo
        left_container = QWidget()
        left_container.setLayout(left_Vlayout)

        # Generar el layout central
        center_Vlayout = QVBoxLayout()

        top_frame = QFrame()
        top_frame.setFrameShape(QFrame.Box) 
        top_frame.setLineWidth(1)

        top_center_Vlayout = QVBoxLayout(top_frame)

        top_center_title = QLabel("SOURCE FILE")
        top_center_title.setObjectName("top_center_title")
        top_center_title.setAlignment(Qt.AlignHCenter)
        top_center_title.setFixedHeight(20)
        top_center_Vlayout.addWidget(top_center_title)

        self.radio_text = QRadioButton("Dub a text")
        self.radio_local = QRadioButton("Dub a local video")
        self.radio_url = QRadioButton("Dub a Youtube video")
        self.radio_text.toggled.connect(self.on_radio_button_toggled)
        self.radio_local.toggled.connect(self.on_radio_button_toggled)
        self.radio_url.toggled.connect(self.on_radio_button_toggled)
        self.radio_url.setChecked(True)
        top_center_Vlayout.addWidget(self.radio_text)
        top_center_Vlayout.addWidget(self.radio_local)
        top_center_Vlayout.addWidget(self.radio_url)


        middle_frame = QFrame()
        middle_frame.setFrameShape(QFrame.Box) 
        middle_frame.setLineWidth(1)
        middle_center_Vlayout = QVBoxLayout(middle_frame)

        middle_center_title = QLabel("MODEL SELECTION")
        middle_center_title.setObjectName("middle_center_title")
        middle_center_title.setAlignment(Qt.AlignHCenter)
        middle_center_title.setFixedHeight(20)
        middle_center_Vlayout.addWidget(middle_center_title)
        spacer = QSpacerItem(0, 3)
        top_center_Vlayout.addItem(spacer)
        # Etiqueta de elección del modelo de trasncripción
        transcribe_model_label = QLabel("Transcriber model:")
        transcribe_model_label.setObjectName("transcribe_model_label")
        transcribe_model_label.setAlignment(Qt.AlignCenter)
        middle_center_Vlayout.addWidget(transcribe_model_label)

        # ComboBox para seleccionar el modelo de transcripción
        self.transcriber_combo = QComboBox()
        for i in TRANSCRIPTION_MODELS.keys():
            self.transcriber_combo.addItem(i)
        middle_center_Vlayout.addWidget(self.transcriber_combo)

        # Etiqueta de elección del modelo de doblaje
        dubbing_model_label = QLabel("Dubbing model:")
        dubbing_model_label.setObjectName("dubbing_model_label")
        dubbing_model_label.setAlignment(Qt.AlignCenter)
        middle_center_Vlayout.addWidget(dubbing_model_label)

        self.dubbing_combo = QComboBox()
        for i in DUBBING_MODELS.keys():
            self.dubbing_combo.addItem(i)
        middle_center_Vlayout.addWidget(self.dubbing_combo)

        import_sample_title = QLabel("Enter a sample:")
        import_sample_title.setObjectName("import_sample_title")
        import_sample_title.setAlignment(Qt.AlignCenter)
        middle_center_Vlayout.addWidget(import_sample_title)

        import_sample_Hlayout = QHBoxLayout()
        self.import_sample_line = QLineEdit()
        self.import_sample_line.setReadOnly(True)
        import_sample_Hlayout.addWidget(self.import_sample_line)
        self.import_sample_button = QToolButton()
        self.import_sample_button.setText("...")
        self.import_sample_button.clicked.connect(self.open_sample)
        import_sample_Hlayout.addWidget(self.import_sample_button)
        import_sample_container = QWidget()
        import_sample_container.setLayout(import_sample_Hlayout)
        middle_center_Vlayout.addWidget(import_sample_container)

        bottom_frame = QFrame(self)
        bottom_frame.setFrameShape(QFrame.Box)
        bottom_frame.setLineWidth(1)

        bottom_center_Vlayout = QVBoxLayout(bottom_frame)
        bottom_center_title = QLabel("PROCESS OPTIONS")
        bottom_center_title.setObjectName("bottom_center_title")
        bottom_center_title.setAlignment(Qt.AlignCenter)
        bottom_center_title.setFixedHeight(20)
        bottom_center_Vlayout.addWidget(bottom_center_title)
        self.preserve_OT_check = QCheckBox("Preserve original transcript")
        self.preserve_OT_check.setObjectName("preserve_OT_check")
        bottom_center_Vlayout.addWidget(self.preserve_OT_check)
        self.preserve_TT_check = QCheckBox("Preserve translated transcript")
        bottom_center_Vlayout.addWidget(self.preserve_TT_check)
        self.preserve_OV_check = QCheckBox("Preserve original video")
        bottom_center_Vlayout.addWidget(self.preserve_OV_check)
        self.preserve_OA_check = QCheckBox("Preserve original audio")
        bottom_center_Vlayout.addWidget(self.preserve_OA_check)
        self.generate_A_check = QCheckBox("Generate audio")
        bottom_center_Vlayout.addWidget(self.generate_A_check)
        self.generate_AV_check = QCheckBox("Generate video with audio")
        bottom_center_Vlayout.addWidget(self.generate_AV_check)
        self.speed_combo = QComboBox()
        self.speed_combo.addItem("Maintain audio speed")
        self.speed_combo.addItem("Maintain video speed")
        bottom_center_Vlayout.addWidget(self.speed_combo)
        
        # Crear el contenedor central
        center_container = QWidget()
        center_Vlayout.addWidget(top_frame)
        center_Vlayout.addWidget(middle_frame)
        center_Vlayout.addWidget(bottom_frame)
        center_Vlayout.setStretchFactor(top_frame, 1)
        center_Vlayout.setStretchFactor(middle_frame, 2)
        center_Vlayout.setStretchFactor(bottom_frame, 3)
        center_container.setLayout(center_Vlayout)

            #Vertical Layout derecho
        right_Vlayout=QVBoxLayout()

                                        #Bóton
        #Añade el botón de ajustes
        settings_buttton=QPushButton("Settings")
        settings_buttton.setFixedHeight(50)
        right_Vlayout.addWidget(settings_buttton)

        #Añade un espaciador
        spacer = QSpacerItem(0, 5)
        right_Vlayout.addItem(spacer)
        notification_title = QLabel("Notifications")
        notification_title.setObjectName("notification_title")
        notification_title.setAlignment(Qt.AlignHCenter)
        right_Vlayout.addWidget(notification_title)

        #Añade la ventana para mostrar las notificaciones
        self.notification_zone = QListWidget()
        self.notification_zone.setObjectName("notification_zone")
        self.notification_zone.setContentsMargins(0,0,0,10)
        right_Vlayout.addWidget(self.notification_zone)

        #Añade un espaciador
        right_Vlayout.addItem(spacer)

        #Añade un HLayout para los combobox de los idiomas
        right_Hlayout_1 = QHBoxLayout()

        #Añade el combobox del idioma de partida
        self.from_language_combo = QComboBox()
        for i in LANGUAGES.keys():
            self.from_language_combo.addItem(i)
        right_Hlayout_1.addWidget(self.from_language_combo)
                                                #Botón
        #Añade el botón de intercambio de idiomas
        self.swap_language_button = QToolButton()
        self.swap_language_button.setIcon(QIcon(Icons.change_lang))
        self.swap_language_button.setIconSize(QSize(20, 20))
        self.swap_language_button.clicked.connect(self.swap_language)
        right_Hlayout_1.addWidget(self.swap_language_button)

        #Añade el combobox del idioma final
        self.to_language_combo = QComboBox()
        for i in LANGUAGES.keys():
            self.to_language_combo.addItem(i)
        #self.res_input.currentIndexChanged.connect(self.to_language_combo)
        right_Hlayout_1.addWidget(self.to_language_combo)

        #Añade el container del right_Hlayout_1
        Hcontainer_1 = QWidget()
        Hcontainer_1.setLayout(right_Hlayout_1)
        right_Vlayout.addWidget(Hcontainer_1)

        #right_Hlayout_2
        right_Hlayout_2 = QHBoxLayout()

                                        #Bóton
        #Añade un botón para definir la ubicación donde se descargará el video
        self.open_url_button = QPushButton()
        self.open_url_button.setObjectName("open_url_button")
        self.open_url_button.setIcon(QIcon(Icons.save_file))
        self.open_url_button.setIconSize(QSize(45, 45))
        self.open_url_button.setFixedHeight(50)
        self.open_url_button.clicked.connect(self.set_location_url)
        right_Hlayout_2.addWidget(self.open_url_button)

                                        #Bóton
        #Añade el botón para iniciar el proceso
        self.start_button = QPushButton()
        self.start_button.setIcon(QIcon(Icons.start_process))
        self.start_button.setIconSize(QSize(45, 70))
        self.start_button.setFixedHeight(50)
        self.start_button.clicked.connect(self.start_process)
        right_Hlayout_2.addWidget(self.start_button)

        right_Hlayout_2.setContentsMargins(0,0,0,0)

        #Crea un contenedor para los botones
        Hcontainer_2 = QWidget()
        Hcontainer_2.setLayout(right_Hlayout_2)
        right_Vlayout.addWidget(Hcontainer_2)

                                       
        #Genera el contenedor del layout derecho
        right_container = QWidget()
        right_container.setLayout(right_Vlayout)

            #Generar layout principal que contendrá los otros dos layouts
        main_layout = QHBoxLayout()
        main_spacer = QSpacerItem(2,0)
        main_layout.addWidget(left_container)
        main_layout.addItem(main_spacer)
        main_layout.addWidget(center_container)
        main_layout.addItem(main_spacer)
        main_layout.addWidget(right_container)

        #Ajusta la relación de espacio ocupado por ambos layouts
        main_layout.setStretchFactor(left_container, 4)
        main_layout.setStretchFactor(right_container, 1)

        #Se define el container (widget) principal que contendra los otros dos containers
        main_container = QWidget()
        main_container.setLayout(main_layout)
        self.setCentralWidget(main_container)