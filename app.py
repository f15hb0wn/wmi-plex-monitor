from tkinter import Tk, Canvas
from collections import deque
import requests
import yaml
import json
from datetime import datetime
from plexapi.server import PlexServer
import time
import traceback
import pytz


DEBUG = False
# Load the settings from settings.yaml
with open('settings.yaml', 'r') as file:
    settings = yaml.safe_load(file)

# Set the temperature thresholds
CPU_CAUTION_TEMP = settings['CPU_CAUTION_TEMP']
CPU_DANGER_TEMP = settings['CPU_DANGER_TEMP']
GPU_CAUTION_TEMP = settings['GPU_CAUTION_TEMP']
GPU_DANGER_TEMP = settings['GPU_DANGER_TEMP']
RAM_CAUTION_TEMP = settings['RAM_CAUTION_TEMP']
RAM_DANGER_TEMP = settings['RAM_DANGER_TEMP']
NETOPS_CAUTION = settings['NETOPS_CAUTION']
DISKOPS_CAUTION = settings['DISKOPS_CAUTION']
UTILIZATION_CAUTION = settings['UTILIZATION_CAUTION']
# Set the polling interval in milliseconds
POLL_INTERVAL_MS = settings['POLL_INTERVAL_MS']
# Set the number of temperature samples to keep
NUM_SAMPLES = settings['NUM_SAMPLES']
# Consecutive samples to consider for utilization
UTIL_SAMPLES = settings['UTIL_SAMPLES']
# Set the maximum CPU frequency in MHz
MAX_CPU_MHZ = settings['MAX_CPU_MHZ']
REMOTE_SERVER = settings['REMOTE_SERVER']
REMOTE_PORT = settings['REMOTE_PORT']
# Set the window to always be on top
ALWAYS_ON_TOP = settings['ALWAYS_ON_TOP']
# Set width of the window
HEIGHT = settings['HEIGHT']
WIDTH = settings['WIDTH']
SYSTEM_FANS_ENABLED = settings['SYSTEM_FANS_ENABLED']

if HEIGHT == 0 and WIDTH == 0:
    # Create a temporary Tkinter window
    temp_window = Tk()

    # Get the width of the entire screen
    screen_width = temp_window.winfo_screenwidth()
    screen_height = temp_window.winfo_screenheight()

    # Destroy the temporary window
    temp_window.destroy()

    # Set the width of the window
    WIDTH = screen_width
    # Set the height of the window
    HEIGHT = screen_height
# Set the height of each row
ROW_HEIGHT = settings['ROW_HEIGHT']
# Set the font size
#FONT_SIZE = settings['FONT_SIZE']
FONT_SIZE = ROW_HEIGHT - 10
# Set the buffer for the X position of the text
X_BUFFER = ROW_HEIGHT 
# Set the buffer for the Y position of the text
Y_BUFFER = ROW_HEIGHT * 0.6
# Set the Location to load the window
X_LOCATION = settings['X_LOCATION']
Y_LOCATION = settings['Y_LOCATION']
# Plex settings
PLEX_SERVER = settings['PLEX_SERVER']
PLEX_ENABLED = settings['PLEX_ENABLED']
PLEX_ACCOUNT = settings['PLEX_ACCOUNT']
PLEX_TOKEN = settings['PLEX_TOKEN']
# Web Server settings
WEB_SERVERS = settings['WEB_SERVERS']
WEB_SERVER_ENABLED = settings['WEB_SERVER_ENABLED']
#Weather settings
WEATHER_ENABLED = settings['WEATHER_ENABLED']
WEATHER_ZIP_CODE = settings['WEATHER_ZIP_CODE']
WEATHER_API_KEY = settings['WEATHER_API_KEY']
WEATHER_PRECIPITATION_WARNING = settings['WEATHER_PRECIPITATION_WARNING']
WEATHER_HIGH_TEMP_WARNING = settings['WEATHER_HIGH_TEMP_WARNING']
WEATHER_LOW_TEMP_WARNING = settings['WEATHER_LOW_TEMP_WARNING']
last_weather_fetch_time = 0
logfile = "log.txt"
range_file = "range.json"

def log(message):
    try:
        with open(logfile, 'a') as log:
            log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Error occurred in logging: {e}")
        traceback.print_exc()
    log.close()

def load_range():
    try:
        with open(range_file, 'r') as file:
            range_data = json.load(file)
    except:
        range_data = {}
    return range_data

