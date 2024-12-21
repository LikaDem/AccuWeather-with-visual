from flask import Flask, Response, request, jsonify, render_template
import requests  # Библиотека для выполнения HTTP-запросов
from googletrans import Translator

app = Flask(__name__)  # Экземпляр приложения Flask
translator = Translator()

API_KEY = '00RdPed3erHAc01GHcB1OYGXG2Wije28'
BASE_URL = "http://dataservice.accuweather.com"  # Базовый URL для запросов к AccuWeather

# Получение данных о погоде
def get_weather(city_name):
    try:
        # Перевод названия города на английский
        translated_city = translator.translate(city_name, src="ru", dest="en").text

        location_url = f"{BASE_URL}/locations/v1/cities/search"  # URL для поиска города
        response = requests.get(location_url, params={"apikey": API_KEY, "q": translated_city})  # Запрос к API AccuWeather
        response.raise_for_status()  # Проверка успешности ответа от сервера
        location_data = response.json()  # Получаем данные о городе

        # Если данные о городе не найдены
        if not location_data:
            raise ValueError(f"Город '{city_name}' не найден.")

        # Если нет ключа для местоположения
        if "Key" not in location_data[0]:
            raise ValueError(f"Данные о местоположении для '{city_name}' некорректны.")

        location_key = location_data[0]["Key"]  # Уникальный ключ для города
        forecast_url = f"{BASE_URL}/forecasts/v1/hourly/1hour/{location_key}"
        response = requests.get(forecast_url, params={"apikey": API_KEY, "metric": True})
        response.raise_for_status()
        forecast_data = response.json()

        return {
            "temperature": forecast_data[0]["Temperature"]["Value"],
            "wind_speed": forecast_data[0].get("Wind", {}).get("Speed", {}).get("Value", "Нет данных"),
            "precipitation": forecast_data[0].get("PrecipitationProbability", "Нет данных"),
            "humidity": forecast_data[0].get("RelativeHumidity", "Нет данных"),  # Добавляем влажность
        }
    except requests.exceptions.RequestException as e:
        return {"error": "Не удалось подключиться к API. Проверьте соединение с интернетом."}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": "Произошла непредвиденная ошибка. Попробуйте позже."}

def check_bad_weather(temp, wind_speed, precipitation_prob, humidity):
    # Если данные о погоде отсутствуют, считаем погоду плохой
    if isinstance(temp, str) or isinstance(wind_speed, str) or isinstance(precipitation_prob, str):
        return True

    if temp < 0 or temp > 35:
        return True
    if wind_speed > 50:
        return True
    if precipitation_prob > 70:
        return True
    return False

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        start_city = request.form.get("start_city")
        end_city = request.form.get("end_city")

        if not start_city or not end_city:
            return render_template("index.html", error="Введите оба города.")

        # Получаем данные о погоде
        start_weather = get_weather(start_city)
        end_weather = get_weather(end_city)

        # Проверяем ошибки
        if "error" in start_weather:
            return render_template("index.html", error=f"Ошибка для {start_city}: {start_weather['error']}")
        if "error" in end_weather:
            return render_template("index.html", error=f"Ошибка для {end_city}: {end_weather['error']}")

        # Оцениваем погоду
        start_bad_weather = check_bad_weather(
            start_weather["temperature"], start_weather["wind_speed"], start_weather["precipitation"], start_weather["humidity"]
        )
        end_bad_weather = check_bad_weather(
            end_weather["temperature"], end_weather["wind_speed"], end_weather["precipitation"], end_weather["humidity"]
        )

        # Подготовка результата
        result = {
            "start_city": {
                "name": start_city,
                "weather": start_weather,
                "bad_weather": "Плохая" if start_bad_weather else "Хорошая"
            },
            "end_city": {
                "name": end_city,
                "weather": end_weather,
                "bad_weather": "Плохая" if end_bad_weather else "Хорошая"
            }
        }

        # Возвращаем результат на той же странице
        return render_template("result.html", result=result)

    # Если метод GET — просто возвращаем форму
    return render_template("index.html", error=None)

@app.errorhandler(404)
def page_not_found(error):
    return "Страница не найдена, проверьте маршрут и файл HTML.", 404

@app.errorhandler(500)
def internal_server_error(error):
    return "Внутренняя ошибка сервера: {error}", 500

if __name__ == '__main__':
    app.run(debug=True)
