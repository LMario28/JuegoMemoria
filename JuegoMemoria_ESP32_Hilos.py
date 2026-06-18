# NOTAS:

# 1) Pasos para actualizar el sketch en el ESP32

#    Requisitos: 1) Debe estar en donde está la aplicación el sketch ota.py;
#                2) En GitHub, repositorio Aro debe existir  un arhivo con nombre version.json con las lineas:
#                   {
#                     "version":2
#                   }
#                   el número de la versión debe ser mayor que el mismo archivo en el ESP32

#    a) Abrir www.github.com
#    b) lmmsegura@hotmail.com / le...24
#    c) Copiar la nueva versión del sketch a GitHub, repositorio JuegoMemoria

# 2) Correr con al menos MicroPython v.1.27

# JuegoMemoria_ESP32_Hilos.py
# Versión con hilos para comunicación PC y juego simultáneo

#//////////////////////////////////// IMPORTs //////////////////////////////////
import sys                                                                    #/
import machine                                                                #/
from machine import Pin                                                       #/
from time import sleep, sleep_ms                                              #/
import network                                                                #/
import socket                                                                 #/
import _thread                                                                #/
import time                                                                   #/
import ntptime                                                                #/
import random                                                                 #/
from ota_deepseek import OTAUpdater                                           #/

#////////////////////////////////// CONSTANTES /////////////////////////////////
WIFI_SSID = ['INFINITUM2426_2.4','Extensor Sala','Electronica Hotspot PC', 'TP-Link_LMario_DHCP']
WIFI_PASS = ['CNnC917MDE','CNnC917MDE','electronica23','lmario28']
SSID = ''
PASSWD = ''
PUERTO = 8888
TIEMPO_ESPERAR_CONEXION_WIFI = 60

ENCENDIDO_BOTONES = [
    [0,0,0,0,0,0,0,1],
    [0,0,0,0,0,0,1,0],
    [0,0,0,0,0,1,0,0],
    [0,0,0,0,1,0,0,0],
    [0,0,0,1,0,0,0,0],
    [0,0,1,0,0,0,0,0],
    [0,1,0,0,0,0,0,0]
                    ]

DATA_PIN = 13
CLOCK_PIN = 15
LATCH_PIN = 14
NUMERO_BOTONES = 5
PIN_INTERRUPTOR_BOTON = [4,5,19,21,22]

#//////////////////////////////////// OBJETOS //////////////////////////////////
                                                                              #/
# Inicialización de Hardware en main()                                        #/
                                                                              #/
#///////////////////////////////////////////////////////////////////////////////

#/////////////////////////////// VARIABLES GLOBALES ////////////////////////////
data = None                                                                   #/
clock = None                                                                  #/
latch = None                                                                  #/
pin = []                                                                      #/
                                                                              #/
# Estado del juego                                                            #/
bandera_led_2_encendido = False                                               #/
momento_ultimo_evento_blink = 0                                               #/
bandera_jugando = False                                                       #/
nivel_actual_juego = 4                                                        #/
                                                                              #/
# Conexión (compartidas entre hilos)                                          #/
bandera_cliente_conectado = False                                             #/
cliente_socket = None                                                         #/
                                                                              #/
# Variables del juego                                                         #/
secuencia = []                                                                #/
posicion_secuencia = 0                                                        #/
bandera_boton_erroneo = False                                                 #/
momento_empezo_juego = 0                                                      #/
                                                                              #/
# Control de hilos                                                            #/
servidor_ejecutando = True                                                    #/
                                                                              #/
# Configuración WiFi                                                          #/
WIFI_SSID_DEF = "TP-Link_LMario_DHCP"                                         #/
WIFI_PASSWORD_DEF = "lmario28"                                                #/
#///////////////////////////////////////////////////////////////////////////////

#/////////////////////////////// FUNCIONES COMUNES /////////////////////////////

#-------------------------------------------------------------------------------
def encenderLEDs(numeroLED):
#-------------------------------------------------------------------------------
  global data, clock, latch
  for j in range(8):
    data.value(ENCENDIDO_BOTONES[numeroLED][j])
    clock.value(1)
    clock.value(0)
  latch.value(1)
  latch.value(0)

