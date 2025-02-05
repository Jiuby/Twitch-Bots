import tkinter as tk
from tkinter import messagebox
import os

#from libs.utils.AdvancedLicense import AdvancedLicense


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
                self.gui.enable_other_tabs()  # Habilita las demás pestaña

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