import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import threading
import os
import sys
import io
import time

from ssh_client import SSHClient
from audio_module import AudioModule
from audio_analyzer import AudioAnalyzer


class RemoteHostApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Host Manager")
        self.default_width = 1920
        self.default_height = 1080
        self.root.geometry(f"{self.default_width}x{self.default_height}")

        # Default settings
        self.default_aspect_ratio = (16, 9) # only support 16:9 aspect ratio
        self.min_width = 640
        self.max_width = 1920  # Maximum width for the window
        self.default_speaker = "rockchipad82178"
        self.default_mic = "vibemicarray"

        self.default_font_size = 12
        self.language = "en"  # Default language is English

        # SSH connection information
        self.ssh_client = None
        self.audio_module = None
        self.audio_analyzer = None
        self.hostname = "192.168.50.53"
        self.username = "root"
        self.password = "test0000"

        # Create navigation bar (Notebook)
        self.navbar = ttk.Notebook(self.root)
        self.navbar.pack(fill="both", expand=True)

        # Page 1 - SSH connection information
        self.page_home = ttk.Frame(self.navbar)
        self.navbar.add(self.page_home, text=self.get_text("SSH"))

        # Page 3 - File management (Upload/Download)
        self.page_flies = ttk.Frame(self.navbar)
        self.navbar.add(self.page_flies, text=self.get_text("Files"))

        # Page 4 - Audio recording/playback
        self.page_aduios = ttk.Frame(self.navbar)
        self.navbar.add(self.page_aduios, text=self.get_text("Audio"))

        # Page 5 - Video recording/playback
        self.page_videos = ttk.Frame(self.navbar)
        self.navbar.add(self.page_videos, text=self.get_text("Video"))

        # Page 6 - Settings page
        self.page_setings = ttk.Frame(self.navbar)
        self.navbar.add(self.page_setings, text=self.get_text("Settings"))

        # Setup pages
        self.setup_page_home()
        self.setup_page_flies()
        self.setup_page_aduios()
        self.setup_page_videos()
        self.setup_page_setings()

    def setup_page_home(self):
        # Clear page elements
        for widget in self.page_home.winfo_children():
            widget.destroy()

        # Configure row and column weights for page_home to enable resizing
        for i in range(10):  # enough rows
            self.page_home.grid_rowconfigure(i, weight=1)
        for j in range(8):   # enough columns
            self.page_home.grid_columnconfigure(j, weight=1)

        # Top label
        label = tk.ttk.Label(self.page_home, text=self.get_text("Home Page"),
                            font=("Arial", self.default_font_size))
        label.grid(row=0, column=0, columnspan=8, pady=10, sticky="nsew")

        # ssh_frame container and layout configuration
        ssh_frame = tk.Frame(self.page_home, relief=tk.GROOVE, borderwidth=2)
        ssh_frame.grid(row=1, column=0, columnspan=2, rowspan=9,
                    padx=10, pady=10, sticky="nsew")
        # Configure grid weights inside ssh_frame
        for i in range(10):
            ssh_frame.grid_rowconfigure(i, weight=1)
        for j in range(2):
            ssh_frame.grid_columnconfigure(j, weight=1)

        # Hostname label and entry
        tk.Label(ssh_frame, text=self.get_text("Hostname: ")).grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.hostname_entry = tk.Entry(ssh_frame)
        self.hostname_entry.insert(tk.END, self.hostname)
        self.hostname_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Username label and entry
        tk.Label(ssh_frame, text=self.get_text("Username: ")).grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        self.username_entry = tk.Entry(ssh_frame)
        self.username_entry.insert(tk.END, self.username)
        self.username_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Password label and entry
        tk.Label(ssh_frame, text=self.get_text("Password: ")).grid(
            row=2, column=0, sticky="w", padx=5, pady=5)
        self.password_entry = tk.Entry(ssh_frame, show="*")
        self.password_entry.insert(tk.END, self.password)
        self.password_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Connect button
        self.connect_button = tk.Button(ssh_frame, text=self.get_text("Connect"), command=self.connect_to_ssh)
        self.connect_button.grid(row=3, column=0, pady=10, sticky="ew", padx=5)
        
        # Disconnect button
        self.disconnect_button = tk.Button(ssh_frame, text=self.get_text("Disconn"), command=self.disconnect_from_ssh)
        self.disconnect_button.grid(row=3, column=1, sticky="ew", padx=5, pady=10)

        # Status label
        self.status_label = tk.Label(ssh_frame, text=self.get_text("Status: Not connected"), fg="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10, sticky="nsew", padx=5)

        # Remote Reset button
        reset_button = tk.Button(ssh_frame, text=self.get_text("Remote Reset"), command=self.remote_reset)
        reset_button.grid(row=5, column=0, sticky="ew", padx=5, pady=10)

        # UI Refresh button
        ui_fresh_button = tk.Button(ssh_frame, text=self.get_text("UI Fresh"), command=self.refresh_ui)
        ui_fresh_button.grid(row=5, column=1, sticky="ew", padx=5, pady=10)

        # log_frame and its internal widgets
        self.log_frame = tk.Frame(self.page_home, relief=tk.SUNKEN, borderwidth=2)
        self.log_frame.grid(row=1, column=3, columnspan=5, rowspan=6, padx=10, pady=10, sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_frame, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Redirect stdout to log_text widget
        sys.stdout = self.RedirectText(self.log_text)

        # log_ctl_frame and layout
        log_ctl_frame = tk.Frame(self.page_home)
        log_ctl_frame.grid(row=7, column=3, columnspan=5,
                        padx=10, pady=10, sticky="ew")
        for j in range(3):
            log_ctl_frame.grid_columnconfigure(j, weight=1)

        # Clear logs button
        clear_button = tk.Button(log_ctl_frame, text="Clear Logs",
                                command=self.clear_logs)
        clear_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Save logs button
        save_button = tk.Button(log_ctl_frame, text="Save Logs",
                                command=self.save_logs)
        save_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Save path entry
        self.save_path_entry = tk.Entry(log_ctl_frame)
        self.save_path_entry.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.save_path_entry.insert(0, "/tmp/log.txt")

    def clear_logs(self):
        # Clear the content in the Text widget
        self.log_text.delete(1.0, tk.END)
        print("[INFO]: Logs cleared.")  # This message will appear in the log

    def save_logs(self):
        # Get all the text in the Text widget
        log_content = self.log_text.get(1.0, tk.END)
        if log_content.strip():  # Check if there is any content to save
            try:
                # Get the path from the entry widget
                file_path = self.save_path_entry.get()
                print(f"[INFO]: Saving logs to: {file_path}")  # Log the save path
                if file_path.strip() == "" or file_path == "Enter file path to save logs...":
                    messagebox.showwarning(
                        "Invalid Path", "Please enter a valid file path.")
                    return

                # Save the log content to the specified file path
                with open(file_path, "w") as file:
                    file.write(log_content)
                messagebox.showinfo(
                    "Log Saved", f"Logs have been saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {str(e)}")
        else:
            messagebox.showwarning("No Logs", "There are no logs to save.")

    class RedirectText(io.StringIO):
        def __init__(self, text_widget):
            super().__init__()
            self.text_widget = text_widget

        def write(self, message):
            # Insert the message into the Text widget
            self.text_widget.insert("end", message)
            self.text_widget.yview("end")  # Auto scroll to the end

    def setup_page_flies(self):
        # Clear all widgets on page_flies
        for widget in self.page_flies.winfo_children():
            widget.destroy()

        # Configure grid weights for page_flies for responsiveness
        for i in range(10):  # enough rows
            self.page_flies.grid_rowconfigure(i, weight=1)
        for j in range(2):  # 2 columns enough
            self.page_flies.grid_columnconfigure(j, weight=1)

        # Title label for file operations
        file_operations_label = tk.Label(
            self.page_flies, text=self.get_text("File Upload/Download"),
            font=("Arial", self.default_font_size)
        )
        file_operations_label.grid(row=0, column=0, columnspan=2, pady=10, sticky="nsew")

        # Upload Frame setup
        upload_frame = tk.LabelFrame(
            self.page_flies, text="Upload File", padx=10, pady=10
        )
        upload_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # Configure grid inside upload_frame
        for i in range(3):
            upload_frame.grid_rowconfigure(i, weight=1)
        upload_frame.grid_columnconfigure(0, weight=0)
        upload_frame.grid_columnconfigure(1, weight=1)

        # Upload button
        upload_button = tk.Button(
            upload_frame, text=self.get_text("Upload File"), command=self.upload_file
        )
        upload_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Upload source path label and entry
        update_src_label = tk.Label(upload_frame, text=self.get_text("Source Path:"))
        update_src_label.grid(row=1, column=0, pady=5, sticky="e")
        self.upload_entry_src = tk.Entry(upload_frame)
        self.upload_entry_src.insert(tk.END, "./tmp/")  # Default source path
        self.upload_entry_src.grid(row=1, column=1, pady=5, sticky="ew")

        # Upload destination path label and entry
        update_dest_label = tk.Label(upload_frame, text=self.get_text("Destination Path:"))
        update_dest_label.grid(row=2, column=0, pady=5, sticky="e")
        self.upload_entry_dest = tk.Entry(upload_frame)
        self.upload_entry_dest.insert(tk.END, "/root/plays/")  # Default destination path
        self.upload_entry_dest.grid(row=2, column=1, pady=5, sticky="ew")

        # Download Frame setup
        download_frame = tk.LabelFrame(
            self.page_flies, text="Download File", padx=10, pady=10
        )
        download_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # Configure grid inside download_frame
        for i in range(3):
            download_frame.grid_rowconfigure(i, weight=1)
        download_frame.grid_columnconfigure(0, weight=0)
        download_frame.grid_columnconfigure(1, weight=1)

        # Download button
        download_button = tk.Button(
            download_frame, text=self.get_text("Download File"), command=self.download_file
        )
        download_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Download source path label and entry
        download_src_label = tk.Label(download_frame, text=self.get_text("Source Path:"))
        download_src_label.grid(row=1, column=0, pady=5, sticky="e")
        self.download_var = tk.StringVar(value="/root/records/")  # Default destination path
        self.download_combobox_src = ttk.Combobox(download_frame, textvariable=self.download_var)
        self.download_combobox_src.grid(row=1, column=1, pady=5, sticky="ew")

        # Download destination path label and entry
        download_dest_label = tk.Label(download_frame, text=self.get_text("Destination Path:"))
        download_dest_label.grid(row=2, column=0, pady=5, sticky="e")
        self.download_entry_dest = tk.Entry(download_frame)
        self.download_entry_dest.insert(tk.END, "./tmp/")  # Default destination path
        self.download_entry_dest.grid(row=2, column=1, pady=5, sticky="ew")


    def setup_page_aduios(self):
        # Clear page elements
        for widget in self.page_aduios.winfo_children():
            widget.destroy()
        
        #### Configure grid weights for page_aduios to make it responsive
        ### Page-Header
        header_rows = 1
        header_cols = 10
        record_play_label = tk.Label(self.page_aduios, text=self.get_text("Audio"), font=("Arial", self.default_font_size))
        record_play_label.grid(row=0, column=0, rowspan=header_rows, columnspan=header_cols, pady=1, sticky="nsew")
        ### Page-Parameters
        paras_rows = 8
        paras_cols = 4
        self.audio_settings_frame = tk.LabelFrame(self.page_aduios, text="Audio Settings", padx=10, pady=10)
        self.audio_settings_frame.grid(row=header_rows, column=0, rowspan=paras_rows, columnspan=paras_cols, padx=2, pady=1, sticky="nsew")
        ### Page-Recorder
        rec_rows = 4
        rec_clos = 6
        self.record_frame = tk.LabelFrame(self.page_aduios, text="Audio Recorder", padx=10, pady=10)
        self.record_frame.grid(row=header_rows, column=paras_cols, rowspan=rec_rows, columnspan=rec_clos, padx=2, pady=1, sticky="nsew")
        ### Page-Player
        play_rows = 4
        play_cols = 6
        self.play_frame = tk.LabelFrame(self.page_aduios, text="Audio Player", padx=10, pady=10)
        self.play_frame.grid(row=header_rows+rec_rows, column=paras_cols, rowspan=play_rows, columnspan=play_cols, padx=2, pady=1, sticky="nsew")
        ### Page-Analyzer
        ana_rows = 4
        ana_cols = 10
        self.analysis_frame = tk.LabelFrame(self.page_aduios, text="Audio Analyzer", padx=10, pady=10)
        self.analysis_frame.grid(row=header_rows+rec_rows+play_rows, column=0, rowspan=ana_rows, columnspan=ana_cols, padx=2, pady=1, sticky="nsew")
   
        # Configure page_aduios grid layout
        whole_rows = header_rows + paras_rows + ana_rows
        whole_columns = paras_cols + rec_clos 
        for i in range(whole_rows - 1):
            self.page_aduios.grid_rowconfigure(i, weight=1)
        for j in range(whole_columns - 1):  
            self.page_aduios.grid_columnconfigure(j, weight=1)
            
        ## Frame-Header
        pass
        ## Frame-Parameters
        # Configure audio_settings_frame grid layout
        for i in range(paras_rows - 1):
            self.audio_settings_frame.grid_rowconfigure(i, weight=1)
        for j in range(paras_cols - 1):
            self.audio_settings_frame.grid_columnconfigure(j, weight=1)
        
        self.audio_settings_frame.grid_columnconfigure(0, weight=4)
        self.audio_settings_frame.grid_columnconfigure(1, weight=4)
        # Sampling rate settings
        self.sampling_rate_label = tk.Label(self.audio_settings_frame, text="Rate:")
        self.sampling_rate_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.sampling_rate = tk.StringVar(value="48000")
        self.sampling_rate_combobox = ttk.Combobox(self.audio_settings_frame, textvariable=self.sampling_rate,
                                                    values=["8000", "16000", "44100", "48000", "96000"],
                                                    state="readonly")
        self.sampling_rate_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Channels settings
        self.channels_label = tk.Label(self.audio_settings_frame, text="Chns:")
        self.channels_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.channels = tk.StringVar(value="2")
        self.channels_combobox = ttk.Combobox(self.audio_settings_frame, textvariable=self.channels,
                                            values=["1", "2", "6", "8"], state="readonly")
        self.channels_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Data type settings
        self.data_type_label = tk.Label(self.audio_settings_frame, text="Fmt:")
        self.data_type_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.data_type = tk.StringVar(value="S16_LE")
        self.data_type_entry = ttk.Combobox(self.audio_settings_frame, textvariable=self.data_type,
                                            values=["S16_LE", "S24_LE", "S32_LE", "FLOAT_LE"],
                                            state="readonly")
        self.data_type_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # File type selection (wav/pcm)
        self.file_type_label = tk.Label(self.audio_settings_frame, text="Type:")
        self.file_type_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.file_type = tk.StringVar(value="wav")
        self.file_type_combobox = ttk.Combobox(self.audio_settings_frame, textvariable=self.file_type,
                                                  values=["wav", "pcm"], state="readonly")
        self.file_type_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        ## Frame-Recorder
        # Configure record_frame grid layout
        for i in range(rec_rows - 1):
            self.record_frame.grid_rowconfigure(i, weight=1)
        for i in range(rec_clos - 1):
            self.record_frame.grid_columnconfigure(i, weight=1)

        # === Row 0: Device selection and rec duration ===
        # Device
        self.record_device_label = tk.Label(self.record_frame, text="Device:")
        self.record_device_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")  

        self.record_device = tk.StringVar(value="Default")
        self.record_device_combobox = ttk.Combobox(
            self.record_frame, textvariable=self.record_device,
            values=["Default", "menu", "none"], state="readonly"
        )
        self.record_device_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")  

        # Engine
        self.rec_engine_label = tk.Label(self.record_frame, text="Engine:")
        self.rec_engine_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.rec_engine = tk.StringVar(value="alsa")
        self.rec_engine_combobox = ttk.Combobox(
            self.record_frame, textvariable=self.rec_engine,
            values=["alsa", "cras"], state="readonly"
        )
        self.rec_engine_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Duration
        self.rec_dur_label = tk.Label(self.record_frame, text="Duration(s):")
        self.rec_dur_label.grid(row=0, column=4, padx=5, pady=5, sticky="e")

        self.rec_dur = tk.StringVar(value="10")
        self.rec_dur_entry = tk.Entry(self.record_frame, textvariable=self.rec_dur)
        self.rec_dur_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        # === Row 1: Progress Bar ===
        self.record_progress = ttk.Progressbar(self.record_frame, orient="horizontal", length=400, mode="determinate")
        self.record_progress.grid(row=1, column=0, columnspan=6, padx=5, pady=(0, 10), sticky="nsew")
        self.rec_progress_running = False

        # === Row 2: Start/Stop Button + Path Entry ===
        self.record_button = tk.Button(self.record_frame, text=self.get_text("Start Recording"), command=self.toggle_recording)
        self.record_button.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")

        self.rec_path_var = tk.StringVar(value="/root/records/")  # Default path for recording
        self.rec_path_combobox = ttk.Combobox(self.record_frame, textvariable=self.rec_path_var)
        self.rec_path_combobox.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="nsew")

        ## Frame-Player

        # Configure play_frame grid layout
        for i in range(play_rows - 1):
            self.play_frame.grid_rowconfigure(i, weight=1)
        for i in range(play_cols - 1):
            self.play_frame.grid_columnconfigure(i, weight=1)
        # === Row 0: Playback Device Selector + Duration display ===
        # Device
        self.play_deviece_label = tk.Label(self.play_frame, text="Device:")
        self.play_deviece_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.play_device = tk.StringVar(value="Default")
        self.play_device_combobox = ttk.Combobox(
            self.play_frame, textvariable=self.play_device,
            values=["Default", "menu", "none"], state="readonly"
        )
        self.play_device_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Engine
        self.play_engine_label = tk.Label(self.play_frame, text="Engine:")
        self.play_engine_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.play_engine = tk.StringVar(value="cras")
        self.play_engine_combobox = ttk.Combobox(
            self.play_frame, textvariable=self.play_engine,
            values=["alsa", "cras"], state="readonly"
        )
        self.play_engine_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Duration
        self.play_duration_static_label = tk.Label(self.play_frame, text="Duration(s):")
        self.play_duration_static_label.grid(row=0, column=4, padx=5, pady=5, sticky="e")

        self.play_duration_value = tk.StringVar(value="")
        self.play_duration_entry = tk.Entry(self.play_frame, textvariable=self.play_duration_value)
        self.play_duration_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        # === Row 1: Progress Bar ===
        self.play_progress = ttk.Progressbar(self.play_frame, orient="horizontal", length=400, mode="determinate")
        self.play_progress.grid(row=1, column=0, columnspan=6, padx=5, pady=(0, 10), sticky="nsew")
        self.play_progress_running = False

        # === Row 2: Start/Stop Button + File Path Entry ===
        self.play_button = tk.Button(self.play_frame, text=self.get_text("Start Playing"), command=self.toggle_playing)
        self.play_button.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        
        self.plays_file_path_var = tk.StringVar(value="/root/plays/")  # Default path for playback
        self.file_path_combobox = ttk.Combobox(self.play_frame, textvariable=self.plays_file_path_var)
        self.file_path_combobox.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="nsew")

        ## Frame-Analyzer        
        # Configure analysis_frame grid layout
        for i in range(ana_rows - 1):
            self.analysis_frame.grid_rowconfigure(i, weight=1)
        for i in range(ana_cols - 1):
            self.analysis_frame.grid_columnconfigure(i, weight=1)
        self.analysis_frame.grid_columnconfigure(1, weight=3)

        self.analysis_label = tk.Label(self.analysis_frame, text="Analysis Menu:")
        self.analysis_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.analysis_method = tk.StringVar(value="DOA")
        methods = ["PESG", "Reverb", "ANR", "AEC", "Spectrogram", "DOA"]
        self.analysis_method_combobox = ttk.Combobox(self.analysis_frame, textvariable=self.analysis_method, values=methods, state="readonly")
        self.analysis_method_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.analysis_progress = ttk.Progressbar(self.analysis_frame, orient="horizontal", length=400, mode="determinate")
        self.analysis_progress.grid(row=1, column=0, columnspan=4, padx=5, pady=(0, 10), sticky="nsew")
        self.analysis_progress_running = False

        ref_label = tk.Label(self.analysis_frame, text="Reference Audio:")
        ref_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.ref_audio_entry = tk.Entry(self.analysis_frame, width=50)
        self.ref_audio_entry.insert(tk.END, "./plays/ref.wav")
        self.ref_audio_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        target_label = tk.Label(self.analysis_frame, text="Target Audio:")
        target_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        
        self.target_audio_path_var = tk.StringVar(value="./records/")  # Default target audio path
        self.target_audio_combobox = ttk.Combobox(self.analysis_frame, textvariable=self.target_audio_path_var)
        self.target_audio_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Analysis run button
        self.analysis_button = tk.Button(self.analysis_frame, text="Run Analysis", command=self.toggle_analysis)
        self.analysis_button.grid(row=4, column=0, columnspan=2, pady=10)

    def setup_page_videos(self):
        # Clear all widgets on page_videos
        for widget in self.page_videos.winfo_children():
            widget.destroy()

        # Configure grid layout for page_videos
        for i in range(3):
            self.page_videos.grid_rowconfigure(i, weight=1, pad=10)
        self.page_videos.grid_columnconfigure(0, weight=1, pad=10)

        # Title label for video section
        video_record_label = tk.Label(
            self.page_videos,
            text=self.get_text("Video Recording and Playback"),
            font=("Arial", self.default_font_size + 2, "bold")
        )
        video_record_label.grid(row=0, column=0, pady=(20, 10), sticky="n")

        # Button to start recording
        record_video_button = tk.Button(
            self.page_videos,
            text=self.get_text("Start Recording"),
            command=self.record_video,
            width=20
        )
        record_video_button.grid(row=1, column=0, pady=10, sticky="n")

        # Button to play recorded video
        play_video_button = tk.Button(
            self.page_videos,
            text=self.get_text("Play Video"),
            command=self.play_video,
            width=20
        )
        play_video_button.grid(row=2, column=0, pady=10, sticky="n")

    def setup_page_setings(self):
        # Clear all widgets on page_setings
        for widget in self.page_setings.winfo_children():
            widget.destroy()

        # Configure grid weights for page_setings to make it responsive
        for i in range(5):
            self.page_setings.grid_rowconfigure(i, weight=1, pad=5)
        for j in range(4):
            self.page_setings.grid_columnconfigure(j, weight=1, pad=5)

        # Title label for settings
        settings_label = tk.Label(
            self.page_setings, text=self.get_text("Settings"),
            font=("Arial", self.default_font_size + 4, "bold")
        )
        settings_label.grid(row=0, column=0, columnspan=4, pady=(10, 15), sticky="nsew")

        # Parameter frame for better grouping (optional)
        para_frame = tk.Frame(self.page_setings)
        para_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=20)

        # Configure grid inside para_frame
        for i in range(4):
            para_frame.grid_rowconfigure(i, weight=1, pad=8)
        for j in range(4):
            para_frame.grid_columnconfigure(j, weight=1, pad=8)

        # Window size label and entries
        size_label = tk.Label(para_frame, text=self.get_text("Window (WxH):"))
        size_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)

        self.width_entry = tk.Entry(para_frame)
        self.width_entry.insert(tk.END, str(self.default_width))
        self.width_entry.grid(row=0, column=1, sticky="ew", padx=5)

        x_label = tk.Label(para_frame, text="x")
        x_label.grid(row=0, column=2, sticky="ew", padx=0)

        self.height_entry = tk.Entry(para_frame)
        self.height_entry.insert(tk.END, str(self.default_height))
        self.height_entry.grid(row=0, column=3, sticky="ew", padx=5)

        # Font size label and entry
        font_size_label = tk.Label(para_frame, text=self.get_text("Font Size:"))
        font_size_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)

        self.font_size_entry = tk.Entry(para_frame)
        self.font_size_entry.insert(tk.END, str(self.default_font_size))
        self.font_size_entry.grid(row=1, column=1, sticky="ew", padx=5)

        # Language selection label and combobox
        language_label = tk.Label(para_frame, text=self.get_text("Language:"))
        language_label.grid(row=2, column=0, sticky="e", padx=5, pady=5)

        self.language_var = tk.StringVar(value=self.language)
        language_combobox = ttk.Combobox(
            para_frame, textvariable=self.language_var,
            values=["en", "zh"], state="readonly"
        )
        language_combobox.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # Save button centered and spans all columns
        save_button = tk.Button(
            para_frame, text=self.get_text("Save Settings"),
            command=self.save_settings
        )
        save_button.grid(row=3, column=0, columnspan=4, pady=(20, 10), sticky="ew")


    def constraint_window_size(self, new_width, new_height):
        # Ensure the window size maintains the aspect ratio and minimum width
        aspect_ratio = self.default_aspect_ratio[0] / \
            self.default_aspect_ratio[1]
        if new_width < self.min_width:
            new_width = self.min_width
        elif new_width > self.max_width:
            new_width = self.max_width
        new_height = int(new_width / aspect_ratio)
        self.default_width = new_width
        self.default_height = new_height
        return new_width, new_height

    def save_settings(self):
        try:
            new_width = int(self.width_entry.get())
            new_height = int(self.height_entry.get())
            new_font_size = int(self.font_size_entry.get())
            self.language = self.language_var.get()  # Get the selected language

            constrainted_width, constrained_height = self.constraint_window_size(
                new_width, new_height)
            if constrainted_width != new_width or constrained_height != new_height:
                messagebox.showwarning(self.get_text("Warning"), self.get_text(
                    f"Window size has been adjusted to maintain aspect ratio: {constrainted_width}x{constrained_height},"
                    "minimum width is {self.min_width}, maximun width is {self.max_width}"))
            # Update window size and font size
            self.root.geometry(f"{constrainted_width}x{constrained_height}")
            self.default_font_size = new_font_size

            # Update interface language
            self.update_language()

            messagebox.showinfo(self.get_text("Settings Saved"),
                                self.get_text("Settings have been saved!"))
        except ValueError:
            messagebox.showerror(self.get_text(
                "Input Error"), self.get_text("Please enter valid numbers!"))

    def get_text(self, key):
        translations = {
            "en": {
                "SSH": "SSH",
                "Logs": "Logs",
                "Files": "Files",
                "Audio": "Audio",
                "Video": "Video",
                "Settings": "Settings",
                "Enter SSH Info": "Enter SSH Info",
                "Hostname: ": "Hostname: ",
                "Username: ": "Username: ",
                "Password: ": "Password: ",
                "Connect": "Connect",
                "Status: Not connected": "Status: Not connected",
                "File Upload/Download": "File Upload/Download",
                "Upload File": "Upload File",
                "Download File": "Download File",
                "Recording and Playback": "Recording and Playback",
                "Start Recording": "Start Recording",
                "Play Recording": "Play Recording",
                "Video Recording and Playback": "Video Recording and Playback",
                "Save Settings": "Save Settings",
                "Settings Saved": "Settings Saved",
                "Language": "Language",
                "Window Size (Width x Height):": "Window Size (Width x Height):",
                "Font Size:": "Font Size:",
                "Please enter valid numbers!": "Please enter valid numbers!",
                "Input Error": "Input Error",
                "Settings have been saved!": "Settings have been saved!"
            },
            "zh": {
                "SSH": "SSH连接",  # Ensure the key matches exactly
                "Logs": "日志",
                "Files": "文件管理",
                "Audio": "录音",
                "Video": "视频录制",
                "Settings": "设置",
                "Enter SSH Info": "请输入SSH信息",
                "Hostname: ": "主机名: ",
                "Username: ": "用户名: ",
                "Password: ": "密码: ",
                "Connect": "连接",
                "Status: Not connected": "状态: 尚未连接",
                "File Upload/Download": "文件上传/下载",
                "Upload File": "上传文件",
                "Download File": "下载文件",
                "Recording and Playback": "录音与播放",
                "Start Recording": "开始录音",
                "Play Recording": "播放录音",
                "Video Recording and Playback": "视频录制与播放",
                "Save Settings": "保存设置",
                "Settings Saved": "设置保存",
                "Language": "语言",
                "Window Size (Width x Height):": "窗口大小 (宽 x 高):",
                "Font Size:": "字体大小:",
                "Please enter valid numbers!": "请输入有效的数字！",
                "Input Error": "输入错误",
                "Settings have been saved!": "设置已保存！"
            }
        }

        return translations[self.language].get(key, key)

    def update_language(self):
        # Update navigation bar labels when language is changed
        self.navbar.tab(self.page_home, text=self.get_text("SSH"))
        self.navbar.tab(self.page_flies, text=self.get_text("Files"))
        self.navbar.tab(self.page_aduios, text=self.get_text("Audio"))
        self.navbar.tab(self.page_videos, text=self.get_text("Video"))
        self.navbar.tab(self.page_setings, text=self.get_text("Settings"))

        # Reload each page
        self.setup_page_home()
        self.setup_page_flies()
        self.setup_page_aduios()
        self.setup_page_videos()
        self.setup_page_setings()

    def connect_to_ssh(self):
        self.hostname = self.hostname_entry.get()
        self.username = self.username_entry.get()
        self.password = self.password_entry.get()

        try:
            self.ssh_client = SSHClient(
                self.hostname, self.username, self.password)
            if not self.ssh_client.connect():
                raise Exception("SSH connection failed")

            self.status_label.config(text=self.get_text(
                "Status: Connected"), fg="green")
            # Reset remote sever
            self.remote_reset('mute')
            # Update the device and folder menus
            self.update_device_menu()
            self.update_folder_menu()
            # Initialize audio module and analyzer
            self.audio_module = AudioModule(self.ssh_client)
            self.audio_analyzer = AudioAnalyzer(self.audio_module)
        except Exception as e:
            self.status_label.config(text=self.get_text(
                "Status: Connection Failed"), fg="red")
            messagebox.showerror(self.get_text(
                "Connection Error"), f"{self.get_text('Connection Failed')}: {str(e)}")
            
    def disconnect_from_ssh(self):
        if self.ssh_client:
            try:
                self.ssh_client.disconnect()
                self.ssh_client = None
                self.audio_module = None
                self.status_label.config(text=self.get_text("Status: Not connected"), fg="red")
                # messagebox.showinfo(self.get_text("Disconnected"), self.get_text("SSH connection closed."))
            except Exception as e:
                messagebox.showerror(self.get_text("Error"), f"{self.get_text('Disconnection Failed')}: {str(e)}")
        else:
            messagebox.showwarning(self.get_text("Warning"), self.get_text("Not connected to any SSH host."))

    def upload_file(self):
        if self.ssh_client:
            print("[INFO]: Uploading file...") 
            src_path = self.upload_entry_src.get()
            if not os.path.exists(src_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Source file does not exist"))
                print("[ERR]: Source file does not exist") 
                return
            dest_path = self.upload_entry_dest.get()
            if not self.ssh_client.is_dir(dest_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Destination path directory does not exist"))
                print("[ERR]: Destination path directory does not exist") 
                return
            try:
                self.ssh_client.upload_file(src_path, dest_path)
                print("[INFO]: File uploaded successfully") 
                messagebox.showinfo(self.get_text("Success"),
                                    self.get_text("File uploaded successfully"))
            except Exception as e:
                messagebox.showerror(self.get_text("Error"),
                                     f"{self.get_text('File upload failed')}: {str(e)}")
                print("[ERR]: File upload failed: ") + str(e) 
        else:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))

    def download_file(self):
        if self.ssh_client:
            print("[INFO]: Downloading file...") 
            src_path = self.download_entry_src.get()
            if not self.ssh_client.file_exists(src_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Source file does not exist on remote host"))
                print("[ERR]: Source file does not exist on remote host") 
                return
            dest_path = self.download_combobox_src.get()
            if not os.path.isdir(dest_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Destination path does not exist or is not a directory"))
                print("[ERR]: Destination path does not exist or is not a directory") 
                return
            try:
                self.ssh_client.download_file(src_path, dest_path)
                print("[INFO]: File downloaded successfully") 
                messagebox.showinfo(self.get_text("Success"),
                                    self.get_text("File downloaded successfully"))
            except Exception as e:
                messagebox.showerror(self.get_text("Error"),
                                     f"{self.get_text('File download failed')}: {str(e)}")
                print("[ERR]: File download failed: ") + str(e) 
        else:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))
    def toggle_playing(self):
        def stop_playing(self):
            print("[INFO]: Playback stopped") 
            if self.audio_module is not None:
                ret = self.audio_module.stop_playing()
                if ret:
                    # self.play_progress_running = False
                    # self.play_button.config(text=self.get_text("Start Playing"))
                    return True
                else:
                    messagebox.showerror(self.get_text("Error"), self.get_text("Failed to stop playback"))
                    return False
            else:
                messagebox.showerror(self.get_text("Error"), self.get_text("Audio module not initialized"))
                return False
        if self.play_progress_running:
            self.play_button.config(text=self.get_text("Start Playing"))
            self.play_progress_running = False
            self.play_progress.stop()
            stop_playing(self)
        else:
            self.play_button.config(text=self.get_text("Stop Playing"))
            self.play_progress_running = True
            self.audio_player_thread()

    def toggle_recording(self):
        def stop_recording(self):
            print("[INFO]: Recording stopped") 
            if self.audio_module is not None:
                ret = self.audio_module.stop_recording()
                if ret:
                    # self.rec_progress_running = False
                    # self.record_button.config(text=self.get_text("Start Recording"))
                    return True
                else:
                    messagebox.showerror(self.get_text("Error"), self.get_text("Failed to stop recording"))
                    return False
            else:
                messagebox.showerror(self.get_text("Error"), self.get_text("Audio module not initialized"))
                return False
        if self.rec_progress_running:
            self.record_button.config(text=self.get_text("Start Recording"))
            self.rec_progress_running = False
            self.record_progress.stop()
            stop_recording()
        else:
            self.record_button.config(text=self.get_text("Stop Recording"))
            self.rec_progress_running = True
            self.audio_recorder_thread()

    
    def update_progress(self, elapsed, total, progress_bar=None):
        if progress_bar is None:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Progress bar not initialized"))
            return
        if elapsed > total + 1:  # Allow a small buffer for rounding errors
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Elapsed time exceeds total time"))
            return
        percent = int((elapsed / total) * 100)
        progress_bar['value'] = percent

    def audio_recorder(self) -> bool:
        if self.audio_module is None:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Audio module not initialized"))
            return False
        # Check if the recording path is valid
        self.audio_module.paras_settings(
            rate=int(self.sampling_rate.get()),
            channels=int(self.channels.get()),
            audio_format=self.data_type.get(),
            file_type=self.file_type.get(),
            engine=self.rec_engine.get(),
            device=self.record_device.get(),
            rec_sec= int(self.rec_dur.get() or 10)  # Default to 10 seconds if empty
        )
        # Start recording progress
        print("[INFO]: Starting audio recording...") 
        audio_dir_record = self.rec_path_combobox.get()
        if self.ssh_client.is_dir(audio_dir_record):
            # messagebox.showerror(self.get_text("Error"), self.get_text("Recording path is a directory, please specify a file path"))
            print("[INFO]: Recording path is a directory, please specify a file path") 
            return False
        new_audio_dir = audio_dir_record
        ret,new_audio_dir = self.audio_module.record_audio(audio_dir_record)
        if new_audio_dir != audio_dir_record:
            print(f"[WARN]: Audio recorded to {audio_dir_record}") 
            self.rec_path_combobox.set(new_audio_dir)  # Update the path combobox to new recorded file
            messagebox.showinfo(self.get_text("warning"), f"{self.get_text('Audio recorded to')} {audio_dir_record}")
        # download the recorded file to local
        if ret is True:
            print("[INFO]: Downloading recorded audio file to local dir: ./tmp/ ") 
            local_record_path = "./tmp/"
            if not os.path.exists(local_record_path):
                os.makedirs(local_record_path)
            local_record_path = os.path.join(local_record_path, os.path.basename(new_audio_dir))
            try:
                self.ssh_client.download_file(new_audio_dir, local_record_path)
                print(f"[INFO]: Recorded audio file downloaded to {local_record_path}") 
                # messagebox.showinfo(self.get_text("Success"), f"{self.get_text('Recorded audio file downloaded to')} {local_record_path}")
            except Exception as e:
                messagebox.showerror(self.get_text("Error"),
                                     f"{self.get_text('Download failed')}: {str(e)}")
                print("[ERR]: Download failed: ") + str(e) 
        return ret

    def audio_recorder_thread(self):
        total_sec = int(self.rec_dur.get() or 10)

        # Record audio in a separate thread to avoid blocking the UI
        def do_record():
            # Start the progress bar
            start_time = time.time()
            def update():
                update_frequency_ms = 200 
                if not self.rec_progress_running:
                    return
                elapsed = time.time() - start_time
                self.update_progress(elapsed, total_sec, self.record_progress)
                
                if elapsed >= total_sec:
                    self.rec_progress_running = False
                    self.record_progress['value'] = 100
                    return
                self.record_progress.after(update_frequency_ms, update)
            self.record_progress.after(0, update)
            # Start the actual recording
            ret = self.audio_recorder()
            self.rec_progress_running = False 
            self.record_progress.stop()

            # after recording, update the UI
            def on_finish():
                if ret:
                    print("[INFO]: Recording completed successfully") 
                    messagebox.showinfo(self.get_text("Success"), self.get_text("Recording completed successfully"))
                    self.record_button.config(text=self.get_text("Start Recording"))
                else:
                    print("[ERR]: Recording failed") 
                    messagebox.showerror(self.get_text("Error"), self.get_text("Recording failed"))
            self.record_progress.after(0, on_finish)

        threading.Thread(target=do_record).start() 

    def audio_player(self) -> bool:
        print("[INFO]: Play recording...") 
        audio_file = self.file_path_combobox.get()
        if self.audio_module is None:
            messagebox.showerror(self.get_text("Error"), self.get_text("Audio module not initialized"))
            return False
        play_device = self.play_device.get()
        play_rate = self.audio_module.rate
        self.audio_module.paras_settings(
            rate=self.audio_module.rate,                    # Use the format from WAV info
            channels=self.audio_module.channels,            # Use the format from WAV info
            audio_format= self.audio_module.audio_format,   # Use the format from WAV info
            file_type=self.audio_module.file_type,          # Use the format from WAV info
            engine=self.play_engine.get(),
            device=play_device
        )
        if self.audio_module.is_loopback_device(play_device):
            if self.audio_module.rate != 48000:  # Loopback device requires a specific sample rate
                print(f"[err]: Loopback device {play_device} requires sample rate 48000, but got {play_rate}.")
                return False
            print("[INFO]: Loopback device selected, playback will be looped.") 
            ret = self.audio_module.loopback_file_mode_start(audio_file)
        else:
             ret = self.audio_module.play_audio(audio_file)
        return ret
        
    def audio_player_thread(self):
        wav_info = self.audio_module.get_wav_info(self.file_path_combobox.get())
        if wav_info is None:
            messagebox.showerror(self.get_text("Error"), self.get_text("Audio module not initialized or failed to get WAV info"))
            return
        try:
            expect_duration = int(self.play_duration_entry.get())
        except ValueError:
            expect_duration = 0

        # Default to 1 hour if duration is set < 0 
        expect_duration = 3600 if expect_duration < 0 else expect_duration   # Default to 1 hour if invalid
        print(f"[INFO]: Expect duration: {expect_duration}")
        
        # print(f"[INFO]: WAV Info: {wav_info}")
        file_dur_sec_float = float(wav_info['duration'])
        file_dur_sec = int(file_dur_sec_float) + 1 # Add 1 second buffer to avoid rounding issues
        total_sec = max(file_dur_sec, expect_duration)
        self.audio_module.play_dur_sec = total_sec  # Set the playback duration for the module
        sample_rate = self.audio_module.rate = int(wav_info['sample_rate'])
        channels = self.audio_module.channels = int(wav_info['channels'])
        sample_fmt = self.audio_module.audio_format = wav_info['sample_fmt']
        self.file_type.set('wav')  # Set file type from WAV info
        print(f"[INFO]: Audio file: {self.file_path_combobox.get()}, Sample Rate: {sample_rate}, Channels: {channels}, Sample Format: {sample_fmt}", 
              f"Duration: {total_sec} sec")
        self.play_progress_running = True
        device = self.play_device.get()

        # Play audio in a separate thread to avoid blocking the UI
        def do_play():
            # Start the progress bar
            start_time = time.time()
            def update():
                update_frequency_ms = 200 
                if not self.play_progress_running:
                    return
                elapsed = time.time() - start_time
                self.update_progress(elapsed, total_sec, self.play_progress)
                
                if elapsed >= total_sec:
                    print(f"[INFO]: Playback duration total reached: {elapsed:.2f} sec")
                    self.play_progress_running = False
                    self.play_progress['value'] = 100
                    return
                self.play_progress.after(update_frequency_ms, update)

            self.play_progress.after(0, update)

            # Start the actual playback
            if self.audio_module.is_loopback_device(device):
                ret = self.audio_player()
                while self.play_progress_running and ret:
                    time.sleep(1)
                self.audio_module.loopback_file_mode_stop()
            else:
                while self.play_progress_running and  self.audio_module.play_dur_sec > 0:
                    ret = self.audio_player()
                    self.audio_module.play_dur_sec -= file_dur_sec 
                    if not ret:
                        print("[ERR]: Playback failed") 
                        break
            self.play_progress_running = False 
            self.play_progress.stop()

            # after playback, update the UI
            def on_finish():
                if ret:
                    print("[INFO]: Playback completed successfully") 
                    messagebox.showinfo(self.get_text("Success"), self.get_text("Playback completed successfully"))
                else:
                    print("[ERR]: Playback failed") 
                    messagebox.showerror(self.get_text("Error"), self.get_text("Playback failed"))
                self.play_button.config(text=self.get_text("Start Playing"))

            self.play_progress.after(0, on_finish)

        threading.Thread(target=do_play).start()

    def record_video(self):
        print("[INFO]: Start video recording...") 
        # TODO: Implement video recording

    def play_video(self):
        print("[INFO]: Play video...") 
        # TODO: Implement play video

    def update_device_menu(self, *args):
        print(f"[init]: Updating playback/recording device list...")
        if not self.ssh_client:
            messagebox.showerror(self.get_text("Error"), self.get_text("Not connected to remote host"))
            return None
        
        new_speaker_list = self.ssh_client.get_speaker_list()
        def_spk_idx = 0
        for i, speaker in enumerate(new_speaker_list):
            if self.default_speaker in speaker:
                def_spk_idx = i
                break
        self.play_device_combobox['values'] = new_speaker_list
        self.play_device_combobox.current(def_spk_idx)

        new_mic_list = self.ssh_client.get_mic_list()
        def_mic_idx = 0
        for i, mic in enumerate(new_mic_list):
            if self.default_mic in mic:
                def_mic_idx = i
                break
        self.record_device_combobox['values'] = new_mic_list
        self.record_device_combobox.current(def_mic_idx)
    
    def get_file_name_list(self, path):
        """
        Get a list of file names in the specified directory on the local filesystem.
        """
        if not os.path.exists(path):
            messagebox.showerror(self.get_text("Error"), self.get_text(f"Directory {path} does not exist"))
            return []
        try:
            files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(('.wav'))]
            return sorted(files)
        except Exception as e:
            messagebox.showerror(self.get_text("Error"), f"{self.get_text('Failed to list files')}: {str(e)}")
            return []
        
    def update_folder_menu(self):
        if not self.ssh_client:
            messagebox.showerror(self.get_text("Error"), self.get_text("Not connected to remote host"))
            return None
        play_menu = self.ssh_client.get_file_name_list("/root/plays/")
        self.file_path_combobox.config(values=play_menu)

        rec_menu = self.ssh_client.get_file_name_list("/root/records/")
        self.rec_path_combobox.config(values=rec_menu)

        local_rec_menu = self.get_file_name_list("./records/")
        self.target_audio_combobox.config(values=local_rec_menu)

        # Update the upload/download folder paths
        self.download_combobox_src.config(values=rec_menu)
    
    def toggle_analysis(self):
        if self.analysis_progress_running:
            print("[INFO]: Analysis already running, stopping...")
            self.analysis_progress_running = False
            self.analysis_progress.stop()
            self.remote_reset('mute') 
            self.analysis_button.config(text=self.get_text("Run Analysis"))
        else:
            print("[INFO]: Starting audio analysis...")
            self.analysis_button.config(text=self.get_text("Stop Analysis"))
            self.audio_analyzer_thread()

    def audio_analyzer_thread(self):
        def task():
            start_time = time.time()
            method = self.analysis_method.get()
            ref_audio = self.ref_audio_entry.get()
            target_audio = self.target_audio_combobox.get()
            wav_info = self.audio_module.get_wav_info(target_audio)
            if wav_info is None:
                messagebox.showerror(self.get_text("Error"), self.get_text("Audio module not initialized or failed to get WAV info"))
                return
            total_sec = int(wav_info['duration']) + 1  # Add 1 second buffer to avoid rounding issues
            print(f"[INFO]: Starting audio analysis with method: {method}, reference audio: {ref_audio}, target audio: {target_audio}, total duration: {total_sec} sec")
            if not os.path.exists(ref_audio):
                print("[WARN]: Reference audio file does not exist") 
            if not os.path.exists(target_audio):
                messagebox.showerror(self.get_text("Error"), self.get_text("Target audio file does not exist"))
                print("[ERR]: Target audio file does not exist") 
                return
            
            def update_analyse_progress():
                if not self.analysis_progress_running:
                    return
                update_frequency_ms = 200  # Update every 200 ms
                elapsed = time.time() - start_time
                self.update_progress(elapsed, total_sec, self.analysis_progress)
                if elapsed >= total_sec:
                    self.analysis_progress_running = False
                    self.analysis_progress['value'] = 100
                    return
                self.analysis_progress.after(update_frequency_ms, update_analyse_progress)
            # Start the progress bar
            self.analysis_progress_running = True
            self.analysis_start_time = time.time()
            self.analysis_progress.after(0, update_analyse_progress)
            # Perform the audio analysis
            result = self.audio_analyzer.analyze_audio(method=method, ref_audio=ref_audio, target_audio=target_audio)

            def on_finish():
                self.analysis_progress_running = False
                self.analysis_progress.stop()
                if result is True:
                    print("[INFO]: Audio analysis completed successfully") 
                    messagebox.showinfo(self.get_text("Success"), f"{self.get_text('Audio analysis completed successfully')}: {result}")
                else:
                    print("[ERR]: Audio analysis failed") 
                    messagebox.showerror(self.get_text("Error"), self.get_text("Audio analysis failed"))
            self.analysis_progress.after(0, on_finish)
            
        # Run the analysis task in a separate thread to avoid blocking the UI
        print("[INFO]: Starting audio analysis thread...")
        threading.Thread(target=task, daemon=True).start()

    def restart_app(self):
        """
        Restart the application.
        """
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def refresh_ui(self):
        """
        Refresh the UI to reflect any changes.
        """
        print("[INFO]: Refreshing UI...") 
        self.update_device_menu()
        print("[INFO]: UI refreshed successfully") 
        messagebox.showinfo(self.get_text("Success"),
                            self.get_text("UI refreshed successfully"))

    def remote_reset(self, flag="normal"):
        """
        Reset the remote host.
        """
        if self.ssh_client:
            self.ssh_client.reset(self.ssh_client)
            print("[INFO]: Remote host reset successfully")
            if 'mute' not in flag:
              messagebox.showinfo(self.get_text("Success"),
                                  self.get_text("Remote host reset successfully"))
        else:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))


if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteHostApp(root)
    app.connect_to_ssh()  # Expose for external use
    root.mainloop()