#-------------------------------------------------------------------------------
def apagarLEDs():
#-------------------------------------------------------------------------------
  global data, clock, latch
  for j in range(8):
    data.value(0)
    clock.value(1)
    clock.value(0)
  latch.value(1)
  latch.value(0)

#-------------------------------------------------------------------------------
def blink_led_3():
#-------------------------------------------------------------------------------
  global bandera_led_2_encendido, momento_ultimo_evento_blink

  if time.time() - momento_ultimo_evento_blink > 0.5:
    if not bandera_led_2_encendido:
      encenderLEDs(2)
      bandera_led_2_encendido = True
    else:
      apagarLEDs()
      bandera_led_2_encendido = False
    momento_ultimo_evento_blink = time.time()

#-------------------------------------------------------------------------------
def seleccionarMejorRedWiFiDisponible():
#-------------------------------------------------------------------------------
  global SSID, PASSWD

  wiFi = network.WLAN(network.STA_IF)
  wiFi.active(True)

  redesWiFiDisponibles = wiFi.scan()
  # print(redesWiFiDisponibles)
  rssiMasFuerte = -999
  for (ssid, bssid, channel, RSSI, authmode, hidden) in redesWiFiDisponibles:
    ssidLocal = "{:s}".format(ssid)
    try:
      indiceRed=WIFI_SSID.index(ssidLocal)
      rssiLocal="{}".format(RSSI)
      rssiLocal = int(rssiLocal)
    except ValueError:
      continue
    if rssiLocal > rssiMasFuerte:
      SSID = ssidLocal
      PASSWD = WIFI_PASS[indiceRed]
      rssiMasFuerte = rssiLocal

#     print(ssidLocal)
#     #print("   - Auth: {} {}".format(authmodes[authmode], '(hidden)' if hidden else ''))
#     #print("   - Channel: {}".format(channel))
#     print("   - RSSI: {}".format(RSSI))
#     #print("   - BSSID: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}".format(*bssid))
#     print()
  print("Mejor red disponible:",SSID,"|",PASSWD)

#-------------------------------------------------------------------------------
def conectar_wifi():
#-------------------------------------------------------------------------------
  global SSID, PASSWD

  #================================================ DHCP
#   wifi = network.WLAN(network.STA_IF)
#   wifi.active(True)
#   wifi.connect(SSID, PASSWD)
#   print("Conectando a la red '{}'".format(SSID), end='')
#   tiempoInicial = time.time()
#   while not wifi.isconnected() and (time.time() - tiempoInicial) < TIEMPO_ESPERAR_CONEXION_WIFI:
#     print(".", end='')
#     time.sleep(1)
#   if not wifi.isconnected():
#     print("No se pudo conectar. Reiniciando...")
#     return False
#   print('\nRed conectada. IP:', wifi.ifconfig()[0])

#================================================ IP FIJA
  wlan = network.WLAN(network.STA_IF)
  wlan.active(True)
  try:
    wlan.config(pm=network.WLAN.PM_NONE)
  except:
    pass
    
# Configurar IP FIJA
  IP_FIJA = "192.168.0.111"
  MASCARA = "255.255.255.0"
  GATEWAY = "192.168.0.1"
  DNS = "192.168.0.1"
#   # CASA
#   IP_FIJA = "192.168.1.110"
#   MASCARA = "255.255.255.0"
#   GATEWAY = "192.168.1.254"
#   DNS = "192.168.1.254"

  wlan.ifconfig((IP_FIJA, MASCARA, GATEWAY, DNS))

  print(f"Conectando a WiFi con IP fija: {IP_FIJA}", end="")
  wlan.connect(SSID, PASSWD)

  TIMEOUT = 60
  start_time = time.time()

  while not wlan.isconnected() and (time.time() - start_time) < TIMEOUT:
    time.sleep(0.5)
    print(".", end="")
 
  if wlan.isconnected():
    print("\n✅ Conectado a WiFi")
    config = wlan.ifconfig()
    print(f"📡 IP asignada: {config[0]}")
    print(f"   Máscara: {config[1]}")
    print(f"   Gateway: {config[2]}")
    print(f"   DNS: {config[3]}")                 # Verificar que el DNS está configurado

    # Verificar que se asignó la IP fija
    if config[0] != IP_FIJA:
      print(f"⚠️ Advertencia: IP asignada ({config[0]}) diferente a IP fija ({IP_FIJA})")
      print("   Posible conflicto - prueba con otra IP")
  else:
    print("\n❌ No se pudo conectar a WiFi")
    return False

  return True

