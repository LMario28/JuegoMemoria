import os
import sys

if sys.platform == "linux":
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6 import QtWidgets as qtw
from PySide6.QtWidgets import (QMainWindow, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QFileDialog)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from pathlib import Path

# Importar la UI generada por Qt Designer
# from JuegoMemoriaUI_Ampliada import Ui_MainWindow
from JuegoMemoriaUI_Ampliada_Casa import Ui_MainWindow

# Importar la clase de conexión ESP32
from ConnectionPC_ESP32_Clase import ESP32Connection

# Importar la clase para el manejo de los archivos Excel
import openpyxl

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        # ========== CONFIGURACIÓN DEL ESP32 ==========
        # CAMBIAR ESTA IP por la real del ESP32
        #self.ESP32_IP = "192.168.0.111"
        # CASA
        self.ESP32_IP = "192.168.1.110"
        self.ESP32_PORT = 8888
        # =============================================

        # ========== VARIABLES DEL JUEGO ==========
        self.ronda_actual = 1                     # Ronda actual (empieza en 1)
        self.nivel_actual_juego = 1               # Nivel actual (empieza en 4)
        self.concurso_activo = False
        self.indice_competidor_actual= 0
        self.lista_competidores = []
        self.ronda_terminada = False
        self.oportunidades_usadas = {}            # dict para rastrear oportunidades por jugador
        # === VARIABLES PARA EL SISTEMA DE VUELTAS ===
        self.cola_fallidos = []                   # Jugadores que fallaron y esperan otra oportunidad
        self.en_vuelta_actual = False             # Si estamos en una vuelta (no al final)
        self.lista_competidores_original = []     # Guardar lista completa para referencia

        # El nivel se calcula: NIVEL = RONDA + 3
        # =========================================

        # Configurar la interfaz de usuario (diseñada en Qt Designer)
        self.setupUi(self)

        # Configurar ventana
        self.setWindowTitle("Programación Visual - Proyecto Juego de Memoria")

        # Configurar rutas de imágenes
        self._setup_image_paths()

        # ========== CONFIGURAR TABLA =================
        self._configurar_tabla()  # ← LLAMAR AQUÍ
        self._cargar_datos_iniciales()  # ← LLAMAR AQUÍ
        # =============================================

        # Inicializar la conexión con el ESP32
        self.esp32 = ESP32Connection(self.ESP32_IP, self.ESP32_PORT)
        self.esp32.connection_status_changed.connect(self._on_connection_changed)
        self.esp32.data_received.connect(self._on_data_received)

        # Conectar las señales de los componentes de la UI (si los hubiera)
        self._setup_connections()

        # Mostrar nivel y ronda inicial en la UI
        self._actualizar_ui_completa()

        # Intentar conectar automáticamente después de 1 segundo
        QTimer.singleShot(1000, self._attempt_connection)

        # El botón debe estar activado al inicio
        self.pushButton_empezar_concurso.setEnabled(True)
        self.pushButton_empezar_concurso.setText("Empezar Concurso")
        self.pushButton_empezar_concurso.setStyleSheet("color: rgb(0, 80, 0);")

        self.show()

        # Ventana maximizada
        self.showMaximized()

        # ==================== MÉTODOS DE CONFIGURACIÓN DE TABLA ====================
    def _configurar_tabla(self):
        """Configuración básica de la tabla - DENTRO DE LA CLASE"""
        from PySide6.QtWidgets import QHeaderView, QAbstractItemView

        # Configurar el header
        header = self.tableWidget_Competidores.horizontalHeader()

        # Permitir que el usuario redimensione las columnas
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Configurar selección de filas completas
        self.tableWidget_Competidores.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget_Competidores.setSelectionMode(QAbstractItemView.SingleSelection)

        # Alternar colores de filas
        self.tableWidget_Competidores.setAlternatingRowColors(True)

        # Deshabilitar edición (solo visualización)
        self.tableWidget_Competidores.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def _ajustar_anchos_columnas(self):
        """Ajusta el ancho de las columnas - DENTRO DE LA CLASE"""
        from PySide6.QtWidgets import QHeaderView

        # Ajuste automático al contenido
        self.tableWidget_Competidores.resizeColumnsToContents()

        # Asegurar un ancho mínimo para cada columna
        header = self.tableWidget_Competidores.horizontalHeader()
        anchos_minimos = [150, 120, 130, 60]  # Apellidos, Nombre, Carrera, Grupo

        for col, ancho_min in enumerate(anchos_minimos):
            ancho_actual = self.tableWidget_Competidores.columnWidth(col)
            if ancho_actual < ancho_min:
                self.tableWidget_Competidores.setColumnWidth(col, ancho_min)

        # La última columna se estira
        header.setStretchLastSection(True)

    def _cargar_desde_excel(self, ruta_archivo):
        try:
            import openpyxl
            from PySide6.QtWidgets import QTableWidgetItem

            wb = openpyxl.load_workbook(ruta_archivo, data_only=True)
            hoja = wb.active

            # Limpiar lista anterior
            self.lista_competidores = []

            # Leer datos (asumiendo fila 1 = encabezados)
            for fila in hoja.iter_rows(min_row=2, values_only=True):
                if fila[0] is not None:
                    # Guardar como diccionario
                    competidor = {
                        'apellidos': fila[0],
                        'nombre': fila[1],
                        'carrera': fila[2],
                        'grupo': fila[3],
                        'op1': '',               # Primera oportunidad. Se usa en todas las rondas
                        'op2': '',               # Segunda oportunidad. Se usa en las rondas 3 y 4
                        'op3': '',               # Tercera oportunidad. Se usa de la ronda 5 en adelante
                        # === HISTORIAL DE RESULTADOS ===
                        'resultados': [],        # Lista: ["✓", "✗", "✓", ...] para cada ronda
                        'rondas_ganadas': 0,     # Contador de rondas ganadas
                        'nivel_maximo': 0,       # Nivel más alto alcanzado
                        'detalle_rondas': [],    # Números de rondas que ganó
                        # ================================
                        'comentarios': '',
                        'activo': True,
                    }
                    self.lista_competidores.append(competidor)

            self._actualizar_tabla()
            print(f"✅ Cargados {len(self.lista_competidores)} competidores")
            return True


        except Exception as e:
            print(f"❌ Error al cargar Excel: {e}")
            return False

    def _cargar_datos_ejemplo(self):
        """Carga datos de ejemplo - DENTRO DE LA CLASE"""
        from PySide6.QtWidgets import QTableWidgetItem

        self.lista_competidores = [
            {'numero': 1, 'apellidos': 'García Pérez', 'nombre': 'Juan', 'carrera': 'Electrónica', 'grupo': 'A'},
            {'numero': 2, 'apellidos': 'Martínez López', 'nombre': 'Ana', 'carrera': 'Mecatrónica', 'grupo': 'B'},
            {'numero': 3, 'apellidos': 'López Hernández', 'nombre': 'Carlos', 'carrera': 'Electrónica', 'grupo': 'A'},
            {'numero': 4, 'apellidos': 'Sánchez Ramírez', 'nombre': 'María', 'carrera': 'Computación', 'grupo': 'B'},
            {'numero': 5, 'apellidos': 'Ramírez Gómez', 'nombre': 'José', 'carrera': 'Electrónica', 'grupo': 'A'},
        ]

        self.tableWidget_Competidores.setRowCount(len(self.lista_competidores))

        for fila, comp in enumerate(self.lista_competidores):
            self.tableWidget_Competidores.setItem(fila, 0, QTableWidgetItem(str(comp['numero'])))
            self.tableWidget_Competidores.setItem(fila, 1, QTableWidgetItem(comp['apellidos']))
            self.tableWidget_Competidores.setItem(fila, 2, QTableWidgetItem(comp['nombre']))
            self.tableWidget_Competidores.setItem(fila, 3, QTableWidgetItem(comp['carrera']))
            self.tableWidget_Competidores.setItem(fila, 4, QTableWidgetItem(comp['grupo']))

        self._ajustar_anchos_columnas()
        print(f"✅ Cargados {len(self.lista_competidores)} competidores de ejemplo")

    def _cargar_datos_iniciales(self):
        """Carga los datos al iniciar - DENTRO DE LA CLASE"""
        from pathlib import Path

        # Buscar archivo Excel en la misma carpeta
        ruta_excel = Path(__file__).parent / "ConcursoMemoria_ListaConcursantes.xlsx"

        if ruta_excel.exists():
            self._cargar_desde_excel(ruta_excel)
        else:
            print(f"⚠️ No se encontró: {ruta_excel}")
            print("   Usando datos de ejemplo...")
            self._cargar_datos_ejemplo()

    # ==================== MÉTODOS DE CONFIGURACIÓN ====================
    def _setup_image_paths(self):
        """Configura las rutas de las imágenes para el círculo de estado"""
        current_dir = Path(__file__).parent
        images_dir = current_dir / "Imagenes"

        self.red_image_path = images_dir / "CirculoColorRojo.png"
        self.green_image_path = images_dir / "CirculoColorVerde.png"

        # ← Imágenes para resultado del juego
        self.pulgar_arriba_path = images_dir / "PulgarArriba.png"
        self.pulgar_abajo_path = images_dir / "PulgarAbajo.png"

        # Verificar que las imágenes existen
        if not self.red_image_path.exists():
            print(f"⚠️ No se encontró: {self.red_image_path}")
        if not self.green_image_path.exists():
            print(f"⚠️ No se encontró: {self.green_image_path}")
        if not self.pulgar_arriba_path.exists():
            print(f"⚠️ No se encontró: {self.pulgar_arriba_path}")
        if not self.pulgar_abajo_path.exists():
            print(f"⚠️ No se encontró: {self.pulgar_abajo_path}")

        # Mostrar estado inicial (rojo - desconectado)
        self._update_circle_image(False)

        # ← Limpiar la etiqueta de resultado al inicio
        self.label_siguiente_jugador.clear()
        self.label_siguiente_jugador.setText("🤔 Esperando...")

    def _setup_connections(self):

        """Conectar los componentes de la UI a las funciones."""
        self.pushButton_empezar_concurso.clicked.connect(self._empezar_concurso)

    def _calcular_nivel(self):
        """Calcula el nivel actual basado en la ronda"""
        return self.ronda_actual + 3

    def _actualizar_ui_completa(self):
        """Actualiza todas las etiquetas de la UI"""
        self.nivel_actual_juego = self._calcular_nivel()

        # Actualizar texto del encabezado: "Ronda No. X (Nivel Y)"
        if self.nivel_actual_juego<=5:
            numero_de_oportunidades = 1
            etiqueta_oportunidades = "oportunidad"
        elif self.nivel_actual_juego<=7:
            numero_de_oportunidades = 2
            etiqueta_oportunidades = "oportunidades"
        else:
            numero_de_oportunidades = 3
            etiqueta_oportunidades = "oportunidades"
        self.label_ronda_nivel.setText(f"Ronda No. {self.ronda_actual} (Nivel {self.nivel_actual_juego}; \
{numero_de_oportunidades} {etiqueta_oportunidades})")

        print(f"🔄 UI Actualizada: Ronda {self.ronda_actual} → Nivel {self.nivel_actual_juego}")

    def _empezar_concurso(self):
        """Punto de entrada: Inicia el concurso o avanza a la siguiente ronda"""

        # Si la ronda terminó y estamos esperando siguiente ronda
        if self.ronda_terminada:
            self._iniciar_siguiente_ronda()
            return

        # Si no hay concurso activo, iniciar nuevo
        if not self.concurso_activo:
            self._iniciar_nuevo_concurso()

    def _iniciar_nuevo_concurso(self):
        """Inicia un nuevo concurso desde cero"""
        if not self.lista_competidores:
            print("⚠️ No hay competidores cargados")
            self.label_ronda_nivel.setText("❌ No hay competidores")
            return

        # Reiniciar resultados
        for comp in self.lista_competidores:
            comp['op1'] = ''
            comp['op2'] = ''
            comp['op3'] = ''
            comp['activo'] = True
            comp['resultados'] = []
            comp['rondas_ganadas'] = 0
            comp['detalle_rondas'] = []
            comp['nivel_maximo'] = 0

        # Reiniciar variables de vueltas
        self.cola_fallidos = []
        self.en_vuelta_actual = False
        self.lista_competidores_original = []  # ← Limpiar

        # Reiniciar oportunidades usadas
        self.oportunidades_usadas = {}
        for idx, comp in enumerate(self.lista_competidores):
            self.oportunidades_usadas[idx] = 0

        # Capturar rondas ganadas al inicio
        self.rondas_al_inicio_ronda = {}
        for comp in self.lista_competidores:
            clave = f"{comp['nombre']}_{comp['apellidos']}"
            self.rondas_al_inicio_ronda[clave] = comp.get('rondas_ganadas', 0)

        self._actualizar_tabla()

        self.concurso_activo = True
        self.ronda_terminada = False
        self.indice_competidor_actual = 0
        self.ronda_actual = 1

        # Cambiar texto del botón
        self.pushButton_empezar_concurso.setEnabled(False)                # Desactivado
        self.pushButton_empezar_concurso.setText("Primera Ronda en Curso")
        self.pushButton_empezar_concurso.setStyleSheet("color: rgb(200, 100, 0);")

        # Enviar nivel inicial
        nivel_inicial = self._calcular_nivel()
        comando = f"JUGAR_CON_NIVEL {nivel_inicial}"
        print(f"🎮 [RONDA {self.ronda_actual}] Enviando nivel: {comando}")
        if self.esp32.is_connected():
            self.esp32.send_data(comando)

        # Mostrar primer competidor
        self._mostrar_siguiente_competidor()

    def _iniciar_siguiente_ronda(self):
        """Inicia la siguiente ronda después de que el usuario presiona el botón"""
        print(f"🎮 Iniciando RONDA {self.ronda_actual}")

        self.ronda_terminada = False
        self.indice_competidor_actual = 0

        # === REINICIAR VARIABLES DE VUELTAS PARA NUEVA RONDA ===
        self.cola_fallidos = []
        self.en_vuelta_actual = False
        self.lista_competidores_original = []  # ← Limpiar lista original
        # =====================================================

        # === LIMPIAR COLUMNAS VISUALES Op.X (NO el historial) ===
        for comp in self.lista_competidores:
            for i in range(1, 6):
                columna = f'op{i}'
                if columna in comp:
                    comp[columna] = ''
        # =====================================================

        # Reiniciar oportunidades usadas
        self.oportunidades_usadas = {}
        for idx, comp in enumerate(self.lista_competidores):
            self.oportunidades_usadas[idx] = 0

        # Capturar rondas ganadas al inicio
        self.rondas_al_inicio_ronda = {}
        for comp in self.lista_competidores:
            clave = f"{comp['nombre']}_{comp['apellidos']}"
            self.rondas_al_inicio_ronda[clave] = comp.get('rondas_ganadas', 0)

        # Cambiar texto del botón y desactivarlo
        self.pushButton_empezar_concurso.setText("Ronda {self.ronda_actual} en Curso")
        self.pushButton_empezar_concurso.setStyleSheet("color: rgb(200, 100, 0);")
        self.pushButton_empezar_concurso.setEnabled(False)

        # Actualizar UI
        self._actualizar_ui_completa()
        self._actualizar_tabla()

        # Enviar nuevo nivel al ESP32
        nuevo_nivel = self._calcular_nivel()
        comando = f"JUGAR_CON_NIVEL {nuevo_nivel}"
        print(f"🎮 [RONDA {self.ronda_actual}] Enviando nivel: {comando}")
        if self.esp32.is_connected():
            self.esp32.send_data(comando)

        # Mostrar primer competidor
        self._mostrar_siguiente_competidor()

    def _actualizar_tabla(self):
        """Actualiza la tabla - muestra resultados según oportunidades de la ronda"""
        from PySide6.QtWidgets import QTableWidgetItem

        # Configurar encabezados
        headers = ["Apellidos", "Nombre", "Carrera", "Grupo"]

        # Siempre mostrar Op.1, Op.2, Op.3 (todas las columnas posibles)
        headers.append("Op.1")
        headers.append("Op.2")
        headers.append("Op.3")

        headers.append("Rondas Ganadas")
        headers.append("Comentarios")

        self.tableWidget_Competidores.setColumnCount(len(headers))
        for col, header in enumerate(headers):
            self.tableWidget_Competidores.setHorizontalHeaderItem(col, QTableWidgetItem(header))

        self.tableWidget_Competidores.setRowCount(len(self.lista_competidores))

        for fila, comp in enumerate(self.lista_competidores):
            self.tableWidget_Competidores.setItem(fila, 0, QTableWidgetItem(comp['apellidos']))
            self.tableWidget_Competidores.setItem(fila, 1, QTableWidgetItem(comp['nombre']))
            self.tableWidget_Competidores.setItem(fila, 2, QTableWidgetItem(comp['carrera']))
            self.tableWidget_Competidores.setItem(fila, 3, QTableWidgetItem(comp['grupo']))

            # Mostrar resultados según columna (si existen)
            self._set_resultado_celda(fila, 4, comp.get('op1', ''))
            self._set_resultado_celda(fila, 5, comp.get('op2', ''))
            self._set_resultado_celda(fila, 6, comp.get('op3', ''))

            # Mostrar rondas ganadas
            self.tableWidget_Competidores.setItem(fila, 7, QTableWidgetItem(str(comp.get('rondas_ganadas', 0))))

            # Comentarios
            self.tableWidget_Competidores.setItem(fila, 8, QTableWidgetItem(comp.get('comentarios', '')))

        self._ajustar_anchos_columnas()

    def _set_resultado_celda(self, fila, columna, valor):
        """Establece una celda de resultado con formato (✓ verde o ✗ rojo)"""
        from PySide6.QtWidgets import QTableWidgetItem

        item = QTableWidgetItem(valor)

        if valor == "✓":
            item.setForeground(Qt.GlobalColor.green)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        elif valor == "✗":
            item.setForeground(Qt.GlobalColor.red)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tableWidget_Competidores.setItem(fila, columna, item)

    def _refrescar_tabla_completa(self):
        """Refresca completamente la tabla para mostrar resultados actualizados"""
        self._actualizar_tabla()
        self.tableWidget_Competidores.update()
        self.tableWidget_Competidores.repaint()

    def _avanzar_al_siguiente(self):
        """Avanza al siguiente competidor - Sistema de vueltas como salto de altura"""
        print("➡️ _avanzar_al_siguiente() llamado")

        if not self.concurso_activo:
            print("⚠️ Concurso no activo")
            return

        oportunidades = self._get_oportunidades_por_ronda()

        # REGISTRAR RESULTADO
        if self.indice_competidor_actual < len(self.lista_competidores):
            competidor = self.lista_competidores[self.indice_competidor_actual]

            if hasattr(self, 'ultimo_resultado'):
                resultado = "✓" if self.ultimo_resultado == "GANADO" else "✗"

                # === CORRECCIÓN: Usar número de intento para la columna ===
                intento_actual = self.oportunidades_usadas.get(self.indice_competidor_actual, 0) + 1

                # Determinar columna según el intento (no según la ronda)
                if intento_actual == 1:
                    columna_op = 'op1'
                elif intento_actual == 2:
                    columna_op = 'op2'
                else:
                    columna_op = 'op3'
                # ========================================================

                # Guardar en historial
                if 'resultados' not in competidor:
                    competidor['resultados'] = []
                competidor['resultados'].append(resultado)

                # Guardar en columna visual (según intento)
                competidor[columna_op] = resultado

                if self.ultimo_resultado == "GANADO":
                    competidor['rondas_ganadas'] = competidor.get('rondas_ganadas', 0) + 1
                    competidor['detalle_rondas'].append(self.ronda_actual)
                    competidor['nivel_maximo'] = self._calcular_nivel()
                    print(f"✅ {competidor['nombre']} - GANÓ Ronda {self.ronda_actual} (Intento {intento_actual})")
                    # Los que ganan se marcan como completados
                    self.oportunidades_usadas[self.indice_competidor_actual] = oportunidades
                else:
                    # Los que pierden
                    intentos_usados = self.oportunidades_usadas.get(self.indice_competidor_actual, 0) + 1
                    self.oportunidades_usadas[self.indice_competidor_actual] = intentos_usados

                    print(
                        f"❌ {competidor['nombre']} - PERDIÓ Ronda {self.ronda_actual} (Intento {intentos_usados} de {oportunidades})")

                    # Si aún tiene oportunidades, va a la cola de fallidos
                    if intentos_usados < oportunidades:
                        self.cola_fallidos.append({
                            'indice': self.indice_competidor_actual,
                            'competidor': competidor,
                            'intentos': intentos_usados
                        })
                        print(
                            f"   → {competidor['nombre']} espera nueva oportunidad (queda {oportunidades - intentos_usados})")

                self._refrescar_tabla_completa()

        # AVANZAR AL SIGUIENTE COMPETIDOR
        self.indice_competidor_actual += 1

        if self.indice_competidor_actual < len(self.lista_competidores):
            self._mostrar_siguiente_competidor()
        else:
            # Terminó una vuelta completa
            self._procesar_fin_vuelta()

    def _mostrar_siguiente_competidor(self):
        """Muestra el siguiente competidor - salta los que ya ganaron en esta ronda"""

        # Saltar competidores que ya completaron todas sus oportunidades
        oportunidades = self._get_oportunidades_por_ronda()
        while (self.indice_competidor_actual < len(self.lista_competidores) and
               self.oportunidades_usadas.get(self.indice_competidor_actual, 0) >= oportunidades):
            print(
                f"   Saltando a {self.lista_competidores[self.indice_competidor_actual]['nombre']} (ya completó sus oportunidades)")
            self.indice_competidor_actual += 1

        if self.indice_competidor_actual < len(self.lista_competidores):
            competidor = self.lista_competidores[self.indice_competidor_actual]
            nombre_grupo = f"{competidor['nombre']} ({competidor['grupo']})"
            self.label_siguiente_jugador.setText(f"Que juegue {nombre_grupo}")
            self.label_siguiente_jugador.setStyleSheet("color: blue; font-size: 24px; font-weight: bold;")

            # ===== IMPORTANTE: Actualizar la UI de ronda/nivel =====
            self._actualizar_ui_completa()
            # =======================================================
        else:
            print("No hay más competidores en esta vuelta")

    def _procesar_fin_vuelta(self):
        """Procesa el fin de una vuelta - decide si hay otra vuelta o termina la ronda"""
        print(f"🏁 Fin de vuelta - Ronda {self.ronda_actual}")
        print(f"   Fallidos pendientes: {len(self.cola_fallidos)}")

        # Verificar si hay fallidos con oportunidades restantes
        if self.cola_fallidos:
            # Obtener los ganadores de esta vuelta (los que NO están en fallidos)
            indices_fallidos = [f['indice'] for f in self.cola_fallidos]
            ganadores = []

            # Usar la lista ACTUAL de competidores (self.lista_competidores)
            for idx, comp in enumerate(self.lista_competidores):
                if idx not in indices_fallidos:
                    ganadores.append(comp)
                    print(f"   Ganador conservado: {comp['nombre']}")

            # Nueva lista: SOLO los ganadores de la vuelta anterior + fallidos que siguen
            # NO volver a poner a todos
            nueva_lista = ganadores.copy()

            for fallido in self.cola_fallidos:
                nueva_lista.append(fallido['competidor'])
                print(f"   Fallido que sigue: {fallido['competidor']['nombre']} (intento {fallido['intentos']})")

            # Actualizar la lista de competidores
            self.lista_competidores = nueva_lista

            # Actualizar oportunidades_usadas para la nueva vuelta
            nuevas_oportunidades = {}
            for idx, comp in enumerate(self.lista_competidores):
                # Buscar si es un fallido
                encontrado = False
                for fallido in self.cola_fallidos:
                    if comp['nombre'] == fallido['competidor']['nombre'] and comp['apellidos'] == fallido['competidor'][
                        'apellidos']:
                        nuevas_oportunidades[idx] = fallido['intentos']
                        encontrado = True
                        break
                if not encontrado:
                    # Es un ganador, marcar como completado
                    nuevas_oportunidades[idx] = self._get_oportunidades_por_ronda()

            self.oportunidades_usadas = nuevas_oportunidades

            # Limpiar cola para la próxima vuelta
            self.cola_fallidos = []

            # Reiniciar índice
            self.indice_competidor_actual = 0

            # Mostrar mensaje en UI
            self.label_siguiente_jugador.setText(f"🔄 Nueva oportunidad - Ronda {self.ronda_actual}")
            self.label_siguiente_jugador.setStyleSheet("color: orange; font-size: 20px; font-weight: bold;")

            # Enviar mismo nivel al ESP32
            nivel = self._calcular_nivel()
            comando = f"JUGAR_CON_NIVEL {nivel}"
            print(f"🎮 Nueva vuelta - Mismo nivel {nivel}")
            if self.esp32.is_connected():
                self.esp32.send_data(comando)

            # Mostrar primer competidor de la nueva vuelta
            QTimer.singleShot(2000, self._mostrar_siguiente_competidor)

        else:
            # No hay más fallidos, terminar la ronda
            print(f"✅ Ronda {self.ronda_actual} completada")
            self._finalizar_ronda()

    def _get_oportunidades_por_ronda(self):
        """Retorna el número de oportunidades según la ronda actual"""
        if self.ronda_actual <= 2:
            return 1
        elif self.ronda_actual <= 4:
            return 2
        else:
            return 3

    def _get_columna_oportunidad(self, intento):
        """Regresa la columna a usar según el intento (1, 2, 3)"""
        if intento == 1:
            return 'op1'
        elif intento == 2:
            return 'op2'
        else:
            return 'op3'

    def _finalizar_concurso(self):
        """Finaliza el concurso y muestra los tres primeros lugares"""
        self.concurso_activo = False
        self.ronda_terminada = False

        # Usar la lista original (todos los participantes)
        competidores_para_ranking = self.lista_competidores_original if self.lista_competidores_original else self.lista_competidores

        # Calcular ranking
        ranking = []
        for comp in competidores_para_ranking:
            puntaje = self._calcular_puntaje_desempate(comp)
            ranking.append((comp, puntaje))

        # Ordenar por puntaje (mayor a menor)
        ranking.sort(key=lambda x: x[1], reverse=True)

        # Mostrar en consola
        print("\n" + "=" * 60)
        print("🏆 RANKING FINAL 🏆")
        print("=" * 60)

        for pos, (comp, (p1, p2)) in enumerate(ranking, 1):
            if pos == 1:
                medalla = "🥇 "
            elif pos == 2:
                medalla = "🥈 "
            elif pos == 3:
                medalla = "🥉 "
            else:
                medalla = f"{pos}. "
            print(f"{medalla}{comp['nombre']} {comp['apellidos']}")
            print(f"   Rondas ganadas: {comp.get('rondas_ganadas', 0)}")
            print(f"   Nivel máximo: {comp.get('nivel_maximo', 0)}")
            print("-" * 40)

        # Mostrar tres primeros lugares en la UI
        texto_ranking = ""
        medallas = ["🥇", "🥈", "🥉"]

        for pos, (comp, _) in enumerate(ranking[:3], 0):
            texto_ranking += f"{medallas[pos]} {comp['nombre']} {comp['apellidos']}\n"

        if texto_ranking:
            self.label_siguiente_jugador.setText(f"🏆 RANKING FINAL 🏆\n\n{texto_ranking}")
            self.label_siguiente_jugador.setStyleSheet("color: gold; font-size: 18px; font-weight: bold;")
        else:
            self.label_siguiente_jugador.setText("🏆 CONCURSO FINALIZADO 🏆")
            self.label_siguiente_jugador.setStyleSheet("color: gold; font-size: 20px; font-weight: bold;")

        self.label_ronda_nivel.setText("¡Gracias por participar!")

        # Desactivar botón
        self.pushButton_empezar_concurso.setEnabled(False)
        self.pushButton_empezar_concurso.setText("Concurso Finalizado")
        self.pushButton_empezar_concurso.setStyleSheet("color: gray; background-color: lightgray;")

        print("✅ Concurso finalizado")
        print("👋 ¡Gracias por participar!")

    def _finalizar_ronda(self):
        """Finaliza la ronda actual y prepara para la siguiente"""
        print(f"🏁 RONDA {self.ronda_actual} FINALIZADA")

        # Usar las rondas capturadas al inicio de la ronda
        ganadores = []
        for comp in self.lista_competidores:
            clave = f"{comp['nombre']}_{comp['apellidos']}"
            rondas_inicio = self.rondas_al_inicio_ronda.get(clave, 0)
            rondas_actual = comp.get('rondas_ganadas', 0)

            print(f"   {comp['nombre']}: inicio={rondas_inicio}, actual={rondas_actual}")

            if rondas_actual > rondas_inicio:
                ganadores.append(comp)
                print(f"   ✅ {comp['nombre']} - GANÓ Ronda {self.ronda_actual}")
            else:
                print(f"   ❌ {comp['nombre']} - PERDIÓ Ronda {self.ronda_actual}")

        # ===== CORRECCIÓN: Si no hay ganadores, el concurso termina =====
        if not ganadores:
            print("   ❌❌❌ NO HUBO GANADORES EN ESTA RONDA - CONCURSO TERMINADO ❌❌❌")
            self._finalizar_concurso()
            return
        # =================================================================

        print(f"   Ganadores: {len(ganadores)} de {len(self.lista_competidores)}")

        if len(ganadores) > 1:
            self.ronda_terminada = True
            self.ronda_actual += 1
            self.lista_competidores = ganadores

            # Actualizar rondas_inicio para la nueva ronda
            self.rondas_al_inicio_ronda = {}
            for comp in self.lista_competidores:
                clave = f"{comp['nombre']}_{comp['apellidos']}"
                self.rondas_al_inicio_ronda[clave] = comp.get('rondas_ganadas', 0)

            # Limpiar variables de vueltas
            self.cola_fallidos = []
            self.en_vuelta_actual = False
            self.lista_competidores_original = []

            self.pushButton_empezar_concurso.setText("Siguiente Ronda")
            self.pushButton_empezar_concurso.setStyleSheet("color: rgb(0, 80, 200);")
            # Activar botón
            self.pushButton_empezar_concurso.setEnabled(True)

            self.label_siguiente_jugador.setText("Esperando...")
            self.label_siguiente_jugador.setStyleSheet("color: gray; font-size: 24px; font-weight: bold;")

            print(f"✅ Preparando RONDA {self.ronda_actual} con {len(self.lista_competidores)} competidores")
        else:
            # Solo un ganador o ninguno - Fin del concurso
            self._finalizar_concurso()

    def _avanzar_ronda(self):
        """
        Avanza a la siguiente ronda del competidor actual
        Se llama cuando el ESP32 completa una ronda exitosamente
        """
        if not self.concurso_activo:
            return

        # Incrementar ronda
        self.ronda_actual += 1

        # Calcular nuevo nivel
        nuevo_nivel = self._calcular_nivel()

        # Actualizar UI
        self._actualizar_ui_completa()

        # Enviar nuevo nivel al ESP32
        comando = f"JUGAR_CON_NIVEL {nuevo_nivel}"
        print(f"🎮 Avanzando a ronda {self.ronda_actual} (nivel {nuevo_nivel})")

        if self.esp32.is_connected():
            self.esp32.send_data(comando)

    def _calcular_puntaje_desempate(self, competidor):
        """Calcula puntaje para desempate usando el historial"""
        rondas_ganadas = competidor.get('rondas_ganadas', 0)
        nivel_maximo = competidor.get('nivel_maximo', 0)
        puntaje_principal = rondas_ganadas * 100 + nivel_maximo

        resultados = competidor.get('resultados', [])
        fallos = resultados.count("✗")
        puntaje_secundario = -fallos

        return (puntaje_principal, puntaje_secundario)

    # ==================== MÉTODOS DE CONEXIÓN ====================

    def _attempt_connection(self):
        """Intenta conectar automáticamente al ESP32"""
        self.esp32.connect()
        # Esperar un poco después de conectar antes de enviar el nivel inicial
        QTimer.singleShot(500, self._enviar_nivel_inicial)

    def _enviar_nivel_inicial(self):
        """Envía el nivel inicial cuando se conecta"""
        if self.esp32.is_connected():
            comando = f"JUGAR_CON_NIVEL {self.nivel_actual_juego}"
            print(f"🎮 Enviando nivel inicial: {comando}")
            self.esp32.send_data(comando)
        else:
            print("⚠️ No se pudo enviar nivel inicial: ESP32 no conectado")

    def _toggle_connection(self):
        """Conectar o desconectar manualmente del ESP32"""
        if self.esp32.is_connected():
            self.esp32.disconnect()
        else:
            self._attempt_connection()

    def send_command_to_esp32(self, command):
        """
        Envía un comando al ESP32.

        Args:
            command (str): Comando a enviar

        Returns:
            bool: True si se envió correctamente
        """
        if self.esp32.is_connected():
            return self.esp32.send_data(command)
        else:
            print("❌ No se puede enviar: No hay conexión con ESP32")
            return False

    # ==================== MANEJADORES DE EVENTOS ====================

    def _on_connection_changed(self, connected):
        """
        Actualiza la UI cuando cambia el estado de conexión.
        Actualiza el círculo y muestra mensajes en consola.
        """
        # Actualizar imagen del círculo
        self._update_circle_image(connected)

        if connected:
            print("✅ CONECTADO al ESP32")
            # Enviar nivel actual cuando se conecta
            QTimer.singleShot(100, self._enviar_nivel_inicial)
        else:
            print("❌ DESCONECTADO del ESP32")
            # Opcional: Mostrar mensaje en la UI
            #self.label_ronda_nivel.setText("❌ ESP32 Desconectado")
            # Intentar reconectar después de 5 segundos
            QTimer.singleShot(5000, self._attempt_connection)

    def _on_data_received(self, data):
        """
        Procesa los datos recibidos desde el ESP32.
        """
        print(f"Dato recibido: '{data}'")

        data_upper = data.upper().strip()
        print(f"Comparando: '{data_upper}'")

        # PRIMERO: Resultados del juego
        if "JUEGO GANADO" in data_upper:
            self.ultimo_resultado = "GANADO"
            print(f"🏆 ASIGNANDO: self.ultimo_resultado = {self.ultimo_resultado}")
            self._mostrar_pulgar_arriba()
            QTimer.singleShot(3000, self._avanzar_al_siguiente)
            return  # Importante: salir después de procesar

        elif "JUEGO PERDIDO" in data_upper:
            self.ultimo_resultado = "PERDIDO"
            print(f"💀 ASIGNANDO: self.ultimo_resultado = {self.ultimo_resultado}")
            self._mostrar_pulgar_abajo()
            QTimer.singleShot(3000, self._avanzar_al_siguiente)
            return  # Importante: salir después de procesar

        # SEGUNDO: Estado del juego
        elif "JUGANDO" in data_upper:
            if self.concurso_activo and self.indice_competidor_actual < len(self.lista_competidores):
                competidor = self.lista_competidores[self.indice_competidor_actual]
                nombre_grupo = f"{competidor['nombre']} ({competidor['grupo']})"
                self.label_siguiente_jugador.setText(f"Jugando {nombre_grupo}")
                self.label_siguiente_jugador.setStyleSheet("color: orange; font-size: 24px; font-weight: bold;")
            print("🎮 ESP32 está jugando")

        # TERCERO: Confirmaciones
        elif "OK" in data_upper:
            print("✅ ESP32 confirmó recepción")
        elif "ERROR" in data_upper:
            print("⚠️ ESP32 reportó error")
        else:
            print(f"⚠️ Comando no reconocido: {data_upper}")

    def _update_circle_image(self, connected):
        if connected:
            image_path = self.green_image_path
        else:
            image_path = self.red_image_path

        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            self.label_estado_conexion.setPixmap(pixmap)
            self.label_estado_conexion.setScaledContents(True)  # ← Línea clave
        else:
            self.label_estado_conexion.setText("🔴" if not connected else "🟢")
            self.label_estado_conexion.setAlignment(Qt.AlignCenter)

    def _mostrar_pulgar_arriba(self):
        """Muestra el pulgar arriba (JUEGO GANADO)"""
        if self.pulgar_arriba_path.exists():
            pixmap = QPixmap(str(self.pulgar_arriba_path))
            pixmap = pixmap.scaled(
                self.label_siguiente_jugador.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.label_siguiente_jugador.setPixmap(pixmap)
            #print("👍 Mostrando PULGAR ARRIBA")
        else:
            self.label_siguiente_jugador.setText("👍 JUEGO GANADO 👍")
            self.label_siguiente_jugador.setStyleSheet("color: green; font-size: 24px; font-weight: bold;")
        self.label_siguiente_jugador.setAlignment(Qt.AlignCenter)

    def _mostrar_pulgar_abajo(self):
        """Muestra el pulgar abajo (JUEGO PERDIDO)"""
        if self.pulgar_abajo_path.exists():
            pixmap = QPixmap(str(self.pulgar_abajo_path))
            pixmap = pixmap.scaled(
                self.label_siguiente_jugador.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.label_siguiente_jugador.setPixmap(pixmap)
            #print("👎 Mostrando PULGAR ABAJO")
        else:
            self.label_siguiente_jugador.setText("👎 JUEGO PERDIDO 👎")
            self.label_siguiente_jugador.setStyleSheet("color: red; font-size: 24px; font-weight: bold;")
        self.label_siguiente_jugador.setAlignment(Qt.AlignCenter)

    def _limpiar_resultado(self):
        """Limpia el resultado mostrado anteriormente"""
        self.label_siguiente_jugador.clear()
        self.label_siguiente_jugador.setText("🎮 En juego...")
        self.label_siguiente_jugador.setStyleSheet("")

    def closeEvent(self, event):
        """
        Maneja el cierre de la ventana para cerrar la conexión correctamente
        """
        print("🔌 Cerrando aplicación...")
        self.esp32.disconnect()
        event.accept()

# ==================== PUNTO DE ENTRADA ====================

if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
