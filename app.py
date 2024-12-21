import requests
from googletrans import Translator
from dash import Dash, html, dcc, Input, Output
import plotly.graph_objs as go

app = Dash(__name__)
translator = Translator()

API_KEY = '00RdPed3erHAc01GHcB1OYGXG2Wije28'
BASE_URL = "http://dataservice.accuweather.com"

# Получение данных о погоде
def get_weather(city_name):
    try:
        # Перевод названия города на английский
        translated_city = translator.translate(city_name, src="ru", dest="en").text

        location_url = f"{BASE_URL}/locations/v1/cities/search"
        response = requests.get(location_url, params={"apikey": API_KEY, "q": translated_city})
        response.raise_for_status()
        location_data = response.json()

        if not location_data:
            raise ValueError(f"Город '{city_name}' не найден.")

        if "Key" not in location_data[0]:
            raise ValueError(f"Данные о местоположении для '{city_name}' некорректны.")

        location_key = location_data[0]["Key"]
        forecast_url = f"{BASE_URL}/forecasts/v1/hourly/1hour/{location_key}"
        response = requests.get(forecast_url, params={"apikey": API_KEY, "metric": True})
        response.raise_for_status()
        forecast_data = response.json()

        return {
            "temperature": forecast_data[0]["Temperature"]["Value"],
            "wind_speed": forecast_data[0].get("Wind", {}).get("Speed", {}).get("Value", "Нет данных"),
            "precipitation": forecast_data[0].get("PrecipitationProbability", "Нет данных"),
            "humidity": forecast_data[0].get("RelativeHumidity", "Нет данных"),
        }
    except requests.exceptions.RequestException as e:
        return {"error": "Не удалось подключиться к API. Проверьте соединение с интернетом."}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": "Произошла непредвиденная ошибка. Попробуйте позже."}

def check_bad_weather(temp, wind_speed, precipitation_prob, humidity):
    if isinstance(temp, str) or isinstance(wind_speed, str) or isinstance(precipitation_prob, str):
        return True

    if temp < 0 or temp > 35:
        return True
    if wind_speed > 50:
        return True
    if precipitation_prob > 70:
        return True
    return False

app.layout = html.Div([
    html.H1("Погодный анализ", style={'textAlign': 'center'}),
    html.Div([
        html.Label("Введите начальный город:"),
        dcc.Input(id="start-city-input", type="text", placeholder="Введите начальный город", debounce=True),
    ]),
    html.Div([
        html.Label("Введите конечный город:"),
        dcc.Input(id="end-city-input", type="text", placeholder="Введите конечный город", debounce=True),
    ]),
    dcc.Graph(id="weather-graph"),
    html.Div(id="error-message", style={'color': 'red', 'textAlign': 'center'}),
])

@app.callback(
    [Output("weather-graph", "figure"), Output("error-message", "children")],
    [Input("start-city-input", "value"), Input("end-city-input", "value")]
)
def update_graph(start_city, end_city):
    if not start_city or not end_city:
        return go.Figure(), "Введите оба города для отображения данных."

    # Получение данных для начального города
    start_weather_data = get_weather(start_city)
    if "error" in start_weather_data:
        return go.Figure(), start_weather_data["error"]

    # Получение данных для конечного города
    end_weather_data = get_weather(end_city)
    if "error" in end_weather_data:
        return go.Figure(), end_weather_data["error"]

    # Построение графика для начального города
    start_temperature = start_weather_data["temperature"]
    start_wind_speed = start_weather_data["wind_speed"]
    start_precipitation = start_weather_data["precipitation"]
    start_humidity = start_weather_data["humidity"]

    # Построение графика для конечного города
    end_temperature = end_weather_data["temperature"]
    end_wind_speed = end_weather_data["wind_speed"]
    end_precipitation = end_weather_data["precipitation"]
    end_humidity = end_weather_data["humidity"]

    # Создание фигуры для графика
    fig = go.Figure()

    # Соединение температуры начального и конечного города
    fig.add_trace(go.Scatter(
        x=["Начальный город", "Конечный город"], 
        y=[start_temperature, end_temperature], 
        mode="lines+markers", 
        name="Температура (°C)"
    ))

    # Соединение скорости ветра начального и конечного города
    fig.add_trace(go.Scatter(
        x=["Начальный город", "Конечный город"], 
        y=[start_wind_speed, end_wind_speed], 
        mode="lines+markers", 
        name="Скорость ветра (м/с)"
    ))

    # Соединение осадков начального и конечного города
    fig.add_trace(go.Scatter(
        x=["Начальный город", "Конечный город"], 
        y=[start_precipitation, end_precipitation], 
        mode="lines+markers", 
        name="Осадки (%)"
    ))

    # Соединение влажности начального и конечного города
    fig.add_trace(go.Scatter(
        x=["Начальный город", "Конечный город"], 
        y=[start_humidity, end_humidity], 
        mode="lines+markers", 
        name="Влажность (%)"
    ))

    # Обновление макета графика
    fig.update_layout(
        title=f"Погодные данные для городов {start_city} и {end_city}",
        xaxis_title="Города",
        yaxis_title="Значения",
        legend_title="Параметры",
    )

    return fig, ""

if __name__ == '__main__':
    app.run_server(debug=True)