def save_range(range_data):
    try:
        with open(range_file, 'w') as file:
            json.dump(range_data, file)
    except Exception as e:
        print(f"Error occurred in saving range: {e}")
        traceback.print_exc()
range_data = load_range()
if 'temp_cpu_min' not in range_data:
    range_data['temp_cpu_min'] = 1000
    range_data['temp_gpu_min'] = 1000
    range_data['temp_ram_min'] = 1000
    range_data['temp_cpu_max'] = 0
    range_data['temp_gpu_max'] = 0
    range_data['temp_ram_max'] = 0

def world_time():
    # Use pytz.timezone to get tzinfo objects based on timezone strings
    chicago_time = datetime.now().astimezone(pytz.timezone('America/Chicago'))
    newyork_time = datetime.now().astimezone(pytz.timezone('America/New_York'))
    tokyo_time = datetime.now().astimezone(pytz.timezone('Asia/Tokyo'))
    losangeles_time = datetime.now().astimezone(pytz.timezone('America/Los_Angeles'))
    hawaii_time = datetime.now().astimezone(pytz.timezone('Pacific/Honolulu'))
    month_day_year = datetime.now().strftime('%a %m/%d')
    return f"{month_day_year} {chicago_time.strftime('%H:%M:%S')}  | ET: {newyork_time.strftime('%H:%M')} | PT: {losangeles_time.strftime('%H:%M')} | HI: {hawaii_time.strftime('%H:%M')} | JP: {tokyo_time.strftime('%H:%M')}"

weather_data = {}
def fetch_weather():
    global last_weather_fetch_time, weather_data
    if time.time() - last_weather_fetch_time < 300:
        return weather_data
    last_weather_fetch_time = time.time()
    # Make a request to the weather API
    url = f'http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={WEATHER_ZIP_CODE}&days=1&aqi=yes&alerts=yes'
    try:
        response = requests.get(url)
    except:
        print("Error occurred in fetching weather data")
        return False
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract the current temperature, high, low, and chance of rain
        # Pretty print the JSON response
        # if DEBUG: print(json.dumps(data, indent=4))

      
        current_temp = data['current']['temp_f']
        high_temp = data['forecast']['forecastday'][0]['day']['maxtemp_f']
        low_temp = data['forecast']['forecastday'][0]['day']['mintemp_f']
        totalprecip_in = data['forecast']['forecastday'][0]['day']['totalprecip_in']
        # Calculate the chance of rain based on the total precipitation of more than 0.25 inches
        rain_modifier = totalprecip_in * 4
        if rain_modifier > 1:
            rain_modifier = 1
        chance_of_rain = data['forecast']['forecastday'][0]['day']['daily_chance_of_rain'] * rain_modifier
        chance_of_snow = data['forecast']['forecastday'][0]['day']['daily_chance_of_snow'] * rain_modifier
        condition = data['forecast']['forecastday'][0]['day']['condition']['text']
        if chance_of_rain > 100:
            chance_of_rain = 100
        if chance_of_snow > 100:
            chance_of_snow = 100
        # round the chance of rain to the nearest whole number
        chance_of_rain = round(chance_of_rain)
        chance_of_snow = round(chance_of_snow)
        try:
            aq_ozone = data['current']['air_quality']['o3']
        except:
            aq_ozone = 0
        try:
            aq_pm10 = data['current']['air_quality']['pm10']
        except:
            aq_pm10 = 0
        try:
            aq_pm2_5 = data['current']['air_quality']['pm2_5']
        except:
            aq_pm2_5 = 0
        try:
            aq_no2 = data['current']['air_quality']['no2']
        except:
            aq_no2 = 0
        try:
            aq_so2 = data['current']['air_quality']['so2']
        except:
            aq_so2 = 0
        try:
            aq_co = data['current']['air_quality']['co']
        except:
            aq_co = 0
        # Check if any alerts exist
        alert = False
        alert_level = 0
        if 'alerts' in data and 'alert' in data['alerts'] and len(data['alerts']['alert']) > 0:
            for event in data['alerts']['alert']:
                lower_case = event['event'].lower()
                if 'warning' in lower_case or 'alert' in lower_case or 'emergency' in lower_case:
                    if 'flood' in lower_case and totalprecip_in < 0.25:
                        continue
                    alert = event['event']
                    alert_level = 2
                elif 'watch' in lower_case and alert_level < 2:
                    if 'flood' in lower_case and totalprecip_in < 0.25:
                        continue
                    alert = event['event']
                    alert_level = 1


        aq_score = "Good"
        if aq_ozone > 100 or aq_pm10 > 20 or aq_pm2_5 > 11 or aq_no2 > 11 or aq_so2 > 11 or aq_co > 10000:
            aq_score = "Moderate"
        if aq_ozone > 180 or aq_pm10 > 50 or aq_pm2_5 > 25 or aq_no2 > 20 or aq_so2 > 20 or aq_co > 20000:
            aq_score = "Poor"

        # Set the color based on the weather conditions
        color = 'green'

        if alert_level == 1:
            color = 'yellow'

        if alert_level == 2:
            color = 'red'
        if color == 'green':
            alert = condition

        weather_data = {
            'alert': alert,
            'current_temp': current_temp,
            'high_temp': high_temp,
            'low_temp': low_temp,
            'chance_of_rain': chance_of_rain,
            'chance_of_snow': chance_of_snow,
            'color': color,
            'aq_score': aq_score
        }
        return weather_data
    else:
        print(f"Error fetching weather data. Response code: {response.status_code}")
        return False
