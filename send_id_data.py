import requests
from requests.exceptions import HTTPError
from write_error import write_error
from send_email import send_email
from datetime import datetime
from time import strftime

# A www.időkép.hu-ra küldés URL első felének megadása
ID_url = "https://automata.idokep.hu/sendws.php?"
ID_user = "XXXX"                  # felhsználónév
ID_pwd = "YYYY"                 # jelszó
ID_creds = "user=" + ID_user + "&pass="+ ID_pwd
ID_utc = "&0"
ID_type = "&RaspberryPi"
ID_action_str = "&action=updateraw"

# A www.időkép.hu-ra küldés URL első felének megadása a PM2,5 és PM10 értékeknek
IDPM_url = "https://automata.idokep.hu/sendszmog.php?"
IDPM_id = "XXXX"
IDPM_varos = "YOUR CITY"
IDPM_helyseg = "YOUR PLACE"
IDPM_eszel = "XX.XX"
IDPM_khossz = "YY.YY"
IDPM_action_str = "&action=updateraw"

def kmh_to_ms(speed_in_kmh):                                # km/h konvertálása m/s-ba
    speed_in_ms = speed_in_kmh / 3.6
    return speed_in_ms

def send_id_data(dt,
                 ambient_temp,
                 humidity,
                 wind_average,
                 wind_speed,
                 wind_gust,
                 dailyrain,
                 rainfall,
                 pressure,
                 p0,
                 uv_index):
    
    # ID küldött adatok formai követelményeinek összeállítása
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    day = dt.strftime("%d")
    hour = dt.strftime("%H")
    minute = st.strftime("%M")
    secound = dt.strftime("%S")
    ambient_temp_ID_str = "{0:.2f}".format(ambient_temp)
    humidity_ID_str = "{0:.2f}".format(humidity)
    wind_average_ID_str = "{0:.2f}".format(wind_average)
    wind_speed_ms_str = "{0:.2f}".format(kmh_to_ms(wind_speed))
    wind_gust_ms_str = "{0:.2f}".format(kmh_to_ms(wind_gust))
    dailyrain_ID_str = "{0:.2f}".format(dailyrain)
    rainfall_ID_str = "{0:.2f}".format(rainfall)
    pressure_ID_str = "{0:.2f}".format(pressure)
    pressure0_ID_str = "{0:.2f}".format(p0)
    uv_index_ID_str = "{0:.2f}".format(uv_index)

    # Mért értékek kiíratása (Időképre küldött):
    print('\n')
    print('Szélsebesség: ', wind_speed_ms_str, 'm/s')
    print('Széllökés :   ', wind_gust_ms_str, 'm/s')
    print('Szélirány:    ', wind_average_ID_str,'°')
    print('Órás eső:     ', rainfall_ID_str, 'mm')
    print('Napi eső:     ', dailyrain_ID_str, 'mm')
    print('Páratartalom: ', humidity_ID_str, '%')
    print('Légnyomás:    ', pressure_ID_str, 'hPa')
    print('Légnyomás:    ', pressure0_ID_str, 'hPa')
    print('Hőmérséklet:  ', ambient_temp_ID_str, '°C')
    print(dt)
    
    # Adatküldés a www.időkép.hu-ra
    try:
       rid= requests.get(
           ID_url +
           ID_creds +
           ID_utc +
           ID_type +
           "&ev=" + year +                                         # Év
           "&honap=" + month +                                     # Hónap
           "&nap=" + day +                                         # Nap
           "&ora=" + hour +                                        # Óra
           "&perc=" + minute +                                     # Perc
           "&mp=" + secound +                                      # Másodperc
           "&hom=" + ambient_temp_ID_str +                         # [°C] Hőmérséklet
           "&rh=" + humidity_ID_str +                              # [0-100%] Páratartalom 
           "&szelirany=" + wind_average_ID_str +                   # [0-360°] Szélitány
           "&szelero=" + wind_speed_ms_str +                       # [m/s] Szélsebesség
           "&szellokes=" + wind_gust_ms_str +                      # [m/s] Széllökés
           "&csap=" + dailyrain_ID_str +                           # [mm] Az elmúlt 1 napban eset eső
           "&csap1h=" + rainfall_ID_str +                          # [mm] Az elmúlt 1 órában esett eső
           "&p=" + pressure0_ID_str +                              # [hPa] Tengerszintre számított légnyomás
           "&ap=" + pressure_ID_str +                              # [hPa] Műszerszinti légnyomás
           "&uv=" + uv_index_iD_str +                              # [index] UV-index
           ID_action_str)

       print('\n', "Received " + str(rid.status_code) + " " + str(rid.text))

    except (requests.exceptions.RequestException, requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print (e)
        write_error(dt, "Valami halozatos hiba adodott.")
        # write_error(dt, e)
    except Exception as e:
        print(e)
        write_error(dt, "Ismeretlen hiba adodott.")                    
        write_error(dt, e)
        msg = str(dt) + "Időkép adatkuldes hiba!" + str(e)
        send_email(msg)



def send_idpm_data(dt,
                   pm2_5,
                   pm10):
    
    # Időképre küldött adatok formai követelményeinek összeállítása
    timestamp = datetime.timestamp(dt)                              # UNIX timestamp előállítása és formázása
    ts_str = "{0:.0f}".format(timestamp)
    AqPM2_5_str = str("{0:.2f}".format(pm2_5))
    AqPM10_str = str("{0:.2f}".format(pm10))

    # Mért értékek kiíratása (Időképre küldött PM)
    print('\n')
    print('PM2.5:        ', AqPM2_5_str, 'ug/m3')
    print('PM10:         ', AqPM10_str, 'ug/m3')
    print(dt)

    # Adatküldés a www.időkép.hu-ra, csak a PM értékek
    try:
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
        
        print('\n', "Received " + str(ridpm.status_code) + " " + str(ridpm.text))
    except (requests.exceptions.RequestException, requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print (e)
        write_error(dt, "Valami halozatos hiba adodott.")
        # write_error(dt, e)
    except Exception as e:
        print(e)
        write_error(dt, "Ismeretlen hiba adodott.")                    
        write_error(dt, e)
        msg = str(dt) + "Idokep PM adatkuldes hiba!" + str(e)
        send_email(msg) 
