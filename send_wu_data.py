import requests
from requests.exceptions import HTTPError
from write_error import write_error
from send_email import send_email


# A www.wunderground.com-ra küldés URL első felének megadása
WUurl = "https://weatherstation.wunderground.com/weatherstation\
/updateweatherstation.php?"
WU_station_id = "XXXXXXX"               # állomas ID
WU_station_pwd = "XXXXXXXX"             # állomas jelszó
WUcreds = "ID=" + WU_station_id + "&PASSWORD="+ WU_station_pwd
date_str = "&dateutc=now"
action_str = "&action=updateraw"


def degc_to_degf(temperature_in_c):                         # C fok konvertálása F-re hőmérséklet
    temperature_in_f = (temperature_in_c * (9/5.0)) + 32
    return temperature_in_f

def hpa_to_inches(pressure_in_hpa):                         # hPa konvertálása inch-re nyomás
    pressure_in_inches_of_m = pressure_in_hpa * 0.0295
    return pressure_in_inches_of_m

def kmh_to_mph(speed_in_kmh):                               # km/h konvertálása mph-ba
    speed_in_mph = speed_in_kmh * 0.621371
    return speed_in_mph

def mm_to_inchesrh(rainfall_in_mm):                         # mm konvertálása inch-be eső órai
    rainfall_in_inches = rainfall_in_mm * 0.0393701
    return rainfall_in_inches

def mm_to_inchesrd(dailyrain_in_mm):                        # mm konvertálása inch-be eső napi
    dailyrain_in_inches = dailyrain_in_mm * 0.0393701
    return dailyrain_in_inches

def dewpc_to_dewpf(dewp_in_c):                              # C fok konvertálása F-re harmatpont (Dewpoint)
    dewp_in_f = (dewp_in_c * (9/5.0)) + 32
    return dewp_in_f

def send_wu_data(dt,
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
                 softwaretype_str):

    # WU küldött adatok formai követelményeinek összeállítása
    ambient_temp_str = "{0:.2f}".format(degc_to_degf(ambient_temp))
    humidity_str = "{0:.2f}".format(humidity)
    pressure_in_str = "{0:.2f}".format(hpa_to_inches(p0))
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
    print(dt)

    # Adatküldés a www.wundwerground.com-ra
    try:
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
        
        print('\n', "Received " + str(r.status_code) + " " + str(r.text))
    except (requests.exceptions.RequestException, requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print (e)
        write_error(dt, "Valami halozatos hiba adodott.")
        # write_error(dt, e)
    except Exception as e:
        print(e)
        write_error(dt, "Ismeretlen hiba adodott.")                    
        write_error(dt, e)
        msg = str(dt) + "Weather Underground adatkuldes hiba!" + str(e)
        send_email(msg)
