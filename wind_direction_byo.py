from gpiozero import MCP3008
import time
import math

adc = MCP3008(channel = 0)
count = 0
values = []
#volts = {0.4: 0.0,
#         1.4: 22.5,
#         1.2: 45.0,
#         2.8: 67.5,
#         2.7: 90.0,
#         2.9: 112.5,
#         2.2: 135.0,
#         2.5: 157.5,
#         1.8: 180.0,
#         2.0: 202.5,
#         0.7: 225.0,
#         0.8: 247.5,
#         0.1: 270.0,
#         0.3: 292.5,
#         0.2: 315.0,
#         0.6: 337.5}

#while True:
#    wind = round(adc.value * 3.3, 1)
#    if wind in volts:
#        print('Talalat:' + str(wind) + ' ' + str(volts[wind]))   
#    else:
#        print('Ismeretlen ertek: ' + str(wind))
        

def get_average(angles):
    sin_sum = 0.0
    cos_sum = 0.0

    for angle in angles:
        r = math.radians(angle)
        sin_sum += math.sin(r)
        cos_sum += math.cos(r)

    flen = float(len(angles))
    s = sin_sum / flen
    c = cos_sum / flen
    arc = math.degrees(math.atan(s / c))
    average = 0.0

    if s > 0 and c > 0:
        average = arc
    elif c < 0:
        average = arc + 180
    elif s < 0 and c > 0:
        average = arc + 360

    return 0.0 if average == 360 else average

def get_value(length=5):
    data = []
    print("Szélirány mérése %d másodpercig..." % length)
    start_time = time.time()

    while time.time() - start_time <= length:
        windval = round(adc.value * 3.3,1)         #Kerekites * 3.3
        if 0.3 <= windval <= 0.5:
            wind = 0
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
 
        if 1.3 <= windval <= 1.5:
            wind = 22.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 1.1 <= windval <= 1.3:
            wind = 45
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 2.8 <= windval <= 2.9:
            wind = 67.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 2.6 <= windval <= 2.8:
            wind = 90
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 2.8 <= windval <= 3.0:
            wind = 112.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 2.1 <= windval <= 2.3:
            wind = 135
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 2.4 <= windval <= 2.6:
            wind = 157.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 1.7 <= windval <= 1.9:
            wind = 180
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 1.9 <= windval <= 2.1:
            wind = 202.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 0.6 <= windval <= 0.8:
            wind = 225
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 0.7 <= windval <= 0.9:
            wind = 247.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 0.0 <= windval <= 0.2:
            wind = 270
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 0.2 <= windval <= 0.4:
            wind = 292.5
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 0.1 <= windval <= 0.3:
            wind = 315
            data.append(wind)
            #print('value ' + str(windval) + ' ' + str(wind))
        
        if 0.5 <= windval <= 0.7:
            wind = 337.5
            data.append(wind)

    return get_average(data)
