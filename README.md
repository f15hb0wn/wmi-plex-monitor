# Windows Temperature Overlay

I finished a new rig for hosting my personal website, Plex and running other projectsand am running it hard and wanted to know how hot the hardware is getting.

I wanted a simple widget to display GPU and CPU temperatures to have the following characteristics:
- Green/Yellow/Red indicator on temperature against configured thresholds
- An average of temperature readings to avoid excessive alerting
- Stays on top of windows
- Can be run on a remote host (on same LAN)
- Can be resized or displayed in full mode
- Show status of my web server
- Show active sessions on my Plex Server


![Interface Screenshot](/demo.png)

# Pre-requisites
- Download, extract and run (as Administrator) Libre Hardware Monitor: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor on the server to monitor
- Enable Web server in LibreHardwareMonitor
- Install Python for Windows (tested on 3.12): https://www.python.org/downloads/
- Download this code and change directory to it.
- Install dependencies: `pip install -r requirements.txt`
- Create `settings.yaml` using `settings.yaml.example`
- Run `python app.py`

