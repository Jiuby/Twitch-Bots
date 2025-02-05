import os  # Para manejar rutas y crear directorios
import threading  # Para manejar hilos y ejecutar tareas en segundo plano
import requests  # Para realizar solicitudes HTTP a la API de validación de tokens
from tkinter import ttk, filedialog, messagebox  # Para widgets de la GUI y diálogos
import tkinter as tk  # Para componentes principales de la interfaz gráfica


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
