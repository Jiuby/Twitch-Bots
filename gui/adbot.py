import threading
import tkinter as tk
from tkinter import ttk


class TabAdbot(tk.Frame):
    def __init__(self, parent, manager, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.manager = manager
        self.headless = tk.BooleanVar(value=manager.get_headless())
        self.auto_restart = tk.BooleanVar(value=manager.get_auto_restart())
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

        # Control (Above Instances)
        control_frame = ttk.Labelframe(self, text="Control", padding=(5, 5))
        control_frame.grid(row=0, column=3, padx=5, pady=(0, 0), sticky="n")

        ttk.Label(control_frame, text="Channel Name:").grid(row=0, column=0, columnspan=2, padx=2, pady=(0, 2), sticky="w")
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
            text="Spawn 3",
            command=self.spawn_three_func,
            width=5,
        ).grid(row=2, column=1, padx=2, pady=(0, 1), sticky="ew")

        ttk.Button(
            control_frame,
            text="Destroy 1",
            command=self.delete_one_func,
            width=5,
        ).grid(row=3, column=0, padx=2, pady=(0, 1), sticky="ew")

        ttk.Button(
            control_frame,
            text="Destroy All",
            command=self.delete_all_func,
            width=5,
        ).grid(row=3, column=1, padx=2, pady=(0, 1), sticky="ew")

        # Expandable Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

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

    def spawn_three_func(self):
        print("Spawning three instances. Please wait for alive & watching instances increase.")
        target_url = self.build_twitch_url(self.channel_name.get())
        threading.Thread(target=self.manager.spawn_instances, args=(3, target_url)).start()

    def delete_one_func(self):
        print("Destroying one instance. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_latest).start()

    def delete_all_func(self):
        print("Destroying all instances. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_all_instances).start()

    def build_twitch_url(self, channel_name):
        """Construye la URL completa de Twitch usando el nombre del canal."""
        return f"https://www.twitch.tv/{channel_name.strip()}"