#-------------------------------------------------------------------------------
def actualizarSketch():
#-------------------------------------------------------------------------------
  """Actualiza el sketch desde GitHub - FUNCIÓN PRIMORDIAL"""
  global SSID, PASSWD

  print("=" * 50)
  print("🔧 ACTUALIZANDO SKETCH...")
  print("=" * 50)

  firmware_url = "https://github.com/LMario28/JuegoMemoria/"

  try:
    print(f"📡 Conectando a GitHub desde {SSID}...")
    ota_updater = OTAUpdater(SSID, PASSWD, firmware_url, "JuegoMemoria_ESP32_Hilos.py")
    ota_updater.download_and_install_update_if_available()
    print("✅ Actualización completada (o no había nueva versión)")

  except Exception as e:
    print(f"\n✗ ERROR DURANTE LA ACTUALIZACIÓN: {e}")
    import sys
    sys.print_exception(e)

  print("=" * 50)
  print("📌 FIN DEL PROCESO DE ACTUALIZACIÓN")
  print("=" * 50)

#-------------------------------------------------------------------------------
def obtener_dia_semana():
#-------------------------------------------------------------------------------
  try:
    print("🕐 Sincronizando hora con NTP...")
    servidores = ["pool.ntp.org", "time.google.com", "time.windows.com", "mx.pool.ntp.org"]
    for servidor in servidores:
      try:
        print(f"  Probando {servidor}...")
        ntptime.host = servidor
        ntptime.settime()
        print(f"  ✅ Sincronizado con {servidor}")
        break
      except Exception as e:
        print(f"  ❌ Falló {servidor}: {e}")
        continue
    else:
      print("❌ No se pudo sincronizar")
      return -1

    time.sleep(1)
    UTC_OFFSET = -6 * 3600
    hora_actual = time.localtime(time.time() + UTC_OFFSET)
    dia_semana = hora_actual[6]
    print(f"Día de la semana: {dia_semana} (0: Lunes)")
    return dia_semana
  except Exception as e:
    print(f"Error: {e}")
    return -1

#-------------------------------------------------------------------------------
def procesar_comando(datos):
#-------------------------------------------------------------------------------
  """Procesa comandos de la PC - EJECUTADO EN HILO SERVIDOR"""
  global nivel_actual_juego, bandera_jugando
  datos = datos.strip().upper()
  print(f"📝 Procesando: '{datos}'")

  if datos.startswith("JUGAR_CON_NIVEL"):
    try:
      nivel = int(datos.split()[1])
      nivel_actual_juego = nivel
      bandera_jugando = False  # Reiniciar estado del juego
      print(f"🎮 NIVEL ACTUALIZADO: {nivel_actual_juego}")
      return f"OK_NIVEL_{nivel_actual_juego}"
    except Exception as e:
      print(f"Error: {e}")
      return "ERROR_COMANDO"
  elif datos == "PING":
    return "PONG"
  elif datos == "STATUS":
    return f"NIVEL_{nivel_actual_juego}"
  else:
    return f"COMANDO_RECIBIDO"

