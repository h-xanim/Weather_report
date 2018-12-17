from __future__ import division, unicode_literals
import codecs
from flask import Flask
from flask import render_template
import requests
import re
import itertools
import sqlite3
import seaborn as sns
import base64
import random
from flask import Response
from werkzeug.contrib.fixers import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup as Soup
import atexit

try:
    from StringIO import StringIO
except ImportError:
    import io as StringIO

app = Flask(__name__)
scheduler = BackgroundScheduler()
conn = sqlite3.connect("weather.db")

# Input values
wind_crit = 10
humid_crit = 90
temp_crit = -5
pressure_if_lower_crit = 1000
icao = ['KINK', 'KTVY', 'KMLU', 'LIRL', 'KC62', 'OISL', 'EDSB', 'LIPU', 'SKVP', 'LIMY', 'SKLT',
          'KGXF', 'KACJ', 'KDZJ', 'FMMT', 'KPRX', 'LEBR', 'KGEY', 'EDLV', 'KMZZ', 'KCVH', 'CXET',
          'KZPH', 'CWDQ', 'UTDK', 'KPNA', 'KHOU', 'KELD', 'KP68', 'UIUU'] #30
link = 'http://tgftp.nws.noaa.gov/data/observations/metar/decoded/{}.TXT'


@app.route('/')
def hello():
    #getdata()
    return render_template('index.html')


def getdata():
    for icao_i in icao:
        result_date = 'N/A'
        result_dp = 0
        result_pressure = 0
        result_relhum = 0
        result_temp = 0
        result_tempo = 0
        result_visibility = 0
        result_windspd = 0
        result_place = ''
        result_overallconditions = 0
        result_critwind = 0
        result_crithumid = 0
        result_crittemp = 0
        result_critpressure = 0
        try:
            f = requests.get(link.format(icao_i))
            print(f)
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            if f.text.split('\n')[0]:
                result_place = f.text.split('\n')[0]
                print(result_place)
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            result_date = re.findall('/ (\d+.\d+.\d+) ', f.text)[0]
            print('date: ' + result_date)
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            if re.findall('at (\d+) MPH', f.text):
                result_windspd = float(re.findall('at (\d+) MPH', f.text)[0])
                if result_windspd > wind_crit:
                    result_critwind = 1
            else:
                result_windspd = ""

        except Exception as err:
            print(err)
            return {"error": err}
        try:
            if re.findall('Relative Humidity: (\d+)%', f.text):
              result_relhum = float(re.findall('Relative Humidity: (\d+)%', f.text)[0])
              if result_relhum > humid_crit:
                  result_crithumid = 1
            else:
              result_relhum = ""
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            if f.text.partition('Visibility: ')[-1].rpartition(':0'):
                result_visibility = f.text.partition('Visibility: ')[-1].rpartition(':0')[0]
            else:
                result_visibility = 'N/A'
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            if f.text.partition('Dew Point: ')[-1].rpartition('\nRelative '):
                result_dp = f.text.partition('Dew Point: ')[-1].rpartition('\nRelative ')[0]
            else:
                result_dp = 0
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            result_pressure = re.search('([0-9]{3,5})( hPa)', f.text, re.MULTILINE)
            if result_pressure is None:
                result_pressure = ""
            else:
                result_pressure = float(re.search('([0-9]{3,5})( hPa)', f.text, re.MULTILINE).group(1))
                if result_pressure < pressure_if_lower_crit:
                    result_critpressure = 1
        except Exception as err:
            print(err)
            return {"error": err}
        try:
            result_temp = re.search('(Temperature: )([0-9]{0,2})', f.text, re.MULTILINE)
            if result_temp is None:
                result_tempo = ""
                print("None")
            qwe = result_temp.group(0)
            result_tempo = ""
            val = re.search(r'\d+', qwe)
            if val is None:
                print("None")
            else:
                result_tempo = float(re.search(r'\d+', qwe).group())
                if result_tempo < temp_crit:
                    result_crittemp = 1
        except Exception as err:
            print(err)
            pass
        result_overallconditions = result_crittemp + result_crithumid + result_critwind + result_critpressure
        result_place = result_place + " ICAO: " + icao_i
        result_info = ""
        result_info = "" + result_place + " Weather condition: " + str(100 - result_overallconditions*25) + "%"
        print("***-------------------------------***")
        print(icao_i)
        print(result_place)
        print(result_date)
        print(result_pressure)
        print(result_windspd)
        print(result_relhum)
        print(result_tempo)
        print("///-------------------------------///")
        recordtext(icao_i, result_info)
        setdb(icao_i, result_date, result_pressure, result_windspd, result_relhum, result_tempo, result_place, result_overallconditions, result_critwind, result_crithumid, result_crittemp)
    return 'Test'


