

def write_error(dt, e):                                     # Hibák kiírása fájlba
    with open('/media/pi/B415-25E9/error.txt',mode='a') as ew:                
         ew.write(str(dt) + str(e) + '\n')
