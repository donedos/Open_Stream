> python3.13 -m venv venv313
> source venv/bin/activate

> python main.py --lowvram
> python main.py --listen --lowvram (to broadcast)

Open your terminal/command prompt and install it:
> pip install pyinstaller

Run this exact command inside the folder where your script is:
> pyinstaller --noconsole --onefile OpenStreamServer.py

#autostart folder
/home/zed/.config/autostart