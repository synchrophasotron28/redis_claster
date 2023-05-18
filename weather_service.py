from flask import Flask
from flask import request
import requests
import json
import flask
from rediscluster import RedisCluster
import rediscluster

app = Flask(__name__)
app.config.from_pyfile('settings.py')




#задание параметров redis'а
redis_host, redis_port = '127.0.0.1', "6379"
rc = rediscluster.RedisCluster(startup_nodes=[{"host":  redis_host, "port": "6379"},{"host": redis_host, "port": "6380"}, {"host": redis_host, "port": "6381"}], decode_responses=True)
#,{"host": redis_host, "port": 6380}, {"host": redis_host, "port": 6381}
time_storage = 60*10				#10 минут - актуальность данных о погоде в городе


def current_weather(city: str):
	#обращение к внешнему сервису
    url = app.config.get("URL")
    url = url.format(city)
    data = requests.get(url).content
    data = json.loads(data.decode('utf-8'))
    # print(app.config.get("URL"))
    temp = {"city": data["location"]["name"], "unit": "celsius", "temperature": data["current"]["temp_c"]}

    ses = json.dumps(temp)
    rc.set(city, ses, ex=time_storage)

    #возвращение текущей погоды
    return temp

def forecast_weather(city: str, dt: str) -> dict:
    # url = 'http://api.weatherapi.com/v1/forecast.json?key=92b2b54828074632897211731232702&q={}&days=14'
    url = app.config.get("URL")
    url = url.format(city)
    data = requests.get(url).content
    data = json.loads(data.decode('utf-8'))
    #print(type(data))
    if len(dt.split("_")) == 2:
        dt = dt.replace("_", " ")
        for date in data["forecast"]["forecastday"]:
            for dtime in date["hour"]:
                #print(dtime)
                #print(str(dt))
                if str(dtime["time"]) == str(dt):
                    #print("da2")
                    resp_date = str(dtime["temp_c"])
    elif len(dt.split("_")) == 1:
        for date in data["forecast"]["forecastday"]:
            if date["date"] == dt:
                #print(date["hour"][1])
                resp_date = str(date["day"]["avgtemp_c"])

    #print(resp_date)
    resp = {"city": data["location"]["name"], "unit": "celsius", "temperature": resp_date}

    print(str(city+dt).replace("_"," "))
    ses = json.dumps(resp)
    rc.set(str(city+dt).replace("_"," "), ses, ex=time_storage)
    print("положили в редис")

    return resp


def find_data(city: str, metod: bool, dt: str):
    if metod == True:
        if type(rc.get(city)) != type(None):
            #если в базе найдено значение
            print(metod)
            print("взято из кэша current")
            print("city: ",city," взято из кэша и актуально: ", rc.ttl(city))
            response = json.loads(rc.get(city))
            return response
        else:
            #если не найдено значение
            print("city: ",city," ищем в API")
            return current_weather(city)
    elif metod == False:
        if type(rc.get(str(city + dt).replace("_"," "))) != type(None):
            print("city+dt: ", city+dt, " взято из кэша и актуально: ", rc.ttl(str(city+dt).replace("_", " ")))
            print("взяли из кэша forecast")
            response = json.loads(rc.get(str(city+dt).replace("_"," ")))
            return response
        else:
            #если не найдено значение
            print("city+dt: ",city+dt," ищем в API")
            return forecast_weather(city,dt)


@app.route('/forecast_weather', methods=['GET'])
def get():
    city = request.args.get('city')
    dt = request.args.get('dt')
    temp = find_data(city,False,dt)
    print("метод forecast")

    return flask.jsonify(temp)


@app.route('/current_weather', methods=['GET'])
def cur():
    city = request.args.get('city')

    temp = find_data(city, True, "")
    print("метод current")

    return flask.jsonify(temp)


if __name__ == '__main__':
    app.run(debug=True)
