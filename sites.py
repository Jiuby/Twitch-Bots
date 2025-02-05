import datetime
import json
import logging
import os
from random import choice
import time

import utils
from instance import Instance

logger = logging.getLogger(__name__)


class Twitch(Instance):
    site_name = "TWITCH"
    site_url = "twitch.tv"
    login_css = 'button[data-a-target=login-button]'  # Selector del botón de login
    cookie_auth = {
        'name': 'auth-token',  # Nombre de la cookie que almacenará el token
        'value': None,  # Este será el token que se inyectará
        'domain': '.twitch.tv',
        'path': '/',
    }
    cookie_css = "button[data-a-target=consent-banner-accept]"  # Selector para aceptar cookies
    local_storage = {
        "mature": "true",
        "video-muted": '{"default": "false"}',
        "volume": "0.5",
        "video-quality": '{"default": "160p30"}',
        "lowLatencyModeEnabled": "false",
    }
    token_file_path = os.path.join("settings", "twitch_token_list.txt")  # Ruta del archivo de tokens
    token_index = 0  # Contador de tokens para asignar uno a cada instancia

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.twitch_token = self.load_token()  # Cargar el token correspondiente a la instancia

    @classmethod
    def load_token(cls):
        """
        Carga los tokens desde el archivo y devuelve el token correspondiente según el índice.
        """
        if not os.path.exists(cls.token_file_path):
            logger.error(f"El archivo {cls.token_file_path} no existe.")
            return None

        with open(cls.token_file_path, "r") as file:
            tokens = file.readlines()

        # Limpiar los tokens eliminando saltos de línea y espacios innecesarios
        tokens = [token.strip() for token in tokens if token.strip()]

        if tokens:  # Verificar si hay tokens disponibles
            if cls.token_index < len(tokens):
                token = tokens[cls.token_index]  # Obtener el token según el índice actual
                logger.info(f"Usando el token #{cls.token_index + 1} para esta instancia.")
                cls.token_index += 1  # Aumentar el índice para la siguiente instancia
                return token
            else:
                logger.warning("No hay más tokens disponibles para asignar a esta instancia.")
                return None  # No hay tokens restantes
        else:
            logger.warning("El archivo de tokens está vacío o no contiene tokens válidos.")
            return None

    def todo_after_load(self):
        self.page.wait_for_selector(".persistent-player", timeout=30000)
        self.page.wait_for_timeout(1000)
        self.page.keyboard.press("Alt+t")

    def update_status(self):
        current_time = datetime.datetime.now()
        if not self.status_info:
            self.status_info = {
                "last_active_resume_time": 0,
                "last_active_timestamp": current_time - datetime.timedelta(seconds=10),
                "last_stream_id": None,
            }

        # Si la transmisión fue activa hace menos de 30 segundos, sigue activa (aumentado de 10 a 30 segundos)
        time_since_last_activity = current_time - self.status_info["last_active_timestamp"]
        if time_since_last_activity < datetime.timedelta(seconds=30):  # Aumentado de 10 a 30 segundos
            logger.info(f"Instancia activa. Última actividad hace {time_since_last_activity.seconds} segundos.")
            self.status = utils.InstanceStatus.WATCHING
            return

        # Obtener el tiempo actual de reanudación de la transmisión desde el localStorage
        fetched_resume_times = self.page.evaluate("window.localStorage.getItem('livestreamResumeTimes');")
        logger.info(f"livestreamResumeTimes: {fetched_resume_times}")

        if fetched_resume_times:
            resume_times_dict = json.loads(fetched_resume_times)
            current_stream_id = list(resume_times_dict.keys())[-1]
            current_resume_time = list(resume_times_dict.values())[-1]

            # Si es la primera vez, establece el stream id
            if not self.status_info["last_stream_id"]:
                self.status_info["last_stream_id"] = current_stream_id

            # Si el stream ha cambiado, restablecer el tiempo de reanudación
            if current_stream_id != self.status_info["last_stream_id"]:
                logger.info(f"Stream cambiado de {self.status_info['last_stream_id']} a {current_stream_id}")
                self.status_info["last_stream_id"] = current_stream_id
                self.status_info["last_active_resume_time"] = 0

            # Si el tiempo actual de reanudación ha avanzado, actualiza el estado
            if current_resume_time > self.status_info["last_active_resume_time"]:
                self.status_info["last_active_timestamp"] = current_time
                self.status_info["last_active_resume_time"] = current_resume_time
                logger.info("Reanudación de transmisión detectada, cambiando a WATCHING.")
                self.status = utils.InstanceStatus.WATCHING
                return

        # Verificar si el reproductor persistente está presente como condición adicional
        player_exists = self.page.evaluate("document.querySelector('.persistent-player') !== null;")
        if player_exists:
            logger.info("Reproductor cargado, cambiando a estado WATCHING.")
            self.status = utils.InstanceStatus.WATCHING
            return

        # Si no se cumplen las condiciones anteriores, el stream está en "buffering"
        logger.info("No hay actividad reciente, la instancia está en BUFFERING.")
        self.status = utils.InstanceStatus.BUFFERING

    def todo_after_spawn(self):
        # Escoger una URL de referencia aleatoria de la lista
        referrer_urls = [
            "https://www.twitch.tv/directory/all",
            "https://www.twitch.tv/directory/following",
            "https://www.twitch.tv/directory/category/valorant",
            "https://www.twitch.tv/directory/category/league-of-legends",
            "https://www.twitch.tv/directory/category/just-chatting",
            "https://www.youtube.com/",
            "https://x.com/",
        ]

        selected_referrer = choice(referrer_urls)
        logger.info(f"Navegando a la URL de referencia: {selected_referrer}")
        self.goto_with_retry(selected_referrer)
        self.page.wait_for_timeout(2000)  # Esperar un tiempo breve para simular el comportamiento del usuario

        # Navegar a la página objetivo
        self.goto_with_retry("https://www.twitch.tv/m3xicang0d_")

        # Verificar si hay un token disponible
        if self.twitch_token:
            logger.info(f"Inyectando el token de autenticación en cookies: {self.twitch_token}")
            self.cookie_auth['value'] = self.twitch_token  # Asignar el token a las cookies
            self.page.context.add_cookies([self.cookie_auth])  # Agregar las cookies al contexto de la página
        else:
            logger.warning("No hay token disponible para esta instancia. Continuando sin autenticación.")

        # Configurar otros valores en el localStorage
        for key, value in self.local_storage.items():
            tosend = """window.localStorage.setItem('{key}','{value}');""".format(key=key, value=value)
            self.page.evaluate(tosend)

        # Tamaño de la ventana
        self.page.set_viewport_size(
            {
                "width": 1280,
                "height": 720,
            }
        )
        self.page.wait_for_timeout(3000)

        # Intentar navegar a la URL de destino
        self.goto_with_retry(self.target_url)
        self.page.wait_for_timeout(1000)

        # Si hay un botón de login, hacer clic en él solo si hay un token disponible
        if self.twitch_token:
            try:
                logger.info("Intentando hacer clic en el botón de login si está presente.")
                self.page.click(self.login_css, timeout=3000)
            except:
                logger.info("No se encontró o no se hizo clic en el botón de login.")
        else:
            logger.info("No se intentará hacer login ya que no hay un token disponible para esta instancia.")

        # Esperar al reproductor persistente
        self.page.wait_for_selector(".persistent-player", timeout=15000)
        self.page.keyboard.press("Alt+t")
        self.page.wait_for_timeout(1000)

        # Intentar hacer clic en el botón de contenido maduro
        try:
            self.page.click(
                "button[data-a-target=content-classification-gate-overlay-start-watching-button]", timeout=3000
            )
        except:
            logger.info("No se encontró o no se hizo clic en el botón de contenido maduro.")

        self.page.set_viewport_size(
            {
                "width": self.location_info["width"],
                "height": self.location_info["height"],
            }
        )

        # Establecer el estado como inicializado
        self.status = utils.InstanceStatus.INITIALIZED
        print("Iniciando verificacion de anuncios")
        start_time = time.time()
        while self.manager.get_ad_counter() and self.manager.get_ad_count() < self.manager.get_ad_max():
            try:
                if self.auto_restart and time.time() - start_time > 900:
                    print(f"[INFO] [Instance {self.id}] Restarting instance after 15 minutes.")
                    break

                ad_elements = self.page.locator(
                    "//div[contains(@class, 'ad-container')] | //span[contains(text(), 'Anuncio')]")
                if ad_elements.count() > 0:
                    self.manager.set_ad_count(self.manager.get_ad_count() + 1)
                    print(f"[INFO] [Instance {self.id}] Ad detected. Waiting for it to finish.")
                    while ad_elements.count() > 0:
                        time.sleep(1)
                        ad_elements = self.page.locator(
                            "//div[contains(@class, 'ad-container')] | //span[contains(text(), 'Anuncio')]")

                    # self.ad_count += 1
                    print(
                        f"[INFO] [Instance {self.id}] Ad completed ({self.manager.get_ad_count()}/{self.manager.get_ad_max()}).")
                    if self.manager.get_ad_count() >= self.manager.get_ad_max():
                        print(f"[INFO] Monitoring completed. Total ads watched: {self.manager.get_ad_count()}")
                        # self.monitoring_active = False
                        exit(0)
                        break
                else:
                    refresh_button = self.page.locator(
                        "//button[contains(text(), 'Actualizar reproductor')] | //div[contains(@class, 'player-error-message')]//button")
                    if refresh_button.count() > 0:
                        print(f"[INFO] [Instance {self.id}] Network error detected. Clicking the refresh button.")
                        refresh_button.first.click()
                        time.sleep(5)
                    else:
                        time.sleep(5)
            except Exception as e:
                print(f"[ERROR] [Instance {self.id}] Ad detection error: {e}")
                break

