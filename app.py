import requests
from googletrans import Translator
from dash import Dash, html, dcc, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px

app = Dash(__name__)  # Экземпляр приложения
translator = Translator()

API_KEY = '76whizPHXN1HYfY9AuPTV78kVyk47Gsd'
BASE_URL = "https://dataservice.accuweather.com"

# Получение данных о погоде
def get_weather_forecast(city_name, days):
    try:
        translated_city = translator.translate(city_name, src="ru", dest="en").text

        location_url = f"{BASE_URL}/locations/v1/cities/search"
        response = requests.get(location_url, params={"apikey": API_KEY, "q": translated_city})
        response.raise_for_status()

        location_data = response.json()
        if not location_data:
            raise ValueError(f"Город '{city_name}' не найден.")

        location_key = location_data[0]["Key"]
        if days == 1:
            forecast_url = f"{BASE_URL}/forecasts/v1/daily/1day/{location_key}"
        elif days == 5:
            forecast_url = f"{BASE_URL}/forecasts/v1/daily/5day/{location_key}"
        else:
            return {"error": "Недопустимое количество дней для прогноза."}

        response = requests.get(forecast_url, params={"apikey": API_KEY, "metric": True})
        response.raise_for_status()

        forecast_data = response.json()
        forecast_data["GeoPosition"] = location_data[0]["GeoPosition"]
        return forecast_data
    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка при подключении к API: {e}"}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": "Произошла непредвиденная ошибка. Попробуйте позже."}

# Функция для создания карты с базовой легендой
def create_map(cities_data):
    locations = []
    route_lines = []
    hover_texts = []  # Для хранения текста, который будет показываться при наведении на линии

    # Цвета для маршрутов
    route_colors = px.colors.qualitative.Set1  # Множество ярких цветов для маршрутов

    for i, city_data in enumerate(cities_data):
        city = city_data["city"]
        geo = city_data["weather"]["GeoPosition"]
        latitude = geo["Latitude"]
        longitude = geo["Longitude"]

        temperature = city_data["weather"]["DailyForecasts"][0]["Temperature"]["Maximum"].get("Value", 0)
        wind_speed = city_data["weather"]["DailyForecasts"][0].get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value", 0)
        precipitation = city_data["weather"]["DailyForecasts"][0]["Day"].get("PrecipitationProbability", {}).get("Value", 0)

        locations.append({
            "city": city,
            "lat": latitude,
            "lon": longitude,
            "temperature": temperature,
            "wind_speed": wind_speed,
            "precipitation": precipitation,
        })

        hover_texts.append(f"{city}: Температура {temperature}°C, Ветер {wind_speed} км/ч, Вероятность осадков: {precipitation}%")

        if i < len(cities_data) - 1:
            next_city = cities_data[i + 1]
            route_lines.append([locations[-1], {
                "lat": next_city["weather"]["GeoPosition"]["Latitude"],
                "lon": next_city["weather"]["GeoPosition"]["Longitude"]
            }])

    # Построение карты
    fig = px.scatter_mapbox(
        locations,
        lat="lat",
        lon="lon",
        text="city",
        color="temperature",
        size="wind_speed",
        hover_name="city",
        hover_data=["temperature", "wind_speed", "precipitation"],
        zoom=4,
    )

    # Убираем цветовую легенду с карты
    fig.update_layout(coloraxis_showscale=False)

    # Добавляем линии маршрута с текстом при наведении
    for i, route in enumerate(route_lines):
        route_name = f"Маршрут {i + 1}"
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=[point["lon"] for point in route],
            lat=[point["lat"] for point in route],
            line={"width": 2, "color": route_colors[i % len(route_colors)]},  # Цвет в зависимости от маршрута
            hoverinfo="text",  # Добавление текста при наведении
            text=hover_texts[i],  # Сообщение для линии
            name=route_name
        ))

    # Убираем изменения в легенде, оставляем стандартное отображение
    fig.update_layout(
        title="Маршрут с прогнозами погоды",
        showlegend=True,
        legend_title="Маршруты",
        mapbox_style="open-street-map"
    )
    return fig

