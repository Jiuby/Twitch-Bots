import os  # Para verificar el sistema operativo y manejar procesos
import re  # Para validar y analizar el formato de tiempo
import threading  # Para ejecutar tareas en segundo plano sin bloquear la GUI
import time  # Para gestionar retrasos y cálculos de tiempo
import subprocess  # Para ejecutar comandos del sistema, como cerrar procesos
import tkinter as tk  # Para crear la interfaz gráfica principal
from tkinter import ttk  # Para widgets estilizados de Tkinter

class TabOFFTool(tk.Frame):
    def __init__(self, parent, manager, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.root = parent
        self.manager = manager
        self.shutdown_time_seconds = 0
        self.remaining_time = tk.StringVar(value="00:00:00")
        self.create_gui()

    def create_gui(self):
        # Main Configuration Frame
        config_frame = ttk.Labelframe(self, text="Automatic Timer Configuration", padding=(10, 10))
        config_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")  # Adjusted pady to bring it closer to the top

        ttk.Label(config_frame, text="Enter Time (1m, 1h, 1d):").grid(row=0, column=0, padx=5, pady=(0, 2), sticky="w")  # Reduced bottom padding
        self.time_entry = ttk.Entry(config_frame, width=20, justify="center", font=("Arial", 10))
        self.time_entry.grid(row=1, column=0, padx=5, pady=(0, 2), sticky="ew")  # Reduced padding for compact layout

        self.confirm_button = ttk.Button(
            config_frame,
            text="Confirm Time",
            command=self.confirm_time
        )
        self.confirm_button.grid(row=2, column=0, padx=5, pady=(0, 5), sticky="ew")  # Small bottom padding for spacing

        # Summary Frame
        summary_frame = ttk.Labelframe(self, text="Summary", padding=(10, 10))
        summary_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ttk.Label(summary_frame, text="Remaining Time:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.remaining_time_label = ttk.Label(summary_frame, textvariable=self.remaining_time,  anchor="center", width=10)
        self.remaining_time_label.grid(row=0, column=1, padx=5, pady=5)

        self.message_label = ttk.Label(summary_frame, text="", foreground="blue", anchor="center")
        self.message_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        # Layout Adjustments
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def confirm_time(self):
        time_input = self.time_entry.get().strip()
        self.shutdown_time_seconds = self.parse_time_input(time_input)
        if self.shutdown_time_seconds is not None:
            self.message_label.config(text=f"Time confirmed: {self.shutdown_time_seconds} seconds", foreground="green")
            print(f"Time confirmed in seconds: {self.shutdown_time_seconds}")  # Debugging
            threading.Thread(target=self.wait_and_notify, daemon=True).start()
        else:
            self.message_label.config(text="Invalid format. Please use 1s, 1m, 1h, or 1d.", foreground="red")
            print("Invalid time format.")  # Debugging

    def parse_time_input(self, time_input):
        match = re.match(r"(\d+)([smhd])$", time_input)
        if match:
            value, unit = int(match.group(1)), match.group(2)
            return value * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(unit, 0)
        return None

    def wait_and_notify(self):
        total_time = self.shutdown_time_seconds
        while total_time > 0:
            mins, secs = divmod(total_time, 60)
            hours, mins = divmod(mins, 60)
            self.remaining_time.set(f"{hours:02}:{mins:02}:{secs:02}")
            time.sleep(1)
            total_time -= 1

        self.remaining_time.set("00:00:00")
        self.message_label.config(text="Time is up! Closing the program...", foreground="red")
        print("Time completed, forcing program shutdown...")  # Debugging
        self.force_quit_program()

    def force_quit_program(self):
        print("Forcing program shutdown and stopping all streams...")
        # Cerrar procesos de FFmpeg
        if os.name == "nt":  # Windows
            try:
                subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], check=True)
                print("All FFmpeg processes terminated.")
            except subprocess.CalledProcessError as e:
                print(f"Error terminating FFmpeg processes: {e}")
        else:  # macOS/Linux
            try:
                subprocess.run(["pkill", "-f", "ffmpeg"], check=True)
                print("All FFmpeg processes terminated.")
            except subprocess.CalledProcessError as e:
                print(f"Error terminating FFmpeg processes: {e}")

        # Salir del programa
        os._exit(0)  # Forzar la terminación inmediata del programa
