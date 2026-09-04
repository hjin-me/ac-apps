import os
import sys #for error messaging
import traceback
import configparser
import datetime
import calendar
import win32con
import math

import ac
import acsys

import AutoCamCar
import random
import time
import re

#is all this for the traceback?
import platform
if platform.architecture()[0] == "64bit":
    sysdir=os.path.dirname(__file__)+'/stdlib64'
else:
    sysdir=os.path.dirname(__file__)+'/stdlib'
sys.path.insert(0, sysdir)
os.environ['PATH'] = os.environ['PATH'] + ";."

import AutoCam_sim_info
from shutil import copyfile

#from obsremote import OBSRemote
#import json
#import logging
#import threading
#import websocket

#ALL THE CODE NECESSARY FOR HOTKEYS --------------------------------------
import threading

import ctypes
from ctypes import wintypes
user32 = ctypes.WinDLL('user32', use_last_error=True)
INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_UNICODE     = 0x0004
KEYEVENTF_SCANCODE    = 0x0008
MAPVK_VK_TO_VSC = 0
# msdn.microsoft.com/en-us/library/dd375731
VK_TAB  = 0x09
VK_MENU = 0x12
VK_CTRL = 0x11
VK_SHIFT = 0x10
VK_I = 0x49
VK_D = 0x44
VK_M = 0x4D
VK_LCONTROL = 0xA2
VK_LSHIFT = 0xA0

wintypes.ULONG_PTR = wintypes.WPARAM

class MOUSEINPUT(ctypes.Structure):
    _fields_ = (("dx",          wintypes.LONG),
                ("dy",          wintypes.LONG),
                ("mouseData",   wintypes.DWORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR))

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk",         wintypes.WORD),
                ("wScan",       wintypes.WORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR))

    def __init__(self, *args, **kwds):
        super(KEYBDINPUT, self).__init__(*args, **kwds)
        # some programs use the scan code even if KEYEVENTF_SCANCODE
        # isn't set in dwFflags, so attempt to map the correct code.
        if not self.dwFlags & KEYEVENTF_UNICODE:
            self.wScan = user32.MapVirtualKeyExW(self.wVk,
                                                 MAPVK_VK_TO_VSC, 0)

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (("uMsg",    wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD))

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = (("ki", KEYBDINPUT),
                    ("mi", MOUSEINPUT),
                    ("hi", HARDWAREINPUT))
    _anonymous_ = ("_input",)
    _fields_ = (("type",   wintypes.DWORD),
                ("_input", _INPUT))

LPINPUT = ctypes.POINTER(INPUT)

def _check_count(result, func, args):
    if result == 0:
        raise ctypes.WinError(ctypes.get_last_error())
    return args

user32.SendInput.errcheck = _check_count
user32.SendInput.argtypes = (wintypes.UINT, # nInputs
                             LPINPUT,       # pInputs
                             ctypes.c_int)  # cbSize
#END OF HOTKEYS CODE ------------------------------------------------------

#ToDo:
#checkboxes to enable/disable the app itself as well as the various camera modes? just use INI options instead?
#Calculate GAPS based on average speed and position on track?
#document all possible camera functions
#create/write an INI to store data (already reading it)
#track when cars have had (and not had) focus and even out distribution during no current battles
#reset various variables when a session starts (focusCount, etc)
#special first lap and last lap logic
#add logic (mouse clicks) to get the car out of the setup screens? No, already in IS_AddShortcutKey

camWindow = 0
btnToggle = 0
lblInfo = 0
windowTitle = "Auto Cam"
SettingsINI = 'apps\\python\\AutoCam\\AutoCam.ini'
HideIcon = 1
verbose = 0

cars = {}
currentId = 0
focusTracking = {} #make a dictionary for tracking who's had focus

#this distances should be in meters, same as the track length
gapBattles = 0.1   #load these values from the INI?
gapFending = 0.75  #
gapFollowing = 2.5 #
gapTrailing = 5.0  #

AutoCamActive = 0
driveCam = 0
allDriversInPits = 0
allDriversFinished = 0

defaultSet = 0 #have we set the default cam yet?
defaultCamera = 0 #drive cam?
setCamera = 0     #last specified camera

backgroundOpacity =  0.5
drawBorderVar = 0
windowx = 100
windowy = 100
scale_mult = 1.0

skipDrivers = ["Esotic_Streaming"] #these should be the announcers/streamers
preferredDrivers = []
driverSwitchDelay = 13
quallySwitchDelay = 7

cameraSwitching = {}
cameraDelay = {}
cameraSwitchDelay = 10
cameraSwitchTimer = 0
cameraSwitchingEnabled = 1
driverSwitchingEnabled = 1

dic = {}
dicCars = {}
dicKMH = {}
dicPitEntry = {}

pitCameraSwitching = {"Guess1":0,"Guess2":1,"Guess3":2,"Guess4":4}
pitCameraDelay =     {"Delay1":5,"Delay2":5,"Delay3":5,"Delay4":5}

firstLapSwitching = {"Guess1":3}
firstLapDelay =     {"Delay1":15}

deltasIgnore = [-30.0, 0, 30.0]
lastFocusSwitch = 0
cmExtensions = 0
serverName = ""
serverIP = ""

key_listener = 0   #the listener for hotkeys
lastPreferred = 0
countdownFocusSwitch = 10.0
offPaceCar = -1
minPitKMH = 60.0
maxPitKMH = 85.0
clearPitKMH = 5.0
offPaceSwitchDelay = 120.0
minSwitchDelay = 5.0
defaultPitCam = 0
defaultOffPaceCam = 3
#lastOffPaceCar = -1
strTimestamp = ''

def ConsoleLog(message):
    now = time.clock()
    ac.console("AutoCam(%s): %s"%(strTimestamp, message))
    ac.log("AutoCam(%s): %s"%(strTimestamp, message))
    #ac.console("AutoCam: " + message)
    #ac.log("AutoCam: " + message)            

##############################################################################

import AppCom
if True: # __name__ == "__main__":
    AppCom.initialize()
    ConsoleLog("AppCom Initialized")
else:
    ConsoleLog("AppCom NOT Initialized")
    
order = ''
oldorder = ''

##############################################################################

