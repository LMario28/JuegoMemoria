#//////////////////////////////////// IMPORTs //////////////////////////////////
import machine                                                                #/
from machine import Pin                                                       #/
from time import sleep,sleep_ms                                               #/
import network                                                                #/
import time                                                                   #/
import random                                                                 #/
#///////////////////////////////////////////////////////////////////////////////

#////////////////////////////////// CONSTANTES /////////////////////////////////
WIFI_SSID = ['INFINITUM2426_2.4','Extensor Sala','Electronica Hotspot PC', \
             'TP-Link_LMario_DHCP']                                           #/
WIFI_PASS = ['CNnC917MDE','CNnC917MDE','electronica23','lmario28']            #/
SSID=''                                                                       #/
PASSWD=''                                                                     #/
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
NIVEL_JUEGO=3                                                                 #/
#///////////////////////////////////////////////////////////////////////////////

#//////////////////////////////////// OBJETOS //////////////////////////////////
data = Pin(DATA_PIN, Pin.OUT, value=0)                                        #/
clock = Pin(CLOCK_PIN, Pin.OUT, value=0)                                      #/
latch = Pin(LATCH_PIN,Pin.OUT,value=0)                                        #/
pin=[None] * NUMERO_BOTONES                                                   #/
for i in range(NUMERO_BOTONES):                                               #/
  pin[i]=Pin(PIN_INTERRUPTOR_BOTON[i], Pin.IN)                                #/
#///////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////// VARIABLES /////////////////////////////////
bandera_led_2_encendido=False                                                 #/
momento_ultimo_evento=None                                                    #/
momento_ultimo_evento_blink=time.time()                                       #/
bandera_jugando=False                                                         #/
#///////////////////////////////////////////////////////////////////////////////

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
    ota_updater = OTAUpdater(SSID, PASSWD, firmware_url, "ProgramaPrincipal.py")
    ota_updater.download_and_install_update_if_available()
  except:
    print("NO SE PUDO ACTUALIZAR EL SKETCH")
  print("*************************")

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
#///////////////////////////////////////////////////////////////////////////////

#///////////////////////////////////////////////////////////////////////////////
#/ PROCESO   PROCESO   PROCESO   PROCESO   PROCESO   PROCESO   PROCESO        //
#///////////////////////////////////////////////////////////////////////////////
#-------------------------------------------------------------------------------
def proceso():
  pass

# CONECTAR A WIFI
seleccionarMejorRedWiFiDisponible()
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
  ESP.restart()
print('\nRed conectada. IP:', wifi.ifconfig()[0])

# ACTUALIZAR SKETCH
actualizarSketch()

# JUGAR
random.seed()
bandera_jugando=False
secuencia=[]
while True:
  try:
    if not bandera_jugando:
      blink_led_3()
      # Iniciar juego (botón)
      if(pin[2].value()==0):
        momento_ultimo_evento=time.time()
        while(pin[2].value()==0):
          sleep_ms(5)
        if(time.time()-momento_ultimo_evento>2):
          apagarLEDs()
          bandera_jugando=True
          print("Empezando juego")
          # Desplegando secuencia
          for i in range(NIVEL_JUEGO):
            boton_seleccionado_azar = random.randint(1,NUMERO_BOTONES)
            secuencia.append(boton_seleccionado_azar)
            apagarLEDs()
            sleep(0.5)
            encenderLEDs(boton_seleccionado_azar-1)
            sleep(2)
          apagarLEDs()
          #Esperar respuesta de jugador
          bandera_jugando=False

  except KeyboardInterrupt:
    break

apagarLEDs()
wifi.disconnect()
time.sleep(1)
if not wifi.isconnected():
  print("WiFi disconnected")
else:
  print("No se pudo desconectar de la red WiFi")
print("Programa terminado por el usuario")
