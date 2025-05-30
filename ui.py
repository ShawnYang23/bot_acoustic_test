import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import paramiko
import threading
import os
import sys
import io

from ssh_client import SSHClient
from audio_module import AudioModule

class RemoteHostApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Host Manager")
        self.root.geometry("960x540")  # Default window size

        # Default settings
        self.default_width = 960
        self.default_height = 540
        # only support 16:9 aspect ratio
        self.default_aspect_ratio = (16, 9)
        self.min_width = 640
        self.max_width = 1920  # Maximum width for the window

        self.default_font_size = 12
        self.language = "en"  # Default language is English

        # SSH connection information
        self.ssh_client = None
        self.audio_module = None
        self.hostname = "192.168.50.140"
        self.username = "root"
        self.password = "test0000"

        # Create navigation bar (Notebook)
        self.navbar = ttk.Notebook(self.root)
        self.navbar.pack(fill="both", expand=True)

        # Page 1 - SSH connection information
        self.page1 = ttk.Frame(self.navbar)
        self.navbar.add(self.page1, text=self.get_text("SSH"))


        # Page 3 - File management (Upload/Download)
        self.page3 = ttk.Frame(self.navbar)
        self.navbar.add(self.page3, text=self.get_text("Files"))

        # Page 4 - Audio recording/playback
        self.page4 = ttk.Frame(self.navbar)
        self.navbar.add(self.page4, text=self.get_text("Audio"))

        # Page 5 - Video recording/playback
        self.page5 = ttk.Frame(self.navbar)
        self.navbar.add(self.page5, text=self.get_text("Video"))

        # Page 6 - Settings page
        self.page6 = ttk.Frame(self.navbar)
        self.navbar.add(self.page6, text=self.get_text("Settings"))

        # Setup pages
        self.setup_page1()
        self.setup_page3()
        self.setup_page4()
        self.setup_page5()
        self.setup_page6()

    def setup_page1(self):
        # Clear page elements
        for widget in self.page1.winfo_children():
            widget.destroy()

        label = tk.ttk.Label(self.page1, text=self.get_text("Home Page"),
                                font=("Arial", self.default_font_size))
        label.grid(row=0, column=0, columnspan=8, pady=10)
        
        ssh_frame = tk.Frame(self.page1)
        ssh_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        # Hostname entry with default value
        default_hostname = self.hostname
        tk.Label(ssh_frame, text=self.get_text("Hostname: ")).grid(
            row=1, column=0, sticky="e")
        self.hostname_entry = tk.Entry(ssh_frame)
        # Set the default value in the entry field
        self.hostname_entry.insert(tk.END, default_hostname)
        self.hostname_entry.grid(row=1, column=1)

        # Username entry with default value
        default_username = self.username
        tk.Label(ssh_frame, text=self.get_text("Username: ")).grid(
            row=2, column=0, sticky="e")
        self.username_entry = tk.Entry(ssh_frame)
        # Set the default value in the entry field
        self.username_entry.insert(tk.END, default_username)
        self.username_entry.grid(row=2, column=1)

        # Password entry with default value
        default_password = self.password
        tk.Label(ssh_frame, text=self.get_text("Password: ")).grid(
            row=3, column=0, sticky="e")
        self.password_entry = tk.Entry(ssh_frame, show="*")
        # Set the default value in the entry field
        self.password_entry.insert(tk.END, default_password)
        self.password_entry.grid(row=3, column=1)

        # Connect Button
        connect_button = tk.Button(ssh_frame, text=self.get_text(
            "Connect"), command=self.connect_to_ssh)
        connect_button.grid(row=4, column=0, columnspan=2, pady=10)
        self.status_label = tk.Label(
            ssh_frame, text=self.get_text("Status: Not connected"), fg="red")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=10)
        # remote reset button
        reset_button = tk.Button(ssh_frame, text=self.get_text(
            "Remote Reset"), command=lambda: self.remote_reset())
        reset_button.grid(row=9, column=0, rowspan=2, pady=10)
        # ui fresh button
        ui_fresh_button = tk.Button(ssh_frame, text=self.get_text(
            "UI Fresh"), command=lambda: self.restart_app())
        ui_fresh_button.grid(row=9, column=1, columnspan=2, pady=10)
        #log text widget
        self.log_frame = tk.Frame(self.page1)
        self.log_frame.grid(row=1, column=3, columnspan=4, rowspan=4, padx=10, pady=10, sticky="nsew")
        self.log_text = tk.Text(self.log_frame, wrap="word", height=20, width=80)
        self.log_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        # Redirect stdout to log_text
        sys.stdout = self.RedirectText(self.log_text)

        log_ctl_frame = tk.Frame(self.page1)
        log_ctl_frame.grid(row=5, column=3, columnspan=4, padx=10, pady=10, sticky="nsew")
        # Configure columns so that they don't expand
        # Column 0 for "Clear Logs" button
        log_ctl_frame.grid_columnconfigure(0, weight=1, minsize=50)
        # Column 1 for "Save Logs" button
        log_ctl_frame.grid_columnconfigure(1, weight=1, minsize=50)
        # Column 2 for file path Entry
        log_ctl_frame.grid_columnconfigure(2, weight=1, minsize=50)

        # Buttons and Entry for saving logs
        clear_button = tk.Button(
            log_ctl_frame, text="Clear Logs", command=self.clear_logs)
        clear_button.grid(row=4, column=0, padx=1, pady=5, sticky="ew")

        save_button = tk.Button(
            log_ctl_frame, text="Save Logs", command=self.save_logs)
        save_button.grid(row=4, column=1, padx=1, pady=5, sticky="ew")

        # Entry for saving log path
        self.save_path_entry = tk.Entry(log_ctl_frame, width=30)
        self.save_path_entry.grid(row=4, column=2, padx=1, pady=5, sticky="ew")
        self.save_path_entry.insert(0, "/tmp/log.txt")

    def clear_logs(self):
        # Clear the content in the Text widget
        self.log_text.delete(1.0, tk.END)
        print("Logs cleared.")  # This message will appear in the log

    def save_logs(self):
        # Get all the text in the Text widget
        log_content = self.log_text.get(1.0, tk.END)
        if log_content.strip():  # Check if there is any content to save
            try:
                # Get the path from the entry widget
                file_path = self.save_path_entry.get()
                print(f"Saving logs to: {file_path}")  # Log the save path
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

    def setup_page3(self):
        # 清空页面上的所有控件
        for widget in self.page3.winfo_children():
            widget.destroy()

        # 文件操作标题
        file_operations_label = tk.Label(self.page3, text=self.get_text(
            "File Upload/Download"), font=("Arial", self.default_font_size))
        file_operations_label.pack(pady=10)

        # 创建 Upload 部分的 Frame
        upload_frame = tk.LabelFrame(
            self.page3, text="Upload File", padx=10, pady=10)
        upload_frame.pack(padx=10, pady=10, fill="x")

        # 上传按钮
        upload_button = tk.Button(upload_frame, text=self.get_text(
            "Upload File"), command=self.upload_file)
        upload_button.grid(row=0, column=0, padx=5, pady=5)

        # 上传源路径输入框
        update_src_label = tk.Label(upload_frame, text=self.get_text("Source Path:"))
        update_src_label.grid(row=1, column=0, pady=5)
        self.upload_entry_src = tk.Entry(upload_frame, width=50)
        self.upload_entry_src.insert(tk.END, "/tmp/")  # 默认源路径
        self.upload_entry_src.grid(row=1, column=1, pady=5)
        # 上传目标路径输入框
        update_dest_label = tk.Label(upload_frame, text=self.get_text("Destination Path:"))
        update_dest_label.grid(row=2, column=0, pady=5)
        self.upload_entry_dest = tk.Entry(upload_frame, width=50)
        self.upload_entry_dest.insert(tk.END, "/root/plays/")  # 默认目标路径
        self.upload_entry_dest.grid(row=2, column=1, pady=5)    

        # 创建 Download 部分的 Frame
        download_frame = tk.LabelFrame(
            self.page3, text="Download File", padx=10, pady=10)
        download_frame.pack(padx=10, pady=10, fill="x")

        # 下载按钮
        download_button = tk.Button(download_frame, text=self.get_text(
            "Download File"), command=self.download_file)
        download_button.grid(row=0, column=0, padx=5, pady=5)

        # 下载源路径输入框
        download_src_label = tk.Label(download_frame, text=self.get_text("Source Path:"))
        download_src_label.grid(row=1, column=0, pady=5)
        self.download_entry_src = tk.Entry(download_frame, width=50)
        self.download_entry_src.insert(tk.END, "/root/records/")  # 默认源路径
        self.download_entry_src.grid(row=1, column=1, pady=5)

        # 下载目标路径输入框
        download_dest_label = tk.Label(download_frame, text=self.get_text("Destination Path:"))
        download_dest_label.grid(row=2, column=0, pady=5)
        self.download_entry_dest = tk.Entry(download_frame, width=50)
        self.download_entry_dest.insert(tk.END, "/tmp/")  # 默认目标路径
        self.download_entry_dest.grid(row=2, column=1, pady=5)

    def setup_page4(self):
        # Clear page elements
        for widget in self.page4.winfo_children():
            widget.destroy()

        # page4 label
        record_play_label = tk.Label(self.page4, text=self.get_text(
            "Audio"), font=("Arial", self.default_font_size))
        record_play_label.grid(row=0, column=0, columnspan=4, rowspan=2, pady=10)

        # Basic audio parameters settings
        self.audio_settings_frame = tk.LabelFrame(
            self.page4, text="Audio Settings", padx=10, pady=10)
        self.audio_settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nesw", columnspan=2, rowspan=2)

        # Sampling rate settings
        self.sampling_rate_label = tk.Label(
            self.audio_settings_frame, text="Sampling Rate:")
        self.sampling_rate_label.grid(row=0, column=0, padx=5, pady=5)
        self.sampling_rate = tk.StringVar(value="48000")
        self.sampling_rate_entry = tk.Entry(
            self.audio_settings_frame, textvariable=self.sampling_rate)
        self.sampling_rate_entry.grid(row=0, column=1, padx=5, pady=5)

        # Channels settings
        self.channels_label = tk.Label(
            self.audio_settings_frame, text="Channels:")
        self.channels_label.grid(row=1, column=0, padx=5, pady=5)
        self.channels = tk.StringVar(value="2")
        self.channels_entry = tk.Entry(
            self.audio_settings_frame, textvariable=self.channels)
        self.channels_entry.grid(row=1, column=1, padx=5, pady=5)

        # Data type settings
        self.data_type_label = tk.Label(
            self.audio_settings_frame, text="Data Type:")
        self.data_type_label.grid(row=2, column=0, padx=5, pady=5)
        self.data_type = tk.StringVar(value="S16_LE")
        self.data_type_entry = tk.Entry(
            self.audio_settings_frame, textvariable=self.data_type)
        self.data_type_entry.grid(row=2, column=1, padx=5, pady=5)

        # Engine selection (alsa/cras)
        self.engine_label = tk.Label(self.audio_settings_frame, text="Engine:")
        self.engine_label.grid(row=3, column=0, padx=5, pady=5)
        self.engine = tk.StringVar(value="alsa")
        self.engine_combobox = tk.OptionMenu(
            self.audio_settings_frame, self.engine, "alsa", "cras")
        self.engine_combobox.grid(row=3, column=1, padx=5, pady=5)

        # File type selection (wav/pcm)
        self.file_type_label = tk.Label(
            self.audio_settings_frame, text="File Type:")
        self.file_type_label.grid(row=4, column=0, padx=5, pady=5)
        self.file_type = tk.StringVar(value="wav")
        self.file_type_combobox = tk.OptionMenu(
            self.audio_settings_frame, self.file_type, "wav", "pcm")
        self.file_type_combobox.grid(row=4, column=1, padx=5, pady=5)

        # Audio recording module
        self.record_frame = tk.LabelFrame(
            self.page4, text="Record Audio", padx=10, pady=10)
        self.record_frame.grid(row=2, column=3, padx=20, pady=1, sticky="nesw")

        self.record_device_label = tk.Label(
            self.record_frame, text="Recording Device:")
        self.record_device_label.grid(
            row=0, column=0, padx=5, pady=5, sticky="w")
        self.record_device = tk.StringVar(value="Default")
        self.record_device.trace_add("write", self.update_device_menu)
        self.record_device_combobox = tk.OptionMenu(
            self.record_frame, self.record_device, "menu", "none")
        self.record_device_combobox.grid(
            row=0, column=1, padx=5, pady=5, sticky="w")
        record_button = tk.Button(self.record_frame, text=self.get_text(
            "Start Recording"), command=self.record_audio)
        record_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.rec_path_entry = tk.Entry(self.record_frame, width=50)
        self.rec_path_entry.insert(
            tk.END, "/root/records/")  # Default save path
        self.rec_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Audio playback module
        self.play_frame = tk.LabelFrame(
            self.page4, text="Audio Playback", padx=10, pady=10)
        self.play_frame.grid(row=3, column=3, padx=20, pady=1, sticky="nesw")
        self.play_deviece_label = tk.Label(
            self.play_frame, text="Playback Device:")
        self.play_deviece_label.grid(
            row=0, column=0, padx=5, pady=5, sticky="e")
        self.play_device = tk.StringVar(value="Default")
        self.play_device.trace_add("write", self.update_device_menu)
        self.play_device_combobox = tk.OptionMenu(
            self.play_frame, self.play_device, "menu", "none")
        self.play_device_combobox.grid(
            row=0, column=1, padx=5, pady=5, sticky="w")

        play_button = tk.Button(self.play_frame, text=self.get_text(
            "Start Playing"), command=self.play_audio)
        play_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.file_path_entry = tk.Entry(self.play_frame, width=50)
        # Default file path for playback
        self.file_path_entry.insert(tk.END, "/root/plays/")
        self.file_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        #audio analysis module
        self.analysis_frame = tk.LabelFrame(
            self.page4, text="Audio Analysis", padx=10, pady=10)
        self.analysis_frame.grid(row=4, column=0, padx=20, pady=1, sticky="nesw", columnspan=4)

        self.analysis_label = tk.Label(self.analysis_frame, text="Analysis Menu:")
        self.analysis_label.grid(row=0, column=0, padx=5, pady=5)
        self.analysis_method = tk.StringVar(value="PESG")
        methods = ["PESG", "Reverb", "ANR", "AEC", "Spectrogram", "DOA"]
        self.analysis_method_combobox = ttk.Combobox(
            self.analysis_frame, textvariable=self.analysis_method, values=methods, state="readonly")
        self.analysis_method_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ref_label = tk.Label(self.analysis_frame, text="Reference Audio:")
        ref_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ref_audio_entry = tk.Entry(self.analysis_frame, width=50)
        self.ref_audio_entry.insert(tk.END, "./plays/ref.wav")  # Default reference audio
        self.ref_audio_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        target_label = tk.Label(self.analysis_frame, text="Target Audio:")
        target_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.target_audio_entry = tk.Entry(self.analysis_frame, width=50)
        self.target_audio_entry.insert(tk.END, "./records/record.wav")  # Default target audio
        self.target_audio_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        analyze_button = tk.Button(self.analysis_frame, text="Analyze", command=self.analyze_audio)
        analyze_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)


    def setup_page5(self):
        for widget in self.page5.winfo_children():
            widget.destroy()

        video_record_label = tk.Label(self.page5, text=self.get_text(
            "Video Recording and Playback"), font=("Arial", self.default_font_size))
        video_record_label.pack(pady=10)

        record_video_button = tk.Button(self.page5, text=self.get_text(
            "Start Recording"), command=self.record_video)
        record_video_button.pack(pady=5)

        play_video_button = tk.Button(self.page5, text=self.get_text(
            "Play Video"), command=self.play_video)
        play_video_button.pack(pady=5)

    def setup_page6(self):
        for widget in self.page6.winfo_children():
            widget.destroy()

        settings_label = tk.Label(self.page6, text=self.get_text(
            "Settings"), font=("Arial", self.default_font_size))
        settings_label.pack(pady=5)

        # Create parameter settings frame
        para_frame = tk.Frame(self.page6)
        para_frame.pack(pady=10)
        # Window Size settings

        size_label = tk.Label(para_frame, text=self.get_text(
            "Window(WxH):"))
        size_label.grid(row=0, column=0, padx=5, pady=5)

        self.width_entry = tk.Entry(para_frame)
        self.width_entry.insert(tk.END, str(self.default_width))
        self.width_entry.grid(row=0, column=1, padx=5)

        x_label = tk.Label(para_frame, text="x")
        x_label.grid(row=0, column=2, padx=1)

        self.height_entry = tk.Entry(para_frame)
        self.height_entry.insert(tk.END, str(self.default_height))
        self.height_entry.grid(row=0, column=3, padx=5)

        font_size_label = tk.Label(
            para_frame, text=self.get_text("Font Size:"))
        font_size_label.grid(row=1, column=0, padx=5, pady=5)
        self.font_size_entry = tk.Entry(para_frame)
        self.font_size_entry.insert(tk.END, str(self.default_font_size))
        self.font_size_entry.grid(row=1, column=1, padx=5)

        # Language selection (English/Chinese)
        language_label = tk.Label(para_frame, text=self.get_text("Language:"))
        language_label.grid(row=2, column=0, padx=5, pady=5)

        self.language_var = tk.StringVar(value=self.language)
        language_combobox = ttk.Combobox(
            para_frame, textvariable=self.language_var, values=["en", "zh"], state="readonly")
        language_combobox.grid(row=2, column=1, padx=5, pady=5)

        # Save settings button
        save_button = tk.Button(para_frame, text=self.get_text(
            "Save Settings"), command=self.save_settings)
        save_button.grid(row=3, column=0, columnspan=4, pady=20)

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
        self.navbar.tab(self.page1, text=self.get_text("SSH"))
        self.navbar.tab(self.page3, text=self.get_text("Files"))
        self.navbar.tab(self.page4, text=self.get_text("Audio"))
        self.navbar.tab(self.page5, text=self.get_text("Video"))
        self.navbar.tab(self.page6, text=self.get_text("Settings"))

        # Reload each page
        self.setup_page1()
        self.setup_page3()
        self.setup_page4()
        self.setup_page5()
        self.setup_page6()

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
            self.update_device_menu() 
            self.audio_module = AudioModule(self.ssh_client)
            self.remote_reset()
        except Exception as e:
            self.status_label.config(text=self.get_text(
                "Status: Connection Failed"), fg="red")
            messagebox.showerror(self.get_text(
                "Connection Error"), f"{self.get_text('Connection Failed')}: {str(e)}")

    def upload_file(self):
        if self.ssh_client:
            self.log_text.insert(tk.END, self.get_text(
                "Uploading file...") + "\n")
            src_path = self.upload_entry_src.get()
            if not os.path.exists(src_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Source file does not exist"))
                self.log_text.insert(tk.END, self.get_text(
                    "Source file does not exist") + "\n")
                return
            dest_path = self.upload_entry_dest.get()
            if not self.ssh_client.is_dir(dest_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Destination path directory does not exist"))
                self.log_text.insert(tk.END, self.get_text(
                    "Destination path directory does not exist") + "\n")
                return
            try:
                self.ssh_client.upload_file(src_path, dest_path)
                self.log_text.insert(tk.END, self.get_text(
                    "File uploaded successfully") + "\n")
                messagebox.showinfo(self.get_text("Success"),
                                    self.get_text("File uploaded successfully"))
            except Exception as e:
                messagebox.showerror(self.get_text("Error"),
                                     f"{self.get_text('File upload failed')}: {str(e)}")
                self.log_text.insert(tk.END, self.get_text(
                    "File upload failed: ") + str(e) + "\n")
        else:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))

    def download_file(self):
        if self.ssh_client:
            self.log_text.insert(tk.END, self.get_text(
                "Downloading file...") + "\n")
            src_path = self.download_entry_src.get()
            if not self.ssh_client.file_exists(src_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Source file does not exist on remote host"))
                self.log_text.insert(tk.END, self.get_text(
                    "Source file does not exist on remote host") + "\n")
                return
            dest_path = self.download_entry_dest.get()
            if not os.path.isdir(dest_path):
                messagebox.showerror(self.get_text("Error"),
                                     self.get_text("Destination path does not exist or is not a directory"))
                self.log_text.insert(tk.END, self.get_text(
                    "Destination path does not exist or is not a directory") + "\n")
                return
            try:
                self.ssh_client.download_file(src_path, dest_path)
                self.log_text.insert(tk.END, self.get_text(
                    "File downloaded successfully") + "\n")
                messagebox.showinfo(self.get_text("Success"),
                                    self.get_text("File downloaded successfully"))
            except Exception as e:
                messagebox.showerror(self.get_text("Error"),
                                     f"{self.get_text('File download failed')}: {str(e)}")
                self.log_text.insert(tk.END, self.get_text(
                    "File download failed: ") + str(e) + "\n")
        else:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))

    def record_audio(self):
        self.log_text.insert(tk.END, self.get_text(
            "Start recording...") + "\n")
        self.audio_module.paras_settings(
            rate=int(self.sampling_rate.get()),
            channels=int(self.channels.get()),
            audio_format=self.data_type.get(),
            file_type=self.file_type.get(),
            engine=self.engine.get(),
            device=self.record_device.get()
        )
        self.audio_module.audio_dir_record = self.rec_path_entry.get()
        ret = self.audio_module.record_audio(
            self.audio_module.audio_dir_record,
            self.audio_module.engine,
            self.audio_module.device
        )
        if ret:
            self.log_text.insert(tk.END, self.get_text(
                "Recording completed successfully") + "\n")
            messagebox.showinfo(self.get_text("Success"),
                                self.get_text("Recording completed successfully"))
        else:
            self.log_text.insert(tk.END, self.get_text(
                "Recording failed") + "\n")
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Recording failed"))

    def play_audio(self):
        self.log_text.insert(tk.END, self.get_text("Play recording...") + "\n")
        audio_file = self.file_path_entry.get()
        if not os.path.exists(audio_file):
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Audio file does not exist"))
            self.log_text.insert(tk.END, self.get_text(
                "Audio file does not exist") + "\n")
            return
        self.audio_module.paras_settings(
            rate=int(self.sampling_rate.get()),
            channels=int(self.channels.get()),
            audio_format=self.data_type.get(),
            file_type=self.file_type.get(),
            engine=self.engine.get(),
            device=self.play_device.get()
        )
        self.audio_module.audio_dir_play = audio_file
        ret = self.audio_module.play_audio(
            audio_file,
            self.audio_module.engine,
            self.audio_module.device
        )
        if ret:
            self.log_text.insert(tk.END, self.get_text(
                "Playback completed successfully") + "\n")
            messagebox.showinfo(self.get_text("Success"),
                                self.get_text("Playback completed successfully"))
        else:
            self.log_text.insert(tk.END, self.get_text(
                "Playback failed") + "\n")
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Playback failed"))

    def record_video(self):
        self.log_text.insert(tk.END, self.get_text(
            "Start video recording...") + "\n")
        # TODO: Implement video recording

    def play_video(self):
        self.log_text.insert(tk.END, self.get_text("Play video...") + "\n")
        # TODO: Implement play video

    def update_device_menu(self, *args):
        print(f"Updating playback device and recording device menus...")
        if not self.ssh_client:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))
            return None
        menu = self.play_device_combobox['menu']
        menu.delete(0, 'end')
        new_speaker_list = self.ssh_client.get_speaker_list()
        for speaker in new_speaker_list:
            menu.add_command(label=speaker, command=tk._setit(
                self.play_device, speaker))
        self.play_device.set(new_speaker_list[0])

        menu = self.record_device_combobox['menu']
        menu.delete(0, 'end')
        new_mic_list = self.ssh_client.get_mic_list()
        for mic in new_mic_list:
            menu.add_command(
                label=mic, command=tk._setit(self.play_device, mic))
        self.record_device.set(new_mic_list[0])

    def analyze_audio(self):
        self.log_text.insert(tk.END, self.get_text("Start audio analysis...") + "\n")
        method = self.analysis_method.get()
        ref_audio = self.ref_audio_entry.get()
        target_audio = self.target_audio_entry.get()

        if not os.path.exists(ref_audio):
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Reference audio file does not exist"))
            self.log_text.insert(tk.END, self.get_text(
                "Reference audio file does not exist") + "\n")
            return
        if not os.path.exists(target_audio):
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Target audio file does not exist"))
            self.log_text.insert(tk.END, self.get_text(
                "Target audio file does not exist") + "\n")
            return

        try:
            result = self.audio_module.analyze_audio(
                method, ref_audio, target_audio)
            self.log_text.insert(tk.END, f"{self.get_text('Analysis Result')}: {result}\n")
            messagebox.showinfo(self.get_text("Analysis Result"),
                                f"{self.get_text('Analysis Result')}: {result}")
        except Exception as e:
            messagebox.showerror(self.get_text("Error"),
                                 f"{self.get_text('Audio analysis failed')}: {str(e)}")
            self.log_text.insert(tk.END, f"{self.get_text('Audio analysis failed')}: {str(e)}\n")

    def restart_app(self):
        """
        Restart the application.
        """
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    def remote_reset(self):
        """
        Reset the remote host.
        """
        if self.ssh_client:
            self.ssh_client.reset(self.ssh_client)
            self.log_text.insert(tk.END, self.get_text("Remote host reset successfully") + "\n")
            messagebox.showinfo(self.get_text("Success"),
                                self.get_text("Remote host reset successfully"))
        else:
            messagebox.showerror(self.get_text("Error"),
                                 self.get_text("Not connected to remote host"))
        
if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteHostApp(root)
    root.mainloop()
