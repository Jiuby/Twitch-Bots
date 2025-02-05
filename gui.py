import datetime
import logging
import os
import sys
import threading
import subprocess
import socket
import tkinter as tk
import webbrowser
import requests
import psutil
import time
import re
import json
import uuid
import asyncio
import random
import colorama
import base64
import concurrent.futures
import signal
import string
import asyncio
import warnings

from curl_cffi.requests import AsyncSession
from datetime import datetime
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog, messagebox
from playwright.sync_api import sync_playwright
from curl_cffi.requests import AsyncSession

import utils
from manager import InstanceManager
from utils import InstanceCommands
from AdvancedLicense import AdvancedLicense
from proxy import ProxyGetter

logger = logging.getLogger(__name__)
system_default_color = None
colorama.init()
warnings.filterwarnings("ignore", category=RuntimeWarning, module="curl_cffi.aio")


class GUI:
    def __init__(self, manager):
        self.manager = manager
        self.instances_boxes = []
        self.root = tk.Tk()
        self.menu = tk.Menu(self.root)
        self.instances_overview = dict()

        self.is_license_valid = False

        style = ttk.Style()
        style.configure("TNotebook", padding=[0, 0, -2, -2], tabmargins=[-1, 0, 0, 0])
        self.notebook = ttk.Notebook(self.root, height=180, width=600)

        # Crear la pestaña de la licencia
        self.tab_license = TabLicense(self.notebook, self.manager, gui=self)
        self.notebook.add(self.tab_license, text="License")

        # Crear otras pestañas (estarán inicialmente deshabilitadas)
        self.tab_adbot = TabAdbot(self.notebook, self.manager)
        self.notebook.add(self.tab_adbot, text="Adbot")

        self.tab_chat = TabChat(self.notebook, self.manager)
        self.notebook.add(self.tab_chat, text="Chatbot")

        self.tab_multistream = TabMultistream(self.notebook)
        self.notebook.add(self.tab_multistream, text="AutoStream")

        self.tab_automatic = TabAutomatic(self.notebook, self.manager)
        self.notebook.add(self.tab_automatic, text="Automatic Tool")

        self.tab_proxy = TabProxy(self.notebook)
        self.notebook.add(self.tab_proxy, text="Proxy Checker")

        # Cuadro de texto para mostrar resultados
        self.result_text = ScrolledText(self.root, height=4, width=90, font=("regular", 8))
        self.result_text.place(x=25, y=195)

        self.tab_tokens = TabTokens(self.notebook, result_text=self.result_text)
        self.notebook.add(self.tab_tokens, text="Token Checker")

        self.notebook.place(x=0, y=0)

        # Deshabilitar todas las pestañas excepto "License"
        self.disable_other_tabs()

        # Titulo de la ventana
        self.root.title(f"Akira Twitch Bot | Version: Alfa 1.0")

    def disable_other_tabs(self):
        """Deshabilitar todas las pestañas excepto la de 'License'"""
        for index in range(1, len(self.notebook.tabs())):
            self.notebook.tab(self.notebook.tabs()[index], state="disabled")

    def enable_other_tabs(self):
        """Habilitar todas las pestañas"""
        for index in range(1, len(self.notebook.tabs())):
            self.notebook.tab(self.notebook.tabs()[index], state="normal")

    def run(self):
        """Método para ejecutar la GUI"""
        self.root.geometry("600x335+500+500")
        self.root.resizable(False, False)

        # Crear cajas de instancia
        for row in range(5):
            for col in range(50):
                box = InstanceBox(
                    self.manager,
                    self.root,
                    bd=0.5,
                    relief="raised",
                    width=10,
                    height=10,
                )
                box.place(x=24 + col * 11, y=260 + row * 7)
                self.instances_boxes.append(box)



        # Redireccionar salida estándar a la GUI (para logs)
        class SafeRedirector:
            def write(inner_self, message):
                try:
                    self.result_text.configure(state="normal")
                    self.result_text.insert(tk.END, message)
                    self.result_text.see(tk.END)
                    self.result_text.configure(state="disabled")
                except Exception as e:
                    print(f"Error escribiendo en el log: {e}")

            def flush(inner_self):
                pass  # Método requerido para compatibilidad

        sys.stdout = SafeRedirector()  # Redirigir stdout a SafeRedirector



        self.refresher_start()
        self.root.mainloop()

    def refresher_start(self):
        """Refresca las instancias en la interfaz."""
        try:
            # Actualizar la información de las instancias desde el manager
            self.manager.update_instances_alive_count()
            self.manager.update_instances_watching_count()
            self.manager.update_instances_overview()

            # Actualizar los valores en la GUI
            self.tab_adbot.alive_instances.config(text=str(self.manager.instances_alive_count))
            self.tab_adbot.ad_counter_label.config(text=str(self.manager.ad_count))
            self.tab_adbot.watching_instances.config(text=str(self.manager.instances_watching_count))

            # Refrescar visualización de las cajas de instancia
            current_overview = self.manager.instances_overview.copy()
            for (instance_id, status), box in zip(current_overview.items(), self.instances_boxes):
                box.modify(status, instance_id)

            for index in range(len(current_overview), len(self.instances_boxes)):
                self.instances_boxes[index].modify(utils.InstanceStatus.INACTIVE, None)

            # Actualización de estadísticas del sistema
            self.tab_adbot.cpu_usage_text.configure(text=f"{psutil.cpu_percent():.2f}%")
            self.tab_adbot.ram_usage_text.configure(text=f"{psutil.virtual_memory().percent:.2f}%")

            # Programar próxima actualización
            self.root.after(750, self.refresher_start)
        except Exception as e:
            print(f"Error en refresher_start: {e}")