#/////////////////////////////////// HILO DEL SERVIDOR /////////////////////////////////
#-------------------------------------------------------------------------------
def hilo_servidor():
#-------------------------------------------------------------------------------
  """Hilo dedicado exclusivamente a la comunicación con la PC"""
  global bandera_cliente_conectado, cliente_socket, servidor_ejecutando

  print("🧵 [HILO] Iniciando servidor...")

  # Crear socket del servidor
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server_socket.bind(('0.0.0.0', PUERTO))
  server_socket.listen(1)
  server_socket.settimeout(0.5)

  print(f"🌐 [HILO] Servidor en puerto {PUERTO}")

  while servidor_ejecutando:
    try:
      # Aceptar nueva conexión
      if not bandera_cliente_conectado:
        try:
          nuevo_cliente, dir = server_socket.accept()
          cliente_socket = nuevo_cliente
          # === DESHABILITAR BUFFER (Nagle) ===
          # Esto hace que los mensajes se envíen inmediatamente
          cliente_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
          # ===================================
          bandera_cliente_conectado = True
          print(f"✅ [HILO] PC conectada: {dir}")
          cliente_socket.send("OK_CONECTADO")
        except OSError:
          pass  # Timeout normal
            
      # Procesar datos del cliente
      if bandera_cliente_conectado and cliente_socket:
        try:
          cliente_socket.settimeout(0.1)
          datos = cliente_socket.recv(1024).decode().strip()

          if datos:
            print(f"📥 [HILO] Recibido: {datos}")
            respuesta = procesar_comando(datos)
            if respuesta:
              cliente_socket.send(f"{respuesta}")
              print(f"📤 [HILO] Respuesta: {respuesta}")
          else:
            print("❌ [HILO] PC desconectada")
            cliente_socket.close()
            cliente_socket = None
            bandera_cliente_conectado = False

        except OSError:
          pass  # Timeout normal

    except Exception as e:
      print(f"Error en servidor: {e}")

    time.sleep_ms(10)
    
  print("🧵 [HILO] Servidor terminado")
  if server_socket:
    server_socket.close()

#/////////////////////////////////// FUNCIONES DEL JUEGO /////////////////////////////////
#-------------------------------------------------------------------------------
def jugar():
#-------------------------------------------------------------------------------
    """Función principal del juego - EJECUTADA EN HILO PRINCIPAL"""
    global bandera_jugando, secuencia, posicion_secuencia, bandera_boton_erroneo
    global momento_empezo_juego, nivel_actual_juego

    if not bandera_jugando:
        # Generar y mostrar secuencia
        secuencia = []
        for i in range(nivel_actual_juego):
            boton = random.randint(1, NUMERO_BOTONES)
            secuencia.append(boton)
            encenderLEDs(boton - 1)
            time.sleep(0.5)
            apagarLEDs()
            time.sleep(0.3)
        print(f"📋 Secuencia: {secuencia}")
        apagarLEDs()
        momento_empezo_juego = time.time()
        posicion_secuencia = 0
        bandera_boton_erroneo = False
        bandera_jugando = True
        
    else:
        # Verificar tiempo límite
        if time.time() - momento_empezo_juego > 25:
            encenderLEDs(6)
            bandera_jugando = False
            print("Tiempo agotado. Juego perdido")
            if bandera_cliente_conectado and cliente_socket:
              try:
                cliente_socket.send("JUEGO PERDIDO")
                time.sleep_ms(200)     #DELAY
                print("Enviado a la PC: JUEGO PERDIDO")
              except:
                pass
            time.sleep(4)
            apagarLEDs()
            return
        
        # Esperar respuesta del jugador
        if posicion_secuencia < len(secuencia):
            for i in range(NUMERO_BOTONES):
                if pin[i].value() == 0:
                    # Debounce
                    time.sleep_ms(50)
                    if pin[i].value() == 0:
                        encenderLEDs(i)
                        # Esperar a que suelte
                        while pin[i].value() == 0:
                            time.sleep_ms(10)
                        apagarLEDs()
                        
                        boton_oprimido = i + 1
                        if secuencia[posicion_secuencia] == boton_oprimido:
                            print(f"✅ Correcto: {boton_oprimido}")
#                             if bandera_cliente_conectado and cliente_socket:
#                                 try:
#                                     cliente_socket.send("FEEDBACK_CORRECTO\n")
#                                 except:
#                                     pass
                        else:
                            print(f"❌ Incorrecto: esperaba {secuencia[posicion_secuencia]}, presionó {boton_oprimido}")
                            bandera_boton_erroneo = True
#                             if bandera_cliente_conectado and cliente_socket:
#                                 try:
#                                     cliente_socket.send("FEEDBACK_INCORRECTO\n")
#                                 except:
#                                     pass
                        
                        posicion_secuencia += 1
                        break
        else:
            # Fin de la ronda
            if not bandera_boton_erroneo:
                encenderLEDs(5)  # Éxito
                print("¡Juego ganado!")
                if bandera_cliente_conectado and cliente_socket:
                    try:
                        cliente_socket.send("JUEGO GANADO")
                        time.sleep_ms(200)     #DELAY
                        print("Enviado a la PC: JUEGO GANADO")
                    except:
                        pass
            else:
                encenderLEDs(6)  # Fracaso
                if bandera_cliente_conectado and cliente_socket:
                    try:
                        cliente_socket.send("JUEGO PERDIDO")
                        time.sleep_ms(200)     #DELAY
                        print("Enviado a la PC: JUEGO PERDIDO")
                    except:
                        pass
            
            bandera_jugando = False
            time.sleep(3)
            apagarLEDs()

