# Invisible-Cloak
### This project detects the color of the cloak by which you want to be invisible and replaces the masked color with background

## To run this code in your terminal:
* ***Open your terminal**
* ***Change directory to where you have downloaded this code***
* ***Install python3 if you have not, if installed already then it's ok!***
* **Run**  `  python3 -m venv venv  ` ***to create a virtual environment named venv.***
* **Run**   `  source venv/bin/activate  ` 
***to activate your environment!***

*  **Run this to install the dependencies**
```python
pip install -r requirements.txt
```
> * ***First we need to choose the color to mask. The code works by masking a specific color.***
```python
python color_range_detector.py -f HSV --webcam
```
> * ***When you run this, you will be presented with 3 camera views (Trackbar,Original & Thresh). Go to the one with the slider(Trackbar) and the one which starts  with a white screen(Thresh).***

> * ***Adjust the values of H, S & V till only the object you wish to make invisible becomes white and the rest is black. The precise you get this, the accurate your invisibility will be.***

> * ***Enter q to exit from all cameras***

> * ***After you do that. Run*** 
``` python 
python3 invisible.py
```

> * ***Stay away from the webcam for a few seconds and come back holding the cloak***

### Say 'Evanesco'😂 and Congratulations! You will be like this:
![InvisibleGif](https://github.com/abd-shoumik/Invisible-Cloak/blob/master/Invisible.gif)

## Contacts:
* **Created by:[Abdullah Shoumik](https://github.com/abd-shoumik)**
* **Email:[abd.shoumik@gmail.com](https://abd.shoumik@gmail.com)**
* **Youtube:[TheLazyCoder](https://youtube.com/channel/UCWjx_FKjjfjAL-wtSi-iS4g)**
* **LinkedIn: [Abdullah Shoumik](https://www.linkedin.com/in/abdullah-shoumik-7a0b36135/)**


