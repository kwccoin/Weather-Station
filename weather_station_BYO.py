#!/usr/bin/python

"""
MIT License

Copyright (c) 2019 Bajusz Norbert

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Időjárás állomas Raspberry Pi 3 B+ (c) 2019
Készítette: Bajusz Norbert Hungary (HU)

Verzió: Python BNWS 4.0
- PM1 por mérés hozzáadása
- Tengerszintre számított nyomás hozzáadása

Verzió: Python BNWS 3.3
- UV értékek folyamatos olvasása, tárolóba helyezése, számítása

Verzió: Python BNWS 3.2
- Hőmérséklet, páratartalom, nyomás, magasság kód hibajavítás, közvetlen elérés kódolása

Verzió: Python BNWS 3.1
- UVA, UVB, UVIndex kód hibajavítás, közvetlen elérés kódolása

Verzió: Python BNWS 3.0
- UVA, UVB, UVIndex

Verzió: Python BNWS 2.1
 - Időkép adatküldés leállítása

Verzió: Python BNWS 2.0
 - Időkép adatküldés

Verzió: Python BNWS 1.0
 - PMS7003 szenzor telepítése
 - PM2.5, PM10 részecskék mérése

Verzió: Python BNWS 0.2
 - WeatherUnderground adatküldés

Verzió: Python BNWS 0.1
 - SparkFun  SEN-08942 Időjárás állomás telepítése
 - Szélsebesség, széllökés, szélirány, eső mérése

Verzió: Python BNWS 0.0
 - BM280 érzékelő
 - Hőmérséklet, páratartlom, nyomás mérése
"""

# KÖNYVTÁRAK, SEGEDPROGRAMOK IMPORTÁLÁSA:

from gpiozero import Button, LED
from datetime import datetime
import time
import os
import statistics
import requests
import serial
import math
import wind_direction_byo
import board
import busio
import adafruit_bme280
import adafruit_veml6075
from pms7003 import PMS7003

# ALAPÉRTEKEK MEGADASA:

upload_interval = 300                   # Feltöltés hurokfutás ideje (sec-ban), (300 sec)
store_speeds = []                       # Szélsebesség tároló
store_directions = []                   # Szélirány tároló
store_uvi = []                          # UV-index tároló
store_uva = []                          # UVA tároló
store_uvb = []                          # UVB tároló
rainh = []                              # Eső tároló órai
raind = []                              # Eső tároló napi
wind_count = 0                          # Szél számláló                         
rain_count = 0                          # Eső számláló
gust = 0                                # Szélirány 
radius_cm = 9.0                         # Szélsebesség mérő sugara (cm-ben)
wind_interval = 5                       # Szélsebesség merő mintavételezési ideje (sec-ban), (5 sec)
CM_IN_A_KM = 100000.0                   # Hány cm van egy kilométerben
SECS_IN_AN_HOUR = 3600                  # Hány másodperc van egy órában
ADJUSTMENT = 1.18                       # Szélsebesség mérő korekciós tényező
BUCKET_SIZE = 0.2794                    # Esőmerő billenőedeny mérete
a = 6.1121                              # a, b, c álandók a harmatpont számításhoz (lásd: Wikipédia)
b = 18.678
c = 257.14
g = 9.80665                             # Nehézségi gyorsulás
hs = 84                                 # Tengerszint feletti magasság
R = 287.05                              # Száraz levegőre vonatkozó gázállandó
gamma = 0.0065                          # Függőleges hőmérsékleti gradiens
s = 0                                   # Ciklusszámláló PMS7003 indítására
n = 0                                   # Ciklusszámláló képernyőtörlésre

i2c = busio.I2C(board.SCL, board.SDA)

# A www.wunderground.com-ra küldés URL első felének megadása
WUurl = "https://weatherstation.wunderground.com/weatherstation\
/updateweatherstation.php?"
WU_station_id = "YOUR STATION ID"               # állomas ID
WU_station_pwd = "YOUR STATION PASSWORD"             # állomas jelszó
WUcreds = "ID=" + WU_station_id + "&PASSWORD="+ WU_station_pwd
date_str = "&dateutc=now"
action_str = "&action=updateraw"
softwaretype_str = "Python BNWS 4.0"

