import tkinter as tk
import os
import sys
from ui import RemoteHostApp

def restart_program():
    python = sys.executable
    os.execl(python, python, *sys.argv)

def create_ui():
    root = tk.Tk()
    app = RemoteHostApp(root)
    root.mainloop()


# 启动 UI
create_ui()
