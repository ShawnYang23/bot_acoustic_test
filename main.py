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
        self.hostname = "192.168.50.140"
        self.username = "root"
        self.password = "test0000"

        # Create navigation bar (Notebook)
        self.navbar = ttk.Notebook(self.root)
        self.navbar.pack(fill="both", expand=True)

        # Page 1 - SSH connection information
        self.page1 = ttk.Frame(self.navbar)
        self.navbar.add(self.page1, text=self.get_text("SSH"))

        # Page 2 - Logs
        self.page2 = ttk.Frame(self.navbar)
        self.navbar.add(self.page2, text=self.get_text("Logs"))

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
        self.setup_page2()
        self.setup_page3()
        self.setup_page4()
        self.setup_page5()
        self.setup_page6()

    def setup_page1(self):
        # Clear page elements
        for widget in self.page1.winfo_children():
            widget.destroy()

        label = tk.Label(self.page1, text=self.get_text(
            "Enter SSH Info"), font=("Arial", self.default_font_size))
        label.grid(row=0, column=0, columnspan=2, pady=10)

        # Hostname entry with default value
        default_hostname = self.hostname
        tk.Label(self.page1, text=self.get_text("Hostname: ")).grid(
            row=1, column=0, sticky="e")
        self.hostname_entry = tk.Entry(self.page1)
        # Set the default value in the entry field
        self.hostname_entry.insert(tk.END, default_hostname)
        self.hostname_entry.grid(row=1, column=1)

        # Username entry with default value
        default_username = self.username
        tk.Label(self.page1, text=self.get_text("Username: ")).grid(
            row=2, column=0, sticky="e")
        self.username_entry = tk.Entry(self.page1)
        # Set the default value in the entry field
        self.username_entry.insert(tk.END, default_username)
        self.username_entry.grid(row=2, column=1)

        # Password entry with default value
        default_password = self.password
        tk.Label(self.page1, text=self.get_text("Password: ")).grid(
            row=3, column=0, sticky="e")
        self.password_entry = tk.Entry(self.page1, show="*")
        # Set the default value in the entry field
        self.password_entry.insert(tk.END, default_password)
        self.password_entry.grid(row=3, column=1)

        # Connect Button
        connect_button = tk.Button(self.page1, text=self.get_text(
            "Connect"), command=self.connect_to_ssh)
        connect_button.grid(row=4, column=0, columnspan=2, pady=10)

        # Status area
        self.status_label = tk.Label(
            self.page1, text=self.get_text("Status: Not connected"), fg="red")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=10)
        #reset button
        reset_button = tk.Button(self.page1, text=self.get_text(
            "Reset"), command=lambda: self.ssh_client.reset(self.ssh_client))
        reset_button.grid(row=6, column=0, columnspan=2, pady=10)
    def setup_page2(self):
        for widget in self.page2.winfo_children():
            widget.destroy()

        # Create a Text widget to show logs
        self.log_text = tk.Text(self.page2, wrap="word",
                                height=25, width=115, state="normal")
        self.log_text.grid(row=0, column=0, padx=1, pady=1, columnspan=3)

        # Redirect stdout to log_text
        sys.stdout = self.RedirectText(self.log_text)

        # Configure columns so that they don't expand
        # Column 0 for "Clear Logs" button
        self.page2.grid_columnconfigure(0, weight=0, minsize=100)
        # Column 1 for "Save Logs" button
        self.page2.grid_columnconfigure(1, weight=0, minsize=100)
        # Column 2 for file path Entry
        self.page2.grid_columnconfigure(2, weight=0, minsize=200)

        # Buttons and Entry for saving logs
        clear_button = tk.Button(
            self.page2, text="Clear Logs", command=self.clear_logs)
        clear_button.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        save_button = tk.Button(
            self.page2, text="Save Logs", command=self.save_logs)
        save_button.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Entry for saving log path
        self.save_path_entry = tk.Entry(self.page2, width=30)
        self.save_path_entry.grid(row=1, column=2, padx=5, pady=5, sticky="w")
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
        for widget in self.page3.winfo_children():
            widget.destroy()
        file_operations_label = tk.Label(self.page3, text=self.get_text(
            "File Upload/Download"), font=("Arial", self.default_font_size))
        file_operations_label.pack(pady=10)
        # Upload button
        upload_button = tk.Button(self.page3, text=self.get_text(
            "Upload File"), command=self.upload_file)
        upload_button.pack(pady=5)
        self.upload_entry_src = tk.Entry(self.page3, width=50)
        self.upload_entry_src.insert(tk.END, "/tmp/")  # Default source path
        self.upload_entry_src.pack(pady=5)

        self.upload_entry_dest = tk.Entry(self.page3, width=50)
        self.upload_entry_dest.insert(
            tk.END, "/root/plays/")  # Default destination path
        self.upload_entry_dest.pack(pady=5)
        # Download button
        download_button = tk.Button(self.page3, text=self.get_text(
            "Download File"), command=self.download_file)
        download_button.pack(pady=5)

        self.download_entry_src = tk.Entry(self.page3, width=50)
        self.download_entry_src.insert(
            tk.END, "/root/records/")  # Default source path
        self.download_entry_src.pack(pady=5)
        self.download_entry_dest = tk.Entry(self.page3, width=50)
        self.download_entry_dest.insert(
            tk.END, "/tmp/")  # Default destination path
        self.download_entry_dest.pack(pady=5)

    def setup_page4(self):
        for widget in self.page4.winfo_children():
            widget.destroy()

        record_play_label = tk.Label(self.page4, text=self.get_text(
            "Recording and Playback"), font=("Arial", self.default_font_size))
        record_play_label.pack(pady=10)

        record_button = tk.Button(self.page4, text=self.get_text(
            "Start Recording"), command=self.record_audio)
        record_button.pack(pady=5)

        play_button = tk.Button(self.page4, text=self.get_text(
            "Play Recording"), command=self.play_audio)
        play_button.pack(pady=5)

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
        settings_label.pack(pady=10)

        # Window Size settings
        size_label = tk.Label(self.page6, text=self.get_text(
            "Window Size (Width x Height):"))
        size_label.pack(pady=5)
        self.width_entry = tk.Entry(self.page6)
        self.width_entry.insert(tk.END, str(self.default_width))
        self.width_entry.pack(pady=5)
        self.height_entry = tk.Entry(self.page6)
        self.height_entry.insert(tk.END, str(self.default_height))
        self.height_entry.pack(pady=5)

        # Font Size settings
        font_size_label = tk.Label(
            self.page6, text=self.get_text("Font Size:"))
        font_size_label.pack(pady=5)
        self.font_size_entry = tk.Entry(self.page6)
        self.font_size_entry.insert(tk.END, str(self.default_font_size))
        self.font_size_entry.pack(pady=5)

        # Language selection (English/Chinese)
        language_label = tk.Label(self.page6, text=self.get_text("Language:"))
        language_label.pack(pady=5)

        self.language_var = tk.StringVar(value=self.language)
        language_combobox = ttk.Combobox(
            self.page6, textvariable=self.language_var, values=["en", "zh"], state="readonly")
        language_combobox.pack(pady=5)

        # Save settings button
        save_button = tk.Button(self.page6, text=self.get_text(
            "Save Settings"), command=self.save_settings)
        save_button.pack(pady=10)

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
        self.navbar.tab(self.page2, text=self.get_text("Logs"))
        self.navbar.tab(self.page3, text=self.get_text("Files"))
        self.navbar.tab(self.page4, text=self.get_text("Audio"))
        self.navbar.tab(self.page5, text=self.get_text("Video"))
        self.navbar.tab(self.page6, text=self.get_text("Settings"))

        # Reload each page
        self.setup_page1()
        self.setup_page2()
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
            self.ssh_client.reset(self.ssh_client)
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
        # TODO: Implement audio recording

    def play_audio(self):
        self.log_text.insert(tk.END, self.get_text("Play recording...") + "\n")
        # TODO: Implement play audio

    def record_video(self):
        self.log_text.insert(tk.END, self.get_text(
            "Start video recording...") + "\n")
        # TODO: Implement video recording

    def play_video(self):
        self.log_text.insert(tk.END, self.get_text("Play video...") + "\n")
        # TODO: Implement play video


if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteHostApp(root)
    root.mainloop()
