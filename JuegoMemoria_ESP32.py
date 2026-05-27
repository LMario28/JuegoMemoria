# NOTAS:

# 1) Pasos para actualizar el sketch en el ESP32

#    Requisitos: 1) Debe estar en el ESP32 el sketch ota_deepseek.py;
#                2) En GitHub, repositorio JuegoMemoria debe existir  un arhivo con nombre version.json con las lineas:
#                   {
#                     "version":2
#                   }
#                   el número de la versión debe ser mayor que el mismo archivo en el ESP32

#    a) Abrir www.github.com
#    b) lmmsegura@hotmail.com / le...24
#    c) Copiar la nueva versión del sketch (JuegoMemoria -ESP32) a GitHub, repositorio JuegoMemoria

# 2) Correr con al menos MicroPython v1.27

#//////////////////////////////////// IMPORTs //////////////////////////////////
import sys                                                                    #/
import machine                                                                #/
from machine import Pin                                                       #/
from time import sleep,sleep_ms                                               #/
import network                                                                #/
import socket                                                                 #/
import time                                                                   #/
import ntptime                                                                #/
import random                                                                 #/
#///////////////////////////////////////////////////////////////////////////////

#////////////////////////////////// CONSTANTES /////////////////////////////////
WIFI_SSID = ['INFINITUM2426_2.4','Extensor Sala','Electronica Hotspot PC', \
             'TP-Link_LMario_DHCP']                                           #/
WIFI_PASS = ['CNnC917MDE','CNnC917MDE','electronica23','lmario28']            #/
SSID=''                                                                       #/
PASSWD=''                                                                     #/
PUERTO = 8888                                                                 #/
TIEMPO_ESPERAR_CONEXION_WIFI=60                                               #/
ENCENDIDO_BOTONES=[
                   [0,0,0,0,0,0,0,1],
                   [0,0,0,0,0,0,1,0],
                   [0,0,0,0,0,1,0,0],
                   [0,0,0,0,1,0,0,0],
                   [0,0,0,1,0,0,0,0],
                   [0,0,1,0,0,0,0,0],
                   [0,1,0,0,0,0,0,0]
                  ]                                                           #/
DATA_PIN=13                                                                   #/ MOSI (UNO:11)
CLOCK_PIN=15                                                                  #/ SPI SCLK (UNO:13)
LATCH_PIN=14                                                                  #/ SPI SS (UNO:10)
NUMERO_BOTONES=5                                                              #/
PIN_INTERRUPTOR_BOTON=[4,5,19,21,22]                                          #/
#///////////////////////////////////////////////////////////////////////////////

#//////////////////////////////////// OBJETOS //////////////////////////////////
                                                                              #/
# Se pasó a main()                                                            #/
                                                                              #/
#///////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////// VARIABLES /////////////////////////////////
bandera_led_2_encendido=False                                                 #/
momento_ultimo_evento=None                                                    #/
momento_ultimo_evento_blink=time.time()                                       #/
bandera_jugando=False                                                         #/

bandera_cliente_conectado = False                                             #/
cliente_socket = None                                                         #/
servidor_socket = None                                                        #/
nivel_actual_juego = 4                                                        #/ Nivel por defecto
#///////////////////////////////////////////////////////////////////////////////

# Configuración WiFi
SSID = "INFINITUM2426_2.4"
PASSWORD = "CNnC917MDE"
PUERTO = 8888

#/////////////////////////////////// FUNCIONES /////////////////////////////////
#-------------------------------------------------------------------------------
def seleccionarMejorRedWiFiDisponible():
#-------------------------------------------------------------------------------

  global SSID
  global PASSWD

  wiFi = network.WLAN(network.STA_IF)
  wiFi.active(True)

  authmodes = ['Open', 'WEP', 'WPA-PSK' 'WPA2-PSK4', 'WPA/WPA2-PSK']
  redesWiFiDisponibles = wiFi.scan()
