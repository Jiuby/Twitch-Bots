import os
import time
import socket
import threading
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import requests
#from libs.proxy import ProxyGetter


class TabChat(tk.Frame):
    def __init__(self, parent, manager, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.manager = manager
        self.channel_name = tk.StringVar()
        self.interval = tk.IntVar(value=10)
        self.total_messages = tk.IntVar(value=0)
        self.chat_status = tk.StringVar(value="Stopped")
        self.token_count = tk.IntVar(value=0)  # Variable para contar tokens cargados
        self.message_file_path = os.path.join("settings", "chat_messages.txt")
        self.oauth_file_path = os.path.join("settings", "twitch_token_list.txt")
        self.is_chat_running = False

        self.proxy_getter = ProxyGetter()
        self.create_gui()

    def create_gui(self):
        # Chat Configuration Frame
        config_frame = ttk.Labelframe(self, text="Chat Configuration", padding=(10, 10))
        config_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")

        ttk.Label(config_frame, text="Channel Name:").grid(row=0, column=0, padx=5, pady=(0, 5), sticky="w")
        ttk.Entry(config_frame, textvariable=self.channel_name, width=30).grid(row=0, column=1, padx=5, pady=(0, 5),
                                                                               sticky="ew")

        ttk.Label(config_frame, text="Interval (s):").grid(row=1, column=0, padx=5, pady=(0, 5), sticky="w")
        ttk.Entry(config_frame, textvariable=self.interval, width=10).grid(row=1, column=1, padx=5, pady=(0, 5),
                                                                           sticky="w")

        self.start_chat_button = ttk.Button(config_frame, text="Start Chat", command=self.start_chat, width=15)
        self.start_chat_button.grid(row=2, column=0, padx=5, pady=(5, 5), sticky="ew")

        self.stop_chat_button = ttk.Button(config_frame, text="Stop Chat", command=self.stop_chat, state=tk.DISABLED,
                                           width=15)
        self.stop_chat_button.grid(row=2, column=1, padx=5, pady=(5, 5), sticky="ew")

        # Log Frame for Output
        log_frame = ttk.Labelframe(self, text="Logs", padding=(10, 10))
        log_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")

        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.grid(row=0, column=1, sticky="ns")

        # Summary Frame
        summary_frame = ttk.Labelframe(self, text="Summary", padding=(10, 10))
        summary_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")

        ttk.Label(summary_frame, text="Total Messages:").grid(row=0, column=0, padx=5, pady=(0, 5), sticky="w")
        ttk.Label(summary_frame, textvariable=self.total_messages).grid(row=0, column=1, padx=5, pady=(0, 5),
                                                                        sticky="e")

        ttk.Label(summary_frame, text="Chat Status:").grid(row=1, column=0, padx=5, pady=(0, 5), sticky="w")
        ttk.Label(summary_frame, textvariable=self.chat_status).grid(row=1, column=1, padx=5, pady=(0, 5), sticky="e")

        ttk.Label(summary_frame, text="Tokens Loaded:").grid(row=2, column=0, padx=5, pady=(0, 5), sticky="w")
        ttk.Label(summary_frame, textvariable=self.token_count).grid(row=2, column=1, padx=5, pady=(0, 5), sticky="e")

        # Expandable Layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_chat(self):
        if not self.channel_name.get():
            self.log("Please enter a valid channel name.")
            return
        if not os.path.exists(self.message_file_path):
            self.log(f"Message file '{self.message_file_path}' not found.")
            return
        if not os.path.exists(self.oauth_file_path):
            self.log(f"OAuth token file '{self.oauth_file_path}' not found.")
            return

        # Cargar y contar tokens
        with open(self.oauth_file_path, "r", encoding="utf-8") as file:
            tokens = [line.strip() for line in file if line.strip()]
            self.token_count.set(len(tokens))

        if self.token_count.get() == 0:
            self.log("No tokens found in the file.")
            return

        self.is_chat_running = True
        self.start_chat_button.configure(state=tk.DISABLED)
        self.stop_chat_button.configure(state=tk.NORMAL)
        self.chat_status.set("Running")
        self.log("Chat started.")

        threading.Thread(target=self.send_messages_from_file, daemon=True).start()

    def stop_chat(self):
        self.is_chat_running = False
        self.start_chat_button.configure(state=tk.NORMAL)
        self.stop_chat_button.configure(state=tk.DISABLED)
        self.chat_status.set("Stopped")
        self.log("Stopped chat messaging.")

    def send_messages_from_file(self):
        server, port = "irc.chat.twitch.tv", 6667

        with open(self.oauth_file_path, "r", encoding="utf-8") as file:
            oauth_tokens = [f"oauth:{line.strip()}" for line in file if line.strip()]

        if not oauth_tokens:
            self.log("No OAuth tokens found. Please add tokens to the file.")
            return

        with open(self.message_file_path, "r", encoding="utf-8") as file:
            messages = [line.strip() for line in file if line.strip()]

        for index, message in enumerate(messages):
            if not self.is_chat_running:
                break
            token = oauth_tokens[index % len(oauth_tokens)]  # Selección cíclica de tokens

            proxy = self.proxy_getter.get_proxy_as_dict()

            if not proxy:
                self.log("No proxy available.")
                return

            self.log(f"Using proxy: {proxy['server']}")

            self.send_message(server, port, token, message, proxy)
            self.total_messages.set(self.total_messages.get() + 1)
            time.sleep(self.interval.get())
        self.log("Stopped sending messages.")

    def send_message(self, server, port, token, message, proxy):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as irc:
                irc.connect((server, port))

                irc.send(f"PASS {token}\n".encode("utf-8"))
                irc.send("NICK bot\n".encode("utf-8"))
                irc.send(f"JOIN #{self.channel_name.get()}\n".encode("utf-8"))
                irc.send(f"PRIVMSG #{self.channel_name.get()} :{message}\n".encode("utf-8"))
                self.log(f"Sent message: {message} with token: {token} using proxy: {proxy['server']}")
        except Exception as e:
            self.log(f"Error: {e}")
            self.is_chat_running = False