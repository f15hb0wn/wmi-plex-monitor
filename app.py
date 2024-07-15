from tkinter import Tk, Canvas
from collections import deque
import wmi
import requests
import yaml
from datetime import datetime
from plexapi.server import PlexServer
import time

# Load the settings from settings.yaml
with open('settings.yaml', 'r') as file:
    settings = yaml.safe_load(file)

# Set the temperature thresholds
CAUTION_TEMP = settings['CAUTION_TEMP']
DANGER_TEMP = settings['DANGER_TEMP']
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
# Set the ID of the disk to monitor
DISK_ID = settings['DISK_ID']
REMOTE_SERVER = settings['REMOTE_SERVER']
USERNAME = settings['USERNAME']
PASSWORD = settings['PASSWORD']
# Set width of the window
HEIGHT = settings['HEIGHT']
WIDTH = settings['WIDTH']
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
WEB_SERVER = settings['WEB_SERVER']
WEB_SERVER_ENABLED = settings['WEB_SERVER_ENABLED']
WEB_RESPONSE_CODE = settings['WEB_RESPONSE_CODE']
WEB_SERVER_NAME = settings['WEB_SERVER_NAME']

# check if the web server is giving the correct response code
def check_web_server():
    try:
        response = requests.get(WEB_SERVER, timeout=1)
    except Exception as e:
        print(f"Error occurred: {e}")
        return False
    if response.status_code != WEB_RESPONSE_CODE:
        print(f"Web server returned {response.status_code} instead of {WEB_RESPONSE_CODE}")
        return False
    else:
        return True

def get_active_plex_sessions():
    try:
        plex_api = PlexServer(PLEX_SERVER, PLEX_TOKEN)
    except Exception as e:
        print(f"Error occurred: {e}")
        return False
    try:
        sessions = plex_api.sessions()
        active_users = [session.user.title for session in sessions]
    except Exception as e:
        print(f"Error occurred fetching sessions: {e}")
        return False
    if len(sessions) == 0:
        return "None active"
    else:
        print(f"Active sessions: {active_users}")
        active_users_text = ', '.join(active_users)
        print(f"Active users: {active_users_text}")
        return active_users_text


# Track GPU ID's
gpus = []

# Pause polling on window move
pause_polling = False

def wmi_connect():
    global w, u
    # Build connection to WMI server, try with user and password first, if that fails try without
    try:
        w = wmi.WMI(namespace="root\\LibreHardwareMonitor", computer=REMOTE_SERVER, user=USERNAME, password=PASSWORD)
    except:
        try:
            w = wmi.WMI(namespace="root\\LibreHardwareMonitor", computer=REMOTE_SERVER)
        except:
            print("Unable to connect to WMI server")
            return False
    try:
        u = wmi.WMI(namespace="root\\CIMV2", computer=REMOTE_SERVER, user=USERNAME, password=PASSWORD)
    except:
        try:
            u = wmi.WMI(namespace="root\\CIMV2", computer=REMOTE_SERVER)
        except:
            print("Unable to connect to WMI server")
            return False

wmi_connect()
temps = []
utils = []
fan_speeds = []
net = []
disk = []
def poll_wmi():
    global temps, utils, fan_speeds, net, disk
    # Connect to the OpenHardwareMonitor namespace on the remote server
    global w
    
    # Reset values
    temps = []
    utils = []
    fan_speeds = []
    net = []
    disk = []
    # Get temperature sensor information
    try :
        temperature_infos = w.Sensor()
    except:
        return False

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
    # Process temps
    try:
        for sensor in temperature_infos:
            #Temperature sensors
            if sensor.SensorType == u'Temperature' and sensor.Name == "GPU Core":
                temps.append(("GPU-" + str(gpu_id), sensor.Value))
                if sensor.Parent not in gpus:
                    gpus.append(sensor.Parent)
                gpu_id = gpus.index(sensor.Parent)
            if sensor.SensorType == u'Temperature' and sensor.Name == "CPU Socket":
                cpu_temp = sensor.Value
            if sensor.SensorType == u'Temperature' and sensor.Name == "System":
                system_temp = sensor.Value
            if sensor.SensorType == u'Temperature' and sensor.Name == "Temperature" and sensor.Parent == DISK_ID:
                hdd_temp = sensor.Value
            # Get utilization sensor information
            if sensor.SensorType == u'Load' and sensor.Name == "GPU Core":
                if sensor.Parent not in gpus:
                    gpus.append(sensor.Parent)
                gpu_id = gpus.index(sensor.Parent)
                gpu_speed = round(sensor.Value)
                utils.append(("GPU-" + str(gpu_id), gpu_speed))
            if sensor.SensorType == u'Load' and sensor.Name == "CPU Total":
                cpu_total = sensor.Value
            if sensor.SensorType == u'Clock' and sensor.Name == "CPU Core #1":
                cpu_speed = sensor.Value
            if sensor.SensorType == u'Load' and sensor.Name == "Memory":
                ram_used = sensor.Value
            if sensor.SensorType == u'Load' and sensor.Name == "Total Activity" and sensor.Parent == DISK_ID:
                hdd_used = sensor.Value
            #Fan speeds
            if sensor.SensorType == u'Control' and (sensor.Name == "GPU Fan" or sensor.Name == "GPU Fan 1"):
                if sensor.Parent not in gpus:
                    gpus.append(sensor.Parent)
                gpu_id = gpus.index(sensor.Parent)
                fan_speeds.append(("GPU-" + str(gpu_id), sensor.Value))
            if sensor.SensorType == u'Control' and sensor.Name == "CPU Fan":
                fan_speeds.append(("CPU", sensor.Value))
            if sensor.SensorType == u'Control' and sensor.Name == "System Fan #1":
                fan_speeds.append(("RAM", sensor.Value))
                if DISK_ID:
                    fan_speeds.append(("DISK", sensor.Value))
            #Network sensors
            if sensor.Name == "Upload Speed":
                up = sensor.Value + up
            if sensor.Name == "Download Speed":
                down = sensor.Value + down
            #Disk sensors
            if sensor.Name == "Read Rate":
                d_up = sensor.Value + up
            if sensor.Name == "Write Rate":
                d_down = sensor.Value + down
    except:
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
    return True