#   print(redesWiFiDisponibles)
  rssiMasFuerte = -999
  for (ssid, bssid, channel, RSSI, authmode, hidden) in redesWiFiDisponibles:
    ssidLocal="{:s}".format(ssid)
    try:
      indiceRed=WIFI_SSID.index(ssidLocal)
      rssiLocal="{}".format(RSSI)
      rssiLocal = int(rssiLocal)
    except ValueError:
      continue
    if(int(rssiLocal)>rssiMasFuerte):
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
def actualizarSketch():
#-------------------------------------------------------------------------------
  global SSID
  global PASSWD

  firmware_url = "https://raw.githubusercontent.com/LMario28/JuegoMemoria/"

  print("*************************")
  print("ACTUALIZANDO SKETCH...")
  try:
    ota_updater = OTAUpdater(SSID, PASSWD, firmware_url, "JuegoMemoria-ESP32.py")
    ota_updater.download_and_install_update_if_available()
  except:
    print("NO SE PUDO ACTUALIZAR EL SKETCH")
  print("*************************")

#-------------------------------------------------------------------------------
def conectar_wifi():
#-------------------------------------------------------------------------------

#================================================ DHCP
  wifi = network.WLAN(network.STA_IF)
  wifi.active(True)
  wifi.connect(SSID,PASSWD)
  print("Conectando a la red '{}'".format(SSID),end='')
  tiempoInicialTareaLocal= time.time()
  while not wifi.isconnected() and time.time()-tiempoInicialTareaLocal<TIEMPO_ESPERAR_CONEXION_WIFI:
    print(".",end='')
    time.sleep(1)
  if not wifi.isconnected():
    print("No se pudo conectar a la red en 1 minuto. Reiniciando el ESP32")
    return False
  print('\nRed conectada. IP:', wifi.ifconfig()[0])

#================================================ IP FIJA
#  wlan = network.WLAN(network.STA_IF)
#  wlan.active(True)
#   try:
#     wlan.config(pm=network.WLAN.PM_NONE)
#   except:
#     pass
#     
#   # Configurar IP FIJA
#   IP_FIJA = "192.168.0.10"
#   MASCARA = "255.255.255.0"
#   GATEWAY = "192.168.0.1"
#   DNS = "192.168.0.1"
# 
#   wlan.ifconfig((IP_FIJA, MASCARA, GATEWAY, DNS))
# 
#   print(f"Conectando a WiFi con IP fija: {IP_FIJA}", end="")
#   wlan.connect(SSID, PASSWORD)
# 
#   TIMEOUT = 60
#   start_time = time.time()
# 
#   while not wlan.isconnected() and (time.time() - start_time) < TIMEOUT:
#     time.sleep(0.5)
#     print(".", end="")
#  
#   if wlan.isconnected():
#     print("\n✅ Conectado a WiFi")
#     config = wlan.ifconfig()
#     print(f"📡 IP asignada: {config[0]}")
#     print(f"   Máscara: {config[1]}")
#     print(f"   Gateway: {config[2]}")
#     print(f"   DNS: {config[3]}")                 # Verificar que el DNS está configurado
# 
#     # Verificar que se asignó la IP fija
#     if config[0] != IP_FIJA:
#       print(f"⚠️ Advertencia: IP asignada ({config[0]}) diferente a IP fija ({IP_FIJA})")
#       print("   Posible conflicto - prueba con otra IP")
#   else:
#     print("\n❌ No se pudo conectar a WiFi")
#     return False

  return True

#-------------------------------------------------------------------------------
def obtener_dia_semana():
#-------------------------------------------------------------------------------
#   try:
#     # Sincronizar hora con NTP
#     ntptime.settime()
#     time.sleep(1)  # Pequeña pausa para asegurar la sincronización
#         
#     # Obtener hora local ajustada (UTC-6 para México)
#     # Si estás en UTC-6, usa -6*3600, ajusta según tu zona
#     UTC_OFFSET = -6 * 3600
#     hora_actual = time.localtime(time.time() + UTC_OFFSET)
#         
#     # El día de la semana está en el índice 6 (0 = lunes, 6 = domingo)
#     dia_semana = hora_actual[6]                 # 0=lunes, 1=martes...6=domingo
# 
#     return dia_semana
# 
#   except Exception:
#     return -1
  try:
    print("🕐 Sincronizando hora con NTP...")

    # Probar con diferentes servidores NTP
    servidores = [
        "pool.ntp.org",
        "time.google.com", 
        "time.windows.com",
        "mx.pool.ntp.org",                        # Servidor México
        "ntp.ntsc.ac.cn"
                 ]

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
      print("❌ No se pudo sincronizar con ningún servidor NTP")
      return -1

    time.sleep(1)

    # UTC-6 para México
    UTC_OFFSET = -6 * 3600
    hora_actual = time.localtime(time.time() + UTC_OFFSET)
    dia_semana = hora_actual[6]

    print(f"Día de la semana: {dia_semana} (0: Lunes)")
    return dia_semana

  except Exception as e:
    print(f"Error: {e}")
    return -1