# A www.időkép.hu-ra küldés URL első felének megadása
#ID_url = "https://automata.idokep.hu/sendws.php?"
#ID_user = "YOUR USER NAME"                  # felhsználónév
#ID_pwd = "YOUR PASSWORD"                 # jelszó
#ID_creds = "user=" + ID_user + "&pass="+ ID_pwd
#ID_utc = "&0"
#ID_type = "&RaspberryPi"
#ID_action_str = "&action=updateraw"

# A www.időkép.hu-ra küldés URL első felének megadása a PM2,5 és PM10 értékeknek
IDPM_url = "https://automata.idokep.hu/sendszmog.php?"
IDPM_id = "XXXX"			# YOUR ID
IDPM_varos = "XXXXXXXX"		# YOUR CITY
IDPM_helyseg = "XXXXXX"		# YOUR PLACE
IDPM_eszel = "XX.XX"		# YOUR northern latitude
IDPM_khossz = "XX.XX"		# YOUR east length
IDPM_action_str = "&action=updateraw"


# FÜGGVÉNYEK DEFINIÁLÁSA:

def spin():                                                 # Szél számláló, minden fél fordulattal +1 hozzaadasa a számlálóhoz
    global wind_count
    wind_count = wind_count + 1

def calculate_speed(time_sec):                              # Szélsebesseg számítása
    global wind_count
    global gust
    circumference_cm = (2 * math.pi) * radius_cm
    rotations = wind_count / 2.0
    dist_km = (circumference_cm * rotations) / CM_IN_A_KM   # A kupakkal megtett távolság kiszámítása
    km_per_hour = (dist_km / time_sec) * SECS_IN_AN_HOUR    # Sebesseg = távolság / idő
    final_speed = km_per_hour * ADJUSTMENT                  # Sebesseg kiszámolása
    return final_speed

def bucket_tipped():                                        # Esőmérő számítása
    global rain_count
    rain_count = rain_count + 1                             # Eső számláló

def reset_rainfall():                                       # Csapadék számláló törlése
    global rain_count
    rain_count = 0

def reset_wind():                                           # Szelsebesseg szamlalo torlese
    global wind_count
    wind_count = 0

def reset_gust():                                           # Szélirány számláló törlése
    global gust
    gust = 0
    
wind_speed_sensor = Button(5)                               # Szélsebesseg bemenet definiálása
wind_speed_sensor.when_pressed = spin                       # Jel esetén Spin függvény meghívása

rain_sensor = Button(6)                                     # Eső bemenet definiálása
rain_sensor.when_pressed = bucket_tipped                    # Jel eseten Bucket_tripped függvény meghívása

pms = LED(12)                                               #PMS7003 indítására szolgáló kimenet
                                                            # A mérés előtt 30 másodperccel ki kell adni a jelet!

def hpa_to_inches(pressure_in_hpa):                         # hPa konvertálása inch-re nyomás
    pressure_in_inches_of_m = pressure_in_hpa * 0.0295
    return pressure_in_inches_of_m

def mm_to_inchesrh(rainfall_in_mm):                         # mm konvertálása inch-be eső órai
    rainfall_in_inches = rainfall_in_mm * 0.0393701
    return rainfall_in_inches

def mm_to_inchesrd(dailyrain_in_mm):                        # mm konvertálása inch-be eső napi
    dailyrain_in_inches = dailyrain_in_mm * 0.0393701
    return dailyrain_in_inches

def degc_to_degf(temperature_in_c):                         # C fok konvertálása F-re hőmérséklet
    temperature_in_f = (temperature_in_c * (9/5.0)) + 32
    return temperature_in_f

def dewpc_to_dewpf(dewp_in_c):                              # C fok konvertálása F-re harmatpont (Dewpoint)
    dewp_in_f = (dewp_c * (9/5.0)) + 32
    return dewp_in_f

def kmh_to_mph(speed_in_kmh):                               # km/h konvertálása mph-ba
    speed_in_mph = speed_in_kmh * 0.621371
    return speed_in_mph

