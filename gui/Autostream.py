import os
import subprocess
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog


class TabMultistream(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.selected_file = None
        self.stream_keys = []
        self.ffmpeg_path = None
        self.ffmpeg_processes = []
        self.active_channels = tk.IntVar(value=0)
        self.stream_time = tk.StringVar(value="00:00:00")
        self.start_time = None
        self.timer_running = False
        self.stream_settings = {}
        self.create_gui()
        self.load_stream_keys()  # Cargar claves al iniciar

    def create_gui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ttk.Labelframe(self, text="Multistream Configuration")
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(main_frame, text="File to Stream:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.file_label = ttk.Label(main_frame, text="No file selected",  anchor="w")
        self.file_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.choose_file_button = ttk.Button(main_frame, text="Choose File", command=self.choose_file)
        self.choose_file_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.start_stream_button = ttk.Button(main_frame, text="Start Streaming", command=self.start_stream, state=tk.DISABLED)
        self.start_stream_button.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

        self.stop_stream_button = ttk.Button(main_frame, text="Stop Streaming", command=self.stop_stream, state=tk.DISABLED)
        self.stop_stream_button.grid(row=1, column=2, padx=5, pady=10, sticky="ew")

        summary_frame = ttk.Labelframe(self, text="Summary")
        summary_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ttk.Label(summary_frame, text="Stream Keys:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.keys_label = ttk.Label(summary_frame, text="0",  anchor="e")
        self.keys_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        ttk.Label(summary_frame, text="Active Channels:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.active_channels_label = ttk.Label(summary_frame, textvariable=self.active_channels,  anchor="e")
        self.active_channels_label.grid(row=1, column=1, padx=5, pady=5, sticky="e")

        ttk.Label(summary_frame, text="Stream Time:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.stream_time_label = ttk.Label(summary_frame, textvariable=self.stream_time,  anchor="e")
        self.stream_time_label.grid(row=2, column=1, padx=5, pady=5, sticky="e")

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            title="Select a file to stream",
            filetypes=[("Media Files", "*.mp4 *.png *.gif")]
        )
        if file_path and self.check_file_extension(file_path):
            self.selected_file = file_path
            self.file_label.configure(text=os.path.basename(self.selected_file))
            print(f"File selected: {self.selected_file}")
            self.start_stream_button.configure(state=tk.NORMAL)
        else:
            print("Unsupported or no file selected. Please try again.")

    def check_file_extension(self, filename):
        valid_extensions = [".mp4", ".png", ".gif"]
        return os.path.splitext(filename)[1].lower() in valid_extensions

    def load_stream_keys(self):
        file_path = os.path.join("settings", "stream_keys.txt")
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                self.stream_keys = [line.strip() for line in f if line.strip()]
            self.keys_label.configure(text=str(len(self.stream_keys)))  # Actualiza el total de stream keys
        else:
            print("Stream keys file not found. Please add keys in 'settings/stream_keys.txt'.")
            self.stream_keys = []
            self.keys_label.configure(text="0")  # Muestra 0 si no hay claves

    def load_ffmpeg_and_stream_keys(self):
        self.ffmpeg_path = self.get_ffmpeg_path()
        self.load_stream_keys()
        self.load_stream_settings()

    def get_ffmpeg_path(self):
        ffmpeg_executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        path = os.path.join("libs", ffmpeg_executable)
        if os.path.isfile(path):
            return path
        print("FFmpeg executable not found in 'libs' folder.")
        return None

    def load_stream_settings(self):
        settings_path = os.path.join("settings", "stream_settings.txt")
        if os.path.isfile(settings_path):
            with open(settings_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        self.stream_settings[key.strip()] = value.strip()
        else:
            print("Stream settings file not found. Using default settings.")

    def start_stream(self):
        self.load_ffmpeg_and_stream_keys()

        if not self.ffmpeg_path:
            print("FFmpeg executable not found. Please ensure it is in the 'libs' folder.")
            return

        if not self.stream_keys:
            print("No stream keys found. Add keys in 'settings/stream_keys.txt'.")
            return

        if not self.selected_file:
            print("Please select a file to stream before starting.")
            return

        if not os.path.isfile(self.selected_file):
            print(f"File not found: {self.selected_file}")
            return

        print("Starting streams...")
        self.active_channels.set(0)  # Reset active channels
        self.start_time = datetime.now()
        self.timer_running = True
        self.update_timer()  # Start the timer
        for key in self.stream_keys:
            threading.Thread(target=self.start_streaming, args=(self.selected_file, key)).start()

        self.stop_stream_button.configure(state=tk.NORMAL)
        self.start_stream_button.configure(state=tk.DISABLED)

    def start_streaming(self, filename, stream_key):
        if not self.ffmpeg_path:
            print("FFmpeg path not loaded.")
            return

        settings = {
            "video_codec": self.stream_settings.get("video_codec", "libx264"),
            "video_preset": self.stream_settings.get("video_preset", "veryfast"),
            "resolution": self.stream_settings.get("resolution", "1920:1080"),
            "fps": self.stream_settings.get("fps", "30"),
            "bitrate_video": self.stream_settings.get("bitrate_video", "3000k"),
            "bitrate_audio": self.stream_settings.get("bitrate_audio", "128k")
        }

        command = [
            self.ffmpeg_path, "-re", "-stream_loop", "-1", "-i", filename,
            "-c:v", settings["video_codec"], "-preset", settings["video_preset"],
            "-vf", f"scale={settings['resolution']},fps={settings['fps']}",
            "-b:v", settings["bitrate_video"], "-c:a", "aac", "-b:a", settings["bitrate_audio"],
            "-f", "flv", f"rtmp://live.twitch.tv/app/{stream_key}"
        ]

        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
            )
            self.ffmpeg_processes.append(process)

            stdout, stderr = process.communicate(timeout=5)
            if process.returncode == 0:
                self.active_channels.set(self.active_channels.get() + 1)
                print(f"Stream successfully started for key: {stream_key}")
            if stderr:
                print(f"FFmpeg Errors for key {stream_key}:\n{stderr}")
        except subprocess.TimeoutExpired:
            self.active_channels.set(self.active_channels.get() + 1)
            print(f"FFmpeg process for key {stream_key} started successfully.")
        except Exception as e:
            print(f"Error starting stream for key {stream_key}: {e}")

    def stop_stream(self):
        self.timer_running = False  # Stop the timer
        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], check=True)
                print("All FFmpeg processes terminated.")
            except subprocess.CalledProcessError as e:
                print(f"Error terminating FFmpeg processes: {e}")
        else:
            try:
                subprocess.run(["pkill", "-f", "ffmpeg"], check=True)
                print("All FFmpeg processes terminated.")
            except subprocess.CalledProcessError as e:
                print(f"Error terminating FFmpeg processes: {e}")

        self.ffmpeg_processes.clear()
        self.active_channels.set(0)
        self.stop_stream_button.configure(state=tk.DISABLED)
        self.start_stream_button.configure(state=tk.NORMAL)
        print("Stopped all streams.")

    def update_timer(self):
        if self.timer_running and self.start_time:
            elapsed_time = datetime.now() - self.start_time
            self.stream_time.set(str(elapsed_time).split('.')[0])  # Format HH:MM:SS
            self.after(1000, self.update_timer)  # Call again after 1 second