def uptime_wmi():
    global u
    try:
        for os in u.Win32_OperatingSystem():
            return os.LastBootUpTime
    except:
        return False
    return False

# Create a new Tkinter window
window = Tk()
window.attributes('-alpha', 1.0)
window.attributes('-topmost', 1)  # This line keeps the window on top
 
# Hide the window bar
window.overrideredirect(True)

# Variables to store the mouse position
start_x = None
start_y = None


# Make the window always stay on top
window.attributes('-topmost', 1)

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

# Keep the window always on top, but without taking focus
window.attributes('-topmost', 1)

# Prevent the window from taking focus when it is initially created
window.overrideredirect(True)

# Set a static window position (example: top-left corner)
window.geometry('+0+0')


# Create a dictionary to store the last 10 temperatures for each GPU
last_n_temps = {}
device_elements = []
util_poll_samples = []

def update_metrics():
    global pause_polling
    if not pause_polling:
        # Fetch the temperatures
        global temps, utils, fan_speeds, net, disk
        poll_success = poll_wmi()
        if not poll_success:
            wmi_connect()
            time.sleep(1)
            return None    
        # Check if the window is outside the screen's dimensions
        if window.winfo_x() < 0 or window.winfo_x() > window.winfo_screenwidth() or window.winfo_y() < 0 or window.winfo_y() > window.winfo_screenheight():
            # If it is, reset the window's position to the starting position
            window.geometry('+%d+%d' % (0, window.winfo_screenheight() - window.winfo_height() - 180))

        # Make the window always stay on top, but without taking focus
        window.attributes('-topmost', 1)

        # Prevent the window from taking focus when it is initially created
        window.overrideredirect(True)
        
        # Set the canvas height based on the number of GPUs
        canvas.config(width=WIDTH, height=ROW_HEIGHT * (len(temps)+2))
        
        # Set the window height based on the number of GPUs
        window.geometry(f'{WIDTH}x{HEIGHT}+{window.winfo_x()}+{window.winfo_y()}')
        window.attributes('-alpha', 1.0)

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

            # If this is a new GPU, create a new deque for it
            if device_name not in last_n_temps:
                last_n_temps[device_name] = deque(maxlen=NUM_SAMPLES)
            
            # Append the temperature to the deque
            last_n_temps[device_name].append(temp)
            
            # Calculate the average temperature and round it to the nearest whole number
            avg_temp = round(sum(last_n_temps[device_name]) / len(last_n_temps[device_name]))
            
            # Determine the color of the circle based on the average temperature
            if avg_temp < CAUTION_TEMP:
                color = 'green'
            elif avg_temp <= DANGER_TEMP:
                color = 'yellow'
            else:
                color = 'red'
            
            # Create the circle and text elements with the color determined above
            try:         
                if utils[i][1] > UTILIZATION_CAUTION:
                    util_poll_samples[i] = util_poll_samples[i] + 1
                    if color == 'red':
                        # Heat overrides utilization warning
                        shape = canvas.create_oval(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
                    else:
                        if util_poll_samples[i] > UTIL_SAMPLES:        
                            util_color = 'yellow'
                            shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=util_color)
                        else:
                            shape = canvas.create_oval(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
                else:
                    shape = canvas.create_oval(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
                    util_poll_samples[i] = util_poll_samples[i] - 1
                text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"{device_name}\t|     {avg_temp}°  |  {fan_speed}%\t|\t{utils[i][1]}%")

                # Add the elements to the list
                device_elements.append((shape, text))
            except:
                continue
            net_row = i
        # Add Network Up and Down
        i = net_row + 1
        row = i + 1
        if len(util_poll_samples) <= i:
            util_poll_samples.append(0)
        color = 'green'
        total_net = net[0] + net[1]
        if total_net > 0:
            if total_net > NETOPS_CAUTION:
                util_poll_samples[i] = util_poll_samples[i] + 1
                if util_poll_samples[i] > UTIL_SAMPLES:
                    color = 'yellow'
        else:
            if total_net == 0:
                util_poll_samples[i] = util_poll_samples[i] + 1
                if util_poll_samples[i] > UTIL_SAMPLES:
                    color = 'blue'
        if total_net < NETOPS_CAUTION and total_net > 0:
            util_poll_samples[i] = util_poll_samples[i] - 1
        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
        text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"NET IO\t|\t\t| {net[0]}Mb↑ {net[1]}Mb↓")
        device_elements.append((shape, text))

        #Add Disk Ops
        i = i + 1
        row = i + 1
        if len(util_poll_samples) <= i:
            util_poll_samples.append(0)
        color = 'green'
        total_disk = disk[0] + disk[1]
        if total_disk > 0:
            if total_net > DISKOPS_CAUTION:
                util_poll_samples[i] = util_poll_samples[i] + 1
                if util_poll_samples[i] > UTIL_SAMPLES:
                    color = 'yellow'
        else:
            if total_disk == 0:
                util_poll_samples[i] = util_poll_samples[i] + 1
                if util_poll_samples[i] > UTIL_SAMPLES:
                    color = 'blue'
        if total_disk < DISKOPS_CAUTION and total_disk > 0:
            util_poll_samples[i] = util_poll_samples[i] - 1
        shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill=color)
        text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"DISK IO\t|\t\t| {disk[0]}MB↑ {disk[1]}MB↓")
        device_elements.append((shape, text))
        # Check if the web server is giving the correct response code
        if WEB_SERVER_ENABLED:
            row = row + 1
            i = i + 1
            if not check_web_server():
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='red')
            else:
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='green')
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"Web Server ({WEB_SERVER_NAME})")
            device_elements.append((shape, text))
        
        # Check if there are any active Plex sessions
        if PLEX_ENABLED:
            row = row + 1
            i = i + 1
            active_sessions = get_active_plex_sessions()
            if not active_sessions:
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='red')
            else:
                shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='green')
            small_font = int(FONT_SIZE * 0.7)
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", small_font), fill='white', text=f"Plex: {active_sessions}")
            device_elements.append((shape, text))
        # Add the uptime
        row = row + 1
        i = i + 1


        # Assuming uptime_wmi() returns a string like '20240714130432.500000-300'
        uptime_str = uptime_wmi()
        if uptime_str:
            # Parse the string (this step may need to be adjusted based on the exact format)
            # Example format: 'YYYYMMDDHHMMSS.microseconds-timezone'
            parsed_time = datetime.strptime(uptime_str[:14], '%Y%m%d%H%M%S')

            # Calculate uptime as the difference between now and the parsed time
            now = datetime.now()
            uptime_delta = now - parsed_time

            # Convert uptime to total seconds (or another unit as needed)
            uptime_seconds = int(uptime_delta.total_seconds())

            # Now you can use uptime_seconds in your calculations
            days = uptime_seconds // (24 * 3600)
            uptime_seconds %= (24 * 3600)
            hours = uptime_seconds // 3600
            uptime_seconds %= 3600
            minutes = uptime_seconds // 60
            uptime_seconds %= 60
            seconds = uptime_seconds

            # Format the uptime string
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

            # Create the uptime text element
            shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='green')
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"Uptime: {uptime_str}")
        else:
            # Create the uptime text element
            shape = canvas.create_rectangle(5, 5 + row * ROW_HEIGHT, ROW_HEIGHT, ROW_HEIGHT + row * ROW_HEIGHT, fill='Red')
            text = canvas.create_text(X_BUFFER, Y_BUFFER + row * ROW_HEIGHT, anchor='w', font=("Arial", FONT_SIZE), fill='white', text=f"Uptime: Not available")
        # Add the uptime element to the device_elements list
        device_elements.append((shape, text))
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