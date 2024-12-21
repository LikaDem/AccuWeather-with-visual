import requests
from googletrans import Translator
from dash import Dash, html, dcc, Input, Output, State
import plotly.graph_objs as go

app = Dash(__name__)  # Экземпляр приложения Flask
translator = Translator()

API_KEY = 'iX6PSoLfufqQsquVHf4NCoUbaT9b23pu'  # Убедитесь, что ключ правильный
BASE_URL = "https://dataservice.accuweather.com"  # Используем HTTPS для безопасности

# Получение данных о погоде
def get_weather_forecast(city_name, days):
    try:
        translated_city = translator.translate(city_name, src="ru", dest="en").text

        location_url = f"{BASE_URL}/locations/v1/cities/search"
        response = requests.get(location_url, params={"apikey": API_KEY, "q": translated_city})
        response.raise_for_status()

        if response.status_code != 200:
            return {"error": f"Ошибка запроса: {response.status_code} - {response.text}"}

        location_data = response.json()

        if not location_data:
            raise ValueError(f"Город '{city_name}' не найден.")

        if "Key" not in location_data[0]:
            raise ValueError(f"Данные о местоположении для '{city_name}' некорректны.")

        location_key = location_data[0]["Key"]
        
        # Убираем жёстко заданное значение дней (3) и меняем на параметр из входных данных
        if days == 1:
            forecast_url = f"{BASE_URL}/forecasts/v1/daily/1day/{location_key}"
        elif days == 5:
            forecast_url = f"{BASE_URL}/forecasts/v1/daily/5day/{location_key}"
        else:
            return {"error": "Недопустимое количество дней для прогноза."}

        response = requests.get(forecast_url, params={"apikey": API_KEY, "metric": True})
        response.raise_for_status()

        if response.status_code != 200:
            return {"error": f"Ошибка запроса: {response.status_code} - {response.text}"}

        forecast_data = response.json()

        return forecast_data
    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка при подключении к API: {e}"}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": "Произошла непредвиденная ошибка. Попробуйте позже."}

app.layout = html.Div([
    html.H1("Погодный анализ", style={'textAlign': 'center'}),
    html.Div([
        html.Label("Введите начальный город:"),
        dcc.Input(id="start-city-input", type="text", placeholder="Введите город", debounce=True),
    ]),
    html.Div([
        html.Label("Введите конечный город:"),
        dcc.Input(id="end-city-input", type="text", placeholder="Введите город", debounce=True),
    ]),
    html.Div([
        html.Label("Введите промежуточные города (через запятую):"),
        dcc.Input(id="intermediate-cities-input", type="text", placeholder="Введите города", debounce=True),
    ]),
    html.Div([
        html.Label("Выберите количество дней для прогноза:"),
        dcc.Dropdown(
            id='days-dropdown',
            options=[
                {'label': '1 день', 'value': 1},
                {'label': '5 дней', 'value': 5}
            ],
            value=5  # Значение по умолчанию
        ),
    ]),
    html.Button("Получить погоду", id="submit-button", n_clicks=0),  # Кнопка для отправки запроса
    dcc.Graph(id="weather-graph"),
    html.Div(id="error-message", style={'color': 'red', 'textAlign': 'center'}),
])

@app.callback(
    [Output("weather-graph", "figure"), Output("error-message", "children")],
    [Input("submit-button", "n_clicks")],
    [State("start-city-input", "value"), State("intermediate-cities-input", "value"),
     State("end-city-input", "value"), State("days-dropdown", "value")]
)
def update_graph(n_clicks, start_city, intermediate_cities, end_city, days):
    if n_clicks == 0:
        return go.Figure(), ""

    if not start_city or not end_city:
        return go.Figure(), "Введите начальный и конечный город для отображения данных."

    cities = [start_city] + (intermediate_cities.split(",") if intermediate_cities else []) + [end_city]

    all_weather_data = []
    for city in cities:
        weather_data = get_weather_forecast(city, days)
        if "error" in weather_data:
            return go.Figure(), weather_data["error"]
        all_weather_data.append({"city": city, "weather": weather_data})

    # Построение графика
    fig = go.Figure()

    for city_data in all_weather_data:
        city = city_data["city"]
        weather = city_data["weather"]

        days_labels = [f"День {i+1}" for i in range(days)]
        
        # Извлечение данных о температуре
        temperatures = [
            day["Temperature"]["Maximum"]["Value"] for day in weather.get("DailyForecasts", [])
        ]

        # Извлечение данных о скорости ветра (с добавлением проверки на наличие данных)
        wind_speeds = []
        for day in weather.get("DailyForecasts", []):
            wind_speed = day.get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value", None)
            if wind_speed is None:
                wind_speeds.append(0)  # Если данных нет, указываем 0
            else:
                wind_speeds.append(wind_speed)

        # Извлечение данных о осадках (с добавлением проверки на наличие данных)
        precipitation = []
        for day in weather.get("DailyForecasts", []):
            if day["Day"].get("HasPrecipitation", False):
                precipitation.append(day["Day"].get("PrecipitationIntensity", "Нет осадков"))
            else:
                precipitation.append("Нет осадков")

        # Отладочные сообщения
        print(f"Wind Speeds for {city}: {wind_speeds}")
        print(f"Precipitation for {city}: {precipitation}")

        # Добавление графиков
        fig.add_trace(go.Scatter(
            x=days_labels, y=temperatures, mode="lines+markers", name=f"Температура ({city})"
        ))
        fig.add_trace(go.Scatter(
            x=days_labels, y=wind_speeds, mode="lines+markers", name=f"Скорость ветра ({city})"
        ))
        fig.add_trace(go.Scatter(
            x=days_labels, y=precipitation, mode="lines+markers", name=f"Осадки ({city})"
        ))

    fig.update_layout(
        title=f"Погодные данные для маршрута",
        xaxis_title="Дни",
        yaxis_title="Значение",
        legend_title="Города и параметры",
    )

    return fig, ""

if __name__ == '__main__':
    app.run_server(debug=True)