#-------------------------------------------------------------------------------
def jugar():
#-------------------------------------------------------------------------------
  global bandera_jugando,secuencia,posicion_secuencia,bandera_boton_erroneo
  global momento_empezo_juego,bandera_oprimido

  if(not bandera_jugando):
    # Generar y mostrar secuencia
    secuencia=[]
    for i in range(nivel_actual_juego):
      boton_seleccionado_azar = random.randint(1,NUMERO_BOTONES)
      secuencia.append(boton_seleccionado_azar)
      encenderLEDs(boton_seleccionado_azar-1)
      sleep(0.5)
      apagarLEDs()
      sleep(0.5)
    print(secuencia)
    apagarLEDs()
    momento_empezo_juego = time.time()
    posicion_secuencia=-1
    bandera_boton_erroneo = False
    bandera_oprimido = -1
    bandera_jugando = True
  else:
    # Entradas del jugador
    if(time.time()-momento_empezo_juego>30):
      encenderLEDs(6)
      bandera_jugando = False
      print("Juego terminado")
      sleep(10)
    if(posicion_secuencia<nivel_actual_juego-1):
      for i in range(NUMERO_BOTONES):
        if(pin[i].value()==0):                    # Primera detección
          # --- INICIO DEBOUNCE ---
          time.sleep_ms(50)                       # Esperar a que se estabilice
          if pin[i].value() == 0:                 # Confirmar que sigue presionado
            encenderLEDs(i)
            posicion_secuencia += 1
            # Esperar a que SOLTE realmente (para contar solo UNA vez)
            while pin[i].value() == 0:
              time.sleep_ms(10)
            # Fin debounce
            apagarLEDs()
            botonOprimido = i + 1
            #print(botonOprimido,posicion_secuencia,secuencia[posicion_secuencia])
            if(secuencia[posicion_secuencia]==botonOprimido):
              pass
              #print(posicion_secuencia)
            else:
              bandera_boton_erroneo = True
    else:
      if(not bandera_boton_erroneo):
        encenderLEDs(5)
      else:
        encenderLEDs(6)
      bandera_jugando = False
      print("Juego terminado")
      sleep(5)

#-------------------------------------------------------------------------------
def procesar_comando(datos):
#-------------------------------------------------------------------------------
  """Procesa los comandos recibidos de la PC"""
  global nivel_actual_juego,bandera_jugando

  datos = datos.strip().upper()

  if datos=="EMPEZAR A JUGAR":
    bandera_jugando = True
    return "JUGANDO"

  elif datos.startswith("JUGAR_CON_NIVEL"):
    try:
      # Extraer el nivel del comando "JUGAR_NIVEL X"
      print(f"PC->ESP32: {datos}")
      nivel_actual_juego = int(datos.split()[1])
      return "ESP32->PC: COMANDO EJECUTADO CORRECTAMENTE"
    except (IndexError, ValueError):
      print(f"❌ Comando mal formado: {datos}")
      return "ERROR_COMANDO"
    
  elif datos == "PING":
    return "PONG"
    
  elif datos == "STATUS":
    return f"NIVEL ACTUAL DE JUEGO {nivel_actual_juego}"
    
  else:
    print(f"⚠️ Comando no reconocido: {datos}")
    return "COMANDO_NO_RECONOCIDO"

#-------------------------------------------------------------------------------
def blink_led_3():
#-------------------------------------------------------------------------------
  global bandera_led_2_encendido,momento_ultimo_evento_blink

  if(time.time()-momento_ultimo_evento_blink>0.5):
    if(not bandera_led_2_encendido):
      encenderLEDs(2)
      bandera_led_2_encendido = True
    else:
      apagarLEDs()
      bandera_led_2_encendido = False
    momento_ultimo_evento_blink = time.time()

#-------------------------------------------------------------------------------
def encenderLEDs(numeroLED):
#-------------------------------------------------------------------------------
  for j in range(8):
    data.value(ENCENDIDO_BOTONES[numeroLED][j])
    clock.value(1)
    clock.value(0)
  latch.value(1)
  latch.value(0)