last_web_server_check = 0
# check if the web server is giving the correct response code
def check_web_server():
    global last_web_server_check, WEB_SERVERS
    if time.time() - last_web_server_check < 30:
        return WEB_SERVERS
    results = []
    for WEB_SERVER in WEB_SERVERS:
        url = WEB_SERVER['url']
        response_code = WEB_SERVER['response_code']
        start_time_ms = time.time()
        WEB_SERVER['response_time'] = -1
        try:
            response = requests.get(url, timeout=5)
        except Exception as e:
            print(f"Error occurred in fetching web server data")
            print(e)
            WEB_SERVER['response_time'] = -1
            results.append(WEB_SERVER)
            continue
        end_time_ms = time.time()
        if response.status_code != response_code:
            WEB_SERVER['response_time'] = -1
            print(f"Web server returned {response.status_code} instead of {response_code}")
        else:
            time_wait = round(end_time_ms - start_time_ms, 2)
            WEB_SERVER['response_time'] = time_wait
        results.append(WEB_SERVER)
    last_web_server_check = time.time()
    WEB_SERVERS = results
    return results



def get_active_plex_sessions():
    start_time = time.time()
    users = []
    try:
        plex_api = PlexServer(PLEX_SERVER, PLEX_TOKEN)
    except Exception as e:
        print(f"Error occurred: {e}")
        return False
    try:
        sessions = plex_api.sessions()
        for session in sessions:
            user = session.user.title
            users.append(user)
    except Exception as e:
        print(f"Error occurred fetching sessions: {e}")
        return False
    if len(users) == 0:
        return "Idle"
    else:
        end_time = time.time()
        if DEBUG: print(f"Plex check took {end_time - start_time} seconds")
        rendered_users = []
        formatted_users = []
        for user in users:
            if user not in rendered_users:
                rendered_users.append(user)
                session_count = users.count(user)
                if session_count > 1:
                    user = f"{user} ({session_count})"
                else:
                    user = f"{user}"
                formatted_users.append(user)
        active_users_text = ', '.join(formatted_users)
        return active_users_text


# Track GPU ID's
gpus = []

# Pause polling on window move
pause_polling = False

temps = []
utils = []
fan_speeds = []
net = []
disk = []
def remove_units_to_float(temp):
    value = temp
    try:
        strings_to_remove = [' ','°C','°F','%','/s', '/', 'RPM', 'KB', 'MB', 'GB', 'TB','MHz', 'GHz', 'V', 'W','-'] 
        for string in strings_to_remove:
            value = value.replace(string, '')
        try:
            value = float(value)
        except:
            print(f"Error occurred in remove_units_to_float: {e}")
            traceback.print_exc()
            return temp
        if 'KB' in temp or 'Kb' in temp:
            value = float(value) * 1024
        elif 'MB' in temp or 'Mb' in temp:
            value = float(value) * 1024 * 1024
        elif 'GB' in temp or 'Gb' in temp:
            value = float(value) * 1024 * 1024 * 1024
        return float(value)
    except Exception as e:
        print(f"Error occurred in remove_units_to_float: {e}")
        traceback.print_exc()
        return temp
