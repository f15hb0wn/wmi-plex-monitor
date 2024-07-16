import requests

WEATHER_ZIP_CODE = '60126'
WEATHER_API_KEY = '72cbf850e1b94a4994a194156241607'
WEATHER_PRECIPITATION_WARNING = 50
WEATHER_HIGH_TEMP_WARNING = 80
WEATHER_LOW_TEMP_WARNING = 30

def fetch_weather():
    # Make a request to the weather API
    url = f'http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={WEATHER_ZIP_CODE}&days=1&aqi=yes&alerts=yes'
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract the current temperature, high, low, and chance of rain
        # Pretty print the JSON response
        # Check if any alerts exist
        if 'alerts' in data and 'alert' in data['alerts'] and len(data['alerts']['alert']) > 0:
            alert = data['alerts']['alert'][0]['event']
        else:
            alert = False
        
        current_temp = data['current']['temp_f']
        high_temp = data['forecast']['forecastday'][0]['day']['maxtemp_f']
        low_temp = data['forecast']['forecastday'][0]['day']['mintemp_f']
        chance_of_rain = data['forecast']['forecastday'][0]['day']['daily_chance_of_rain']
        chance_of_snow = data['forecast']['forecastday'][0]['day']['daily_chance_of_snow']

        # Set the color based on the weather conditions
        color = 'green'
        if chance_of_rain > WEATHER_PRECIPITATION_WARNING:
            color = 'yellow'
        elif high_temp > WEATHER_HIGH_TEMP_WARNING:
            color = 'yellow'
        elif low_temp < WEATHER_LOW_TEMP_WARNING:
            color = 'yellow'

        if alert:
            color = 'red'

        data = {
            alert: alert,
            current_temp: current_temp,
            high_temp: high_temp,
            low_temp: low_temp,
            chance_of_rain: chance_of_rain,
            chance_of_snow: chance_of_snow,
            color: color
        }
        return data