def setdb(place, rdate, pressure, wind, humidity, temperature, name, crit_sum, crit_w, crit_h, crit_t):
    conn = sqlite3.connect("weather.db")
    c = conn.cursor()
    c.execute("Create TABLE if not exists %s (rdate TEXT,pressure FLOAT,wind FLOAT,humidity FLOAT, temperature FLOAT, name TEXT, crit_overall FLOAT, crit_wind FLOAT, crit_humidity FLOAT, crit_temperature FLOAT)"
              % place)
    try:
        c.execute("INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?)" % place, (rdate, pressure, wind, humidity, temperature, name, crit_sum, crit_w, crit_h, crit_t))
        conn.commit()
    except Exception as err:
        print(err)
        pass
    setuniquedb(place, rdate, pressure, wind, humidity, temperature, name, crit_sum, crit_w, crit_h, crit_t)
    return 'Print'

def setuniquedb(place, rdate, pressure, wind, humidity, temperature, name, crit_sum, crit_w, crit_h, crit_t):
    conn = sqlite3.connect("weather.db")
    c = conn.cursor()
    try:
        c.execute("Create TABLE if not exists currentvalues (place TEXT,rdate TEXT,pressure FLOAT,wind FLOAT,humidity FLOAT, temperature FLOAT, aname TEXT, crit_overall FLOAT, crit_wind FLOAT, crit_humidity FLOAT, crit_temperature FLOAT)")
    except Exception as err:
        print(err)
        pass
    try:
        c.execute("DELETE FROM currentvalues WHERE place=?", (place,))
        conn.commit()
        c.execute("INSERT INTO currentvalues VALUES (?,?,?,?,?,?,?,?,?,?,?)",(place, rdate, pressure, wind, humidity, temperature, name, crit_sum, crit_w, crit_h, crit_t))
        conn.commit()
    except Exception as err:
        print(err)
        pass
    return 'Print'


#@app.route('/elements')
#def elements():
 #   return render_template('index.html')

def recordtext(icao, info):
    f = open("static/" + icao + ".txt", "w+")
    f.write("" + info)
    f.close()
    return 'Done'

@app.route('/reports/')
@app.route('/reports/<name>')
def showreport(name=None):
#забрать данные из бд, вывести

    data = []
    data = getdatabyicao(name)
    print("///////////////RECEIVED DATA///////////////")
    print(data)
    result = '''<!doctype html>
            <title>''' + name + '''Weather Report</title>'''
    result += '<h2>Отчёт о погоде: ' + name + ' Дата: ' + data[1] + ' </h2><h3>///' + str(data[6]) + '///</h3>'
    result += '<h3>Условия погоды: ' + str((4 - data[7]) * 25) + '%</h3>'
    result += '<p>Давление: ' + str(data[2]) + ' Hpa</p>'
    result += '<p>Скорость ветра: ' + str(data[3]) + ' Mph</p>'
    result += '<p>Влажность: ' + str(data[4]) + '%</p>'
    result += '<p>Температура: ' + str(data[5]) + 'C</p>'
    # result += '<p>Latitude: ' + str(data[11]) + 'F</p>'
    # result += '<p>Longitude: ' + str(data[12]) + 'F</p>'
    return result


def getdatabyicao(icao_get):
    datatoreceive = []
    conn = sqlite3.connect("weather.db")
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM currentvalues WHERE place=?", (icao_get,))
        conn.commit()
        rows = c.fetchall()
        for row in rows:
            datatoreceive = row
            print(row)
    except Exception as err:
        print(err)
        pass
    return datatoreceive


scheduler.add_job(func=getdata, trigger="interval", minutes=240)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == '__main__':
    app.run()