def poll_libre():
    start_time = time.time()
    global temps, utils, fan_speeds, net, disk, temperature_infos
    # Connect to the OpenHardwareMonitor namespace on the remote server
    global w
    
    # Reset values
    temps = []
    utils = []
    fan_speeds = []
    net = []
    disk = []
    # Temperature variables
    cpu_temp = 0
    system_temp = 0
    hdd_temp = False
    gpu_id = 0
    gpus = []
    #Utilizations variables
    cpu_total = 0
    cpu_speed = MAX_CPU_MHZ
    ram_used = 0
    hdd_used = False
    #Network variables
    up = 0
    down = 0
    #Disk variables
    d_up = 0
    d_down = 0
    # Process temps into a list of tuples
    try:
        OHW_ADDRESS = f"http://{REMOTE_SERVER}:{REMOTE_PORT}/data.json"
        libre_data = requests.get(OHW_ADDRESS, timeout=10).text
    except:
        print("Error occurred in fetching LibreHW data")
        return False
    try:
        OHW_DICT = json.loads(libre_data)
    except Exception as e:
        print("Error occurred in loading LibreHW data")
        print(e)
        traceback.print_exc()
        return False
    sensors = []
    counta=0
    countb=0
    countc=0
    countd=0
    gpu_id = 0
    for i in OHW_DICT['Children'][0]['Children']:
        parent = OHW_DICT['Children'][0]['Children'][counta]['Text']
        if parent == 'NVIDIA GeForce RTX 4090':
            parent = 'NVIDIA GeForce RTX 4090 #' + str(gpu_id)
            gpu_id = gpu_id + 1
        for o in OHW_DICT['Children'][0]['Children'][counta]['Children']:
            if counta > 0:
                sensor_type = OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Text']
            else:
                parent = OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Text']
                if parent == 'NVIDIA GeForce RTX 4090':
                    parent = 'NVIDIA GeForce RTX 4090 #' + str(gpu_id)
                    gpu_id = gpu_id + 1
            for p in OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Children']:
                if counta > 0:
                    data = OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Children'][countc]
                    #data_min = data['Min']
                    #data_max = data['Max']
                    data_current = remove_units_to_float(data['Value'])
                    data_name = data['Text']
                    sensor = {
                        'Name': data_name,
                        'SensorType': sensor_type,
                        'Parent': parent,
                        'Value': data_current
                    }
                else:
                    for q in OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Children'][countc]['Children']:
                        sensor_type = OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Children'][countc]['Text']
                        data = OHW_DICT['Children'][0]['Children'][counta]['Children'][countb]['Children'][countc]['Children'][countd]
                        #data_min = data['Min']
                        #data_max = data['Max']
                        data_current = remove_units_to_float(data['Value'])
                        data_name = data['Text']
                        sensor = {
                            'Name': data_name,
                            'SensorType': sensor_type,
                            'Parent': parent,
                            'Value': data_current
                        }
                        sensors.append(sensor)
                        countd+=1
                    countd=0
                sensors.append(sensor)
                countc+=1
            countc=0
            countb+=1
        countb=0
        counta+=1
    # Process the sensors
    system_fan_speed = 100
    system_fan_missing = True
    try:
        data_matched = False
        for sensor in sensors:
            #Temperature sensors
            if sensor['SensorType'] == u'Temperatures' and sensor['Name'] == "GPU Core":
                if sensor['Parent'] not in gpus:
                    gpus.append(sensor['Parent'])
                gpu_id = gpus.index(sensor['Parent'])
                temps.append(("GPU-" + str(gpu_id), sensor['Value']))
                data_matched = True
            if sensor['SensorType'] == u'Temperatures' and sensor['Name'] == "Core Average":
                cpu_temp = sensor['Value']
            if sensor['SensorType'] == u'Temperatures' and sensor['Name'] == "System":
                system_temp = sensor['Value']
            # Get utilization sensor information
            if sensor['SensorType'] == u'Load' and sensor['Name'] == "GPU Core":
                if sensor['Parent'] not in gpus:
                    gpus.append(sensor['Parent'])
                gpu_id = gpus.index(sensor['Parent'])
                gpu_speed = round(sensor['Value'])
                utils.append(("GPU-" + str(gpu_id), gpu_speed))
            if sensor['SensorType'] == u'Load' and sensor['Name'] == "CPU Total":
                cpu_total = sensor['Value']
            if sensor['SensorType'] == u'Clocks' and sensor['Name'] == "CPU Core #1":
                cpu_speed = sensor['Value']
            if sensor['SensorType'] == u'Load' and sensor['Name'] == "Memory":
                ram_used = sensor['Value']
            #Fan speeds
            if sensor['SensorType'] == u'Controls' and (sensor['Name'] == "GPU Fan" or sensor['Name'] == "GPU Fan 1"):
                if sensor['Parent'] not in gpus:
                    gpus.append(sensor['Parent'])
                gpu_id = gpus.index(sensor['Parent'])
                fan_speeds.append(("GPU-" + str(gpu_id), sensor['Value']))
            if sensor['SensorType'] == u'Controls' and sensor['Name'] == "CPU Fan":
                fan_speeds.append(("CPU", sensor['Value']))
            for fan_number in SYSTEM_FANS_ENABLED:
                fan_name = f"System Fan #{fan_number}"
                if sensor['SensorType'] == u'Controls' and sensor['Name'] == fan_name:
                    if int(sensor['Value']) <= int(system_fan_speed):
                        system_fan_speed = sensor['Value']
                        system_fan_missing = False
            #Network sensors
            if sensor['Name'] == "Upload Speed":
                up = float(sensor['Value']) + up
            if sensor['Name'] == "Download Speed":
                down = float(sensor['Value']) + down
            #Disk sensors
            if sensor['Name'] == "Read Rate":
                d_up = float(sensor['Value']) + d_up
            if sensor['Name'] == "Write Rate":
                d_down = float(sensor['Value']) + d_down
        if system_fan_missing:
            system_fan_speed = 0
        fan_speeds.append(("RAM", system_fan_speed))
        if not data_matched:
            print("No GPU data found while processing libre_poll")
            return False
    except Exception as e:
        print("Error occurred in processing libre_poll")
        print(e)
        traceback.print_exc()
        return False
    # Process Temperatures     
    temps.append(("CPU", cpu_temp))
    temps.append(("RAM", system_temp))
    if hdd_temp:
        temps.append(("DISK", hdd_temp))
    # Post Process Utilizations
    realized_speed = cpu_speed / MAX_CPU_MHZ
    acutal_cpu = cpu_total * realized_speed
    # Round the CPU utilization to the nearest whole number
    acutal_cpu = round(acutal_cpu)
    utils.append(("CPU", acutal_cpu))
    ram_used = round(ram_used)
    utils.append(("RAM", ram_used))
    if hdd_used:
        hdd_used = round(hdd_used)
        utils.append(("DISK", hdd_used))
    # Post Process Network
    up = round(up / 1024 / 128)
    down = round(down / 1024 / 128)
    net.append(up)
    net.append(down)
    # Post Process Disk
    d_up = round(d_up / 1024 / 1024)
    d_down = round(d_down / 1024 / 1024)
    disk.append(d_up)
    disk.append(d_down)
    end_time = time.time()
    if DEBUG: print(f"Poll took {end_time - start_time} seconds")
    return True