def kmh_to_ms(speed_in_kmh):                               # km/h konvertálása m/s-ba
    speed_in_ms = speed_in_kmh / 3.6
    return speed_in_ms

# HUROK DEFINIÁLÁSA:
                                                                                                           
while True:
    n +=1                                                                   # Képernyő törlése naponta
    if n == 288:
        os.system('clear')
        n = 0
        
    #Szélsebesség, széllokés kiszámolása:
    upload_time = time.time()
    while time.time() - upload_time <= upload_interval:                     # 5 percenkénti upload ciklus
        wind_start_time = time.time()
        reset_wind()
        #time.sleep(wind_interval)
        while time.time() - wind_start_time <= wind_interval:               # 5 másodperces szél ciklus
            store_directions.append(wind_direction_byo.get_value())
            
            s+= 1                                                           # PMS7003 indítása az adatküldés előtt
            if s  >= 53:                                                    # 30 másodperccel
                pms.on()
            print(s)
            if s == 53:
                print("PMS7003 indítása!")

            veml = adafruit_veml6075.VEML6075(i2c, integration_time=100)    # UV értékek
            store_uva.append(veml.uva)                                      # UVA tárolása
            store_uvb.append(veml.uvb)                                      # UVB tárolása
            store_uvi.append(veml.uv_index)                                 # UV-index tárolása
            uva = max(store_uva)                                            # Maximális UVA számítása
            uvb = max(store_uvb)                                            # Maximális UVB számítása
            uv_index = max(store_uvi)                                       # Maximális UV-index számítása
            int_time = veml.integration_time                        # Integrálási idő kiolvasás
                               
        final_speed = calculate_speed(wind_interval)
        store_speeds.append(final_speed)
        
    
    wind_average = wind_direction_byo.get_average(store_directions)
    wind_gust = max(store_speeds)
    wind_speed = statistics.mean(store_speeds)

    # Eső kiszámolása:
    rainf = rain_count * BUCKET_SIZE
    t = time.asctime(time.localtime(time.time()))

    with open('/media/pi/B415-25E9/rain.txt',mode='a') as x:                # Eső érték fájba írása, csak az utolsó sor hozzáadása
         x.write(str(t) + ' ' + str(rainf) + ' ' + '\n,')

    lines = open('/media/pi/B415-25E9/rain.txt').readlines()                # Az első sor törlése
    open('/media/pi/B415-25E9/raintmp.txt', 'w').writelines(lines[1:-1])
    os.remove("/media/pi/B415-25E9/rain.txt")                               # Fájlcsere
    os.rename("/media/pi/B415-25E9/raintmp.txt", "/media/pi/B415-25E9/rain.txt")
    
    with open('/media/pi/B415-25E9/rain.txt') as f:                     
        sorok = f.readlines()
        for i in range(12):                                                 # Elmúlt 1 órai eső kiszámolása
            h = float(sorok[275 + i].split()[5])
            rainh.append(h)
            
    rainfall = sum(rainh)
    rainh = []
    
    with open('/media/pi/B415-25E9/rain.txt') as f:
        for y in range(288):                                                # Elmúlt 1 napi eső kiszámolása
            d = float(sorok[y].split()[5])
            raind.append(d)
            
    dailyrain = sum(raind)
    raind = []
    
    reset_rainfall()
                          
    # Tárolók törlése:
    store_speeds = []
    store_directions = []
    store_uva = []
    store_uvb = []
    store_uvi = []

    # Páratartalom, légnyomas, hőmérséklet:
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
    bme280.sea_level_pressure = 1013.25
    humidity = bme280.humidity
    pressure = bme280.pressure
    ambient_temp = bme280.temperature
    altitude = bme280.altitude

    # Tengerszintre számított nyomás:
    Ts = ambient_temp + 273.15              # Műszer szinti hőmérséklet °K-ben
    ps = pressure * 100                     # Műszer szinti nyomás Pa-ban
    T0 = Ts + gamma * hs                    # Tengerszinti hőmérséklet °K-ben
    e = gamma * hs
    f = g / (gamma * R)
    p0 = ps / ((1 - e / T0) ** f) / 100     # Tengerszintre számított nyomás hPa-ban

    # Harmatpont kiszamítasa 
    gamma = (b * ambient_temp / (c + ambient_temp)) + math.log(humidity / 100.0)
    dewp_c = c * gamma / (b - gamma)

 
    #PMS7003 => PM2.5, PM10
    dust = PMS7003()
    ser = serial.Serial('/dev/ttyS0', 9600, timeout = 1)
    buffer = ser.read(1024)
    if(dust.protocol_chk(buffer)):
        data = dust.unpack_data(buffer)
        pm1 = data[dust.DUST_PM1_0_ATM]
        pm2_5 = data[dust.DUST_PM2_5_ATM]
        pm10 = data[dust.DUST_PM10_0_ATM]
    else:
        print ("PMS7003 adat olvasási hiba")
        pms.on()
        time.sleep(30)
        dust = PMS7003()
        ser = serial.Serial('/dev/ttyS0', 9600, timeout = 1)
        buffer = ser.read(1024)
        if(dust.protocol_chk(buffer)):
            data = dust.unpack_data(buffer)
            pm1 = data[dust.DUST_PM1_0_ATM]
            pm2_5 = data[dust.DUST_PM2_5_ATM]
            pm10 = data[dust.DUST_PM10_0_ATM]
            
    ser.close()
    s=0
    pms.off()  

    # Mért értékek kiíratása (nyers):
    print('\n')
    print('Szélsebesség:    ', "{0:.2f}".format(wind_speed), 'km/h')
    print('Széllökés:       ', "{0:.2f}".format(wind_gust), 'km/h')
    print('Szélirány:       ', "{0:.2f}".format(wind_average),'°')
    print('Órás eső:        ', "{0:.2f}".format(rainfall), 'mm')
    print('Napi eső:        ', "{0:.2f}".format(dailyrain), 'mm')
    print('Páratartalom:    ', "{0:.2f}".format(humidity), '%')
    print('Légnyomás:       ', "{0:.2f}".format(pressure), 'hPa')
    print('Légnyomás p0     ', "{0:.2f}".format(p0), 'hPa')
    print('Hőmérséklet:     ', "{0:.2f}".format(ambient_temp), 'C°')
    print('Harmatpont:      ', "{0:.2f}".format(dewp_c), 'C°')
    print('Magasság:        ', "{0:.2f}".format(altitude), 'm')
    print('Integrációs idő: ', int_time, 'ms')
    print('UV-index:        ', "{0:.2f}".format(uv_index))
    print('UVA:             ', "{0:.2f}".format(uva))
    print('UVB:             ', "{0:.2f}".format(uvb))
    print('PM1              ', pm1, 'ug/m3')
    print('PM2.5:           ', pm2_5, 'ug/m3')
    print('PM10:            ', pm10, 'ug/m3')
    ido = datetime.now()
    print (ido)

    # WU küldött adatok formai követelményeinek összeállítása
    ambient_temp_str = "{0:.2f}".format(degc_to_degf(ambient_temp))
    humidity_str = "{0:.2f}".format(humidity)
    pressure_in_str = "{0:.2f}".format(hpa_to_inches(pressure))
    wind_speed_mph_str = "{0:.2f}".format(kmh_to_mph(wind_speed))
    wind_gust_mph_str = "{0:.2f}".format(kmh_to_mph(wind_gust))
    wind_average_str = "{0:.2f}".format(wind_average)
    rainfall_in_str = "{0:.2f}".format(mm_to_inchesrh(rainfall))
    dailyrain_in_str = "{0:.2f}".format(mm_to_inchesrd(dailyrain))
    dewp_f_str = "{0:.2f}".format(dewpc_to_dewpf(dewp_c))
    uvi_str = str("{0:.2f}".format(uv_index))
    AqPM2_5_str = str("{0:.2f}".format(pm2_5))
    AqPM10_str = str("{0:.2f}".format(pm10))

    # Mért értékek kiíratása (WU-ra küldött):
    print('\n')
    print('Szélsebesség: ', wind_speed_mph_str, 'mph')
    print('Széllökés :   ', wind_gust_mph_str, 'mph')
    print('Szélirány:    ', wind_average_str,'°')
    print('Órás eső:     ', rainfall_in_str, 'inch')
    print('Napi eső:     ', dailyrain_in_str, 'inch')
    print('Páratartalom: ', humidity_str, '%')
    print('Légnyomás:    ', pressure_in_str, 'in')
    print('Hőmérséklet:  ', ambient_temp_str, 'F°')
    print('Harmatpont:   ', dewp_f_str, 'F°')
    print('UV-index:     ', uvi_str)
    print('PM2.5:        ', AqPM2_5_str, 'ug/m3')
    print('PM10:         ', AqPM10_str, 'ug/m3')
    ido = datetime.now()
    print (ido)

    # Adatküldés a www.wundwerground.com-ra
    r= requests.get(
        WUurl +
        WUcreds +
        date_str +
        "&winddir=" + wind_average_str +                    #[0-360°] pillanatnyi szélirány
        "&windspeedmph=" + wind_speed_mph_str +             #[mph] azonnali szélsebesség
        "&windgustmph=" + wind_gust_mph_str +               #[mph] aktuális széllökés, szoftverspecifikus időszak használatával
    #   "&windgustdir=" + wind_gust_dir_str +                #[0-360°] szoftverspecifikus időszak használatával
    #   "&windspdmph_avg2m=" + wind_speed_mph_avg2m_str +    #[mph] 2 perc átlagos szélsebesség
    #   "&winddir_avg2m=" + wind_dir_avg2m_str +             #[0-360°] 2 perces átlagos szélirány
    #   "&windgustmph_10m=" + wind_gust_mph_10m_str +        #[mph] 10 perces átlagos széllökés
    #   "&windgustdir_10m=" + wind_gust_dir_10m_str +        #[0-360°] 10 perces átlagos szélirány
        "&humidity=" + humidity_str +                       #[0-100%] kültéri páratartalom
        "&dewptf=" + dewp_f_str +                           #[F°] kültéri harmatpont
        "&tempf=" + ambient_temp_str +                      #[F°] kültéri hőmérséklet
        "&rainin=" + rainfall_in_str +                      #[inch] az elmúlt órában esett eső
        "&dailyrainin=" + dailyrain_in_str +                #[inch] az elmúlt napban esett eső az aktuális helyi idő szerint
        "&baromin=" + pressure_in_str +                     #[inch] barometikus nyomás
    #   "&weather=" + weather_str +                          #[szöveg] Lásd: METAR Wikipédia
    #   "&clouds=" + clouds_str +                            #[szöveg] Lásd: METAR Wikipédia
    #   "&soiltempf=" + soil_temp_str +                      #[F°] talajhőmérséklet
    #   "&soilmoisture=" + soil_moisture_str +               #[0-100%] talajnedveség
    #   "&leafwetness=" + leafwetness_str +                  #[0-100%] levélszárazság
    #   "&solarradiation=" + solar_radiation_str +           #[W/m2] napsugárzás
        "&UV=" + uvi_str +                                   #[index] UV-index
    #   "&visibility=" + visiblity_str +                     #[nm] láthatóság
    #   "&indoortempf=" + indoor_tempf_str +                 #[F°] beltéri hőmérséklet
    #   "&indoorhumidity=" + indoor_humidity_str +           #[0-100%] beltéri páratartalom
        "&AqPM2.5=" + AqPM2_5_str +                         #[ug/m3] PM 2.5 részecskék
        "&AqPM10=" + AqPM10_str +                           #[ug/m3] PM 10 részecskék
        "&softwaretype=" + softwaretype_str +
        action_str)

    print("Received " + str(r.status_code) + " " + str(r.text))

