import smtplib

port = 587                                      # gmail port
username = "XXXX@gmail.com"          # gmail felhasználónév
password = "XXXX"                           # gmail jelszó
from_email = "XXXX@gmail.com"        # küldő emailcíme
to_email = "XXXX@YYYY.ZZZ"               # fogadó emailcím

def send_email(msg):                                        # Email küldés
    server = smtplib.SMTP('smtp.gmail.com',port)
    server.starttls()
    server.login(username,password)
    server.sendmail(from_email, to_email, msg)
    server.quit()