def acMain(ac_version):
    global camWindow, btnToggle, lblInfo, cmExtensions, serverName, serverIP
    global strTimestamp

    try:    
        strTimestamp = "%0.4f"%(time.clock())
        #backup this file to maintain a "last working copy"
        src = 'apps/python/AutoCam/AutoCam.py'
        dst = 'apps/python/AutoCam/backup/AutoCam.py'
        copyfile(src, dst)

        serverName = ac.getServerName()
        serverIP = ac.getServerIP()
        
        ConsoleLog("ServerName = %s"%(serverName))
        ConsoleLog("ServerIP = %s"%(serverIP))

        #read all relevant INIs
        serverINI = "apps\\python\\AutoCam\\" + serverIP.replace(".", "_") + ".ini"
        if serverIP == "":
            serverINI = "apps\\python\\AutoCam\\127_0_0_1_ini"

        #default INI
        ReadSettings(SettingsINI)
        #IP Specific INI
        ReadSettings(serverINI)    
        #Read Pit Entry Path - we are not doing this for now
        #loadPitEntryToDict()
        
        #read the cars specific camera options
        ReadCarCameras()
        
        #ConsoleLog("acsys.CM.Cockpit = %d"%(acsys.CM.Cockpit))
        #ConsoleLog("acsys.CM.Car = %d"%(acsys.CM.Car))
        #ConsoleLog("acsys.CM.Drivable = %d"%(acsys.CM.Drivable))
        #ConsoleLog("acsys.CM.Track = %d"%(acsys.CM.Track))
        #ConsoleLog("acsys.CM.Helicopter = %d"%(acsys.CM.Helicopter))
        #ConsoleLog("acsys.CM.OnBoardFree = %d"%(acsys.CM.OnBoardFree))
        #ConsoleLog("acsys.CM.Free = %d"%(acsys.CM.Free))
        #ConsoleLog("acsys.CM.Random = %d"%(acsys.CM.Random))
        #ConsoleLog("acsys.CM.ImageGeneratorCamera = %d"%(acsys.CM.ImageGeneratorCamera))
        #ConsoleLog("acsys.CM.Start = %d"%(acsys.CM.Start))
    
        #camWindow = ac.newApp("AutoCamera")
        #tmpInt = ac.newApp("TESTING WINDOW2")
        #ac.setSize(tmpInt, 200, 100)
        #ConsoleLog("App ID = %d"%(tmpInt))
        #tmpInt = ac.newApp("Auto Cam TESTING")
        #ac.setSize(tmpInt, 200, 100)
        #ConsoleLog("App ID = %d"%(tmpInt))
        camWindow = ac.newApp("Auto Cam")
        ac.setSize(camWindow, windowx, windowy)
        ConsoleLog("App ID = %d"%(camWindow))
        if HideIcon == 1:
            ac.setIconPosition(camWindow, 0, -9000)

        #ac.setSize(camWindow,200, 100)
        #ConsoleLog("camWindow = %d"%(camWindow))
        ac.drawBorder(camWindow,0)
        ac.setBackgroundOpacity(camWindow,0.5)
        #ac.setTitle(camWindow, windowTitle)
        
        #do we need to know when it's visible?
        #ac.addRenderCallback(camWindow , onFormRender)

        btnToggle = ac.addButton(camWindow, "On")
        if AutoCamActive == 0:
            ac.setText(btnToggle, "Off")
        ac.setPosition(btnToggle, 5, 25)
        ac.setSize(btnToggle, 80, 25)
        ac.setFontSize(btnToggle, 16)
        ac.addOnClickedListener(btnToggle, onToggle)

        #checkboxes to enable/disable the app itself as well as the various camera modes?
        
        #lblInfo = ac.addLabel(camWindow, "");
        #ac.setPosition(lblInfo, 5, 65)
        #ac.setSize(lblInfo, 80, 25)
        #ac.setFontSize(lblInfo, 12)
    
        InitCars()
        ConsoleLog("acMain finished")
        
        cmExtensions = 0
        try:
            camFOV = ac.ext_getCameraFov()        
            cmExtensions = 1
            ConsoleLog("using cm extensions")
        except:
            ConsoleLog("no cm extensions")
            
        #if this code does not throw an error then extension are available
        
        #should we also check the shader patch version number?
        #cmExtensions = 1
        #ConsoleLog("Shader Patch extensions are available")

        key_listener = threading.Thread(target=listen_key)
        key_listener.daemon = True
        key_listener.start()
        
        ConsoleLog("Returning from acMain")
        return "AutoCam"

    except Exception as e:
        ConsoleLog("AutoCam::acMain() %s" % e)
        #if cmExtensions == 0:
        #    ConsoleLog("Shader Patch extensions are NOT available")    
        

