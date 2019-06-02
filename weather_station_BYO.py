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

Verzió: Python BNWS 6.0
- WeatherUnderground adatküldés kiszervezése
- Időkép adatküldés kiszervezése
- Időkép PM adatküldés kiszervezése

Verzió: Python BNWS 5.1
- Eső tárolók használata MySql szerver segítségével
- MySql tábla törlése havonta

Verzió: Python BNWS 5.0
- MySql connector hozzáadása
- Adatok feltöltése a MySql szerverre

Verzió: Python BNWS 4.3
- Adatfeltöltés hibakezelés
- E-mail küldés hiba esetén

Verzió: Python BNWS 4.2
- Adatfeltöltés hibakezelés javítása

Verzió: Python BNWS 4.1
- Adatfeltöltés hibakezelés hozzáadása

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
from datetime import datetime, timedelta
import time
from time import strftime
import os
import statistics
import serial
import math
import wind_direction_byo
import board
import busio
import adafruit_bme280
import adafruit_veml6075
from pms7003 import PMS7003
from send_wu_data import send_wu_data
#from send_id_data import send_id_data
from send_id_data import send_idpm_data
import mysql.connector

# ALAPÉRTEKEK MEGADASA:

softwaretype_str = "Python BNWS 6.0"    # Szoftver verzió
upload_interval = 300                   # Feltöltés hurokfutás ideje (sec-ban), (300 sec)
store_speeds = []                       # Szélsebesség tároló
store_directions = []                   # Szélirány tároló
store_uvi = []                          # UV-index tároló
store_uva = []                          # UVA tároló
store_uvb = []                          # UVB tároló
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

mysql_aut = {                                   # MySql autentikáció
    'user': 'weather',
    'password': 'station',
    'host': '192.168.1.10',
    'database': 'weather',
    'raise_on_warnings': True
}                                          

i2c = busio.I2C(board.SCL, board.SDA)

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

# HUROK DEFINIÁLÁSA:
                                                                                                           
while True:
    n +=1                                                                   # Képernyő törlése naponta
    if n == 288:
        os.system('clear')
        n = 0
        
    #Szélsebesség, széllokés kiszámolása:
    upload_time = time.time()
    while time.time() - upload_time <= upload_interval:                     # 5 percenkénti upload ciklus
        dt = datetime.now()
        wind_start_time = time.time()
        reset_wind()
        #time.sleep(wind_interval)
        while time.time() - wind_start_time <= wind_interval:               # 5 másodperces szél ciklus
            store_directions.append(wind_direction_byo.get_value())
            
            s+= 1                                                           # PMS7003 indítása az adatküldés előtt
            if s  >= 49:                                                    # 30 másodperccel
                pms.on()
            print(s)
            if s == 49:
                print("PMS7003 indítása!")

            veml = adafruit_veml6075.VEML6075(i2c, integration_time=100)    # UV értékek felolvasása
            store_uva.append(veml.uva)                                      # UVA tárolása
            store_uvb.append(veml.uvb)                                      # UVB tárolása
            store_uvi.append(veml.uv_index)                                 # UV-index tárolása
            uva = max(store_uva)                                            # Maximális UVA számítása
            uvb = max(store_uvb)                                            # Maximális UVB számítása
            uv_index = max(store_uvi)                                       # Maximális UV-index számítása
            int_time = veml.integration_time                                # Integrálási idő kiolvasás
                               
        final_speed = calculate_speed(wind_interval)
        store_speeds.append(final_speed)
        
    
    wind_average = wind_direction_byo.get_average(store_directions)
    wind_gust = max(store_speeds)
    wind_speed = statistics.mean(store_speeds)

    # Eső kiszámolása:
    rainf = rain_count * BUCKET_SIZE

    t_stop_dailyrain = dt  - timedelta(minutes=5)                           # Napi eső start időpont (jelenlegi idő)
    t_start_dailyrain = dt - timedelta(days=1) - timedelta(minutes=5)       # Napi eső stop időpont (jelenlegi idő - 1 nap)
    t_stop_rainfall = dt - timedelta(minutes=5)                             # 1 órai eső start időpont (jelenlegi idő)
    t_start_rainfall = dt - timedelta(hours=1) - timedelta(minutes=5)       # 1 órai eső stop időpont (jelenlegi idő - 1 óra)

   
    try:
        db = mysql.connector.connect(**mysql_aut)
    
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Hibás felhasználónév vagy jelszó!")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Adatbázis nem megfelelő!")
      else:
        print(err)
    else:
        db.reconnect(attempts=5, delay=30)

    cursor = db.cursor()

    sql_read = ("SELECT rainf FROM WEATHER_MEASUREMENT WHERE dt BETWEEN %s AND %s")

    cursor.execute(sql_read, (t_start_dailyrain, t_stop_dailyrain))
    result_dailyrain = cursor.fetchall()

    cursor.execute(sql_read, (t_start_rainfall, t_stop_rainfall))
    result_rainfall = cursor.fetchall()

    cursor.close()
    db.close()

    list_dailyrain = list(result_dailyrain)
    list_rainfall = list(result_rainfall)
    dailyrain = sum([list_dailyrain[0] for list_dailyrain in list_dailyrain])
    rainfall = sum([list_rainfall[0] for list_rainfall in list_rainfall])
        
                          
    # Tárolók törlése:
    store_speeds = []
    store_directions = []
    store_uva = []
    store_uvb = []
    store_uvi = []
    reset_rainfall()

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

 
    #PMS7003 => PM2.5, PM10, PM1
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
    print(dt)

    send_wu_data(dt,
                 ambient_temp,
                 humidity,
                 p0,
                 wind_speed,
                 wind_gust,
                 wind_average,
                 rainfall,
                 dailyrain,
                 dewp_c,
                 uv_index,
                 pm2_5,
                 pm10,
                 softwaretype_str
                 )

    """send_id_data(dt,
                 ambient_temp,
                 humidity,
                 wind_average,
                 wind_speed,
                 wind_gust,
                 dailyrain,
                 rainfall,
                 pressure,
                 p0,
                 uv_index,
                 )"""
    
    send_idpm_data(dt,
                   pm2_5,
                   pm10
                   )
        

    # MySql adatfeltöltés
    try:
        db = mysql.connector.connect(**mysql_aut)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Hibás felhasználónév vagy jelszó!")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Adatbázis nem megfelelő!")
        else:
            print(err)
    else:
        db.reconnect(attempts=5, delay=30)
       
    cursor = db.cursor()
    sql = "INSERT INTO WEATHER_MEASUREMENT (dt, wind_speed, wind_gust, wind_average, rainf, rainfall, dailyrain, humidity, pressure, p0, ambient_temp, dewp_c, altitude, uv_index, uva, uvb, pm1, pm2_5, pm10) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    val = (dt,
           wind_speed,
           wind_gust,
           wind_average,
           rainf,
           rainfall,
           dailyrain,
           humidity,
           pressure,
           p0,
           ambient_temp,
           dewp_c,
           altitude,
           uv_index,
           uva,
           uvb,
           pm1,
           pm2_5,
           pm10)
    cursor.execute(sql, val)
    
    t_delete = dt - timedelta(days=31)
    sql_delete = ("DELETE FROM WEATHER_MEASUREMENT WHERE dt < %s")
    cursor.execute(sql_delete, (t_delete,))
    
    db.commit()
    cursor.close()
    db.close()
    print(cursor.rowcount, "MySql adatok beillesztése sikeres.", '\n')

   