#    # ID küldött adatok formai követelményeinek összeállítása
#    now = datetime.now()
#    year = now.strftime("%Y")
#    month = now.strftime("%m")
#    day = now.strftime("%d")
#    hour = now.strftime("%H")
#    minute = now.strftime("%M")
#    secound = now.strftime("%S")
#    ambient_temp_ID_str = "{0:.2f}".format(ambient_temp)
#    humidity_ID_str = "{0:.2f}".format(humidity)
#    wind_average_ID_str = "{0:.2f}".format(wind_average)
#    wind_speed_ms_str = "{0:.2f}".format(kmh_to_ms(wind_speed))
#    wind_gust_ms_str = "{0:.2f}".format(kmh_to_ms(wind_gust))
#    dailyrain_ID_str = "{0:.2f}".format(dailyrain)
#    rainfall_ID_str = "{0:.2f}".format(rainfall)
#    pressure_ID_str = "{0:.2f}".format(pressure)
#    pressure0_ID_str = "{0:.2f}".format(p0)
#    uv_index_ID_str = "{0:.2f}".format(uv_index)
#    altitude_ID_str = "{0:.2f}".format(altitude)

    # Mért értékek kiíratása (Időképre küldött):
#    print('Szélsebesség: ', wind_speed_ms_str, 'm/s')
#    print('Széllökés :   ', wind_gust_ms_str, 'm/s')
#    print('Szélirány:    ', wind_average_ID_str,'°')
#    print('Órás eső:     ', rainfall_ID_str, 'mm')
#    print('Napi eső:     ', dailyrain_ID_str, 'mm')
#    print('Páratartalom: ', humidity_ID_str, '%')
#    print('Légnyomás:    ', pressure_ID_str, 'hPa')
#    print('Légnyomás:    ', pressure0_ID_str, 'hPa')
#    print('Hőmérséklet:  ', ambient_temp_ID_str, '°C')
#    print('Magasság:     ', altitude_ID_str, 'm')
#    ido = datetime.now()
#    print (ido)
    
    # Adatküldés a www.időkép.hu-ra
