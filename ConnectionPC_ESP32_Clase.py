"""
Módulo de conexión ESP32 - PC
Proporciona la clase ESP32Connection para manejar comunicación WiFi
"""

import socket
import threading

from PySide6.QtCore import QObject, Signal

class ESP32Connection(QObject):
    """
    Clase para manejar la conexión WiFi entre PC y ESP32

    Señales:
        connection_status_changed(bool): Emitida cuando cambia el estado de conexión
        data_received(str): Emitida cuando se reciben datos del ESP32

    Métodos públicos:
        connect(): Establece conexión con el ESP32
        disconnect(): Cierra la conexión
        send_data(data): Envía datos al ESP32
        is_connected(): Retorna estado de conexión
    """

    # Señales para comunicar cambios a la UI
    connection_status_changed = Signal(bool)
    data_received = Signal(str)

    def __init__(self, esp32_ip, esp32_port=8888):
        """
        Inicializa la conexión

        Args:
            esp32_ip: Dirección IP del ESP32 (ej: "192.168.0.102")
            esp32_port: Puerto de comunicación (default: 8888)
        """
        super().__init__()
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.socket = None
        self.connected = False
        self.running = False
        self.receive_thread = None

    def connect(self):
        """Establece conexión persistente con el ESP32"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Timeout para conexión inicial
            self.socket.connect((self.esp32_ip, self.esp32_port))
            self.socket.settimeout(None)  # Sin timeout para comunicación continua

            self.connected = True
            self.running = True
            self.connection_status_changed.emit(True)

            # Iniciar hilo para recibir datos
            self.receive_thread = threading.Thread(target=self._receive_data,
                                                   daemon=True)
            self.receive_thread.start()

            print(f"✅ Conectado al ESP32 en {self.esp32_ip}:{self.esp32_port}")
            return True

        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            self.connected = False
            self.connection_status_changed.emit(False)
            return False

    def _receive_data(self):
        """Hilo interno para recibir datos del ESP32 continuamente"""
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024)
                if data:
                    message = data.decode('utf-8').strip()
                    self.data_received.emit(message)
                else:
                    print("⚠️ ESP32 cerró la conexión")
                    self.disconnect()
                    break

            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ Error al recibir datos: {e}")
                self.disconnect()
                break

    def send_data(self, data):
        """
        Envía datos al ESP32

        Args:
            data: String o datos a enviar

        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        if self.connected and self.socket:
            try:
                self.socket.sendall(f"{data}\n".encode('utf-8'))
                print(f"📤 Datos enviados: {data}")
                return True
            except Exception as e:
                print(f"❌ Error al enviar datos: {e}")
                self.disconnect()
                return False
        return False

    def disconnect(self):
        """Cierra la conexión con el ESP32"""
        self.running = False
        self.connected = False

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        self.connection_status_changed.emit(False)
        print("🔌 Conexión cerrada")

    def is_connected(self):
        """Retorna el estado actual de la conexión"""
        return self.connected