def ReadSettings(INI_File):
    global HideIcon, backgroundOpacity, drawBorderVar
    global windowx, windowy, scale_mult, skipDrivers
    global AutoCamActive, driverSwitchDelay, defaultCamera, cameraSwitchDelay
    global verbose, cameraSwitchingEnabled, driverSwitchingEnabled
    global pitCameraDelay, pitCameraSwitching, preferredDrivers
    global firstLapSwitching, firstLapDelay
    
    try:
        if os.path.isfile(INI_File):
            ConsoleLog("ReadSettings from %s"%(INI_File))
            section = 'SETTINGS'
            SettingsConfig = configparser.ConfigParser()
            SettingsConfig.read(INI_File)
            boolWriteSettings = False #we aren't managing this yet
                     
                
            #from datetime import date
            tdate = datetime.date.today()
            DAY = calendar.day_name[tdate.weekday()]

            #hard code this for testing
            #DAY = "Thursday"
            
            if SettingsConfig.has_option(section, DAY):  
                ConsoleLog("Loading skipDrivers for %s"%(DAY))
                skipDrivers = SettingsConfig.get(section, DAY).split("|") #in the python
            elif SettingsConfig.has_option(section, 'skipDrivers'): 
                ConsoleLog("Loading skipDrivers")
                skipDrivers = SettingsConfig.get(section, 'skipDrivers').split("|") #in the python

            for strDriver in skipDrivers:
                ConsoleLog("Skipping %s"%(strDriver))

            #preferredDrivers
            if SettingsConfig.has_option(section, 'preferredDrivers'): 
                ConsoleLog("Loading preferredDrivers")
                preferredDrivers = SettingsConfig.get(section, 'preferredDrivers').split("|")

            for strDriver in skipDrivers:
                ConsoleLog("Preferred %s"%(strDriver))
                
            #driverSwitchDelay
            if SettingsConfig.has_option(section, 'driverSwitchDelay'):  
                driverSwitchDelay = SettingsConfig.getint(section, 'driverSwitchDelay')    
            else:
                ConsoleLog("driverSwitchDelay not found")
                boolWriteSettings = True

            ConsoleLog("driverSwitchDelay = %d"%(driverSwitchDelay))

            #verbose
            if SettingsConfig.has_option(section, 'verbose'):  
                verbose = SettingsConfig.getint(section, 'verbose')    
            else:
                ConsoleLog("verbose not found")
                boolWriteSettings = True
                
            #cameraSwitchDelay
            if SettingsConfig.has_option(section, 'cameraSwitchDelay'):  
                cameraSwitchDelay = SettingsConfig.getint(section, 'cameraSwitchDelay')    
            else:
                ConsoleLog("cameraSwitchDelay not found")
                boolWriteSettings = True
                
            intGuess = 1
            #cameraSwitching
            if SettingsConfig.has_option(section, 'cameraSwitching'):  
                switchingTemp = SettingsConfig.get(section, 'cameraSwitching').split("|")
                
                for strCamera in switchingTemp:
                    cam, usage, delay = strCamera.split("^")
                    for i in range(0, int(usage)):
                        cameraSwitching["Guess%d"%(intGuess)] = int(cam)
                        cameraDelay["Delay%d"%(intGuess)] = int(delay)
                        if verbose == 1:
                            ConsoleLog("Camera Guess%d = %d"%(intGuess, cameraSwitching["Guess%d"%(intGuess)]))
                            ConsoleLog("Camera Delay%d = %d"%(intGuess, cameraDelay["Delay%d"%(intGuess)]))
                        intGuess = intGuess + 1
                
            else:
                ConsoleLog("cameraSwitching not found")
                boolWriteSettings = True


            intGuess = 1
            #pitCameraSwitching
            if SettingsConfig.has_option(section, 'pitCameraSwitching'):  
                switchingTemp = SettingsConfig.get(section, 'pitCameraSwitching').split("|")
                
                for strCamera in switchingTemp:
                    cam, usage, delay = strCamera.split("^")
                    for i in range(0, int(usage)):
                        pitCameraSwitching["Guess%d"%(intGuess)] = int(cam)
                        pitCameraDelay["Delay%d"%(intGuess)] = int(delay)
                        if verbose == 1:
                            ConsoleLog("pitCamera Guess%d = %d"%(intGuess, pitCameraSwitching["Guess%d"%(intGuess)]))
                            ConsoleLog("pitCamera Delay%d = %d"%(intGuess, pitCameraDelay["Delay%d"%(intGuess)]))
                        intGuess = intGuess + 1
                
            else:
                ConsoleLog("pitCameraSwitching not found")
                boolWriteSettings = True


            intGuess = 1
            #firstLapSwitching
            if SettingsConfig.has_option(section, 'firstLapSwitching'):  
                switchingTemp = SettingsConfig.get(section, 'firstLapSwitching').split("|")
                
                for strCamera in switchingTemp:
                    cam, usage, delay = strCamera.split("^")
                    for i in range(0, int(usage)):
                        firstLapSwitching["Guess%d"%(intGuess)] = int(cam)
                        firstLapDelay["Delay%d"%(intGuess)] = int(delay)
                        if verbose == 1:
                            ConsoleLog("firstLap Guess%d = %d"%(intGuess, firstLapSwitching["Guess%d"%(intGuess)]))
                            ConsoleLog("firstLap Delay%d = %d"%(intGuess, firstLapDelay["Delay%d"%(intGuess)]))
                        intGuess = intGuess + 1
                
            else:
                ConsoleLog("firstLapSwitching not found")
                boolWriteSettings = True
                
                
                
            #cameraSwitchingEnabled
            if SettingsConfig.has_option(section, 'cameraSwitchingEnabled'):  
                cameraSwitchingEnabled = SettingsConfig.getint(section, 'cameraSwitchingEnabled')    
            else:
                ConsoleLog("cameraSwitchingEnabled not found")
                boolWriteSettings = True

            ConsoleLog("cameraSwitchingEnabled = %d"%(cameraSwitchingEnabled))
                
            #driverSwitchingEnabled
            if SettingsConfig.has_option(section, 'driverSwitchingEnabled'):  
                driverSwitchingEnabled = SettingsConfig.getint(section, 'driverSwitchingEnabled')    
            else:
                ConsoleLog("driverSwitchingEnabled not found")
                boolWriteSettings = True
                
            ConsoleLog("driverSwitchingEnabled = %d"%(driverSwitchingEnabled))
                
            #AutoCamActive
            if SettingsConfig.has_option(section, 'AutoCamActive'):  
                AutoCamActive = SettingsConfig.getint(section, 'AutoCamActive')    
            else:
                ConsoleLog("AutoCamActive not found")
                boolWriteSettings = True

            #defaultCamera
            if SettingsConfig.has_option(section, 'defaultCamera'):  
                defaultCamera = SettingsConfig.getint(section, 'defaultCamera')
            else:
                ConsoleLog("defaultCamera not found")
                boolWriteSettings = True
            
            ConsoleLog("defaultCamera = %d"%(defaultCamera))
            
            if SettingsConfig.has_option(section, 'HideIcon'):  
                HideIcon = SettingsConfig.getint(section, 'HideIcon')    
            else:
                ConsoleLog("HideIcon not found")
                boolWriteSettings = True
                
            if SettingsConfig.has_option(section, 'AppWidth'):  
                windowx = SettingsConfig.getint(section, 'AppWidth')    
            else:
                ConsoleLog("AppWidth not found")
                boolWriteSettings = True
                
            #this sets the aspect for the window
            #windowy = windowx * 0.4181818181818182
            #windowx is 110 by default, so this sets the multiplier for all screen elements
            #scale_mult = windowx/110
                
            #override these values? per car?
            if SettingsConfig.has_option(section, 'AppHeight'):  
                windowy = SettingsConfig.getint(section, 'AppHeight')
                
            #if SettingsConfig.has_option(section, 'FontScale'):  
            #    scale_mult = SettingsConfig.getfloat(section, 'FontScale')    
            

            #backgroundOpacity
            if SettingsConfig.has_option(section, 'backgroundOpacity'):  
                backgroundOpacity = SettingsConfig.getfloat(section, 'backgroundOpacity')    
            else:
                ConsoleLog("backgroundOpacity not found")
                boolWriteSettings = True

            #drawBorderVar
            if SettingsConfig.has_option(section, 'drawBorder'):  
                drawBorderVar = SettingsConfig.getint(section, 'drawBorder')    
            else:
                ConsoleLog("drawBorder not found")
                boolWriteSettings = True
        
            #we aren't doing this for now    
            #if False: # boolWriteSettings == True and INI_File == SettingsINI:
            #    ac.console("AutoCam new settings found, writing new AutoCam.ini")
            #    WriteSettings()

        else:
            ConsoleLog("AutoCam Unable to read %s"%(INI_File))
            #if INI_File == SettingsINI:
            #    ConsoleLog("AutoCam Error reading %s, creating new one"%(INI_File))
            #    WriteSettings()

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ac.console('AutoCam ReadSettings Error (logged to file)')
        ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))    
    
    
def ReadCarCameras():
    
    try:
        INI_File = 'apps\\python\\AutoCam\\carCameras.ini'
        if os.path.isfile(INI_File):
            ConsoleLog("ReadCarCameras from %s"%(INI_File))
            section = 'SETTINGS'
            SettingsConfig = configparser.ConfigParser()
            SettingsConfig.read(INI_File)
            
            for carId in range(0, ac.getCarsCount(),1):
                carName = ac.getCarName(carId)
                carCamCount = ac.getCameraCarCount(carId)
                ConsoleLog("carName = %s, carCamCount = %d"%(carName, carCamCount))
            
                if carCamCount > 0:
                    bWrite = False
                    if not SettingsConfig.has_option(section, carName):                        
                        bWrite = True
                        if verbose == 1:
                            ConsoleLog("%s not found in %s"%(carName, INI_File))
                    else:
                        switchingTemp = SettingsConfig.get(section, carName)
                        if switchingTemp == "":
                            bWrite = True
                            
                    if bWrite == True:
                        ConsoleLog("Writing options for %s to %s"%(carName, INI_File))
                        #write this cars string to file and create defaults?
                        strCameras = ""
                        for i in range(0, carCamCount):
                            if strCameras == "":
                                strCameras = "%d^1"%(i)
                            else:
                                strCameras = "%s|%d^1"%(strCameras, i)

                        SettingsConfig.set(section,carName,'%s'%strCameras)                    
        
                        with open(INI_File, 'w') as configfile:
                            configfile.write(';for each car there should be one line' + '\n')
                            configfile.write(';each car camera has a number and a weight for how often to use it' + '\n')
                
                            SettingsConfig.write(configfile)
                
                if SettingsConfig.has_option(section, carName) and carCamCount > 0:
                    ConsoleLog("Found %s in %s"%(carName, INI_File))
                    if not carName in dicCars:
                        ConsoleLog("Reading Car Camera options for %s"%(carName))
                        dicCars[carName] = {} #create an empty dictionary for this car
                        
                        #read the car cameras info from the INI
                        intGuess = 1
                        #cameraSwitching
                        switchingTemp = SettingsConfig.get(section, carName)
                        
                        if not switchingTemp == "":
                            switchingTemp = switchingTemp.split("|")
                            
                            for strCamera in switchingTemp:
                                cam, usage = strCamera.split("^")
                                cam = int(cam)
                                if cam < carCamCount:
                                    for i in range(0, int(usage)):
                                        dicCars[carName]["Guess%d"%(intGuess)] = cam
                                        if verbose == 1:
                                            ConsoleLog("Car Cam Guess%d = %d"%(intGuess, dicCars[carName]["Guess%d"%(intGuess)]))
                                        intGuess = intGuess + 1                
                                else:
                                    ConsoleLog("cam %d > carCamCount - 1 (%d)"%(cam, carCamCount - 1))
                        else:
                            ConsoleLog("carCamera options for %s were empty"%(carName))
                    else:
                        ConsoleLog("Car %s already found in dicCars"%(carName))
                else:
                    ConsoleLog("Car %s NOT FOUND"%(carName))
                
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ac.console('AutoCam ReadCars Error (logged to file)')
        ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))    
        