# Create a new Tkinter window
window = Tk()
window.attributes('-alpha', 1.0)
if ALWAYS_ON_TOP:
    window.attributes('-topmost', 1)  # This line keeps the window on top
 
# Hide the window bar
window.overrideredirect(True)

# Variables to store the mouse position
start_x = None
start_y = None


# Create a canvas to draw on
canvas = Canvas(window, width=WIDTH, height=HEIGHT, bd=0, highlightthickness=0, bg='black')


# Create a red "X" in the upper right that closes the window when clicked
close_button = canvas.create_text(window.winfo_width() - 10, 10, anchor='ne', font=("Arial", 8), fill='white', text="X")

def close_window(event):
    global pause_polling
    pause_polling = True 
    window.destroy()

canvas.tag_bind(close_button, '<Button-1>', close_window)
canvas.pack()

# Comment out or remove the dynamic window positioning logic
# if X_LOCATION < 0 or X_LOCATION > window.winfo_screenwidth() or Y_LOCATION < 0 or Y_LOCATION > window.winfo_screenheight():
#     window.geometry('+%d+%d' % (0, 0))
# else:
#     window.geometry('+%d+%d' % (X_LOCATION, Y_LOCATION))

# Prevent the window from taking focus when it is initially created
window.overrideredirect(True)

# Set a static window position (example: top-left corner)
window.geometry('+0+0')


# Create a dictionary to store the last 10 temperatures for each GPU
last_n_temps = {}
device_elements = []
util_poll_samples = []
cold_poll_samples = []