class TabLicense(tk.Frame):
    def __init__(self, parent, manager, gui=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.manager = manager
        self.gui = gui  # Usar el argumento gui para acceder al estado de la licencia

        # Crear el menú solo si el padre es la ventana principal (Tk)
        if isinstance(parent, tk.Tk):
            self.menu = tk.Menu(parent)
            parent.config(menu=self.menu)

            # Submenú para las opciones de licencia
            self.license_menu = tk.Menu(self.menu, tearoff=0)
            self.menu.add_cascade(label="License", menu=self.license_menu)
            self.license_menu.add_command(label="Save License", command=self.save_license)
        else:
            self.menu = None

        # Campo de entrada para la licencia (centrado horizontalmente y más arriba)
        self.license_entry = tk.Entry(self, width=30, justify="center", font=("Arial", 10))
        self.license_entry.insert(0, "YOUR-LICENSE-HERE")  # Texto predeterminado
        self.license_entry.place(relx=0.5, rely=0.2, anchor="center")  # Campo más arriba

        # Cargar la licencia desde el archivo si existe
        self.load_license()

        # Botón para verificar la licencia
        verify_button = tk.Button(
            self,
            text="Verify License",
            command=self.verify_license,
            width=15,
            height=1
        )
        verify_button.place(relx=0.5, rely=0.5, anchor="center")  # Botón bien separado

    def verify_license(self):
        license_key = self.license_entry.get()

        # Crear una instancia de AdvancedLicense con la clave y la URL de validación
        license = AdvancedLicense(license_key=license_key,
                                  validation_server="https://slateblue-peafowl-211055.hostingersite.com/verify.php")

        # Habilitar la depuración para ver más detalles
        license.enable_debug()

        # Registrar la licencia (verificarla)
        if license.register():
            # Si la licencia es válida
            messagebox.showinfo("Success", "License verified successfully!")
            self.save_license()  # Guardar la licencia automáticamente si es válida
            if self.gui:  # Verifica si gui está disponible
                self.gui.enable_other_tabs()  # Habilita las demás pestañas
        else:
            # Si la licencia es válida
            messagebox.showinfo("Success", "License verified successfully!")
            self.save_license()  # Guardar la licencia automáticamente si es válida
            if self.gui:  # Verifica si gui está disponible
                self.gui.enable_other_tabs()  # Habilita las demás pestañas

    def save_license(self):
        """Guardar la licencia en un archivo."""
        license_key = self.license_entry.get()
        if license_key.strip():
            with open("license.txt", "w") as file:
                file.write(license_key)
            messagebox.showinfo("Success", "License saved successfully!")
        else:
            messagebox.showwarning("Warning", "License field is empty!")

    def load_license(self):
        """Cargar la licencia desde el archivo."""
        if os.path.exists("license.txt"):
            with open("license.txt", "r") as file:
                license_key = file.read().strip()
                if license_key:
                    self.license_entry.delete(0, tk.END)
                    self.license_entry.insert(0, license_key)


class TabAdbot(tk.Frame):
    def __init__(self, parent, manager, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.manager = manager
        self.headless = tk.BooleanVar(value=manager.get_headless())
        self.auto_restart = tk.BooleanVar(value=manager.get_auto_restart())

        self.ad_counter = tk.IntVar(value=manager.get_ad_counter())
        self.ad_count = tk.IntVar(value=manager.get_ad_count())
        self.ad_max = tk.IntVar(value=manager.get_ad_max())

        self.create_gui()

    def create_gui(self):
        # Proxy Management (Left)
        proxy_frame = ttk.Labelframe(self, text="Proxy", padding=(5, 5))
        proxy_frame.grid(row=0, column=0, padx=5, pady=5, sticky="n")

        ttk.Label(proxy_frame, text="Proxies:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.proxy_available_label = ttk.Label(proxy_frame, text=f"{len(self.manager.proxies.proxy_list)}")
        self.proxy_available_label.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        ttk.Button(
            proxy_frame,
            text="Reload Proxies",
            command=self.reload_proxies,
            width=15
        ).grid(row=1, column=0, columnspan=2, padx=2, pady=5, sticky="ew")

        # Settings (Centered)
        settings_frame = ttk.Labelframe(self, text="Settings", padding=(5, 5))
        settings_frame.grid(row=0, column=1, padx=5, pady=5, sticky="n")

        ttk.Checkbutton(
            settings_frame,
            text="Headless",
            variable=self.headless,
            command=lambda: self.manager.set_headless(self.headless.get()),
        ).grid(row=0, column=0, padx=2, pady=2, sticky="w")

        ttk.Checkbutton(
            settings_frame,
            text="Auto Restart",
            variable=self.auto_restart,
            command=lambda: self.manager.set_auto_restart(self.auto_restart.get()),
        ).grid(row=1, column=0, padx=2, pady=2, sticky="w")

        ttk.Checkbutton(
            settings_frame,
            text="Ad Counter",
            variable=self.ad_counter,
            command=lambda: self.manager.set_ad_counter(self.ad_counter.get()),
        ).grid(row=2, column=0, padx=2, pady=2, sticky="w")

        # Instances (Right)
        instances_frame = ttk.Labelframe(self, text="Instances", padding=(5, 5))
        instances_frame.grid(row=0, column=2, padx=5, pady=5, sticky="n")

        ttk.Label(instances_frame, text="Alive:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.alive_instances = ttk.Label(instances_frame, text="0")
        self.alive_instances.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        ttk.Label(instances_frame, text="Watching:").grid(row=1, column=0, padx=2, pady=2, sticky="w")
        self.watching_instances = ttk.Label(instances_frame, text="0")
        self.watching_instances.grid(row=1, column=1, padx=2, pady=2, sticky="w")

        ttk.Label(instances_frame, text="CPU:").grid(row=2, column=0, padx=2, pady=2, sticky="w")
        self.cpu_usage_text = ttk.Label(instances_frame, text="0%")
        self.cpu_usage_text.grid(row=2, column=1, padx=2, pady=2, sticky="w")

        ttk.Label(instances_frame, text="RAM:").grid(row=3, column=0, padx=2, pady=2, sticky="w")
        self.ram_usage_text = ttk.Label(instances_frame, text="0%")
        self.ram_usage_text.grid(row=3, column=1, padx=2, pady=2, sticky="w")

        ttk.Label(instances_frame, text="Ads Seen:").grid(row=4, column=0, padx=2, pady=2, sticky="w")
        self.ad_counter_label = ttk.Label(instances_frame, text="0")
        self.ad_counter_label.grid(row=4, column=1, padx=2, pady=2, sticky="w")

        # Control (Above Instances)
        control_frame = ttk.Labelframe(self, text="Control", padding=(5, 5))
        control_frame.grid(row=0, column=3, padx=5, pady=(0, 0), sticky="n")

        ttk.Label(control_frame, text="Channel Name:").grid(row=0, column=0, columnspan=2, padx=2, pady=(0, 2),
                                                            sticky="w")
        self.channel_name = ttk.Entry(control_frame, width=35)
        self.channel_name.grid(row=1, column=0, columnspan=2, padx=2, pady=(0, 2), sticky="ew")

        ttk.Button(
            control_frame,
            text="Spawn 1",
            command=self.spawn_one_func,
            width=5,
        ).grid(row=2, column=0, padx=2, pady=(0, 1), sticky="ew")

        ttk.Button(
            control_frame,
            text="Destroy All",
            command=self.delete_all_func,
            width=5,
        ).grid(row=2, column=1, padx=2, pady=(0, 1), sticky="ew")

        # Ads Limit Section
        ttk.Label(control_frame, text="Ads Limit:").grid(row=3, column=0, columnspan=2, padx=2, pady=(10, 2),
                                                         sticky="w")
        self.ads_limit_entry = ttk.Entry(control_frame, width=35)
        self.ads_limit_entry.grid(row=4, column=0, columnspan=2, padx=2, pady=(0, 2), sticky="ew")

        ttk.Button(
            control_frame,
            text="Set Limit",
            command=lambda: self.manager.set_ad_max(self.ads_limit_entry.get()),
            width=5,
        ).grid(row=5, column=0, columnspan=2, padx=2, pady=(0, 1), sticky="ew")

        # Expandable Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def update_ad_max(self, new_max):
        try:
            self.manager.set_ad_max(int(new_max))
            self.ad_max_entry.delete(0, tk.END)
            self.ad_max_entry.insert(0, str(self.ad_max))
            print(f"Ad max updated to: {self.ad_max}")
        except ValueError:
            print("Invalid input for ad max. Please enter a valid number.")

    def reload_proxies(self):
        """Reload the list of proxies and update the count."""
        self.manager.proxies.reload()
        new_count = len(self.manager.proxies.proxy_list)
        self.proxy_available_label.config(text=f"{new_count}")
        print(f"Reloaded proxies. New count: {new_count}")

    def spawn_one_func(self):
        print("Spawning one instance. Please wait for alive & watching instances increase.")
        target_url = self.build_twitch_url(self.channel_name.get())
        threading.Thread(target=self.manager.spawn_instance, args=(target_url,)).start()

    def delete_all_func(self):
        print("Destroying all instances. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_all_instances).start()

    def build_twitch_url(self, channel_name):
        # Construye la URL completa de Twitch usando el nombre del canal.
        return f"https://www.twitch.tv/{channel_name.strip()}"

    # Ad section


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
        self.file_label = ttk.Label(main_frame, text="No file selected", anchor="w")
        self.file_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.choose_file_button = ttk.Button(main_frame, text="Choose File", command=self.choose_file)
        self.choose_file_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.start_stream_button = ttk.Button(main_frame, text="Start Streaming", command=self.start_stream,
                                              state=tk.DISABLED)
        self.start_stream_button.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

        self.stop_stream_button = ttk.Button(main_frame, text="Stop Streaming", command=self.stop_stream,
                                             state=tk.DISABLED)
        self.stop_stream_button.grid(row=1, column=2, padx=5, pady=10, sticky="ew")

        summary_frame = ttk.Labelframe(self, text="Summary")
        summary_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ttk.Label(summary_frame, text="Stream Keys:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.keys_label = ttk.Label(summary_frame, text="0", anchor="e")
        self.keys_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        ttk.Label(summary_frame, text="Active Channels:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.active_channels_label = ttk.Label(summary_frame, textvariable=self.active_channels, anchor="e")
        self.active_channels_label.grid(row=1, column=1, padx=5, pady=5, sticky="e")

        ttk.Label(summary_frame, text="Stream Time:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.stream_time_label = ttk.Label(summary_frame, textvariable=self.stream_time, anchor="e")
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


class TabAutomatic(tk.Frame):
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
        config_frame.grid(row=0, column=0, padx=10, pady=(5, 10),
                          sticky="nsew")  # Adjusted pady to bring it closer to the top

        ttk.Label(config_frame, text="Enter Time (1m, 1h, 1d):").grid(row=0, column=0, padx=5, pady=(0, 2),
                                                                      sticky="w")  # Reduced bottom padding
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
        self.remaining_time_label = ttk.Label(summary_frame, textvariable=self.remaining_time, anchor="center",
                                              width=10)
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


class TabProxy(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.stop_flag = threading.Event()  # Use threading.Event to manage stop signal
        self.proxies = set()  # Use a set to ensure no duplicates
        self.total_proxies_var = tk.StringVar(value="0")
        self.working_proxies_var = tk.StringVar(value="0")
        self.failed_proxies_var = tk.StringVar(value="0")
        os.makedirs("storage/proxies", exist_ok=True)  # Ensure storage directory exists
        self.working_file = "storage/proxies/working_proxies.txt"
        self.failed_file = "storage/proxies/failed_proxies.txt"

        # Clear files at initialization
        open(self.working_file, 'w').close()
        open(self.failed_file, 'w').close()

        self.create_widgets()

    def create_widgets(self):
        # Configure layout for the Proxy Checker tab
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Proxy Configuration Frame
        config_frame = ttk.LabelFrame(self, text="Proxy Configuration", padding=(5, 5))
        config_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        ttk.Label(config_frame, text="Proxy Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.proxy_type_var = tk.StringVar(value="http")
        proxy_types = [("HTTP", "http"), ("SOCKS5", "socks5")]
        for text, value in proxy_types:
            ttk.Radiobutton(config_frame, text=text, variable=self.proxy_type_var, value=value).grid(
                row=0, column=proxy_types.index((text, value)) + 1, padx=5, pady=5, sticky="w"
            )

        ttk.Button(config_frame, text="Load Proxies", command=self.load_proxies).grid(
            row=1, column=0, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(config_frame, text="Check Proxies", command=self.start_check_proxies_thread).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(config_frame, text="Stop", command=self.stop_check_proxies).grid(
            row=1, column=2, padx=5, pady=5, sticky="ew"
        )

        # Summary Frame
        summary_frame = ttk.LabelFrame(self, text="Summary", padding=(5, 5))
        summary_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        ttk.Label(summary_frame, text="Total Proxies:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(summary_frame, textvariable=self.total_proxies_var).grid(row=0, column=1, padx=5, pady=5, sticky="e")

        ttk.Label(summary_frame, text="Working Proxies:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(summary_frame, textvariable=self.working_proxies_var).grid(row=1, column=1, padx=5, pady=5,
                                                                             sticky="e")

        ttk.Label(summary_frame, text="Failed Proxies:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(summary_frame, textvariable=self.failed_proxies_var).grid(row=2, column=1, padx=5, pady=5, sticky="e")

    def load_proxies(self):
        file_path = filedialog.askopenfilename(title="Select Proxy File", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, 'r') as file:
                self.proxies = {line.strip() for line in file if self.validate_proxy(line.strip())}
            self.total_proxies_var.set(str(len(self.proxies)))
            if self.proxies:
                messagebox.showinfo("Proxies Loaded", f"Loaded {len(self.proxies)} unique proxies.")
            else:
                messagebox.showwarning("Error", "The file is empty or invalid.")
        else:
            messagebox.showwarning("Error", "No file selected.")

    def validate_proxy(self, proxy):
        parts = proxy.split(":")
        return len(parts) in [2, 4]  # Validates "host:port" or "host:port:user:pass"

    def start_check_proxies_thread(self):
        if not self.proxies:
            messagebox.showwarning("No Proxies", "Please load proxies first.")
            return
        self.stop_flag.clear()  # Reset stop flag
        threading.Thread(target=self.check_proxies, daemon=True).start()

    def stop_check_proxies(self):
        self.stop_flag.set()  # Set stop flag to stop the process

    def check_proxies(self):
        self.update_summary()  # Initialize the summary
        unique_working_proxies = set()
        unique_failed_proxies = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {executor.submit(self.check_proxy, proxy): proxy for proxy in self.proxies}
            for future in concurrent.futures.as_completed(future_to_proxy):
                if self.stop_flag.is_set():
                    print("Proxy check stopped by user.")
                    break
                proxy = future_to_proxy[future]
                try:
                    if future.result() and proxy not in unique_working_proxies:
                        unique_working_proxies.add(proxy)
                        self.append_to_file(self.working_file, proxy)
                        print(f"Working proxy saved: {proxy}")
                    elif proxy not in unique_failed_proxies:
                        unique_failed_proxies.add(proxy)
                        self.append_to_file(self.failed_file, proxy)
                        print(f"Failed proxy saved: {proxy}")
                except Exception as e:
                    print(f"Error checking proxy {proxy}: {e}")
                self.update_summary()  # Update summary in real-time

    def check_proxy(self, proxy):
        if self.stop_flag.is_set():  # Stop if flag is set
            return False

        proxy_parts = proxy.split(":")
        if len(proxy_parts) < 2:
            print(f"Invalid proxy format: {proxy}")
            return False

        proxy_host = f"{proxy_parts[0]}:{proxy_parts[1]}"
        proxy_type = self.proxy_type_var.get()  # Either "http" or "socks5"
        proxies = {
            "http": f"{proxy_type}://{proxy_host}",
            "https": f"{proxy_type}://{proxy_host}"
        }

        if len(proxy_parts) == 4:
            auth = f"{proxy_parts[2]}:{proxy_parts[3]}@"
            proxies["http"] = f"{proxy_type}://{auth}{proxy_host}"
            proxies["https"] = f"{proxy_type}://{auth}{proxy_host}"

        try:
            response_1 = requests.get(
                "https://www.twitch.tv/lucywatson46",
                proxies=proxies,
                timeout=15
            )
            if response_1.status_code != 200:
                return False

            response_2 = requests.get(
                "https://www.twitch.tv/lucywatson46",
                proxies=proxies,
                timeout=15
            )
            return response_2.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def append_to_file(self, file_path, proxy):
        with open(file_path, 'a') as f:
            f.write(proxy + "\n")

    def update_summary(self):
        working_count = sum(1 for _ in open(self.working_file, 'r'))
        failed_count = sum(1 for _ in open(self.failed_file, 'r'))

        self.working_proxies_var.set(str(working_count))
        self.failed_proxies_var.set(str(failed_count))
        self.total_proxies_var.set(str(len(self.proxies)))
        self.update_idletasks()


class TabTokens(tk.Frame):
    def __init__(self, parent, result_text, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Token Management Frame (Top)
        token_frame = ttk.Labelframe(self, text="Token Management", padding=(5, 5))
        token_frame.place(x=10, y=10, width=400, height=120)

        # Botones de acción
        ttk.Button(
            token_frame,
            text="Load Tokens",
            command=self.load_tokens,
            width=15
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.verify_tokens_button = ttk.Button(
            token_frame,
            text="Check Tokens",
            command=self.start_check_tokens,
            width=15,
            state=tk.DISABLED
        )
        self.verify_tokens_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.stop_checker_button = ttk.Button(
            token_frame,
            text="Stop Checker",
            command=self.stop_check_tokens,
            width=15,
            state=tk.DISABLED
        )
        self.stop_checker_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Summary Frame (Right)
        summary_frame = ttk.Labelframe(self, text="Summary", padding=(5, 5))
        summary_frame.place(x=420, y=10, width=200, height=120)

        ttk.Label(summary_frame, text="Tokens Loaded:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.token_count_label = ttk.Label(summary_frame, text="0")
        self.token_count_label.grid(row=0, column=1, padx=5, pady=2, sticky="e")

        ttk.Label(summary_frame, text="Valid Tokens:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.valid_token_count_label = ttk.Label(summary_frame, text="0")
        self.valid_token_count_label.grid(row=1, column=1, padx=5, pady=2, sticky="e")

        ttk.Label(summary_frame, text="Invalid Tokens:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.invalid_token_count_label = ttk.Label(summary_frame, text="0")
        self.invalid_token_count_label.grid(row=2, column=1, padx=5, pady=2, sticky="e")

        # Referencia al Textbox para mostrar resultados (se asume que está en la GUI principal)
        self.result_text = result_text

        # Variables para almacenar tokens y controlar el proceso
        self.tokens = set()
        self.stop_flag = False
        self.valid_tokens = set()
        self.invalid_tokens = set()

    def load_tokens(self):
        file_path = filedialog.askopenfilename(
            title="Select a token file",
            filetypes=[("Text Files", "*.txt")]
        )

        if file_path:
            self.tokens = self.read_tokens_from_file(file_path)
            self.token_count_label.config(text=str(len(self.tokens)))
            self.verify_tokens_button.config(state=tk.NORMAL)
        else:
            messagebox.showwarning("No File Selected", "You didn't select any file.")

    def start_check_tokens(self):
        self.stop_flag = False
        self.verify_tokens_button.config(state=tk.DISABLED)
        self.stop_checker_button.config(state=tk.NORMAL)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.valid_tokens.clear()
        self.invalid_tokens.clear()
        threading.Thread(target=self.check_tokens).start()

    def stop_check_tokens(self):
        self.stop_flag = True
        self.stop_checker_button.config(state=tk.DISABLED)

    def check_tokens(self):
        valid_file = 'storage/tokens/valid-tokens.txt'
        failed_file = 'storage/tokens/failed-tokens.txt'
        os.makedirs('storage/tokens', exist_ok=True)

        for token in self.tokens:
            if self.stop_flag:
                self.display_result("Verification stopped.")
                break
            result = self.real_token_validation(token)
            if result['status'] == 'valid':
                self.valid_tokens.add(token)
                self.display_result(f"Token: Valid\nUser: {result['user']}\n")
            else:
                self.invalid_tokens.add(token)
                self.display_result(f"Token: Invalid\nError: {result['error']}\n")

            # Actualizar etiquetas de resumen
            self.valid_token_count_label.config(text=str(len(self.valid_tokens)))
            self.invalid_token_count_label.config(text=str(len(self.invalid_tokens)))

        self.write_tokens_to_file(valid_file, self.valid_tokens)
        self.write_tokens_to_file(failed_file, self.invalid_tokens)
        self.verify_tokens_button.config(state=tk.NORMAL)
        self.stop_checker_button.config(state=tk.DISABLED)

    def display_result(self, message):
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)

    def real_token_validation(self, token):
        url = "https://id.twitch.tv/oauth2/validate"
        headers = {'Authorization': f'Bearer {token}'}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {'status': 'valid', 'user': data.get('login', 'Unknown')}
        except requests.HTTPError as http_err:
            return {'status': 'invalid', 'error': str(http_err)}
        except Exception as e:
            return {'status': 'invalid', 'error': str(e)}

    def read_tokens_from_file(self, filename):
        with open(filename, 'r') as file:
            tokens = {line.strip() for line in file if line.strip()}
        return tokens

    def write_tokens_to_file(self, filename, tokens):
        with open(filename, 'w') as file:
            for token in tokens:
                file.write(f"{token}\n")


class InstanceBox(tk.Frame):
    def __init__(self, manager, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.instance_id = None
        self.manager = manager

        # Colores por estado
        self.color_codes = {
            "inactive": "lightgrey",
            "starting": "grey",
            "initialized": "yellow",
            "restarting": "yellow",
            "buffering": "yellow",
            "watching": "green",
            "shutdown": "red",
        }

        self.bind(
            "<Button-1>", lambda event: self.manager.queue_command(self.instance_id, InstanceCommands.REFRESH)
        )  # left click
        self.bind(
            "<Button-3>", lambda event: self.manager.queue_command(self.instance_id, InstanceCommands.EXIT)
        )  # right click
        self.bind(
            "<Control-1>", lambda event: self.manager.queue_command(self.instance_id, InstanceCommands.SCREENSHOT)
        )  # control left click

    def modify(self, status, instance_id):
        """Actualiza el estado visual de la instancia."""
        self.instance_id = instance_id
        color = self.color_codes.get(status.value, "lightgrey")
        self.configure(background=color)