#    rid= requests.get(
#        ID_url +
#        ID_creds +
#        ID_utc +
#        ID_type +
#        "&ev=" + year +                                         # Év
#        "&honap=" + month +                                     # Hónap
#        "&nap=" + day +                                         # Nap
#        "&ora=" + hour +                                        # Óra
#        "&perc=" + minute +                                     # Perc
#        "&mp=" + secound +                                      # Másodperc
#        "&hom=" + ambient_temp_ID_str +                         # [°C] Hőmérséklet
#        "&rh=" + humidity_ID_str +                              # [0-100%] Páratartalom 
#        "&szelirany=" + wind_average_ID_str +                   # [0-360°] Szélitány
#        "&szelero=" + wind_speed_ms_str +                       # [m/s] Szélsebesség
#        "&szellokes=" + wind_gust_ms_str +                      # [m/s] Széllökés
#        "&csap=" + dailyrain_ID_str +                           # [mm] Az elmúlt 1 napban eset eső
#        "&csap1h=" + rainfall_ID_str +                          # [mm] Az elmúlt 1 órában esett eső
#        "&p=" + pressure0_ID_str +                               # [hPa] Tengerszintre számított légnyomás
#        "&ap=" + pressure_ID_str +                              # [hPa] Műszerszinti légnyomás
#        "&uv=" + uv_index_iD_str +                              # [index] UV-index
#        ID_action_str)

#    print("Received " + str(rid.status_code) + " " + str(rid.text))

    # Adatküldés a www.időkép.hu-ra, csak a PM értékek
    dt = datetime.now()                                         # UNIX timestamp előállítása és formázása
    timestamp = datetime.timestamp(dt)
    ts_str = "{0:.0f}".format(timestamp)

    ridpm = requests.get(
        IDPM_url +
        "id=" + IDPM_id +
        "&pm25=" + AqPM2_5_str +
        "&pm10=" + AqPM10_str +
        "&varos=" + IDPM_varos +
        "&helyseg=" + IDPM_helyseg +
        "&eszaki=" + IDPM_eszel +
        "&keleti=" + IDPM_khossz +
        "&time=" + ts_str +
        IDPM_action_str)
    
    print("Received " + str(ridpm.status_code) + " " + str(ridpm.text))