def update_metrics():
    global pause_polling
    if not pause_polling:
        try:
            # Fetch the temperatures
            global temps, utils, fan_speeds, net, disk
            poll_status = poll_libre()

            # Check if the window is outside the screen's dimensions
            if window.winfo_x() < 0 or window.winfo_x() > window.winfo_screenwidth() or window.winfo_y() < 0 or window.winfo_y() > window.winfo_screenheight():
                # If it is, reset the window's position to the starting position
                window.geometry('+%d+%d' % (0, window.winfo_screenheight() - window.winfo_height() - 180))

            # Make the window always stay on top, but without taking focus
            if ALWAYS_ON_TOP:
                window.attributes('-topmost', 1)

            # Prevent the window from taking focus when it is initially created
            window.overrideredirect(True)
            
            # Set the canvas height based on the number of GPUs
            canvas.config(width=WIDTH, height=HEIGHT)
            
            # Set the window height based on the number of GPUs
            window.geometry(f'{WIDTH}x{HEIGHT}+{window.winfo_x()}+{window.winfo_y()}')
            window.attributes('-alpha', 1.0)
        except Exception as e:
            print("Error occurred preparing canvas")
            print(e)
            time.sleep(1)
            return None
        if not poll_status:
            for circle, text in device_elements:
                canvas.delete(circle)
                canvas.delete(text)
            device_elements.clear()
            row = 1
            i = 0
            shape = canvas.create_oval(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill="red")
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"Libre Connection Error")
            device_elements.append((shape, text))
        else:
            try:
                # Remove the old Device elements
                for circle, text in device_elements:
                    canvas.delete(circle)
                    canvas.delete(text)
                device_elements.clear()
                net_row = 0
                # Calculate the average temperature for each GPU and create the new elements
                header_made = False
                for i, (device_name, temp) in enumerate(temps):
                    if not header_made:
                        row = i
                        header_made = True
                        text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"Device\tTemp\tFan\tUtilization")
                        device_elements.append((text, None))
                    row = i + 1
                    fan_speed = -1
                    for fan in fan_speeds:
                        if fan[0] == device_name:
                            fan_speed = fan[1]
                    # Set util samples if not set
                    if len(util_poll_samples) <= i:
                        util_poll_samples.append(0)
                    if len(cold_poll_samples) <= i: 
                        cold_poll_samples.append(0)

                    # If this is a new GPU, create a new deque for it
                    if device_name not in last_n_temps:
                        last_n_temps[device_name] = deque(maxlen=NUM_SAMPLES)
                    
                    # Append the temperature to the deque
                    last_n_temps[device_name].append(temp)
                    
                    # Calculate the average temperature and round it to the nearest whole number
                    avg_temp = round(sum(last_n_temps[device_name]) / len(last_n_temps[device_name]))
                    if device_name == "CPU":
                        CAUTION_TEMP = CPU_CAUTION_TEMP
                        DANGER_TEMP = CPU_DANGER_TEMP
                        if avg_temp < range_data['temp_cpu_min'] and avg_temp > 0:
                            range_data['temp_cpu_min'] = avg_temp
                        if avg_temp > range_data['temp_cpu_max']:
                            range_data['temp_cpu_max'] = avg_temp
                    elif device_name == "RAM":
                        CAUTION_TEMP = RAM_CAUTION_TEMP
                        DANGER_TEMP = RAM_DANGER_TEMP
                        if avg_temp < range_data['temp_ram_min'] and avg_temp > 0:
                            range_data['temp_ram_min'] = avg_temp
                        if avg_temp > range_data['temp_ram_max']:
                            range_data['temp_ram_max'] = avg_temp
                    else:
                        CAUTION_TEMP = GPU_CAUTION_TEMP
                        DANGER_TEMP = GPU_DANGER_TEMP
                        if avg_temp < range_data['temp_gpu_min'] and avg_temp > 0:
                            range_data['temp_gpu_min'] = avg_temp
                        if avg_temp > range_data['temp_gpu_max']:
                            range_data['temp_gpu_max'] = avg_temp
                    # Determine the color of the circle based on the average temperature
                    if avg_temp < CAUTION_TEMP:
                        color = 'green'
                    elif avg_temp <= DANGER_TEMP:
                        color = 'yellow'
                    else:
                        log(f"High Temp: {device_name} - {avg_temp}")
                        color = 'red'
                    util_color = 'green'
                    if utils[i][1] > UTILIZATION_CAUTION and utils[i][1] < UTIL_SAMPLES:
                        util_poll_samples[i] = util_poll_samples[i] + 1
                    if utils[i][1] == 0 and cold_poll_samples[i] < UTIL_SAMPLES:
                        cold_poll_samples[i] = cold_poll_samples[i] + 1
                    if utils[i][1] < UTILIZATION_CAUTION and util_poll_samples[i] > 0:
                        util_poll_samples[i] = util_poll_samples[i] - 1
                    if utils[i][1] > 0 and cold_poll_samples[i] > 0:
                        cold_poll_samples[i] = cold_poll_samples[i] - 1
                    if cold_poll_samples[i] >= UTIL_SAMPLES and utils[i][1] == 0:
                        util_color = 'blue'
                    if util_poll_samples[i] >= UTIL_SAMPLES:        
                        util_color = 'yellow'
                    if color != 'red' and color != 'yellow':
                        color = util_color
                    # Create the circle and text elements with the color determined above
                    try:         
                        shape = canvas.create_oval(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
                        text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"{device_name}\t|     {avg_temp}°  |  {fan_speed}%\t|\t{utils[i][1]}%")
                        # Add the elements to the list
                        device_elements.append((shape, text))
                    except Exception as e:
                        print("Error occurred in processing main temps")
                        print(e)
                        traceback.print_exc()
                        continue
                    net_row = i
                # Add Network Up and Down
                i = net_row + 1
                row = i + 1
                if len(util_poll_samples) <= i:
                    util_poll_samples.append(0)
                if len(cold_poll_samples) <= i:
                    cold_poll_samples.append(0)
                color = 'green'
                try:
                    total_net = net[0] + net[1]
                except:
                    total_net = 0
                    net = [0, 0]
                if total_net > 0:
                    if total_net > NETOPS_CAUTION and util_poll_samples[i] < UTIL_SAMPLES:
                        util_poll_samples[i] = util_poll_samples[i] + 1
                else:
                    if total_net == 0 and cold_poll_samples[i] < UTIL_SAMPLES:
                        cold_poll_samples[i] = cold_poll_samples[i] + 1
                # Decrement hot and cold utilization samples
                if total_net < NETOPS_CAUTION and util_poll_samples[i] > 0:
                    util_poll_samples[i] = util_poll_samples[i] - 1
                if total_net > 0 and cold_poll_samples[i] > 0:
                    cold_poll_samples[i] = cold_poll_samples[i] - 1
                # Set the color based on the total network utilization poll thresholds        
                if cold_poll_samples[i] >= UTIL_SAMPLES and total_net == 0:
                    color = 'blue'
                if util_poll_samples[i] >= UTIL_SAMPLES:
                    color = 'yellow'
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
                text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"NET IO\t| Up:\t{net[0]}Mb\t| Down: {net[1]}Mb")
                device_elements.append((shape, text))

                #Add Disk Ops
                i = i + 1
                row = i + 1
                if len(util_poll_samples) <= i:
                    util_poll_samples.append(0)
                if len(cold_poll_samples) <= i:
                    cold_poll_samples.append(0)
                color = 'green'
                try:
                    total_disk = disk[0] + disk[1]
                except:
                    total_disk = 0
                    disk = [0, 0]
                if total_disk > 0:
                    if total_disk > DISKOPS_CAUTION and util_poll_samples[i] < UTIL_SAMPLES:
                        util_poll_samples[i] = util_poll_samples[i] + 1
                else:
                    if total_disk == 0 and cold_poll_samples[i] < UTIL_SAMPLES:
                        cold_poll_samples[i] = cold_poll_samples[i] + 1
                # Decrement hot and cold utilization samples
                if total_disk < DISKOPS_CAUTION and util_poll_samples[i] > 0:
                    util_poll_samples[i] = util_poll_samples[i] - 1
                if total_disk > 0 and cold_poll_samples[i] > 0:
                    cold_poll_samples[i] = cold_poll_samples[i] - 1
                # Set the color based on the total network utilization poll thresholds        
                if cold_poll_samples[i] >= UTIL_SAMPLES and total_disk == 0:
                    color = 'blue'
                if util_poll_samples[i] >= UTIL_SAMPLES:
                    color = 'yellow'
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
                text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"DISK IO\t| Read:\t{disk[0]}MB\t| Write: {disk[1]}MB")
                device_elements.append((shape, text))
            except Exception as e:
                log("Error occurred in processing libre data")
                print("Error occurred in processing libre data")
                print(e)
                traceback.print_exc()
                # Remove the old Device elements
                for circle, text in device_elements:
                    canvas.delete(circle)
                    canvas.delete(text)
                device_elements.clear()
                i = 0
                row = 1
                text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"Device\tTemp\tFan\tUtilization")
                device_elements.append((text, None))
            try:
                # Save the range data
                with open(range_file, 'w') as f:
                    json.dump(range_data, f)
            except Exception as e:
                print("Error occurred in saving range data")
                print(e)
                traceback.print_exc()
        small_font = int(FONT_SIZE * 0.7) 
        # Check if the web server is giving the correct response code
        if WEB_SERVER_ENABLED:
            row = row + 1
            i = i + 1
            results = check_web_server()
            color = 'green'
            text = "Web: "
            site = 0
            for result in results:
                site = site + 1
                if site > 1:
                    text = text + " | "
                if result['response_time'] == -1:
                    color = 'red'
                    log(f"Web Server: {result['name']} - down")
                    text = text + f"{result['name']}: down"
                else:
                    text = text + f"{result['name']}: {result['response_time']}s"
                if result['response_time'] > result['response_threshold']:
                    log(f"Web Server: {result['name']} - slow response time: {result['response_time']}s")
                    color = 'yellow'
            shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)   
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"{text}")
            device_elements.append((shape, text))
        
        # Check if there are any active Plex sessions
        if PLEX_ENABLED:
            row = row + 1
            i = i + 1
            active_sessions = get_active_plex_sessions()
            if not active_sessions:
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='red')
            else:
                if active_sessions == "Idle":
                    shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='blue')
                else:
                    shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='green')
           
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"Plex: {active_sessions}")
            device_elements.append((shape, text))

        # Add a row of the weather
        if WEATHER_ENABLED:
            try:
                weather = fetch_weather()
            except Exception as e:
                print("Error occurred in fetching weather")
                print(e)
                traceback.print_exc()
                weather = False
            if weather:
                try:
                    row = row + 1
                    i = i + 1
                    if weather['chance_of_snow'] > weather['chance_of_rain']:
                        precip = f'{weather['chance_of_snow']}% Snow'
                    else:
                        precip = f'{weather['chance_of_rain']}% Rain'
                    if weather['alert']:
                        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=weather['color'])
                        msg = f'{weather["alert"]} | {weather["current_temp"]}°F | {precip},  H: {weather["high_temp"]}°F L: {weather["low_temp"]}°F'
                        text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"{msg}")
                    else:
                        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=weather['color'])
                        msg = f'{weather["current_temp"]}°F | {precip},  H: {weather["high_temp"]}°F L: {weather["low_temp"]}°F'
                        text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"{msg}")
                    device_elements.append((shape, text))
                    #Add Air Quality
                    row = row + 1
                    i = i + 1
                    if weather['aq_score'] == "Moderate":
                        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='yellow')
                    elif weather['aq_score'] == "Poor":
                        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='red')
                    elif weather['aq_score'] == "Good":
                        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='green')
                    text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"Air Quality: {weather['aq_score']}")
                    device_elements.append((shape, text))
                except Exception as e:
                    print("Error occurred in processing weather")
                    print(e)
                    traceback.print_exc()
                    row = row + 1
                    i = i + 1
                    shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='red')
                    text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"Weather: Error fetching weather")
                    device_elements.append((shape, text))
            else:
                row = row + 1
                i = i + 1
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='red')
                text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"Weather: Error fetching weather")
                device_elements.append((shape, text))
            
        # Add a row of the world time
        row = row + 1
        i = i + 1
        text = canvas.create_text(0, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='lightblue', text=f"{world_time()}")
        device_elements.append((None, text))

        # Remember the window's current position and size
        x = window.winfo_x()
        y = window.winfo_y()

       
        # Resize the window and canvas to fit the new elements
        # Set the window height based on the number of GPUs
        #total_height = ROW_HEIGHT * (len(temps) + 3)
        total_height = HEIGHT
        window.geometry(f'{WIDTH}x{total_height}+{window.winfo_x()}+{window.winfo_y()}')
        canvas.config(width=WIDTH, height=total_height)
        
        

    # Schedule the next update
    window.after(POLL_INTERVAL_MS, update_metrics)


# Schedule the first update
window.after(POLL_INTERVAL_MS, update_metrics)

def update_close_button_position():
    canvas.coords(close_button, window.winfo_width() - 10, 10)

def on_close():
    global pause_polling
    pause = True  # Stop all polling
    window.destroy()
# Call this function after the window is displayed
window.after(1, update_close_button_position)
# Run the Tkinter main loop
window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()