#/////////////////////////////////// MAIN /////////////////////////////////

def main():
  global data, clock, latch, pin
  global bandera_cliente_conectado, cliente_socket
  global bandera_led_2_encendido, momento_ultimo_evento_blink, bandera_jugando, nivel_actual_juego
  global servidor_ejecutando

  print("=" * 50)
  print("🎮 JUEGO MEMORIA ESP32 - VERSIÓN CON HILOS")
  print("=" * 50)

  # 1. INICIALIZAR HARDWARE
  print("🔧 Inicializando hardware...")
  data = Pin(DATA_PIN, Pin.OUT, value=0)
  clock = Pin(CLOCK_PIN, Pin.OUT, value=0)
  latch = Pin(LATCH_PIN, Pin.OUT, value=0)
  pin = [None] * NUMERO_BOTONES
  for i in range(NUMERO_BOTONES):
    pin[i] = Pin(PIN_INTERRUPTOR_BOTON[i], Pin.IN)
  print("✅ Hardware inicializado")

  # 2. CONECTAR WiFi
  seleccionarMejorRedWiFiDisponible()
  if not conectar_wifi():
    print("No se pudo conectar. Reiniciando...")
    machine.reset()

  # 3. ACTUALIZAR SKETCH (FUNCIÓN PRIMORDIAL)
  actualizarSketch()

  # 4. OBTENER NIVEL POR DÍA DE SEMANA
  dia = obtener_dia_semana()
  if dia != -1:
    nivel_actual_juego = dia + 3
    print(f"🎮 Nivel inicial: {nivel_actual_juego}")

  # 5. INICIAR HILO DEL SERVIDOR
  print("🔄 Iniciando hilo del servidor...")
  servidor_ejecutando = True
  _thread.start_new_thread(hilo_servidor, ())
  time.sleep(1)  # Dar tiempo para que el servidor se inicialice

  # 6. BUCLE PRINCIPAL DEL JUEGO
  print("🎮 Bucle principal del juego iniciado...")
  print("💡 Presiona el botón parpareando (2 seg) para comenzar a jugar")

  while True:
    try:
      if not bandera_jugando:
        # Blink LED mientras espera
        blink_led_3()

        # Detectar botón de inicio (pin[2] = botón 3)
        if pin[2].value() == 0:
           momento_presion = time.time()
           # Debounce y esperar a que suelte
           while pin[2].value() == 0:
              time.sleep_ms(5)
           if time.time() - momento_presion > 0.5:  # Presión larga
             apagarLEDs()
             time.sleep(0.5)
             print("\n🎮 Iniciando juego...")
             if bandera_cliente_conectado and cliente_socket:
               try:
                 cliente_socket.send("JUGANDO")
                 time.sleep_ms(200)     #DELAY
                 print("ENVIADO A LA PC: JUGANDO")
               except:
                 pass
             jugar()
        elif pin[0].value() == 0:
           momento_presion = time.time()
           # Debounce y esperar a que suelte
           while pin[0].value() == 0:
              time.sleep_ms(5)
           if time.time() - momento_presion > 0.5:  # Presión larga
             apagarLEDs()
             print("\nJugador ausente")
             if bandera_cliente_conectado and cliente_socket:
               try:
                 cliente_socket.send("JUEGO PERDIDO")
                 time.sleep_ms(200)     # RETRASO
                 print("Enviado a la PC: JUEGO PERDIDO")
               except:
                 pass
      else:
        jugar()

      time.sleep_ms(10)  # Pequeña pausa para no saturar
            
    except KeyboardInterrupt:
      print("\n🔌 Cerrando aplicación...")
      servidor_ejecutando = False
      break

  # Limpiar
  if cliente_socket:
    try:
      cliente_socket.close()
    except:
      pass
  apagarLEDs()

def start():
  print("🎮 start() llamada")
  main()

if __name__ == "__main__":
  main()