def onToggle(*args):
    global driveCam, AutoCamActive

    #class CM:Cockpit,Car,Drivable,Track,Helicopter,OnBoardFree,Free,Random,ImageGeneratorCamera,Start = range(10)
    #ac.setCameraMode(<INFO_IDENTIFIER>)
    #ac.getCameraMode()
    #ac.isCameraOnBoard(<CAR_ID>)
    #connect this to a spinner for testing?
    #ac.setCameraCar(<CAMERA_ID>,<CAR_ID>) #sets the F6 camera index (absolute or relative?)
    #this would be the max spinner value
    #ac.getCameraCarCount(<CAR_ID>) #number of F6 cameras
    #ac.focusCar(<CAR_ID>)
    #ac.getFocusedCar()
    
    #CM/SP extensions
    #camFOV = ac.ext_getCameraFov()
    #ac.ext_setCameraFov
    #ac.ext_getCameraMatrix
    #ac.ext_getCameraProj
    #ac.ext_getCameraView
    #ext_chaserCameraDebugText
    #WorldPosition = ac.ext_getCameraPos()
    #ac.ext_getTrackCamerasNumber() #how many different sets of track cameras are there? TV1, TV2, Static would be 3
    #ac.ext_getCurrentTrackCamera() #which track camera set is active
    #ac.ext_setCurrentTrackCamera() #make a set of track cameras active
    #ac.ext_getCurrentCamera()      #
    #ac.ext_setCurrentCamera()
    #ac.ext_getCurrentDrivableCamera()
    #ac.ext_setCurrentDrivableCamera()
    
    if AutoCamActive:
        #we'll return to the "driving mode"
        #ac.setCameraMode(driveCam)
        #ConsoleLog("Setting Focus to Car 0")
        #ac.focusCar(0)
        ac.setText(btnToggle, "Off")
        AutoCamActive = 0
    else:
        #we start the Action mode
        #driveCam = ac.getCameraMode()
        #ConsoleLog("Setting camera to Random")
        #ac.setCameraMode(3) # acsys.CM.Random)
        ac.setText(btnToggle, "On")
        AutoCamActive = 1
        
    ConsoleLog("AutoCamActive = %d"%(AutoCamActive))

def acShutdown(*args):
    ConsoleLog("AutoCam::acShutdown")
    #this code is wrong, ac.removeItem is for ListBoxes
    #ac.removeItem(camWindow)

    
def getPosition(car):
    tmpKey = "APPS:BROADCAST APP"
    if order == "": #not tmpKey in dicPython:
        #ConsoleLog("returning 100 getCarRealTimeLeaderboardPosition for dic[%s]"%(tmpKey))
        return ac.getCarRealTimeLeaderboardPosition(car)
    else:
        tmpKey = "Car%dPosition"%(car) #getPosition
        if tmpKey in dic:
            #ConsoleLog("dic[%s] = %s"%(tmpKey, dic[tmpKey]))
            return int(dic[tmpKey])
        else:
            #ConsoleLog("returning 200 getCarRealTimeLeaderboardPosition for dic[%s]"%(tmpKey))
            return ac.getCarRealTimeLeaderboardPosition(car)
    
def setPositions():
    #ConsoleLog("setPositions subroutine")
    
    #we can return 0 to skip all this logic
    #return 0
    tmpKey = "APPS:BROADCAST APP"
    if order == "": # not tmpKey in dicPython:
        #ConsoleLog("not using setPositions logic")
        return False
    else: #pull the driver order directly from BA textOrder?
        #do we know the value for the BA data share control? ac.sendChatMessage(text) doesn't work offline
        #ConsoleLog("%s"%(ac.getText(displayText)))
        if True:
            #1st|2nd|3rd|4th|5th|6th|etc
            #18|3|25|13|20|24|2|7|12|4|6|1|19|16|17|5|8|9|10|11|14|15|21|22|23|
            if not order == "":
                #ConsoleLog("Order = %s"%(order))
                orderStrings = order.split("|")
                position = 0
                for car in orderStrings:
                    if not car == "":
                        dic["Car%dPosition"%(int(car))] = position #setPositions
                        #ConsoleLog("Driver %d in position %d named %s"%(int(car), position + 1, safeName(int(car))))
                        position = position + 1
                        
                return True
            else:
                ConsoleLog("unable to set order")
                return False    
    
#app does not need to be visible
def acUpdate(deltaT):
    global strTimestamp
    
    strTimestamp = "%0.4f"%(time.clock())

#############################################################################################

    global order, oldorder

    tmpKey = "APPS:BROADCAST APP"
    if not AppCom.runningorder == "" : #tmpKey in dicPython:
        order = AppCom.runningorder
        if order != oldorder:
            oldorder = order
            setPositions()
            #ConsoleLog('order: ' + order)

#############################################################################################

    autoCam()
    
#def onFormRender(deltaT):    
#    try:
#        ConsoleLog("form is being rendered")
#    except Exception as e:
#        ConsoleLog("onFormRender() %s" % e)

def canSwitch(carID):
    # and ((not ac.getCarState(carID, acsys.CS.RaceFinished) == 1 or ac.getCarState(0, acsys.CS.LapTime) < 5000.0) or allDriversFinished):
    if ((not ac.isCarInPitlane(carID)) or (ac.isCarInPitlane(carID) and ac.getCarState(carID,acsys.CS.SpeedKMH) > minPitKMH) or (allDriversInPits == 1)) and not safeName(carID) in skipDrivers and ac.isConnected(carID) and ((not ac.getCarState(carID, acsys.CS.RaceFinished) == 1 or ac.getCarState(carID, acsys.CS.LapTime) < 5000.0) or allDriversFinished):
        if len(preferredDrivers) > 0:
            if not safeName(carID) in preferredDrivers:
                #if any preferrredDrivers connectected then return False
                for carId in range(0,ac.getCarsCount()-1,1):
                    if safeName(carId) in preferredDrivers and ac.isConnected(carId):
                        return False
        return True
    else:
        return False

