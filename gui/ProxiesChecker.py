import os
import threading
import concurrent.futures
import requests
from tkinter import ttk, filedialog, messagebox
import tkinter as tk

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
        ttk.Label(summary_frame, textvariable=self.working_proxies_var).grid(row=1, column=1, padx=5, pady=5, sticky="e")

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