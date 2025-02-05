import os  # Para manejo de rutas y operaciones del sistema
import sys  # Para redireccionar stdout
import threading  # Para hilos concurrentes
import tkinter as tk  # Para la creación de la GUI principal
from tkinter import ttk  # Para widgets estilizados
from tkinter.scrolledtext import ScrolledText  # Para el cuadro de texto con desplazamiento
import webbrowser  # Para abrir enlaces en el navegador
import psutil  # Para obtener estadísticas de CPU y RAM
import warnings  # Para suprimir advertencias innecesarias

import utils
from manager import InstanceManager
from utils import InstanceCommands

from gui.License import TabLicense
from gui.Chatbot import TabChat
from gui.Autostream import TabMultistream
from gui.ProxiesChecker import TabProxy
from gui.TokenChecker import TabTokens
from gui.OFFTool import TabOFFTool
from gui.adbot import TabAdbot


class MENU:
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

        self.tab_offtool = TabOFFTool(self.notebook, self.manager)
        self.notebook.add(self.tab_offtool, text="OFF Tool")

        self.tab_proxy = TabProxy(self.notebook)
        self.notebook.add(self.tab_proxy, text="Proxy Checker")

        self.result_text = ScrolledText(self.root, height=7, width=92, font=("regular", 8))
        self.result_text.place(x=20, y=145)

        self.tab_tokens = TabTokens(self.notebook, result_text=self.result_text)
        self.notebook.add(self.tab_tokens, text="Token Checker")

        self.notebook.place(x=0, y=0)

        # Deshabilitar todas las pestañas excepto "License"
        self.disable_other_tabs()

        # Titulo de la ventana
        self.root.title(f"Akira666 Twitch Bot |  Version: Alfa 1.0")

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
        text_area = ScrolledText(self.root, height="7", width="92", font=("regular", 8))
        text_area.place(x=20, y=145)

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
                box.place(x=24 + col * 11, y=255 + row * 12)
                self.instances_boxes.append(box)



        # Redireccionar salida estándar a la GUI (para logs)
        class SafeRedirector:
            def write(self, message):
                try:
                    text_area.configure(state="normal")
                    text_area.insert(tk.END, message)
                    text_area.see(tk.END)
                    text_area.configure(state="disabled")
                except Exception:
                    pass  # Ignorar errores si no se puede redirigir

            def flush(self):
                pass  # Método requerido para compatibilidad

        sys.stdout = SafeRedirector()  # Redirigir stdout a SafeRedirector
        self.refresher_start()
        self.root.mainloop()

    def refresher_start(self):
        """Refresca las instancias en la interfaz."""
        # Actualizar la información de las instancias desde el manager
        self.manager.update_instances_alive_count()
        self.manager.update_instances_watching_count()
        self.manager.update_instances_overview()

        # Actualizar los valores en la GUI
        self.tab_adbot.alive_instances.config(text=str(self.manager.instances_alive_count))
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
