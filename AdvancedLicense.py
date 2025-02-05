import requests
import logging
import uuid
from enum import Enum

class ValidationType(Enum):
    WRONG_RESPONSE = "WRONG_RESPONSE"
    PAGE_ERROR = "PAGE_ERROR"
    URL_ERROR = "URL_ERROR"
    KEY_OUTDATED = "KEY_OUTDATED"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    NOT_VALID_IP = "NOT_VALID_IP"
    INVALID_PLUGIN = "INVALID_PLUGIN"
    VALID = "VALID"

class AdvancedLicense:
    def __init__(self, license_key, validation_server, security_key="YecoF0I6M05thxLeokoHuW8iUhTdIUInjkfF", debug=False):
        self.license_key = license_key
        self.validation_server = validation_server
        self.security_key = security_key
        self.debug = debug
        self.log_level = logging.INFO
        logging.basicConfig(level=self.log_level)

    def set_security_key(self, security_key):
        self.security_key = security_key
        return self

    def set_log_level(self, log_level):
        self.log_level = log_level
        logging.basicConfig(level=log_level)
        return self

    def enable_debug(self):
        self.debug = True
        return self

    def register(self):
        self._log("Connecting to License Server...")
        validation_type = self._is_valid()
        if validation_type == ValidationType.VALID:
            self._log("License valid!")
            return True
        else:
            self._log(f"License is NOT valid! Failed due to {validation_type}")
            return False

    def is_valid_simple(self):
        return self._is_valid() == ValidationType.VALID

    def _request_server(self, v1, v2):
        try:
            url = f"{self.validation_server}?v1={v1}&v2={v2}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            if self.debug:
                self._log(f"Sent GET request to {url}, Response Code: {response.status_code}")
            return response.text
        except requests.RequestException as e:
            if self.debug:
                self._log(f"Error during HTTP request: {e}")
            return ""

    def _is_valid(self):
        rand = self._to_binary(str(uuid.uuid4()))
        sKey = self._to_binary(self.security_key)
        key = self._to_binary(self.license_key)

        response = self._request_server(self._xor(rand, sKey), self._xor(rand, key))

        # Limpiar la respuesta eliminando saltos de línea y espacios innecesarios
        response = response.strip()

        # Si la respuesta es un error conocido, manejarlo
        if response.startswith("<"):
            self._log("The License Server returned an invalid response!")
            return ValidationType.PAGE_ERROR

        try:
            # Intentar acceder al miembro del Enum correspondiente
            return ValidationType[response]
        except KeyError:
            # Si no se encuentra, revisar si la respuesta tiene un formato esperado
            respRand = self._xor(self._xor(response, key), sKey)
            if rand.startswith(respRand):
                return ValidationType.VALID
            else:
                return ValidationType.WRONG_RESPONSE

    def _xor(self, s1, s2):
        return ''.join(str(int(b1) ^ int(b2)) for b1, b2 in zip(s1, s2))

    def _to_binary(self, s):
        return ''.join(format(ord(c), '08b') for c in s)

    def _log(self, message):
        if self.log_level == logging.DEBUG and not self.debug:
            return
        logging.log(self.log_level, message)