# Макет приложения
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
            value=5 
        ), 
    ]), 
    html.Div([ 
        html.Label("Выберите параметры для отображения на графиках:"), 
        dcc.Checklist( 
            id="parameter-filter", 
            options=[ 
                {"label": "Температура", "value": "temperature"}, 
                {"label": "Скорость ветра", "value": "wind_speed"}, 
                {"label": "Осадки", "value": "precipitation"}, 
            ], 
            value=["temperature", "wind_speed", "precipitation"],  # По умолчанию все выбраны 
            inline=True, 
        ), 
    ]), 
    html.Button("Получить погоду", id="submit-button", n_clicks=0), 
    dcc.Graph(id="weather-graph"), 
    dcc.Graph(id="weather-map", style={"height": "1000px"}),  # Увеличение высоты карты 
    html.Div(id="error-message", style={'color': 'red', 'textAlign': 'center'}), 
    html.Div(id="weather-note", style={'textAlign': 'center', 'fontStyle': 'italic', 'marginTop': '20px'}),  # Примечание
]) 

@app.callback( 
    [Output("weather-graph", "figure"), Output("error-message", "children"), Output("weather-map", "figure"), Output("weather-note", "children")], 
    [Input("submit-button", "n_clicks")], 
    [State("start-city-input", "value"), State("intermediate-cities-input", "value"), 
     State("end-city-input", "value"), State("days-dropdown", "value"), State("parameter-filter", "value")] 
) 
def update_graph(n_clicks, start_city, intermediate_cities, end_city, days, selected_parameters): 
    if n_clicks == 0: 
        return go.Figure(), "", go.Figure(), ""

    if not start_city or not end_city:
        return go.Figure(), "Введите начальный и конечный город для отображения данных.", go.Figure(), ""

    cities = [start_city] + (intermediate_cities.split(",") if intermediate_cities else []) + [end_city]

    all_weather_data = []
    for city in cities:
        weather_data = get_weather_forecast(city, days)
        if "error" in weather_data:
            return go.Figure(), weather_data["error"], go.Figure(), ""
        all_weather_data.append({"city": city, "weather": weather_data})

    # Построение графика
    fig = go.Figure()
    for city_data in all_weather_data:
        city = city_data["city"]
        weather = city_data["weather"]

        days_labels = [f"День {i+1}" for i in range(days)]
        
        # Извлечение данных
        if "temperature" in selected_parameters:
            temperatures = [day["Temperature"]["Maximum"].get("Value", 0) for day in weather.get("DailyForecasts", [])]
            fig.add_trace(go.Scatter(
                x=days_labels, y=temperatures, mode="lines", name=f"Температура {city}",
                hoverinfo="text", text=[f"Город: {city}, Температура: {t}°C" for t in temperatures]
            ))

        if "wind_speed" in selected_parameters:
            wind_speeds = [day.get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value", 0) for day in weather.get("DailyForecasts", [])]
            fig.add_trace(go.Scatter(
                x=days_labels, y=wind_speeds, mode="lines", name=f"Ветер {city}",
                hoverinfo="text", text=[f"Город: {city}, Ветер: {ws} км/ч" for ws in wind_speeds]
            ))

        if "precipitation" in selected_parameters:
            precipitations = [day["Day"].get("PrecipitationProbability", {}).get("Value", 0) for day in weather.get("DailyForecasts", [])]
            fig.add_trace(go.Scatter(
                x=days_labels, y=precipitations, mode="lines", name=f"Осадки {city}",
                hoverinfo="text", text=[f"Город: {city}, Осадки: {p}%" for p in precipitations]
            ))

    # Примечание о значении 0, если информация отсутствует
    note = "Если информация о погоде отсутствует, показывается значение 0 для соответствующего параметра."

    # Строим карту
    map_fig = create_map(all_weather_data)

    return fig, "", map_fig, note


if __name__ == "__main__":
    app.run_server(debug=True)