def autoCam():
    global currentId, lastFocusSwitch, defaultSet, cameraSwitchTimer, cameraSwitchDelay
    global setCamera, lastPreferred, countdownFocusSwitch, offPaceCar #, lastOffPaceCar
    global allDriversFinished, allDriversInPits

    #ac.setBackgroundOpacity(camWindow, 0)
    #ac.setIconPosition(camWindow, -7000, -3000)
    #ac.setTitle(camWindow, "")

    #ConsoleLog("Starting autoCam()")
    
    suffix = ""
    if cameraSwitchingEnabled == 1:
        suffix = "C"
    else:
        suffix = "c"
    
    if driverSwitchingEnabled == 1:
        suffix = suffix + "D"
    else:
        suffix = suffix + "d"
    
    ac.setTitle(camWindow, "AutoCam " + suffix)
    
    sim_info_obj = AutoCam_sim_info.AutoCam_SimInfo()
    bIsQually = False
    if sim_info_obj.graphics.session == 1:
        bIsQually = True
    bIsPractice = False
    if sim_info_obj.graphics.session == 0:
        bIsPractice = True
    bIsRace = False
    if sim_info_obj.graphics.session == 2:
        bIsRace = True    
    
    if (sim_info_obj.graphics.status == 1):
        #ConsoleLog("Session = %d, replayTimeMultiplier = %0.2f"%(sim_info_obj.graphics.session, sim_info_obj.graphics.replayTimeMultiplier))
        #assume all replays are races?
        bIsPractice = False
        bIsQually = False
        bIsRace = True
    
    totalLaps = sim_info_obj.graphics.numberOfLaps    
    trackLength = ac.getTrackLength(0)
    totalDistance = totalLaps * trackLength
    carFound = -1
    driverSwitched = 0
    
    try:
        if AutoCamActive:
            #DRIVER/CAR SWITCHING
            #first we'll iterate the drivers and check wether they need updates. Yes,
            #only 1 car per frame
            #Completely Remove the AutoCamCar library?  Recode it?            
            #we need a way to enable/disable driver switching in the INI?
            if driverSwitchingEnabled == 1: # True:
                #perfMeter = ac.getCarState(ac.getFocusedCar(), acsys.CS.PerformanceMeter)
                #ConsoleLog("Perf Meter for Car %d is %0.3f"%(ac.getFocusedCar(), perfMeter))
                #can we optionally use new logic or old logic?
                #check for the car with the smallest/lowest perfDelta during qually?
                now = time.clock()                
                
                #do all the per car logic here
                allDriversInPits = 1
                allDriversFinished = 1
                anyDriverFinished = 0
                try:
                    for car in range(0,ac.getCarsCount() - 1):
                        if ac.isConnected(car):
                            if ac.isCarInPitlane(car) == 0:
                                allDriversInPits = 0
                            if ac.getCarState(car, acsys.CS.RaceFinished) == 0:
                                allDriversFinished = 0
                            else:
                                anyDriverFinished = 1
                            
                            inPits = ac.isCarInPitlane(car)
                            lapCount = ac.getCarState(car, acsys.CS.LapCount)
                            #lapsSincePit = 0
                            tmpKey = "Car%dLastPitLap"%(car)
                            if tmpKey in dic:
                                if inPits == 1 and not lapCount == dic[tmpKey]:
                                    #lapsSincePit = lapCount - dic[tmpKey]
                                    dic[tmpKey] = lapCount
                                    #how many laps since the last pit?
                            else:
                                dic[tmpKey] = lapCount
                            
                except:
                    pass
                        
                #logic is incorrectly quick switching after setting carFound
                
                if (bIsQually == True): # and now - lastFocusSwitch > quallySwitchDelay:
                    #ConsoleLog("Checking perfDelta Info")
                    lowestPerfDelta = 0.0
                    highestPoT = 0.0
                    try:
                        for car in range(0,ac.getCarsCount() - 1):
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                carPerfDelta = ac.getCarState(car, acsys.CS.PerformanceMeter)
                                #how do we focus on cars that are up towards the end of a lap?
                                if not round(carPerfDelta, 3) in deltasIgnore:
                                    carPoT = ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                                    if carPerfDelta < 0.0 and carPoT > highestPoT:
                                        #ConsoleLog("found low perf delta of %0.3f for car %d at PoT %0.3f"%(carPerfDelta, car, carPoT))
                                        highestPoT = carPoT
                                        carFound = car
                                    #elif carPerfDelta < lowestPerfDelta:
                                    #    ConsoleLog("found lower perf delta of %0.3f for car %d"%(carPerfDelta, car))
                                    #    lowestPerfDelta = carPerfDelta
                                    #    carFound = car
                    except:
                        pass
                
                
                #overrides for a race session?
                        
                #Race Countdown Logic
                if bIsRace == True and ac.getCarState(0, acsys.CS.LapTime) == 0.0 and carFound < 0:
                    #ConsoleLog("running the countdown logic")
                    #run the countdown logic?
                    if now - lastFocusSwitch > countdownFocusSwitch:
                        ConsoleLog("running the countdown logic, focus driver is %s"%(safeName(ac.getFocusedCar())))
                        #get the ID of the car in the next next position
                        currentPosition = getPosition(ac.getFocusedCar())
                        for car in range(0,ac.getCarsCount() - 1):
                            countdownFocusSwitch = 8.0
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                if getPosition(car) > currentPosition:
                                    if carFound >= 0:
                                        if getPosition(car) < getPosition(carFound):
                                            #ConsoleLog("Setting car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                            carFound = car                                        
                                    else: 
                                        #ConsoleLog("Setting car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                        carFound = car
                        if carFound < 0:
                            #force driver to lowest position
                            for car in range(0,ac.getCarsCount() - 1):
                                if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                    if carFound >= 0:
                                        if getPosition(car) < getPosition(carFound):
                                            ConsoleLog("Resetting car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                            carFound = car
                                            countdownFocusSwitch = 10.0
                                    else: 
                                        ConsoleLog("Initializing car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                        carFound = car
                                        countdownFocusSwitch = 10.0
                                        
                if ac.getCarState(0, acsys.CS.LapTime) > 0.0 and anyDriverFinished == 0: #KMH and Pit Lane tracking
                    for car in range(0,ac.getCarsCount() - 1):
                        if ac.isConnected(car) and (not ac.isCarInPitlane(car) or ac.getCarState(car,acsys.CS.SpeedKMH) > minPitKMH):
                            carName = ac.getCarName(car)
                            currPoT = ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                            speedKMH = ac.getCarState(car,acsys.CS.SpeedKMH)
                            lapCount = ac.getCarState(car, acsys.CS.LapCount)
                            raceFinished = ac.getCarState(car, acsys.CS.RaceFinished)
                            driverName = safeName(car)

                            tmpKey = "Car%dLastPitLap"%(car)
                            lapsSincePit = 0
                            if tmpKey in dic:
                                lapsSincePit = lapCount - dic[tmpKey]
                            
                            if speedKMH < 400.0:
                                #keyMaxKMH = "Car%sKMHMax%0.3f"%(carName,currPoT)
                                #if keyMaxKMH in dicKMH:
                                #    dicKMH[keyMaxKMH] = max(keyMaxKMH, speedKMH)
                                keyPoTKMH = "Car%sKMH%0.3f"%(carName,currPoT)
                                if keyPoTKMH in dicKMH:
                                    if dicKMH[keyPoTKMH] > 350.0:
                                        ConsoleLog("dicKMH[%s] = %d"%(keyPoTKMH, dicKMH[keyPoTKMH]))
                                        
                                    #current speed has to be greater than X% of current speed
                                    #only set the KMH data during the first hotlap of a qually session?
                                    if speedKMH > dicKMH[keyPoTKMH] * 0.5 and bIsQually and lapsSincePit == 1:
                                        #ConsoleLog("using %s on lap %d of qually stint to update KMH data"%(driverName, lapsSincePit))
                                        dicKMH[keyPoTKMH] = ((dicKMH[keyPoTKMH] * 9.0) + speedKMH) / 10.0
                                    if speedKMH < (dicKMH[keyPoTKMH] * 0.5) and lapCount > 0 and bIsRace and offPaceCar < 0 and raceFinished == 0 and now - lastFocusSwitch > minSwitchDelay:
                                        tmpKey = "Car%dOffPaceTime"%(car)
                                        if tmpKey in dic:
                                            if now - dic[tmpKey] > offPaceSwitchDelay:
                                                ConsoleLog("resetting offPaceCar = %d for %s; %d|%d"%(car, driverName, speedKMH, dicKMH[keyPoTKMH]))
                                                offPaceCar = car
                                                dic[tmpKey] = now                                            
                                        else:
                                            ConsoleLog("setting offPaceCar = %d for %s; %d|%d"%(car, driverName, speedKMH, dicKMH[keyPoTKMH]))
                                            offPaceCar = car
                                            dic[tmpKey] = now                                            
                                elif bIsQually and lapsSincePit == 1:
                                    #ConsoleLog("using %s on lap %d of qually stint to set KMH data"%(driverName, lapsSincePit))
                                    dicKMH[keyPoTKMH] = speedKMH
                                    
                                    
                                #CHECKING FOR CARS DRIVING TO OR FROM THE PIT BOX IN PIT LANE
                                if offPaceCar < 0 and bIsRace and ac.isCarInPitlane(car) and ac.getCarState(car,acsys.CS.SpeedKMH) > minPitKMH and ac.getCarState(car,acsys.CS.SpeedKMH) < maxPitKMH and now - lastFocusSwitch > minSwitchDelay: # and speedKMH < 90.0: # and lapCount > 0:\
                                    #ConsoleLog("Driver %s driving in pit lane driving %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                                    tmpKey = "Car%dOffPaceTime"%(car)
                                    if tmpKey in dic:
                                        if now - dic[tmpKey] > offPaceSwitchDelay:
                                            ConsoleLog("Driver %s driving in pit lane driving %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                                            offPaceCar = car
                                            setCamera = 2
                                            dic[tmpKey] = now
                                    else:
                                        ConsoleLog("Driver %s driving in pit lane driving %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                                        offPaceCar = car
                                        setCamera = 2
                                        dic[tmpKey] = now
                                    
                                            
                                    #x,y,z = dicPitEntry[strKey]
                                    #dicPitEntry[key] = (x,y,z)
                                    if False: #WE ARE NOT DOING THIS FOR NOW, TRYING OTHER LOGIC INSTEAD
                                        strKey = "PoT%0.4f"%(currPoT)
                                        if strKey in dicPitEntry:
                                            #ConsoleLog("strKey %s in dicPitEntry"%(strKey))
                                            wpX,wpY,wpZ = ac.getCarState(car,acsys.CS.WorldPosition)
                                            strX, strY, strZ = dicPitEntry[strKey]
                                            pwpX = float(strX)
                                            pwpY = float(strY)
                                            pwpZ = float(strZ)
                                            #pwpX, pwpY, pwpZ = dicPitEntry[strKey]
                                            differenceX = wpX - pwpX	
                                            differenceY = wpY - pwpY
                                            differenceZ = wpZ - pwpZ
                                            distance = math.sqrt(math.pow(differenceX,2) + math.pow(differenceY,2) + math.pow(differenceZ,2))
                                            #ConsoleLog("Driver %s distance = %0.2f"%(safeName(car), distance))
                                            if distance < 5.0:
                                                ConsoleLog("Driver %s driving towards pit entry"%(safeName(car)))
                                                offPaceCar = car
                                                setCamera = 2
                                    
                                    
                                #ac.console("avgKMH for %s at %0.3f = %0.1f"%(carName, currPoT, dicKMH[keyPoTKMH]))
                        #else: #THIS IS NOT RELIABLE
                        #    #clear this value when a driver enteres the pits (get them entering and exiting)
                        #    tmpKey = "Car%dOffPaceTime"%(car)
                        #    if tmpKey in dic and ac.getCarState(car,acsys.CS.SpeedKMH) < clearPitKMH:
                        #        ConsoleLog("Clearing offPace timestamp for %s, %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                        #        del dic[tmpKey]


                if len(preferredDrivers) > 0 and carFound > -1:
                    if not safeName(carFound) in preferredDrivers:
                        ConsoleLog("carFound Driver %s not in peferredDrivers"%(safeName(carFound)))
                        carFound = -1

                        
                #drivers approaching the finish line on the lead lap
                if bIsRace == True and totalLaps > 0 and totalDistance > 0 and now - lastFocusSwitch > 5.0:
                    try:
                        maxDistance = 0.0
                        #raceOver = ac.getCarState(car, acsys.CS.RaceFinished)
                        for car in range(0,ac.getCarsCount() - 1):
                            if ac.isConnected(car) and ac.getCarState(car, acsys.CS.RaceFinished) == 0:
                                carLapCount = ac.getCarState(car, acsys.CS.LapCount)
                                carCurrPoT = ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                                carDistance = (carLapCount + carCurrPoT) * trackLength
                                #if the car is within 400 meters of the finish line on the lead lap
                                if carDistance > totalDistance - 800.0 and carDistance > maxDistance:                                    
                                    maxDistance = carDistance
                                    carFound = car
                                    offPaceCar = -1                           
                                    
                        if carFound >= 0:
                            ConsoleLog("Car closest to finishing set to %s"%(safeName(carFound)))
                    except:
                        pass
                        
                        
                #how to handle the offPaceCar car?
                if offPaceCar >= 0: # and not offPaceCar == lastOffPaceCar:
                    if now - lastFocusSwitch > driverSwitchDelay or (ac.isCarInPitlane(offPaceCar) and (ac.getCarState(offPaceCar,acsys.CS.SpeedKMH) < minPitKMH)):
                        ConsoleLog("Clearing offPaceCar, Driver = %s, InPitLane = %d, KMH = %.2f"%(safeName(offPaceCar), ac.isCarInPitlane(offPaceCar),ac.getCarState(offPaceCar,acsys.CS.SpeedKMH)))
                        offPaceCar = -1
                    elif not offPaceCar == ac.getFocusedCar(): # and not offPaceCar == lastOffPaceCar:
                        ConsoleLog("Switching to offPaceCar Driver %s"%(safeName(offPaceCar)))
                        lastFocusSwitch = now
                        ac.focusCar(offPaceCar)
                        driverSwitched = 1
                        if ac.isCarInPitlane(offPaceCar):
                            setCamera = defaultPitCam
                        else:
                            setCamera = defaultOffPaceCam
                        #lastOffPaceCar = offPaceCar
                        #return
                elif carFound >= 0:
                    if bIsQually == True:
                        if now - lastFocusSwitch > quallySwitchDelay:
                            ConsoleLog("using qually optional logic to switch to %s"%(safeName(carFound)))
                            ac.focusCar(carFound)
                            driverSwitched = 1
                            lastFocusSwitch = now
                        #give the carFound time after it crosses start/finish to continue being focus car
                        if carFound == ac.getFocusedCar():
                            lastFocusSwitch = now
                    else:
                        ConsoleLog("using regular optional logic to switch to %s"%(safeName(carFound)))
                        ac.focusCar(carFound)
                        driverSwitched = 1
                        lastFocusSwitch = now                                                            
                elif (not bIsRace or ac.getCarState(0, acsys.CS.LapTime) > 0.0):
                    #THIS IS THE CURRENT LOGIC
                    cars[currentId].check()
                    currentId = currentId + 1
                    if currentId >= ac.getCarsCount() -1:
                        #after all cars have been checked we'll return to Id=0 and try to remap the cam
                        #ConsoleLog("really need a new car now at %d"%(now))
                        currentId = 0
                        #now = time.clock()
                        if now - lastFocusSwitch > driverSwitchDelay or not canSwitch(ac.getFocusedCar()):
                            if verbose == 1:
                                ConsoleLog("Seeking Next Car: now = %d"%(now))
                            nextCar = cars[0] #mostInteresting?
                            minDistance = 10003
                            for car in cars.values():
                                if (not canSwitch(nextCar.slotId) or not canSwitch(ac.getFocusedCar())) and canSwitch(car.slotId):
                                    nextCar = car
                                    #distance = car.distanceTo(xcar)
                                    #minDistance = distance                            
                                for xcar in cars.values():
                                    distance = car.distanceTo(xcar)
                                    if distance < minDistance and canSwitch(car.slotId):
                                        nextCar = car
                                        minDistance = distance

                            #we'll focus the (probably) most interesting situation now.
                            #ofc. this can't happen too often, otherwise we'll get into flickering and stuff
                            #so let's find the next focus only if the last switch is older than 5 (or whatever) seconds                    
                            if canSwitch(nextCar.slotId) and not ac.getFocusedCar() == nextCar.slotId:
                                #if True: # verbose == 1:
                                ConsoleLog("Setting Focus to Interesting Car %s %d"%(nextCar.driverName, nextCar.slotId))
                                ac.focusCar(nextCar.slotId)
                                driverSwitched = 1
                                lastFocusSwitch = now                        
                                #ac.setText(lblInfo, "#{} {}".format(ac.getCarLeaderboardPosition(nextCar.slotId), nextCar.driverName))
                            #else:
                            #    ConsoleLog("Chose a car we can't switch to")
                        #else: 
                        #    if canSwitch(ac.getFocusedCar()):
                        #        ConsoleLog("current car is acceptable")
                        #    else:
                        #        ConsoleLog("waiting")
                    #else:
                    #    ConsoleLog("checking cars, can't process yet")
                

                if len(preferredDrivers) > 0:
                    if not safeName(ac.getFocusedCar()) in preferredDrivers:
                        for carId in range(0,ac.getCarsCount()-1,1):
                            if safeName(carId) in preferredDrivers and ac.isConnected(carId):
                                ConsoleLog("Forcing Preferred Driver %s"%(safeName(carId)))
                                ac.focusCar(carId)
                                driverSwitched = 1
                                return True
             

            #camera switching code goes here
            if cameraSwitchingEnabled == 1:
                now = time.clock()
                countdownCam = 5
                #if bIsRace and ac.getCarState(0, acsys.CS.LapTime) == 0.0 and not ac.getCameraMode() == countdownCam and (now - cameraSwitchDelay > cameraSwitchTimer):
                if bIsRace and ac.getCarState(0, acsys.CS.LapTime) == 0.0 and ac.isCarInPitlane(0) and not ac.getCameraMode() == countdownCam:
                    #once car 0 is in the pits then switch to the countdown
                    ConsoleLog("Forcing countdownCamera to %d, order is %s"%(countdownCam, order))
                    #force the F5 cam?
                    setCamera = countdownCam
                    if driverSwitchingEnabled == 1:
                        #IS THIS CODE IN THE WRONG LOGIC BLOCK?
                        #force the driver to lowest position?
                        for car in range(0,ac.getCarsCount() - 1):
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                ConsoleLog("Driver %s is in position %d"%(safeName(car), getPosition(car)))
                                if carFound >= 0:
                                    if getPosition(car) < getPosition(carFound):
                                        #ConsoleLog("Resetting car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                        carFound = car
                                        countdownFocusSwitch = 12.0
                                else: 
                                    #ConsoleLog("Initializing car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                    carFound = car
                                    countdownFocusSwitch = 12.0
                        if carFound >= 0:
                            ConsoleLog("Selected Driver %s in position %d"%(safeName(carFound), getPosition(carFound)))
                            ac.focusCar(carFound)
                            driverSwitched = 1
                            lastFocusSwitch = now                        
                    
                    
                if bIsRace and ac.getCarState(0, acsys.CS.LapTime) > 0.0 and ac.getCarState(0, acsys.CS.LapTime) < 1000.0 and ac.getCameraMode() == countdownCam:
                    ConsoleLog("Forcing Camera to %d"%(defaultCamera))
                    #force the F5 cam?
                    setCamera = defaultCamera
                    
            
                if defaultSet == 0:
                    defaultSet = 1
                    ConsoleLog("Setting default camera to %d"%(defaultCamera))
                    ac.setCameraMode(defaultCamera)
                    setCamera = defaultCamera
                    #ConsoleLog("camera set to %d"%(defaultCamera))

                if not ac.getCameraMode() == setCamera:
                    #ConsoleLog("setting camera back to %d"%(setCamera))
                    ac.setCameraMode(setCamera)
                    cameraSwitchTimer = time.clock()

                #how to verify that car in the pits is using a pit lane camera?
                if ac.isCarInPitlane(ac.getFocusedCar()):
                    #ConsoleLog("ac.getFocusedCar() = %d, DriverName = %s"%(ac.getFocusedCar(), safeName(ac.getFocusedCar())))
                    currentCam = ac.getCameraMode()
                    usingPitCam = 0
                    for intGuess in range(1, len(pitCameraSwitching)):
                        #ConsoleLog("GUESS 100")
                        tmpKey = "Guess%d"%(intGuess)
                        if tmpKey in pitCameraSwitching:
                            if currentCam == pitCameraSwitching[tmpKey]:
                                usingPitCam = 1
                                break
                    if usingPitCam == 0:
                        #for when a driver has focus and drives into the pits
                        ConsoleLog("Forcing defaultPitCam %d for %s"%(defaultPitCam, safeName(ac.getFocusedCar())))
                        setCamera = defaultPitCam
                            
                            
                    
                    
                #don't interfere with the countdown timer
                if len(cameraSwitching) > 0 and len(firstLapSwitching) > 0 and (not bIsRace or ac.getCarState(0, acsys.CS.LapTime) > 0.0):
                    now = time.clock()
                    if now - cameraSwitchDelay > cameraSwitchTimer: # or driverSwitched == 1: # or not canSwitch(ac.getFocusedCar()):
                        cameraSwitchTimer = now
                        if ac.isCarInPitlane(ac.getFocusedCar()):
                            #how often to the switch cameras?
                            intGuess = randInRange(1, len(pitCameraSwitching))
                            #ConsoleLog("GUESS 200")
                            tmpKey = "Guess%d"%(intGuess)
                            if tmpKey in pitCameraSwitching:
                                nextCam = pitCameraSwitching[tmpKey]
                                cameraSwitchDelay = pitCameraDelay["Delay%d"%(intGuess)]
                                if verbose == 1:
                                    ConsoleLog("Switching to pit camera %d, cameraSwitchDelay = %d"%(nextCam, cameraSwitchDelay))
                                ac.setCameraMode(nextCam)
                                setCamera = nextCam
                            else:
                                ConsoleLog("Pit Guess%d not found"%(intGuess))                        
                        else:
                            if False:
                                #Dave's old logic
                                #ConsoleLog("GUESS 300")
                                tmpKey = "Guess%d"%(intGuess)
                                if tmpKey in cameraSwitching:
                                    nextCam = cameraSwitching[tmpKey]
                                    cameraSwitchDelay = cameraDelay["Delay%d"%(intGuess)]
                                    if verbose == 1:
                                        ConsoleLog("Switching to camera %d, cameraSwitchDelay = %d"%(nextCam, cameraSwitchDelay))
                                    ac.setCameraMode(nextCam)
                                    setCamera = nextCam
                                else:
                                    ConsoleLog("Guess%d not found"%(intGuess))
                            else:
                                #Jon's adjusted logic
                                #how often to the switch cameras?
                                
                                if ac.getCarState(ac.getFocusedCar(), acsys.CS.LapCount) < 1:
                                    #ConsoleLog("using first lap logic")
                                    intGuess = randInRange(1, len(firstLapSwitching))
                                    #ConsoleLog("GUESS 400")
                                    tmpKey = "Guess%d"%(intGuess)
                                    if tmpKey in firstLapSwitching:
                                        #ConsoleLog("GUESS 400")
                                        nextCam = firstLapSwitching["Guess%d"%(intGuess)]
                                        cameraSwitchDelay = firstLapDelay["Delay%d"%(intGuess)]
                                    else:
                                        ConsoleLog("firstLapSwitching[%s] not found"%(tmpKey))
                                else:                                
                                    #ConsoleLog("using regular logic")
                                    intGuess = randInRange(1, len(cameraSwitching))                                    
                                    #ConsoleLog("GUESS 500")
                                    tmpKey = "Guess%d"%(intGuess)
                                    if tmpKey in cameraSwitching:
                                        nextCam = cameraSwitching["Guess%d"%(intGuess)]
                                        cameraSwitchDelay = cameraDelay["Delay%d"%(intGuess)]
                                    else:
                                        ConsoleLog("cameraSwitching[%s] not found"%(tmpKey))
                                    
                                if True: # tmpKey in cameraSwitching:                        
                                    currentCam = ac.getCameraMode()
                                    
                                    if verbose == 1:
                                        ConsoleLog("Switching to camera %d, cameraSwitchDelay = %d"%(nextCam, cameraSwitchDelay))
                                        
                                    if nextCam == 0 and currentCam == 0:
                                        #ConsoleLog("in next cam - currentcam is set to %d"%(currentCam))
                                        if verbose == 1:
                                            ConsoleLog("in next cam - nextcam is set to %d"%(nextCam))
                                    elif nextCam == 1:
                                        if True:
                                            #we need to pick a random camera from dicCars
                                            #dicCars[carName]
                                            carName = ac.getCarName(currentId)
                                            
                                            #ConsoleLog("searching dicCars[%s]"%(carName))
                                            
                                            intGuess = randInRange(1, len(dicCars[carName]))
                                            #ConsoleLog("GUESS 600")
                                            tmpKey = "Guess%d"%(intGuess)
                                            if verbose == 1:
                                                ConsoleLog("Car Camera tmpkey = %s"%(tmpKey))
                                            if tmpKey in dicCars[carName]:
                                                randomCamInt = dicCars[carName][tmpKey] #    randInRange(0,carCamCount)
                                                ac.setCameraCar(randomCamInt,currentId)                      
                                                setCamera = nextCam
                                                if verbose == 1:
                                                    ConsoleLog("carCamera is set to %d"%(randomCamInt))
                                            else:
                                                ConsoleLog("dicCars[%s][%s] NOT FOUND"%(carName,tmpKey))
                                        else:
                                            carCamCount = ac.getCameraCarCount(currentId)
                                            randomCamInt = randInRange(0,carCamCount)
                                            ac.setCameraCar(randomCamInt,currentId)                      
                                            setCamera = nextCam
                                            if verbose == 1:
                                                ConsoleLog("carCamera is set to %d"%(randomCamInt))
                                    else:
                                        if verbose == 1:
                                            ConsoleLog("in else - nextcam is set to %d"%(nextCam))
                                        ac.setCameraMode(nextCam)
                                        setCamera = nextCam
                                else:
                                    ConsoleLog("Guess%d not found"%(intGuess))



                        
                        
            #else:
            #    ConsoleLog("no camera switching defined")
            
        return True
                
    except Exception as e:
        ConsoleLog("Error: %s" % e)

#I'm assuming we can put this in both .PY files        
def gapBetweenCars(car1, car2):

    #closestCarGap
    car1LapCount = ac.getCarState(car1, acsys.CS.LapCount)
    car1CurrPoT = ac.getCarState(car1,acsys.CS.NormalizedSplinePosition)
    car1Distance = (car1LapCount + car1CurrPoT) * trackLength

    car2LapCount = ac.getCarState(car2, acsys.CS.LapCount)
    car2CurrPoT = ac.getCarState(car2,acsys.CS.NormalizedSplinePosition)
    car2Distance = (car2LapCount + car2CurrPoT) * trackLength
    
    carsGap = abs(car1Distance - car2Distance) / (((ac.getCarState(car1,acsys.CS.SpeedKMH) + ac.getCarState(car2,acsys.CS.SpeedKMH)) / 2) / 3.6)
    
    #ConsoleLog("Cars Gap = %0.2f"%(carsGap))
    
    return carsGap
        
        
def InitCars():
    global cars

    carCount = ac.getCarsCount()

    cars = {}
    for carId in range(0,carCount-1,1):
        cars[carId] = AutoCamCar.AutoCamCar(carId)
        
        #read/create an INI for each car?  how to handle multicar servers?  store F6 options in a dic
        #store each cars car cams options in one file?
        
        
    ConsoleLog("InitCars() done".format(carCount))
    
def getValidFileName(filename):
    ###valid file name characters
    validFilenameChars = "-_() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(c for c in filename if c in validFilenameChars)    
    
def safeName(car):
    validFilenameChars = "-_() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(c for c in ac.getDriverName(car) if c in validFilenameChars)
    
def randInRange(lower, upper):
    if upper >= lower:
        return random.randint(lower, upper)
    else:
        return lower
    
def loadPitEntryToDict():
    global dicPitEntry
    
    bLoaded = False
    
    #ConsoleLog("loadPitEntryToDict called")
    
    fileSource = 'apps/python/AutoCam/PIT_ENTRY/'
    fileSource = fileSource + 'PIT_ENTRY_' + getValidFileName(ac.getTrackName(0)) + getValidFileName(ac.getTrackConfiguration(0)) + ".ini"
    
    if os.path.isfile(fileSource):
        ConsoleLog("Pit Entry Loading %s"%(fileSource))
        dicPitEntry.clear()
        lines = [line.rstrip('\n') for line in open(fileSource)]
        for line in lines:
            #ConsoleLog(line)
            if "," in line:
                try:
                    key, WP = line.split("=")
                    x, y, z = WP.split(",")
                    #ConsoleLog("x = %s, y = %s, z = %s, key = %s"%(x, y, z, key))
                    #the keys are strings
                    dicPitEntry[key] = (x,y,z)
                    bLoaded = True
                except:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    ac.console('loadPitEntryToDict Read Pit_Entry Error (logged to file)')
                    ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    else:
        ConsoleLog("loadPitEntryToDict File NOT FOUND %s"%(fileSource))
    
    return bLoaded        
    
    
def hotkey_CtrlF6():
    global cameraSwitchingEnabled

    #ConsoleLog("Ctrl+F6 hotkey called")
    #toggle camera switching

    if cameraSwitchingEnabled == 0:
        cameraSwitchingEnabled = 1
    else:
        cameraSwitchingEnabled = 0

    ConsoleLog("cameraSwitchingEnabled = %d"%(cameraSwitchingEnabled))
    
    return 1

def hotkey_CtrlF7():
    global driverSwitchingEnabled

    #ConsoleLog("Ctrl+F7 hotkey called")
    #toggle camera switching

    if driverSwitchingEnabled == 0:
        driverSwitchingEnabled = 1
    else:
        driverSwitchingEnabled = 0

    ConsoleLog("driverSwitchingEnabled = %d"%(driverSwitchingEnabled))

    return 1
    
def listen_key():
    byref = ctypes.byref
    user32 = ctypes.windll.user32

    ConsoleLog("Just for Chat HotKey Setup")
    #Modifiers (MOD_SHIFT, MOD_ALT, MOD_CONTROL, MOD_WIN)    
    HOTKEYS = {
        1: (win32con.VK_F6, win32con.MOD_CONTROL),
        2: (win32con.VK_F7, win32con.MOD_CONTROL),
    }

    def handle_CF6():
        hotkey_CtrlF6()

    def handle_CF7():
        hotkey_CtrlF7()

    HOTKEY_ACTIONS = {
        1: handle_CF6,
        2: handle_CF7,
    }

    for id, (vk, modifiers) in HOTKEYS.items():
        user32.RegisterHotKey(None, id, modifiers, vk)

    try:
        msg = wintypes.MSG()
        while user32.GetMessageA(byref(msg), None, 0, 0) != 0:
            if msg.message == win32con.WM_HOTKEY:
                action_to_take = HOTKEY_ACTIONS.get (msg.wParam)
                if action_to_take:
                    action_to_take()
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageA(byref(msg))

    finally:
        for id in HOTKEYS.keys():
            user32.UnregisterHotKey(None, id)
        
    