#-------------------------------------------------------------------------------
def apagarLEDs():
#-------------------------------------------------------------------------------
  for j in range(8):
    data.value(0)
    clock.value(1)
    clock.value(0)
  latch.value(1)
  latch.value(0)

#-------------------------------------------------------------------------------
def main():
#-------------------------------------------------------------------------------
  global data, clock, latch, pin
  global bandera_cliente_conectado, cliente_socket, servidor_socket
  global bandera_led_2_encendido, momento_ultimo_evento_blink, bandera_jugando, nivel_actual_juego

#//////////////////////////////////// OBJETOS ////////////////////////////////
  print("🔧 Inicializando hardware...")                                       #/
  data = Pin(DATA_PIN, Pin.OUT, value=0)                                      #/
  clock = Pin(CLOCK_PIN, Pin.OUT, value=0)                                    #/
  latch = Pin(LATCH_PIN,Pin.OUT,value=0)                                      #/
  pin=[None] * NUMERO_BOTONES                                                 #/
  for i in range(NUMERO_BOTONES):                                             #/
    pin[i]=Pin(PIN_INTERRUPTOR_BOTON[i], Pin.IN)                              #/
  print("✅ Hardware inicializado")                                            #/
#///////////////////////////////////////////////////////////////////////////////

  # CONECTAR A WIFI
  seleccionarMejorRedWiFiDisponible()
  if not conectar_wifi():
    print("No se pudo conectar a la red en 1 minuto. Reiniciando el ESP32")
    machine.reset()
    
  # ACTUALIZAR SKETCH
  actualizarSketch()

  # OBTENER DIA DE LA SEMANA
  dia = obtener_dia_semana()
  if dia != -1:
    nivel_actual_juego = dia + 3
    print("Nivel de juego:",nivel_actual_juego)

  servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  servidor_socket.bind(('0.0.0.0', PUERTO))
  servidor_socket.listen(1)
  servidor_socket.settimeout(0.5)
    
  print(f"🌐 Puerto {PUERTO} - Esperando conexión...")

  while True:
    try:
      # Aceptar nueva conexión
      if not bandera_cliente_conectado:
        try:
          nuevo_cliente, dir = servidor_socket.accept()
          cliente_socket = nuevo_cliente
          bandera_cliente_conectado = True
          print(f"✅ PC conectada: {dir}")
          cliente_socket.send("OK_CONECTADO\n")
        except OSError:
          pass  # Timeout normal

        # Procesar datos del cliente
      if bandera_cliente_conectado and cliente_socket:
        try:
          cliente_socket.settimeout(0.1)
          datos = cliente_socket.recv(1024).decode().strip()
 
          if datos:
            print(f"📥 Recibido: {datos}")
 
            # Procesar el comando
            respuesta = procesar_comando(datos)
 
            # Enviar respuesta
            if respuesta:
              cliente_socket.send(f"{respuesta}\n")
              print(f"📤 Respuesta: {respuesta}")
 
          else:
            # Cliente cerró conexión
            print("❌ PC desconectada")
            cliente_socket.close()
            cliente_socket = None
            bandera_cliente_conectado = False
 
        except OSError as e:
          if e.args[0] == 9:  # Bad file descriptor
            print("❌ Conexión perdida")
            cliente_socket = None
            bandera_cliente_conectado = False
            pass  # Timeout normal

      # ¿JUGANDO?
      if not bandera_jugando:
        blink_led_3()
        # ¿SE DESEA JUGAR?
        if(pin[2].value()==0):
          momento_ultimo_evento=time.time()
          while(pin[2].value()==0):
            sleep_ms(5)
          if(time.time()-momento_ultimo_evento>1):
            apagarLEDs()
            sleep(1)
            print("Empezando juego")
            jugar()
      else:
        jugar()

    except KeyboardInterrupt:
      print("\n🔌 Cerrando...")
      break
    
  if cliente_socket:
    cliente_socket.close()
  if servidor_socket:
    servidor_socket.close()

#-------------------------------------------------------------------------------
def start():
#-------------------------------------------------------------------------------
  print("🎮 Función start() llamada")
  main()

if __name__ == "__main__":
    main()