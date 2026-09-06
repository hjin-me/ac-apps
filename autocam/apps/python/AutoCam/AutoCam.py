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
cameraReason = "" #human-readable reason for the current setCamera

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

#Camera acsys.CM.Cockpit = 0
#Camera acsys.CM.Car = 1
#Camera acsys.CM.Drivable = 2
#Camera acsys.CM.Track = 3
#Camera acsys.CM.Helicopter = 4
#Camera acsys.CM.OnBoardFree = 5
#Camera acsys.CM.Free = 6
#Camera acsys.CM.Random = 7
#Camera acsys.CM.ImageGeneratorCamera = 8
#Camera acsys.CM.Start = 9
pitCameraSwitching = {"Guess1":2,"Guess2":1,"Guess3":0,"Guess4":4} #{"Guess1":0,"Guess2":1,"Guess3":2,"Guess4":4}
pitCameraDelay =     {"Delay1":5,"Delay2":5,"Delay3":5,"Delay4":5} #{"Delay1":5,"Delay2":5,"Delay3":5,"Delay4":5}

firstLapSwitching = {"Guess1":3}
firstLapDelay =     {"Delay1":15}

# Raw schedule strings as loaded, so a Save writes back what the user actually configured
# instead of clobbering their tuning with the hardcoded preset below.
rawCameraSwitching = '3^80^18|0^10^10|1^5^8|4^2^5|7^1^5'
rawFirstLapSwitching = '3^1^10'
rawPitCameraSwitching = '1^1^5|0^1^5|4^1^5'
rawBattleCams = '3^2^10|0^1^10|1^1^10'

battleCamSwitching = {"Guess1":3,"Guess2":0,"Guess3":2,"Guess4":1} #{"Guess1":0,"Guess2":1,"Guess3":2,"Guess4":4}
battleCamDelay =     {"Delay1":10,"Delay2":10,"Delay3":5,"Delay4":10} #{"Delay1":5,"Delay2":5,"Delay3":5,"Delay4":5}

deltasIgnore = [-30.0, 0, 30.0]
lastFocusSwitch = 0
cmExtensions = 0
serverName = ""
serverIP = ""

key_listener = 0   #the listener for hotkeys
lastPreferred = 0
countdownFocusSwitch = 10.0
overrideCar = -1
minPitKMH = 40.0
maxPitKMH = 85.0
#clearPitKMH = 5.0
offPaceSwitchDelay = 120.0
minSwitchDelay = 5.0
countdownCam = 5
battleGap = 0.75
battleKMHPercentDiff = 15.0
leadersOverClosest = 0
offPaceCanOverrideBattles = 1
noDrivableCamWithVirtualMirror = 1

positionDecay = 0.92
incidentDetection = 1
incidentMinNormalSpeed = 60.0
incidentMaxSpeed = 25.0
incidentDuration = 8.0
forceTrackCamOnCloseBattles = 1
closeBattleThreshold = 0.35
bestBattleGap = 999.0

chkIncident = 0
prevCarPositions = {}

# per-frame distance-based running order (see computeDistanceOrder): distanceOrder
# is the race order (P1 first), distancePos[car] is the 0-based position.
distanceOrder = []
distancePos = {}

dynamicChaseCam = 1
chaseOnboardThreshold = 0.8
tvCamThreshold = 0.3

chkDynamicChase = 0

#defaultPitCam = 0
#defaultOffPaceCam = 3
strTimestamp = ''
sessionStartTime = 0
sessionDelay = 5.0     #how long to wait before applying any logic?
lastSession = -10      #not an actual session ID
sessionStarted = False #tracking session restarts
promoText = ""

import subprocess

def process_exists(process_name):
    ConsoleLog("Checking for %s"%(process_name))
    try:
        call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
        #ConsoleLog("100")
        # use buildin check_output right away
        output = subprocess.check_output(call).decode("utf-8")
        #ConsoleLog("200")
        # check in last line for process name
        last_line = output.strip().split('\r\n')[-1]
        #ConsoleLog("last_line = %s"%(last_line))
        # because Fail message could be translated
        process_running = last_line.lower().startswith(process_name.lower())
        
        if process_running:
            ConsoleLog("Process %s found to be running"%(process_name))
        else:
            ConsoleLog("Process %s found to be NOT running"%(process_name))
        
        return process_running
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        #ac.console('AutoCam ReadSettings Error (logged to file)')
        #ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        ConsoleLog(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        
    return False
  
def safeText(message):
    validFilenameChars = "-_()=[]{}|/\.,:;`~'\" abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(c for c in message if c in validFilenameChars)

def ConsoleLog(message):
    #now = time.clock()
    ac.console("AutoCam(%s): %s"%(strTimestamp, message))
    ac.log("AutoCam(%s): %s"%(strTimestamp, safeText(message)))
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

def WriteSettings():
    global windowx, windowy, scale_mult, skipDrivers, promoText
    global AutoCamActive, driverSwitchDelay, defaultCamera, cameraSwitchDelay
    global verbose, cameraSwitchingEnabled, driverSwitchingEnabled
    global pitCameraDelay, pitCameraSwitching, preferredDrivers, battleCamSwitching, battleCamDelay
    global firstLapSwitching, firstLapDelay, countdownCam
    global minPitKMH, maxPitKMH, offPaceSwitchDelay, minSwitchDelay
    global battleGap, leadersOverClosest, offPaceCanOverrideBattles, noDrivableCamWithVirtualMirror
    global positionDecay, incidentDetection, incidentMinNormalSpeed, incidentMaxSpeed, incidentDuration, forceTrackCamOnCloseBattles, closeBattleThreshold
    global dynamicChaseCam, chaseOnboardThreshold, tvCamThreshold
    global rawCameraSwitching, rawPitCameraSwitching, rawBattleCams, rawFirstLapSwitching

    try:
        section = 'SETTINGS'
        SettingsConfig = configparser.ConfigParser()
        SettingsConfig.add_section(section)
        SettingsConfig.set(section, 'AutoCamActive', str(AutoCamActive))
        SettingsConfig.set(section, 'defaultCamera', str(defaultCamera))
        SettingsConfig.set(section, 'verbose', str(verbose))
        SettingsConfig.set(section, 'cameraSwitching', rawCameraSwitching)
        SettingsConfig.set(section, 'firstLapSwitching', rawFirstLapSwitching)
        SettingsConfig.set(section, 'pitCameraSwitching', rawPitCameraSwitching)
        SettingsConfig.set(section, 'battleCams', rawBattleCams)
        SettingsConfig.set(section, 'countdownCam', str(countdownCam))
        SettingsConfig.set(section, 'cameraSwitchDelay', str(cameraSwitchDelay))
        SettingsConfig.set(section, 'cameraSwitchingEnabled', str(cameraSwitchingEnabled))
        SettingsConfig.set(section, 'driverSwitchingEnabled', str(driverSwitchingEnabled))
        SettingsConfig.set(section, 'driverSwitchDelay', str(driverSwitchDelay))
        SettingsConfig.set(section, 'minPitKMH', str(minPitKMH))
        SettingsConfig.set(section, 'maxPitKMH', str(maxPitKMH))
        SettingsConfig.set(section, 'offPaceSwitchDelay', str(offPaceSwitchDelay))
        SettingsConfig.set(section, 'offPaceCanOverrideBattles', str(offPaceCanOverrideBattles))
        SettingsConfig.set(section, 'minSwitchDelay', str(minSwitchDelay))
        SettingsConfig.set(section, 'battleGap', str(battleGap))
        SettingsConfig.set(section, 'leadersOverClosest', str(leadersOverClosest))
        SettingsConfig.set(section, 'noDrivableCamWithVirtualMirror', str(noDrivableCamWithVirtualMirror))
        SettingsConfig.set(section, 'positionDecay', str(positionDecay))
        SettingsConfig.set(section, 'incidentDetection', str(incidentDetection))
        SettingsConfig.set(section, 'incidentMinNormalSpeed', str(incidentMinNormalSpeed))
        SettingsConfig.set(section, 'incidentMaxSpeed', str(incidentMaxSpeed))
        SettingsConfig.set(section, 'incidentDuration', str(incidentDuration))
        SettingsConfig.set(section, 'forceTrackCamOnCloseBattles', str(forceTrackCamOnCloseBattles))
        SettingsConfig.set(section, 'closeBattleThreshold', str(closeBattleThreshold))
        SettingsConfig.set(section, 'dynamicChaseCam', str(dynamicChaseCam))
        SettingsConfig.set(section, 'chaseOnboardThreshold', str(chaseOnboardThreshold))
        SettingsConfig.set(section, 'tvCamThreshold', str(tvCamThreshold))
        SettingsConfig.set(section, 'HideIcon', str(HideIcon))
        SettingsConfig.set(section, 'AppWidth', str(windowx))
        SettingsConfig.set(section, 'AppHeight', str(windowy))
        SettingsConfig.set(section, 'backgroundOpacity', str(backgroundOpacity))
        SettingsConfig.set(section, 'drawBorder', str(drawBorderVar))
        SettingsConfig.set(section, 'skipDrivers', "|".join(skipDrivers))
        
        with open(SettingsINI, 'w') as configfile:
            SettingsConfig.write(configfile)
        ConsoleLog("Saved settings to %s" % SettingsINI)
    except Exception as e:
        ConsoleLog("Error in WriteSettings: %s" % e)

def onBattleGapChange(value):
    global battleGap
    battleGap = value
    ConsoleLog("UI Changed battleGap to %0.2f" % battleGap)

def onIncidentToggle(*args):
    global incidentDetection, chkIncident
    incidentDetection = 1 - incidentDetection
    ac.setText(chkIncident, checkboxLabel("Enable Incident Detection", incidentDetection == 1))
    ConsoleLog("UI Changed incidentDetection to %d" % incidentDetection)

def onIncidentDurationChange(value):
    global incidentDuration
    incidentDuration = value
    ConsoleLog("UI Changed incidentDuration to %0.1f" % incidentDuration)

def onSaveSettingsClick(*args):
    WriteSettings()

def onDynamicChaseToggle(*args):
    global dynamicChaseCam, chkDynamicChase
    dynamicChaseCam = 1 - dynamicChaseCam
    ac.setText(chkDynamicChase, checkboxLabel("Enable Dynamic Chase Cam", dynamicChaseCam == 1))
    ConsoleLog("UI Changed dynamicChaseCam to %d" % dynamicChaseCam)

def onTVCamThresholdChange(value):
    global tvCamThreshold
    tvCamThreshold = value
    ConsoleLog("UI Changed tvCamThreshold to %0.2f" % tvCamThreshold)

def checkboxLabel(text, on):
    # stock AC here exposes addCheckBox but neither isChecked nor setChecked, so
    # booleans are drawn as toggle buttons whose label carries the current state.
    return "%s: %s" % (text, "ON" if on else "OFF")


def acMain(ac_version):
    global camWindow, btnToggle, lblInfo, cmExtensions, serverName, serverIP
    global strTimestamp, noDrivableCamWithVirtualMirror
    global chkIncident, windowx, windowy
    global chkDynamicChase

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
            serverINI = "apps\\python\\AutoCam\\127_0_0_1.ini"

        #default INI
        ReadSettings(SettingsINI)
        #IP Specific INI
        ReadSettings(serverINI)

        #the UI layout spans down to y=515 and out to x=265, so a smaller
        #saved/INI size would clip the controls; never go below 280x530
        if windowx < 280:
            windowx = 280
        if windowy < 530:
            windowy = 530

        #Read Pit Entry Path - we are not doing this for now
        #loadPitEntryToDict()
        
        try:
            if not ac.ext_isVirtualMirrorForced():
                #if the virtual mirror is not forced, then disable this check
                ConsoleLog("ac.ext_isVirtualMirrorForced() states False")
                noDrivableCamWithVirtualMirror = 0
            else:
                ConsoleLog("ac.ext_isVirtualMirrorForced() states True")
        except:
            ConsoleLog("Unable to check ac.ext_isVirtualMirrorForced()")
            pass
        
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

        camWindow = ac.newApp("Auto Cam")
        ac.setSize(camWindow, windowx, windowy)
        ConsoleLog("App ID = %d"%(camWindow))
        if HideIcon == 1:
            ac.setIconPosition(camWindow, 0, -9000)

        ac.drawBorder(camWindow,0)
        ac.setBackgroundOpacity(camWindow,0.7)

        btnToggle = ac.addButton(camWindow, "AutoCam ACTIVE")
        if AutoCamActive == 0:
            ac.setText(btnToggle, "AutoCam INACTIVE")
        ac.setPosition(btnToggle, 15, 25)
        ac.setSize(btnToggle, windowx - 30, 25)
        ac.setFontSize(btnToggle, 14)
        ac.addOnClickedListener(btnToggle, onToggle)

        # --- Section 1: Battle Settings ---
        lblSectionBattle = ac.addLabel(camWindow, "--- Battle Settings ---")
        ac.setPosition(lblSectionBattle, 15, 60)
        ac.setFontSize(lblSectionBattle, 13)

        # Spinner for battleGap
        lblBattleGap = ac.addLabel(camWindow, "Battle Gap (sec):")
        ac.setPosition(lblBattleGap, 15, 85)
        ac.setFontSize(lblBattleGap, 12)

        spinBattleGap = ac.addSpinner(camWindow, "")
        ac.setPosition(spinBattleGap, 160, 83)
        ac.setSize(spinBattleGap, 105, 22)
        ac.setRange(spinBattleGap, 0.1, 2.5)
        ac.setStep(spinBattleGap, 0.1)
        ac.setValue(spinBattleGap, battleGap)
        ac.addOnValueChangeListener(spinBattleGap, onBattleGapChange)

        # --- Section 2: Dynamic Chase Camera ---
        lblSectionChase = ac.addLabel(camWindow, "--- Dynamic Chase Cam ---")
        ac.setPosition(lblSectionChase, 15, 205)
        ac.setFontSize(lblSectionChase, 13)

        # Button for Enable Dynamic Chase Cam
        chkDynamicChase = ac.addButton(camWindow, checkboxLabel("Enable Dynamic Chase Cam", dynamicChaseCam == 1))
        ac.setPosition(chkDynamicChase, 15, 230)
        ac.setSize(chkDynamicChase, 250, 22)
        ac.addOnClickedListener(chkDynamicChase, onDynamicChaseToggle)

        # Spinner for tvCamThreshold
        lblTVThreshold = ac.addLabel(camWindow, "TV Cam Threshold (sec):")
        ac.setPosition(lblTVThreshold, 15, 260)
        ac.setFontSize(lblTVThreshold, 12)

        spinTVThreshold = ac.addSpinner(camWindow, "")
        ac.setPosition(spinTVThreshold, 160, 258)
        ac.setSize(spinTVThreshold, 105, 22)
        ac.setRange(spinTVThreshold, 0.1, 1.0)
        ac.setStep(spinTVThreshold, 0.05)
        ac.setValue(spinTVThreshold, tvCamThreshold)
        ac.addOnValueChangeListener(spinTVThreshold, onTVCamThresholdChange)

        # --- Section 3: Incident Settings ---
        lblSectionIncident = ac.addLabel(camWindow, "--- Incident Settings ---")
        ac.setPosition(lblSectionIncident, 15, 350)
        ac.setFontSize(lblSectionIncident, 13)

        # Button for Incident Detection
        chkIncident = ac.addButton(camWindow, checkboxLabel("Enable Incident Detection", incidentDetection == 1))
        ac.setPosition(chkIncident, 15, 375)
        ac.setSize(chkIncident, 250, 22)
        ac.addOnClickedListener(chkIncident, onIncidentToggle)

        # Spinner for incidentDuration
        lblIncidentDuration = ac.addLabel(camWindow, "Incident Duration (sec):")
        ac.setPosition(lblIncidentDuration, 15, 410)
        ac.setFontSize(lblIncidentDuration, 12)

        spinIncidentDuration = ac.addSpinner(camWindow, "")
        ac.setPosition(spinIncidentDuration, 160, 408)
        ac.setSize(spinIncidentDuration, 105, 22)
        ac.setRange(spinIncidentDuration, 2.0, 20.0)
        ac.setStep(spinIncidentDuration, 1.0)
        ac.setValue(spinIncidentDuration, incidentDuration)
        ac.addOnValueChangeListener(spinIncidentDuration, onIncidentDurationChange)

        # Save Settings Button
        btnSave = ac.addButton(camWindow, "SAVE CONFIGURATION")
        ac.setPosition(btnSave, 15, 485)
        ac.setSize(btnSave, windowx - 30, 30)
        ac.setFontSize(btnSave, 14)
        ac.addOnClickedListener(btnSave, onSaveSettingsClick)

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
    global rawCameraSwitching, rawPitCameraSwitching, rawBattleCams, rawFirstLapSwitching
    global windowx, windowy, scale_mult, skipDrivers, promoText
    global AutoCamActive, driverSwitchDelay, defaultCamera, cameraSwitchDelay
    global verbose, cameraSwitchingEnabled, driverSwitchingEnabled
    global pitCameraDelay, pitCameraSwitching, preferredDrivers, battleCamSwitching, battleCamDelay
    global firstLapSwitching, firstLapDelay, countdownCam
    global minPitKMH, maxPitKMH, offPaceSwitchDelay, minSwitchDelay
    global battleGap, leadersOverClosest, offPaceCanOverrideBattles, noDrivableCamWithVirtualMirror
    global positionDecay, incidentDetection, incidentMinNormalSpeed, incidentMaxSpeed, incidentDuration, forceTrackCamOnCloseBattles, closeBattleThreshold
    global dynamicChaseCam, chaseOnboardThreshold, tvCamThreshold

    try:
        if os.path.isfile(INI_File):
            ConsoleLog("ReadSettings from %s"%(INI_File))
            section = 'SETTINGS'
            SettingsConfig = configparser.ConfigParser()
            SettingsConfig.read(INI_File)
            boolWriteSettings = False #we aren't managing this yet
                     
            #verbose
            if SettingsConfig.has_option(section, 'verbose'):  
                verbose = SettingsConfig.getint(section, 'verbose')    
            else:
                ConsoleLog("verbose not found")
                boolWriteSettings = True
                
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

            if verbose == 1:
                for strDriver in skipDrivers:
                    ConsoleLog("Skipping %s"%(strDriver))

            #preferredDrivers
            if SettingsConfig.has_option(section, 'preferredDrivers'): 
                ConsoleLog("Loading preferredDrivers")
                preferredDrivers = SettingsConfig.get(section, 'preferredDrivers').split("|")

            for strDriver in preferredDrivers:
                ConsoleLog("Preferred %s"%(strDriver))
                
            #driverSwitchDelay
            if SettingsConfig.has_option(section, 'driverSwitchDelay'):  
                driverSwitchDelay = SettingsConfig.getint(section, 'driverSwitchDelay')    
            else:
                ConsoleLog("driverSwitchDelay not found")
                boolWriteSettings = True

            ConsoleLog("driverSwitchDelay = %0.0f"%(driverSwitchDelay))
                
            #cameraSwitchDelay
            if SettingsConfig.has_option(section, 'cameraSwitchDelay'):  
                cameraSwitchDelay = SettingsConfig.getint(section, 'cameraSwitchDelay')    
            else:
                ConsoleLog("cameraSwitchDelay not found")
                boolWriteSettings = True
                
            intGuess = 1
            #cameraSwitching
            if SettingsConfig.has_option(section, 'cameraSwitching'):  
                rawCameraSwitching = SettingsConfig.get(section, 'cameraSwitching')
                switchingTemp = rawCameraSwitching.split("|")
                
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
                rawPitCameraSwitching = SettingsConfig.get(section, 'pitCameraSwitching')
                switchingTemp = rawPitCameraSwitching.split("|")
                
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
            #battleCamSwitching
            if SettingsConfig.has_option(section, 'battleCams'):  
                rawBattleCams = SettingsConfig.get(section, 'battleCams')
                switchingTemp = rawBattleCams.split("|")
                
                for strCamera in switchingTemp:
                    cam, usage, delay = strCamera.split("^")
                    for i in range(0, int(usage)):
                        battleCamSwitching["Guess%d"%(intGuess)] = int(cam)
                        battleCamDelay["Delay%d"%(intGuess)] = int(delay)
                        if verbose == 1:
                            ConsoleLog("battleCam Guess%d = %d"%(intGuess, battleCamSwitching["Guess%d"%(intGuess)]))
                            ConsoleLog("battleCam Delay%d = %d"%(intGuess, battleCamDelay["Delay%d"%(intGuess)]))
                        intGuess = intGuess + 1
                
            else:
                ConsoleLog("battleCams not found")
                boolWriteSettings = True
                
                
            intGuess = 1
            #firstLapSwitching
            if SettingsConfig.has_option(section, 'firstLapSwitching'):  
                rawFirstLapSwitching = SettingsConfig.get(section, 'firstLapSwitching')
                switchingTemp = rawFirstLapSwitching.split("|")
                
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
            
            #countdownCam = 5
            if SettingsConfig.has_option(section, 'countdownCam'):  
                countdownCam = SettingsConfig.getint(section, 'countdownCam')
            else:
                ConsoleLog("countdownCam not found")
                boolWriteSettings = True
            
            ConsoleLog("countdownCam = %d"%(countdownCam))
            
            
            #minPitKMH = 20.0
            if SettingsConfig.has_option(section, 'minPitKMH'):  
                minPitKMH = SettingsConfig.getfloat(section, 'minPitKMH')    
            else:
                ConsoleLog("minPitKMH not found")
                boolWriteSettings = True
            ConsoleLog("minPitKMH = %0.2f"%(minPitKMH))
            
            #maxPitKMH = 85.0
            if SettingsConfig.has_option(section, 'maxPitKMH'):  
                maxPitKMH = SettingsConfig.getfloat(section, 'maxPitKMH')    
            else:
                ConsoleLog("maxPitKMH not found")
                boolWriteSettings = True
            ConsoleLog("maxPitKMH = %0.2f"%(maxPitKMH))
                            
            #offPaceSwitchDelay = 120.0
            if SettingsConfig.has_option(section, 'offPaceSwitchDelay'):  
                offPaceSwitchDelay = SettingsConfig.getfloat(section, 'offPaceSwitchDelay')    
            else:
                ConsoleLog("offPaceSwitchDelay not found")
                boolWriteSettings = True
            ConsoleLog("offPaceSwitchDelay = %0.2f"%(offPaceSwitchDelay))
            
            #minSwitchDelay = 5.0
            if SettingsConfig.has_option(section, 'minSwitchDelay'):  
                minSwitchDelay = SettingsConfig.getfloat(section, 'minSwitchDelay')    
            else:
                ConsoleLog("minSwitchDelay not found")
                boolWriteSettings = True
            ConsoleLog("minSwitchDelay = %0.2f"%(minSwitchDelay))
            
            #battleGap = 0.75
            if SettingsConfig.has_option(section, 'battleGap'):  
                battleGap = SettingsConfig.getfloat(section, 'battleGap')    
            else:
                ConsoleLog("battleGap not found")
                boolWriteSettings = True
            ConsoleLog("battleGap = %0.2f"%(battleGap))

            #leadersOverClosest = 0
            if SettingsConfig.has_option(section, 'leadersOverClosest'):  
                leadersOverClosest = SettingsConfig.getint(section, 'leadersOverClosest')
            else:
                ConsoleLog("leadersOverClosest not found")
                boolWriteSettings = True            
            ConsoleLog("leadersOverClosest = %d"%(leadersOverClosest))

            #offPaceCanOverrideBattles
            if SettingsConfig.has_option(section, 'offPaceCanOverrideBattles'):  
                offPaceCanOverrideBattles = SettingsConfig.getint(section, 'offPaceCanOverrideBattles')
            else:
                ConsoleLog("offPaceCanOverrideBattles not found")
                boolWriteSettings = True            
            ConsoleLog("offPaceCanOverrideBattles = %d"%(offPaceCanOverrideBattles))

            #noDrivableCamWithVirtualMirror
            if SettingsConfig.has_option(section, 'noDrivableCamWithVirtualMirror'):  
                noDrivableCamWithVirtualMirror = SettingsConfig.getint(section, 'noDrivableCamWithVirtualMirror')
            else:
                ConsoleLog("noDrivableCamWithVirtualMirror not found")
                boolWriteSettings = True            
            ConsoleLog("noDrivableCamWithVirtualMirror = %d"%(noDrivableCamWithVirtualMirror))

            #positionDecay
            if SettingsConfig.has_option(section, 'positionDecay'):  
                positionDecay = SettingsConfig.getfloat(section, 'positionDecay')
            else:
                ConsoleLog("positionDecay not found, using default 0.92")
            ConsoleLog("positionDecay = %0.3f"%(positionDecay))

            #incidentDetection
            if SettingsConfig.has_option(section, 'incidentDetection'):  
                incidentDetection = SettingsConfig.getint(section, 'incidentDetection')
            else:
                ConsoleLog("incidentDetection not found, using default 1")
            ConsoleLog("incidentDetection = %d"%(incidentDetection))

            #incidentMinNormalSpeed
            if SettingsConfig.has_option(section, 'incidentMinNormalSpeed'):  
                incidentMinNormalSpeed = SettingsConfig.getfloat(section, 'incidentMinNormalSpeed')
            else:
                ConsoleLog("incidentMinNormalSpeed not found, using default 60.0")
            ConsoleLog("incidentMinNormalSpeed = %0.1f"%(incidentMinNormalSpeed))

            #incidentMaxSpeed
            if SettingsConfig.has_option(section, 'incidentMaxSpeed'):  
                incidentMaxSpeed = SettingsConfig.getfloat(section, 'incidentMaxSpeed')
            else:
                ConsoleLog("incidentMaxSpeed not found, using default 25.0")
            ConsoleLog("incidentMaxSpeed = %0.1f"%(incidentMaxSpeed))

            #incidentDuration
            if SettingsConfig.has_option(section, 'incidentDuration'):  
                incidentDuration = SettingsConfig.getfloat(section, 'incidentDuration')
            else:
                ConsoleLog("incidentDuration not found, using default 8.0")
            ConsoleLog("incidentDuration = %0.1f"%(incidentDuration))

            #forceTrackCamOnCloseBattles
            if SettingsConfig.has_option(section, 'forceTrackCamOnCloseBattles'):  
                forceTrackCamOnCloseBattles = SettingsConfig.getint(section, 'forceTrackCamOnCloseBattles')
            else:
                ConsoleLog("forceTrackCamOnCloseBattles not found, using default 1")
            ConsoleLog("forceTrackCamOnCloseBattles = %d"%(forceTrackCamOnCloseBattles))

            #closeBattleThreshold
            if SettingsConfig.has_option(section, 'closeBattleThreshold'):  
                closeBattleThreshold = SettingsConfig.getfloat(section, 'closeBattleThreshold')
            else:
                ConsoleLog("closeBattleThreshold not found, using default 0.35")
            ConsoleLog("closeBattleThreshold = %0.2f"%(closeBattleThreshold))

            #dynamicChaseCam
            if SettingsConfig.has_option(section, 'dynamicChaseCam'):  
                dynamicChaseCam = SettingsConfig.getint(section, 'dynamicChaseCam')
            else:
                ConsoleLog("dynamicChaseCam not found, using default 1")
            ConsoleLog("dynamicChaseCam = %d"%(dynamicChaseCam))

            #chaseOnboardThreshold
            if SettingsConfig.has_option(section, 'chaseOnboardThreshold'):  
                chaseOnboardThreshold = SettingsConfig.getfloat(section, 'chaseOnboardThreshold')
            else:
                ConsoleLog("chaseOnboardThreshold not found, using default 0.8")
            ConsoleLog("chaseOnboardThreshold = %0.2f"%(chaseOnboardThreshold))

            #tvCamThreshold
            if SettingsConfig.has_option(section, 'tvCamThreshold'):  
                tvCamThreshold = SettingsConfig.getfloat(section, 'tvCamThreshold')
            else:
                ConsoleLog("tvCamThreshold not found, using default 0.3")
            ConsoleLog("tvCamThreshold = %0.2f"%(tvCamThreshold))
            
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
        
            #promoText
            if SettingsConfig.has_option(section, 'promoText'): 
                ConsoleLog("Loading promoText")
                promoText = SettingsConfig.get(section, 'promoText').strip()

            ConsoleLog("promoText = %s"%(promoText))
            
        
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
        #ac.console('AutoCam ReadSettings Error (logged to file)')
        #ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        ConsoleLog(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    
    
def ReadCarCameras():
    
    try:
        INI_File = 'apps\\python\\AutoCam\\carCameras.ini'
        if os.path.isfile(INI_File):
            ConsoleLog("ReadCarCameras from %s"%(INI_File))
            section = 'SETTINGS'
            SettingsConfig = configparser.ConfigParser()
            SettingsConfig.read(INI_File)
            
            for carId in range(0, ac.getCarsCount()):
                carName = ac.getCarName(carId)
                carCamCount = ac.getCameraCarCount(carId)
                if verbose == 1:
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
                            elif i == 2:
                                strCameras = "%d^1|%s"%(i, strCameras)
                            else:
                                strCameras = "%s|%d^1"%(strCameras, i)
                                
                        SettingsConfig.set(section,carName,'%s'%strCameras)                    
        
                        with open(INI_File, 'w') as configfile:
                            configfile.write(';for each car there should be one line' + '\n')
                            configfile.write(';each car camera has a number and a weight for how often to use it' + '\n')
                
                            SettingsConfig.write(configfile)
                
                if SettingsConfig.has_option(section, carName) and carCamCount > 0:
                    if verbose == 1:
                        ConsoleLog("Found %s in %s"%(carName, INI_File))
                    if not carName in dicCars:
                        if verbose == 1:
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
                                    ConsoleLog("cam %d >= carCamCount (%d)"%(cam, carCamCount))
                        else:
                            ConsoleLog("carCamera options for %s were empty"%(carName))
                    else:
                        if verbose == 1:
                            ConsoleLog("Car %s already found in dicCars"%(carName))
                else:
                    ConsoleLog("Car %s NOT FOUND"%(carName))
                
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        #ac.console('AutoCam ReadCars Error (logged to file)')
        #ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))    
        ConsoleLog(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))    
        
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

    
def computeDistanceOrder():
    # Build the race order from total distance along the track. Uses the same
    # (LapCount + NormalizedSplinePosition) metric as gapBetweenCars, so it works
    # wherever getCarState returns per-car data — live AND replay — without the
    # live-only CSP getCarRealTimeLeaderboardPosition call. Caches into the
    # distanceOrder / distancePos globals and also returns the order for reuse.
    global distanceOrder, distancePos
    cars_list = []
    trackLength = ac.getTrackLength(0)
    for car in range(0, ac.getCarsCount()):
        if ac.isConnected(car):
            dist = (ac.getCarState(car, acsys.CS.LapCount) + ac.getCarState(car, acsys.CS.NormalizedSplinePosition)) * trackLength
            cars_list.append((dist, car))
    cars_list.sort()
    cars_list.reverse()
    distanceOrder = [car for dist, car in cars_list]
    distancePos = {}
    for idx, car in enumerate(distanceOrder):
        distancePos[car] = idx
    return distanceOrder

def getPosition(car):
    tmpKey = "APPS:BROADCAST APP"
    if order == "": #not tmpKey in dicPython:
        # no broadcast app: fall back to the distance-based race order
        return distancePos.get(car, ac.getCarsCount())
    else:
        tmpKey = "Car%dPosition"%(car) #getPosition
        if tmpKey in dic:
            #ConsoleLog("dic[%s] = %s"%(tmpKey, dic[tmpKey]))
            return int(dic[tmpKey])
        else:
            return distancePos.get(car, ac.getCarsCount())
    
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
                topFive = ""
                for car in orderStrings:
                    if not car == "":
                        dic["Car%dPosition"%(int(car))] = position #setPositions
                        if position < 5:
                            topFive = topFive + safeName(int(car)) + '|'
                        #ConsoleLog("Driver %d in position %d named %s"%(int(car), position + 1, safeName(int(car))))
                        position = position + 1
                #ConsoleLog(topFive)
                        
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
            #log the top 5 drivers names?
            

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
                for carId in range(0,ac.getCarsCount()):
                    if safeName(carId) in preferredDrivers and ac.isConnected(carId):
                        return False

        #this gets fired too frequently?
        if False: #allDriversInPits == 0 and ac.isCarInPitlane(carID):
            #check to see if car is not actually moving
            strPoT = "%0.3f"%ac.getCarState(carID,acsys.CS.NormalizedSplinePosition)
            tmpKey = "Car%dOffPacePoT"%(carID)
            if tmpKey in dic:
                if dic[tmpKey] == strPoT:
                    #ConsoleLog("Car %d stuck moving at %s"%(carID, strPoT))
                    return False
                dic[tmpKey] = strPoT
            else:
                return False
            dic[tmpKey] = strPoT

        return True
    else:
        return False

def timeToMinSecMsecTuple(t):
    mins = t // (60*1000)
    secs = (t - 60*1000*mins) // 1000
    msecs = (t - 60*1000*mins - secs*1000)
    return (mins, secs, msecs)
        
def formatTime(t):
    try:
        mins, secs, msecs = timeToMinSecMsecTuple(abs(t))
        time = "%02d:%02d.%03d" % (mins, secs, msecs)
    except:
        time = "00:00.00"
        pass
        
    return time
    
        
def SetCamera(cam, reason):
    # record the desired camera and why it was chosen; does NOT apply it.
    # actual ac.setCameraMode() calls (and their logs) live at the apply sites.
    global setCamera, cameraReason
    if cam != setCamera:
        cameraReason = reason
    setCamera = cam


def autoCam():
    global currentId, lastFocusSwitch, defaultSet, cameraSwitchTimer, cameraSwitchDelay
    global setCamera, lastPreferred, countdownFocusSwitch, overrideCar
    global allDriversFinished, allDriversInPits, sessionStartTime, lastSession, sessionStarted
    global positionDecay, incidentDetection, incidentMinNormalSpeed, incidentMaxSpeed, incidentDuration, forceTrackCamOnCloseBattles, closeBattleThreshold, bestBattleGap, prevCarPositions
    global dynamicChaseCam, chaseOnboardThreshold, tvCamThreshold

    bestBattleGap = 999.0
    anyDriverFinishing = 0
    focusCarBattling = False

    sim_info_obj = AutoCam_sim_info.AutoCam_SimInfo()

    # AutoCam is a live-broadcast director, but it can also direct a replay: the
    # race order is now computed from track distance (computeDistanceOrder), which
    # needs no live-only call, so replay is safe to direct. Stand down when the
    # game is fully off / paused / in the menu.
    if sim_info_obj.graphics.status not in (AutoCam_sim_info.AC_LIVE, AutoCam_sim_info.AC_REPLAY):
        return

    # rebuild the car wrappers if the connected-car count changed (e.g. cars
    # join/leave, or the app loaded before the grid was populated)
    if len(cars) != ac.getCarsCount():
        currentId = 0
        InitCars()

    # refresh the distance-based running order used by getPosition / battle logic
    computeDistanceOrder()

    #ac.setBackgroundOpacity(camWindow, 0)
    #ac.setIconPosition(camWindow, -7000, -3000)
    #ac.setTitle(camWindow, "")
    
    strErr = "100"
    if verbose == 4:
        ConsoleLog("%s"%strErr)
    
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

    bIsQually = False
    if sim_info_obj.graphics.session == 1:
        bIsQually = True
    bIsPractice = False
    if sim_info_obj.graphics.session == 0:
        bIsPractice = True
    bIsRace = False
    if sim_info_obj.graphics.session == 2:
        bIsRace = True

    # a replay is always a broadcast of a race, so direct it as one
    if sim_info_obj.graphics.status == AutoCam_sim_info.AC_REPLAY:
        bIsRace = True

    totalLaps = sim_info_obj.graphics.numberOfLaps

    strErr = "110"
    if verbose == 4:
        ConsoleLog("%s"%strErr)

    timeLeft = formatTime(sim_info_obj.graphics.sessionTimeLeft)
    if len(timeLeft) > 5:
        timeLeft = timeLeft[0:5]    


    strErr = "120"
    if verbose == 4:
        ConsoleLog("%s"%strErr)
        
    #ConsoleLog("timeLeft = %s"%(timeLeft))
    #extraLap = sim_info_obj.static.hasExtraLap
            
    if sim_info_obj.static.isTimedRace and bIsRace:
        tmpKey = "totalLaps"
        if tmpKey in dic:
            totalLaps = dic[tmpKey]
        
    trackLength = ac.getTrackLength(0)
    totalDistance = totalLaps * trackLength
    carFound = -1
    driverSwitched = 0

    strErr = "130"
    if verbose == 4:
        ConsoleLog("%s"%strErr)
        
    ABot_Talking = False
    ABot_Enabled = False
    
    try:
        if AppCom.ABot_Talking:
            ABot_Talking = True
            #ConsoleLog("ABot is talking")
        else:
            ABot_Talking = False
            #ConsoleLog("ABot is NOT talking")
        ABot_Enabled = AppCom.ABot_Enabled
    except:
        pass
        
    #ConsoleLog("totalLaps = %d, trackLength = %d, totalDistance = %d"%(totalLaps, trackLength, totalDistance))
    
    try:
        #use the same now value for all code
        now = time.clock()

        #tracking session restarts
        if not lastSession == sim_info_obj.graphics.session:
            #ConsoleLog("REPORTING SESSION INFO")
            ConsoleLog("lastSession = %d, Session = %d"%(lastSession, sim_info_obj.graphics.session))
            lastSession = sim_info_obj.graphics.session
            sessionStartTime = now
            prevCarPositions.clear()
            if bIsRace and not promoText == "" and process_exists("obs64.exe"):
                ConsoleLog("Sending promoText %s"%(promoText))
                ac.sendChatMessage(promoText)
        if sessionStarted and ac.getCarState(0, acsys.CS.LapTime) == 0.0:
            ConsoleLog("Resetting the sessionStarted and sessionStartTime")
            sessionStarted = False
            sessionStartTime = now
        elif not sessionStarted and ac.getCarState(0, acsys.CS.LapTime) > 0.0:
            ConsoleLog("sessionStarting")
            sessionStarted = True
    
        #if now - sessionStartTime < sessionDelay:
            #ConsoleLog("Session Started, Waiting Before Processing")
            #wait X seconds before considering anything else in the session
        #    return 1
    
        if AutoCamActive:
            strErr = "200"
            if verbose == 4:
                ConsoleLog("%s"%strErr)
            
            # --- INCIDENT / SPIN DETECTION ---
            if incidentDetection == 1 and bIsRace and anyDriverFinishing == 0 and not ABot_Talking:
                incident_car = -1
                normal_speed = 100.0
                for car in range(0, ac.getCarsCount()):
                    if ac.isConnected(car) and not ac.isCarInPitlane(car) and ac.getCarState(car, acsys.CS.RaceFinished) == 0:
                        speed = ac.getCarState(car, acsys.CS.SpeedKMH)
                        lapCount = ac.getCarState(car, acsys.CS.LapCount)
                        
                        if lapCount > 0:
                            currPoT = ac.getCarState(car, acsys.CS.NormalizedSplinePosition)
                            keyPoTKMH = "Car%sKMH%0.3f"%(ac.getCarName(car), currPoT)
                            if keyPoTKMH in dicKMH:
                                normal_speed = dicKMH[keyPoTKMH]
                                if normal_speed > incidentMinNormalSpeed and speed < incidentMaxSpeed:
                                    incident_car = car
                                    break
                
                if incident_car >= 0:
                    tmpKey = "Car%dIncidentTime"%(incident_car)
                    if tmpKey not in dic:
                        dic[tmpKey] = now
                    
                    if not ac.getFocusedCar() == incident_car:
                        ConsoleLog("INCIDENT: Driver %s is slow (Speed: %0.1f km/h, Normal: %0.1f km/h). Focusing!" % (safeName(incident_car), ac.getCarState(incident_car, acsys.CS.SpeedKMH), normal_speed))
                        ac.focusCar(incident_car)
                        overrideCar = incident_car
                        lastFocusSwitch = now
                        SetCamera(3, "incident: %s" % safeName(incident_car))
                        if ac.getCameraMode() != 3:
                            ConsoleLog("Camera switch -> mode 3 (incident: %s)" % safeName(incident_car))
                        ac.setCameraMode(3)
                        cameraSwitchTimer = now
                        cameraSwitchDelay = incidentDuration
                        driverSwitched = 1
                    
                    if ac.getFocusedCar() == incident_car:
                        if now - dic[tmpKey] < incidentDuration:
                            overrideCar = incident_car
                            focusCarBattling = False
                            bestBattleGap = 999.0
                        else:
                            try:
                                del dic[tmpKey]
                            except:
                                pass
                            overrideCar = -1
            
            # --- OVERTAKE LOCK LOGIC ---
            overtake_car = -1
            if bIsRace and anyDriverFinishing == 0 and not ABot_Talking:
                tmpOvertakeKey = "OvertakeLockTime"
                if tmpOvertakeKey in dic:
                    if now - dic[tmpOvertakeKey] < 5.0:
                        overrideCar = dic["OvertakeLockCar"]
                        focusCarBattling = False
                        bestBattleGap = 999.0
                    else:
                        try:
                            del dic[tmpOvertakeKey]
                            del dic["OvertakeLockCar"]
                        except:
                            pass
                        overrideCar = -1
                
                if tmpOvertakeKey not in dic and "Car%dIncidentTime"%(overrideCar) not in dic:
                    if prevCarPositions:
                        for car in range(0, ac.getCarsCount()):
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                curr_pos = getPosition(car)
                                if car in prevCarPositions:
                                    prev_pos = prevCarPositions[car]
                                    if curr_pos < prev_pos and ac.getCarState(car, acsys.CS.LapCount) > 0:
                                        overtake_car = car
                                        break
                    
                    if overtake_car >= 0:
                        ConsoleLog("OVERTAKE: Driver %s gained position (P%d -> P%d). Locking focus for 5s!" % (safeName(overtake_car), prevCarPositions[overtake_car] + 1, getPosition(overtake_car) + 1))
                        dic[tmpOvertakeKey] = now
                        dic["OvertakeLockCar"] = overtake_car
                        overrideCar = overtake_car
                        lastFocusSwitch = now
                        ac.focusCar(overtake_car)
                        SetCamera(3, "overtake: %s" % safeName(overtake_car))
                        if ac.getCameraMode() != 3:
                            ConsoleLog("Camera switch -> mode 3 (overtake: %s)" % safeName(overtake_car))
                        ac.setCameraMode(3)
                        cameraSwitchTimer = now
                        cameraSwitchDelay = 5.0
                        driverSwitched = 1

                for car in range(0, ac.getCarsCount()):
                    if ac.isConnected(car):
                        prevCarPositions[car] = getPosition(car)
            
            #DRIVER/CAR SWITCHING
            #first we'll iterate the drivers and check wether they need updates. Yes,
            #only 1 car per frame
            #Completely Remove the AutoCamCar library?  Recode it?            
            #we need a way to enable/disable driver switching in the INI?
            if driverSwitchingEnabled == 1: # True:
                #FOCUS CAR CHECKS
                focusCarBattling = False
                bestBattleGap = 999.0
                
                orderStrings = []
                if not AppCom.runningorder == "":
                    orderStrings = AppCom.runningorder.split("|")
                elif bIsRace:
                    orderStrings = [str(car) for car in distanceOrder]

                if len(orderStrings) > 0 and bIsRace:
                    for pos in range(len(orderStrings)):
                        if not orderStrings[pos] == "":
                            car = int(orderStrings[pos])
                            if car == ac.getFocusedCar():
                                try:
                                    if pos < len(orderStrings) - 1 and not orderStrings[pos + 1] == "":
                                        gap = gapBetweenCars(car, int(orderStrings[pos + 1]))
                                        if gap < battleGap:
                                            focusCarBattling = True
                                            bestBattleGap = min(bestBattleGap, gap)
                                    if pos > 0 and not orderStrings[pos - 1] == "":
                                        gap = gapBetweenCars(car, int(orderStrings[pos - 1]))
                                        if gap < battleGap:
                                            focusCarBattling = True
                                            bestBattleGap = min(bestBattleGap, gap)
                                except:
                                    pass
            
                if focusCarBattling == 1:
                    suffix = suffix + "B"
                else:
                    suffix = suffix + "b"
                    
                ac.setTitle(camWindow, "AutoCam " + suffix)

                strErr = "1000"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                #perfMeter = ac.getCarState(ac.getFocusedCar(), acsys.CS.PerformanceMeter)
                #ConsoleLog("Perf Meter for Car %d is %0.3f"%(ac.getFocusedCar(), perfMeter))
                #can we optionally use new logic or old logic?
                #check for the car with the smallest/lowest perfDelta during qually?
                
                #do all the per car logic here
                allDriversInPits = 1
                allDriversFinished = 1
                anyDriverFinishing = 0
                try:
                    maxLaps = 0
                    for car in range(0,ac.getCarsCount()):
                        if ac.isConnected(car):
                            inPits = ac.isCarInPitlane(car)
                            lapCount = ac.getCarState(car, acsys.CS.LapCount)
                            maxLaps = max(maxLaps, lapCount)

                            if ac.isCarInPitlane(car) == 0:
                                allDriversInPits = 0
                                
                            if ac.getCarState(car, acsys.CS.RaceFinished) == 0:
                                allDriversFinished = 0
                            else:
                                anyDriverFinishing = 1

                            #check if focusCar is about to finish the race
                            if anyDriverFinishing == 0 and car == ac.getFocusedCar() and totalDistance > 0 and trackLength > 0:
                                carLapCount = ac.getCarState(car, acsys.CS.LapCount)
                                carCurrPoT = ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                                carDistance = (carLapCount + carCurrPoT) * trackLength
                                #if the car is within 400 meters of the finish line on the lead lap
                                if carDistance > totalDistance - 800.0:
                                    anyDriverFinishing = 1

                                
                                
                            #lapsSincePit = 0
                            tmpKey = "Car%dLastPitLap"%(car)
                            if tmpKey in dic:
                                if inPits == 1 and not lapCount == dic[tmpKey]:
                                    #lapsSincePit = lapCount - dic[tmpKey]
                                    dic[tmpKey] = lapCount
                                    #how many laps since the last pit?
                            else:
                                dic[tmpKey] = lapCount
                    

                    tmpKey = "totalLaps"
                    if not tmpKey in dic and bIsRace and sim_info_obj.static.isTimedRace:
                        if timeLeft == "00:00":
                            if sim_info_obj.static.hasExtraLap:
                                dic[tmpKey] = maxLaps + 2
                            else:
                                dic[tmpKey] = maxLaps + 1
                            ConsoleLog("Setting dic[%s] = %s"%(tmpKey, dic[tmpKey]))
                        #else:
                        #    ConsoleLog("timeLeft = %s"%(timeLeft))

                    
                except:
                    pass
                    
                        
                #logic is incorrectly quick switching after setting carFound
                strErr = "1100"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                if (bIsQually == True): # and now - lastFocusSwitch > quallySwitchDelay:
                    #ConsoleLog("Checking perfDelta Info")
                    lowestPerfDelta = 0.0
                    highestPoT = 0.0
                    try:
                        for car in range(0,ac.getCarsCount()):
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                carPerfDelta = ac.getCarState(car, acsys.CS.PerformanceMeter)
                                carKMH = ac.getCarState(car,acsys.CS.SpeedKMH) # > minPitKMH
                                #how do we focus on cars that are up towards the end of a lap?
                                if not round(carPerfDelta, 3) in deltasIgnore and carKMH > minPitKMH:
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
                strErr = "1200"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                #Race Countdown Logic
                if bIsRace == True and ac.getCarState(0, acsys.CS.LapTime) == 0.0 and carFound < 0 and countdownCam >= 0:
                    if now - sessionStartTime > sessionDelay:                    
                        #can we tighten up the timing on the countdown?
                        tmpKey = "FirstCarSelected"
                        if ABot_Talking and tmpKey in dic:
                            countdownFocusSwitch = 2.0
                            lastFocusSwitch = now
                            return 1
                    
                        #ConsoleLog("running the countdown logic")
                        #run the countdown logic?
                        if now - lastFocusSwitch > countdownFocusSwitch:
                            #ConsoleLog("running the countdown logic, focus driver is %s"%(safeName(ac.getFocusedCar())))
                            #get the ID of the car in the next next position
                            currentPosition = getPosition(ac.getFocusedCar())
                            for car in range(0,ac.getCarsCount()):
                                if not ABot_Enabled:
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
                                for car in range(0,ac.getCarsCount()):
                                    if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                        if carFound >= 0:
                                            if getPosition(car) < getPosition(carFound):
                                                #ConsoleLog("Resetting car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                                carFound = car
                                                if not ABot_Enabled:
                                                    countdownFocusSwitch = 10.0
                                        else: 
                                            #ConsoleLog("Initializing car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                            carFound = car
                                            if not ABot_Enabled:
                                                countdownFocusSwitch = 10.0
                            
                            if carFound >= 0:
                                dic[tmpKey] = 1
                                if verbose == 1:
                                    ConsoleLog("Countdown car in position %d = Driver %s"%(getPosition(carFound), safeName(carFound)))
                                    
                    elif False: #is this really necessary?  can ABot fix this issue?
                        #select the last car on the grid?
                        currentPosition = 0
                        for car in range(0,ac.getCarsCount()):
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                if getPosition(car) > currentPosition:
                                    carFound = car
                                    currentPosition = getPosition(car)
                        if carFound >= 0 and not carFound == ac.getFocusedCar():
                            if verbose == 1:
                                ConsoleLog("Pre-Countdown car in position %d = Driver %s"%(getPosition(carFound), safeName(carFound)))
                        
                        
                
                strErr = "1300"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                #Tracking cars that are off pace
                if (ac.getCarState(0, acsys.CS.LapTime) > 0.0 or countdownCam < 0) and anyDriverFinishing == 0 and focusCarBattling == False:
                    for car in range(0,ac.getCarsCount()):
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
                            
                            if speedKMH < 400.0 and anyDriverFinishing == 0:
                                #keyMaxKMH = "Car%sKMHMax%0.3f"%(carName,currPoT)
                                #if keyMaxKMH in dicKMH:
                                #    dicKMH[keyMaxKMH] = max(keyMaxKMH, speedKMH)
                                keyPoTKMH = "Car%sKMH%0.3f"%(carName,currPoT)
                                if keyPoTKMH in dicKMH:
                                    if dicKMH[keyPoTKMH] > 350.0:
                                        ConsoleLog("Driver %s: dicKMH[%s] = %0.1f"%(driverName, keyPoTKMH, dicKMH[keyPoTKMH]))
                                        
                                    #current speed has to be greater than X% of current speed
                                    #only set the KMH data once a car is genuinely racing (lap > 0, above pit speed)
                                    if speedKMH > dicKMH[keyPoTKMH] * 0.5 and lapCount > 0 and speedKMH > 30.0:
                                        #ConsoleLog("using %s on lap %d of qually stint to update KMH data"%(driverName, lapsSincePit))
                                        dicKMH[keyPoTKMH] = ((dicKMH[keyPoTKMH] * 9.0) + speedKMH) / 10.0
                                    if speedKMH < (dicKMH[keyPoTKMH] * 0.5) and lapCount > 0 and bIsRace and overrideCar < 0 and raceFinished == 0 and now - lastFocusSwitch > minSwitchDelay:
                                        tmpKey = "Car%dOffPaceTime"%(car)
                                        if tmpKey in dic:
                                            if now - dic[tmpKey] > offPaceSwitchDelay: # battleCar
                                                if verbose == 1:
                                                    ConsoleLog("resetting overrideCar = %d for %s; %0.1f|%0.1f"%(car, driverName, speedKMH, dicKMH[keyPoTKMH]))
                                                overrideCar = car
                                                lastFocusSwitch = now
                                                dic[tmpKey] = now                                            
                                        else:
                                            if verbose == 1:
                                                ConsoleLog("setting overrideCar = %d for %s; %0.1f|%0.1f"%(car, driverName, speedKMH, dicKMH[keyPoTKMH]))
                                            overrideCar = car
                                            lastFocusSwitch = now
                                            dic[tmpKey] = now                                            
                                elif lapCount > 0 and speedKMH > 30.0:
                                    #ConsoleLog("using %s on lap %d to set KMH data"%(driverName, lapsSincePit))
                                    dicKMH[keyPoTKMH] = speedKMH
                                
                                
                                #CHECKING FOR CARS DRIVING TO OR FROM THE PIT BOX IN PIT LANE IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING  IS THIS WORKING 
                                if overrideCar < 0 and bIsRace and ac.isCarInPitlane(car) and now - lastFocusSwitch > minSwitchDelay and anyDriverFinishing == 0: # and speedKMH < 90.0: # and lapCount > 0:\
                                    #ConsoleLog("Driver %s driving in pit lane driving %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                                    tmpKey = "Car%dInPitTime"%(car)
                                    if tmpKey in dic:
                                        #cars must be driving in pits for at least 0.5 seconds before having their speed checked
                                        if now - dic[tmpKey] > 0.5:
                                            del dic[tmpKey]
                                            if ac.getCarState(car,acsys.CS.SpeedKMH) > minPitKMH and ac.getCarState(car,acsys.CS.SpeedKMH) < maxPitKMH:
                                                #check the previous PoT
                                                bSkip = False
                                                strPoT = "%0.3f"%ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                                                tmpKey = "Car%dOffPacePoT"%(car)
                                                if tmpKey in dic:
                                                    if dic[tmpKey] == strPoT:
                                                        #ConsoleLog("Car %d stuck moving at %s"%(car, strPoT))
                                                        bSkip = True
                                                    else:
                                                        ConsoleLog("Driver %s moving in pits at PoT %s"%(ac.getDriverName(car), strPoT))
                                                else:
                                                    ConsoleLog("Driver %s moving in pits at PoT %s"%(ac.getDriverName(car), strPoT))
                                                    bSkip = True
                                                dic[tmpKey] = strPoT
                                            
                                                #also check the speed?
                                                if ac.getCarState(car,acsys.CS.SpeedKMH) < 79.0:
                                                    strKMH = "%0f"%(ac.getCarState(car,acsys.CS.SpeedKMH))
                                                    tmpKey = "Car%dOffPaceKMH"%(car)
                                                    if tmpKey in dic:
                                                        if dic[tmpKey] == strKMH:
                                                            #ConsoleLog("Car %d stuck moving at %s"%(car, strKMH))
                                                            bSkip = True
                                                        else:
                                                            ConsoleLog("Driver %s moving in pits at %sKMH"%(ac.getDriverName(car), strKMH))
                                                    else:
                                                        ConsoleLog("Driver %s moving in pits at %sKMH"%(ac.getDriverName(car), strKMH))
                                                        bSkip = True
                                                    dic[tmpKey] = strKMH
                                                    
                                                    
                                            
                                            
                                                tmpKey = "Car%dOffPaceTime"%(car)                                    
                                                #DOES THIS NEED TO BE CONSIDERED WITH AN OFF PACE DELAY?
                                                if False: # tmpKey in dic:
                                                    if now - dic[tmpKey] > offPaceSwitchDelay:
                                                        if verbose == 1:
                                                            ConsoleLog("Driver %s driving in pit lane driving %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                                                        overrideCar = car
                                                        lastFocusSwitch = now
                                                        setCamera = pitCameraSwitching["Guess1"]
                                                        dic[tmpKey] = now
                                                        if verbose > 0 :
                                                            ConsoleLog("overrideCar = %d, setCamera = %d"%(overrideCar, setCamera))
                                                elif not bSkip:
                                                    if verbose == 1:
                                                        ConsoleLog("Driver %s at %s in pit lane driving %0.2fKMH"%(safeName(car), strPoT, ac.getCarState(car,acsys.CS.SpeedKMH)))
                                                    overrideCar = car
                                                    lastFocusSwitch = now
                                                    SetCamera(pitCameraSwitching["Guess1"], "pit lane: %s" % safeName(car))
                                                    dic[tmpKey] = now
                                                    if verbose > 0:
                                                        ConsoleLog("overrideCar = %d, setCamera = %d"%(overrideCar, setCamera))                                        
                                    else:
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
                                                if verbose > 0:
                                                    ConsoleLog("Driver %s driving towards pit entry"%(safeName(car)))
                                                overrideCar = car
                                                SetCamera(pitCameraSwitching["Guess1"], "pit entry: %s" % safeName(car))


                                #ac.console("avgKMH for %s at %0.3f = %0.1f"%(carName, currPoT, dicKMH[keyPoTKMH]))
                        #else: #THIS IS NOT RELIABLE
                        #    #clear this value when a driver enteres the pits (get them entering and exiting)
                        #    tmpKey = "Car%dOffPaceTime"%(car)
                        #    if tmpKey in dic and ac.getCarState(car,acsys.CS.SpeedKMH) < clearPitKMH:
                        #        ConsoleLog("Clearing offPace timestamp for %s, %0.2fKMH"%(safeName(car), ac.getCarState(car,acsys.CS.SpeedKMH)))
                        #        del dic[tmpKey]

                strErr = "1600"                
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                if len(preferredDrivers) > 0 and carFound > -1:
                    if not safeName(carFound) in preferredDrivers:
                        ConsoleLog("carFound Driver %s not in peferredDrivers"%(safeName(carFound)))
                        carFound = -1

                strErr = "1700"        
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                #drivers approaching the finish line on the lead lap - always check this?
                if bIsRace == True and totalLaps > 0 and totalDistance > 0 and now - lastFocusSwitch > 5.0:
                    try:
                        maxDistance = 0.0
                        #raceOver = ac.getCarState(car, acsys.CS.RaceFinished)
                        for car in range(0,ac.getCarsCount()):
                            if ac.isConnected(car) and ac.getCarState(car, acsys.CS.RaceFinished) == 0 and not ac.isCarInPitlane(car):
                                carLapCount = ac.getCarState(car, acsys.CS.LapCount)
                                carCurrPoT = ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                                carDistance = (carLapCount + carCurrPoT) * trackLength
                                #if the car is within 400 meters of the finish line on the lead lap
                                if carDistance > totalDistance - 800.0 and carDistance > maxDistance:                                    
                                    maxDistance = carDistance
                                    carFound = car
                                    overrideCar = -1                           
                                    if verbose == 1:
                                        ConsoleLog("Cars finishing race, setting carFound %d, clearing overrideCar %d"%(carFound, overrideCar))

                        #if no drivers found on the lead lap look for drivers that are some laps down?
                        if carFound < 0 and anyDriverFinishing == 1:
                            maxDistance = 0.0
                            maxPoT = 0.0
                            
                            #raceOver = ac.getCarState(car, acsys.CS.RaceFinished)
                            for car in range(0,ac.getCarsCount()):
                                if ac.isConnected(car) and ac.getCarState(car, acsys.CS.RaceFinished) == 0 and not ac.isCarInPitlane(car):
                                    carCurrPoT = ac.getCarState(car,acsys.CS.NormalizedSplinePosition)
                                    if carCurrPoT > maxPoT:
                                        maxPoT = carCurrPoT
                                        carFound = car
                                        overrideCar = -1                           
                                        if verbose == 1:
                                            ConsoleLog("Car closest to finishing race NOT ON LEAD LAP, setting carFound %d, clearing overrideCar %d"%(carFound, overrideCar))
                                        
                                    if False:
                                        carDistance = carCurrPoT * trackLength
                                        #if the car is within 800 meters of the finish line on any lap
                                        if carDistance > trackLength - 800.0 and carDistance > maxDistance:
                                            maxDistance = carDistance
                                            carFound = car
                                            overrideCar = -1                           
                                            if verbose == 1:
                                                ConsoleLog("Cars finishing race NOT ON LEAD LAP, setting carFound %d, clearing overrideCar %d"%(carFound, overrideCar))
                        
                                    
                        #if carFound >= 0:
                        #    ConsoleLog("Car closest to finishing set to %s"%(safeName(carFound)))
                    except:
                        pass
                        
                   
                strErr = "1750"        
                if verbose == 4:
                    ConsoleLog("%s"%strErr) 
                    
                #search for the closest battle, starting from the top of the grid
                #wait at least X laps before tracking battles?
                orderStrings = []
                if not AppCom.runningorder == "":
                    orderStrings = AppCom.runningorder.split("|")
                elif bIsRace:
                    orderStrings = [str(car) for car in distanceOrder]

                if len(orderStrings) > 0 and bIsRace and now - lastFocusSwitch > (max(minSwitchDelay, driverSwitchDelay - 5)) and ac.getCarState(0, acsys.CS.LapTime) > 0.0 and anyDriverFinishing == 0 and not ABot_Talking:
                    best_score = -1.0
                    battleCar = -1
                    kmh1 = 0
                    kmh2 = 0
                    for pos in range(len(orderStrings) - 1):
                        if not orderStrings[pos] == "" and not orderStrings[pos + 1] == "":
                            car1 = int(orderStrings[pos])
                            car2 = int(orderStrings[pos + 1])
                            if not ac.isCarInPitlane(car1) and not ac.isCarInPitlane(car2):
                                gap = gapBetweenCars(car1, car2)
                                if gap < battleGap:
                                    # Pos weight decay (front priority)
                                    pos_weight = math.pow(positionDecay, pos)
                                    # Gap score: closer is better
                                    gap_score = 1.0 - (gap / battleGap)
                                    score = gap_score * pos_weight
                                    
                                    # Bias to stay on currently focused battle to avoid flickering
                                    if car1 == ac.getFocusedCar() or car2 == ac.getFocusedCar():
                                        score *= 1.15
                                        
                                    if score > best_score:
                                        # Verify speed is reasonable (not crashed or standing)
                                        tmpkmh1 = ac.getCarState(car1, acsys.CS.SpeedKMH)
                                        tmpkmh2 = ac.getCarState(car2, acsys.CS.SpeedKMH)
                                        if tmpkmh1 > minPitKMH and tmpkmh2 > minPitKMH:
                                            # Use the configured battleKMHPercentDiff threshold
                                            if abs((tmpkmh1 - tmpkmh2) / tmpkmh1) * 100 < battleKMHPercentDiff:
                                                best_score = score
                                                battleCar = car2
                                                bestBattleGap = gap
                                                kmh1 = tmpkmh1
                                                kmh2 = tmpkmh2
                    if battleCar >= 0:
                        overrideCar = battleCar
                        focusCarBattling = True
                        lastFocusSwitch = now
                        if verbose == 1:
                            ConsoleLog("Setting overrideCar = battleCar (Score: %0.3f, Gap: %0.2fs) for %s, kmh1 = %0.1f, kmh2 = %0.1f, diff = %0.1f"%(best_score, bestBattleGap, safeName(overrideCar), kmh1, kmh2, abs(kmh1 - kmh2)))
                                
                        #if not car == "":
                        #    ConsoleLog("Checking to see if car %d is in a battle"%(int(car)))
                        #dic["Car%dPosition"%(int(car))] = position #setPositions
                        
                   
                strErr = "1800"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                #how to handle the overrideCar car?
                if overrideCar >= 0:
                    strErr = "1810"
                    if verbose == 4:
                        ConsoleLog("%s"%strErr)
                    
                    if now - lastFocusSwitch > driverSwitchDelay or (ac.isCarInPitlane(overrideCar) and (ac.getCarState(overrideCar,acsys.CS.SpeedKMH) < minPitKMH)):
                        if verbose == 1:
                            ConsoleLog("Clearing overrideCar, now - lastFocusSwitch = %0.1f, driverSwitchDelay = %0.2f, Driver = %s, InPitLane = %d, KMH = %.2f"%(now - lastFocusSwitch, driverSwitchDelay, safeName(overrideCar), ac.isCarInPitlane(overrideCar),ac.getCarState(overrideCar,acsys.CS.SpeedKMH)))
                        overrideCar = -1
                    elif not overrideCar == ac.getFocusedCar(): 
                        if verbose == 1:
                            ConsoleLog("Switching to overrideCar Driver %s CarID %d"%(safeName(overrideCar), overrideCar))
                        lastFocusSwitch = now
                        ac.focusCar(overrideCar)
                        driverSwitched = 1
                        if ac.isCarInPitlane(overrideCar):
                            SetCamera(pitCameraSwitching["Guess1"], "pit lane: %s" % safeName(overrideCar))
                            if verbose > 0:
                                ConsoleLog("Forcing PitLane Cam %d"%(setCamera))
                        else:
                            if focusCarBattling:
                                if dynamicChaseCam == 1:
                                    if bestBattleGap < tvCamThreshold:
                                        SetCamera(3, "battle: side-by-side (gap %.3fs)" % bestBattleGap)
                                        cameraSwitchDelay = 12.0
                                        if verbose > 0:
                                            ConsoleLog("Dynamic Chase Cam (Override): Side-by-side (Gap: %.3fs). Forcing TV Camera." % bestBattleGap)
                                    elif bestBattleGap < chaseOnboardThreshold:
                                        SetCamera(0, "battle: chasing (gap %.3fs)" % bestBattleGap)
                                        cameraSwitchDelay = 6.0
                                        if verbose > 0:
                                            ConsoleLog("Dynamic Chase Cam (Override): Chasing (Gap: %.3fs). Forcing Onboard." % bestBattleGap)
                                    else:
                                        SetCamera(3, "battle: track")
                                        cameraSwitchDelay = 15.0
                                else:
                                    SetCamera(3, "battle: forced TV")
                                    cameraSwitchDelay = 15.0
                                    if verbose > 0:
                                        ConsoleLog("Forcing Track Camera (3) during battle, cameraSwitchDelay = 15")
                                
                                #if verbose == 1:
                                #    ConsoleLog("override car causing camera switch to %d"%(setCamera))
                                    
                elif carFound >= 0:
                    strErr = "1840"
                    if verbose == 4:
                        ConsoleLog("%s"%strErr)
                    
                    if bIsQually == True:
                        if now - lastFocusSwitch > quallySwitchDelay:
                            if verbose == 1:
                                ConsoleLog("using qually optional logic to switch to %s CarID %d"%(safeName(carFound), carFound))
                            ac.focusCar(carFound)
                            driverSwitched = 1
                            lastFocusSwitch = now
                        #give the carFound time after it crosses start/finish to continue being focus car
                        if carFound == ac.getFocusedCar():
                            lastFocusSwitch = now
                    else:
                        if verbose == 1:
                            ConsoleLog("using regular optional logic to switch to %s CarID %d"%(safeName(carFound), carFound))
                        ac.focusCar(carFound)
                        driverSwitched = 1
                        lastFocusSwitch = now                                                            
                elif (not bIsRace or ac.getCarState(0, acsys.CS.LapTime) > 0.0 or countdownCam < 0 or now - sessionStartTime < sessionDelay) and not ABot_Talking:
                    strErr = "1850"
                    if verbose == 4:
                        ConsoleLog("%s"%strErr)
                    
                    #THIS IS MOSTLY THE OLD ACTION CAM CURRENT LOGIC
                    cars[currentId].check()
                    currentId = currentId + 1
                    if currentId >= ac.getCarsCount():
                        strErr = "1860"
                        if verbose == 4:
                            ConsoleLog("%s"%strErr)
                        
                        #after all cars have been checked we'll return to Id=0 and try to remap the cam
                        #ConsoleLog("really need a new car now at %d"%(now))
                        currentId = 0
                        #now = time.clock()
                        if cars and (now - lastFocusSwitch > driverSwitchDelay or not canSwitch(ac.getFocusedCar())):
                            strErr = "1870"
                            if verbose == 4:
                                ConsoleLog("%s"%strErr)
                            
                            #if verbose == 1:
                            #    ConsoleLog("Seeking Next Car: now = %d"%(now))
                            nextCar = cars[0]
                            best_score = -99999.0
                            for car in cars.values():
                                if not canSwitch(car.slotId):
                                    continue
                                for xcar in cars.values():
                                    if car.slotId == xcar.slotId or not canSwitch(xcar.slotId):
                                        continue
                                    distance = car.distanceTo(xcar)
                                    if distance < 10000:
                                        # Score: closer distance is better, front of grid is better.
                                        pos = getPosition(car.slotId)
                                        pos_weight = math.pow(positionDecay, pos)
                                        score = (1000.0 - distance) * pos_weight
                                        
                                        if score > best_score:
                                            best_score = score
                                            nextCar = car
                            
                            strErr = "1895"
                            #we'll focus the (probably) most interesting situation now.
                            #ofc. this can't happen too often, otherwise we'll get into flickering and stuff
                            #so let's find the next focus only if the last switch is older than 5 (or whatever) seconds                    
                            if canSwitch(nextCar.slotId) and (ac.isCarInPitlane(nextCar.slotId) == 0 or allDriversInPits == 1) and not ac.getFocusedCar() == nextCar.slotId:
                                strErr = "1900"
                                #if True: # verbose == 1:
                                if verbose == 1:
                                    ConsoleLog("Setting Focus to Interesting Driver %s CarID %d"%(nextCar.driverName, nextCar.slotId))
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
                
                strErr = "2100"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                if len(preferredDrivers) > 0:
                    if not safeName(ac.getFocusedCar()) in preferredDrivers:
                        for carId in range(0,ac.getCarsCount()):
                            if safeName(carId) in preferredDrivers and ac.isConnected(carId):
                                if verbose == 1:
                                    ConsoleLog("Forcing Preferred Driver %s carId %d"%(safeName(carId), carId))
                                ac.focusCar(carId)
                                driverSwitched = 1
                                lastFocusSwitch = now
                                return True
             

            #camera switching code goes here
            if cameraSwitchingEnabled == 1:
                strErr = "6000"
                if verbose == 4:
                    ConsoleLog("%s"%strErr)
                
                now = time.clock()
                
                #if bIsRace and ac.getCarState(0, acsys.CS.LapTime) == 0.0 and not ac.getCameraMode() == countdownCam and (now - cameraSwitchDelay > cameraSwitchTimer):
                if bIsRace and ac.getCarState(0, acsys.CS.LapTime) == 0.0 and ac.isCarInPitlane(0) and not ac.getCameraMode() == countdownCam and countdownCam >= 0 and now - sessionStartTime > sessionDelay:
                    #once car 0 is in the pits then switch to the countdown
                                  
                    tmpKey = "FirstCarSelected"
                    #can we tighten up the timing on the countdown?  let it pick P1?
                    if ABot_Talking and tmpKey in dic:
                        countdownFocusSwitch = 2.0
                        lastFocusSwitch = now
                        return 1
                                                
                    if verbose > 0:
                        ConsoleLog("Forcing countdownCamera to %d, order is %s"%(countdownCam, order))
                    if driverSwitchingEnabled == 1:
                        #IS THIS CODE IN THE WRONG LOGIC BLOCK? MOVE TO DRIVER SWITCHING?
                        #force the driver to lowest position?
                        for car in range(0,ac.getCarsCount()):
                            if ac.isConnected(car) and not ac.isCarInPitlane(car):
                                #ConsoleLog("Driver %s is in position %d"%(safeName(car), getPosition(car)))
                                if carFound >= 0:
                                    if getPosition(car) < getPosition(carFound):
                                        #ConsoleLog("Resetting car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                        carFound = car
                                        if not ABot_Enabled:
                                            countdownFocusSwitch = 8.0
                                else: 
                                    #ConsoleLog("Initializing car in position %d = Driver %s"%(getPosition(car), safeName(car)))
                                    carFound = car
                                    if not ABot_Enabled:
                                        countdownFocusSwitch = 15.0
                        if carFound >= 0:
                            if True: # verbose == 1:
                                ConsoleLog("CountdownCam focusCar %d = Driver %s in position %d"%(carFound, safeName(carFound), getPosition(carFound)))
                            dic[tmpKey] = 1
                            ac.focusCar(carFound)
                            overrideCar = -1
                            driverSwitched = 1
                            lastFocusSwitch = now

                    #force the F5 cam?
                    if not ac.isCarInPitlane(ac.getFocusedCar()):
                        SetCamera(countdownCam, "countdown")
        
                    
                if bIsRace and ac.getCarState(0, acsys.CS.LapTime) > 0.0 and ac.getCarState(0, acsys.CS.LapTime) < 1000.0 and ac.getCameraMode() == countdownCam:
                    if verbose > 0:
                        ConsoleLog("Forcing Camera to defaultCamera %d"%(defaultCamera))
                    #force the F5 cam?
                    SetCamera(defaultCamera, "default (post-countdown)")


                if defaultSet == 0:
                    defaultSet = 1
                    SetCamera(defaultCamera, "default (init)")
                    if verbose > 0:
                        ConsoleLog("ac.setCameraMode - Setting default camera to %d"%(setCamera))
                    if ac.getCameraMode() != defaultCamera:
                        ConsoleLog("Camera switch -> mode %d (default)" % defaultCamera)
                    ac.setCameraMode(defaultCamera)
                    
                    #ConsoleLog("camera set to %d"%(defaultCamera))

                if not ac.getCameraMode() == setCamera:
                    ConsoleLog("Camera switch -> mode %d (%s)" % (setCamera, cameraReason if cameraReason else "restore"))
                    ac.setCameraMode(setCamera)
                    if setCamera == 1: #car cameras
                        try:
                            if verbose == 1:
                                ConsoleLog("Setting Car Camera Default")
                            #bmw_m3_e30_dtm: 0 = Roof Out Front, 1 = Front Left Tire, 2 = Interior/Driver Out Front, 3 = Passenger Dash Out Front, 4 = Passenger Dash Showing Driver, 5 = Roof Showing Rear
                            ac.setCameraCar(dicCars[ac.getCarName(ac.getFocusedCar())]["Guess1"],ac.getFocusedCar())
                            if verbose == 1:
                                ConsoleLog("SET Car Camera Default to %d completed"%(dicCars[ac.getCarName(ac.getFocusedCar())]["Guess1"]))
                        except:
                            pass
                    
                    
                    cameraSwitchTimer = time.clock()

                #how to verify that car in the pits is using a pit lane camera?
                if ac.isCarInPitlane(ac.getFocusedCar()):
                    #ConsoleLog("ac.getFocusedCar() = %d, DriverName = %s"%(ac.getFocusedCar(), safeName(ac.getFocusedCar())))
                    currentCam = ac.getCameraMode()
                    usingPitCam = 0
                    for intGuess in range(1, len(pitCameraSwitching) + 1):
                        #ConsoleLog("GUESS 100")
                        tmpKey = "Guess%d"%(intGuess)
                        if tmpKey in pitCameraSwitching:
                            if currentCam == pitCameraSwitching[tmpKey]:
                                usingPitCam = 1
                                break
                    if usingPitCam == 0:
                        #for when a driver has focus and drives into the pits
                        if verbose > 0:
                            ConsoleLog("Forcing defaultPitCam %d for %s"%(pitCameraSwitching["Guess1"], safeName(ac.getFocusedCar())))
                        SetCamera(pitCameraSwitching["Guess1"], "pit lane: %s" % safeName(ac.getFocusedCar()))
                            
                            
                    
                    
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
                                SetCamera(pitCameraSwitching[tmpKey], "pit lane (timer)")
                                cameraSwitchDelay = pitCameraDelay["Delay%d"%(intGuess)]
                                if ac.getCameraMode() != setCamera:
                                    ConsoleLog("Camera switch -> mode %d (pit lane: timer)" % setCamera)
                                ac.setCameraMode(setCamera)
                            else:
                                ConsoleLog("Pit Guess%d not found"%(intGuess))                        
                        else:
                            if False:
                                #Dave's old logic
                                #ConsoleLog("GUESS 300")
                                tmpKey = "Guess%d"%(intGuess)
                                if tmpKey in cameraSwitching:
                                    setCamera = cameraSwitching[tmpKey]
                                    cameraSwitchDelay = cameraDelay["Delay%d"%(intGuess)]
                                    if verbose > 0:
                                        ConsoleLog("ac.setCameraMode - Switching to camera %d, cameraSwitchDelay = %0.2f"%(setCamera, cameraSwitchDelay))
                                    ac.setCameraMode(setCamera)
                                else:
                                    ConsoleLog("Guess%d not found"%(intGuess))
                            else:
                                #Jon's adjusted logic
                                #how often to the switch cameras?
                                nextCamReason = "weighted fallback"

                                if ac.getCarState(ac.getFocusedCar(), acsys.CS.LapCount) < 1:
                                    #ConsoleLog("using first lap logic")
                                    intGuess = randInRange(1, len(firstLapSwitching))
                                    #ConsoleLog("GUESS 400")
                                    tmpKey = "Guess%d"%(intGuess)
                                    if tmpKey in firstLapSwitching:
                                        #ConsoleLog("GUESS 400")
                                        nextCam = firstLapSwitching["Guess%d"%(intGuess)]
                                        nextCamReason = "first lap"
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
                                        nextCamReason = "weighted fallback"
                                        cameraSwitchDelay = cameraDelay["Delay%d"%(intGuess)]
                                    else:
                                        ConsoleLog("cameraSwitching[%s] not found"%(tmpKey))
                                
                                # Force Track Cam or Onboard on close battles
                                if forceTrackCamOnCloseBattles == 1 and focusCarBattling:
                                    if dynamicChaseCam == 1:
                                        if bestBattleGap < tvCamThreshold:
                                            nextCam = 3 # Force TV/Track Camera
                                            nextCamReason = "battle: side-by-side (gap %.3fs)" % bestBattleGap
                                            cameraSwitchDelay = max(10.0, cameraSwitchDelay)
                                            if verbose == 1:
                                                ConsoleLog("Dynamic Chase Cam: Side-by-side (Gap: %.3fs). Forcing TV Camera." % bestBattleGap)
                                        elif bestBattleGap < chaseOnboardThreshold:
                                            nextCam = 0 # Force Cockpit
                                            nextCamReason = "battle: chasing (gap %.3fs)" % bestBattleGap
                                            cameraSwitchDelay = max(6.0, cameraSwitchDelay)
                                            if verbose == 1:
                                                ConsoleLog("Dynamic Chase Cam: Chasing (Gap: %.3fs). Forcing Onboard." % bestBattleGap)
                                        else:
                                            nextCam = 3 # Track Cam
                                            nextCamReason = "battle: track"
                                            cameraSwitchDelay = max(12.0, cameraSwitchDelay)
                                    else:
                                        nextCam = 3 # Track Cam
                                        nextCamReason = "battle: forced TV"
                                        cameraSwitchDelay = max(12.0, cameraSwitchDelay)
                                    
                                if True: # tmpKey in cameraSwitching:                        
                                    currentCam = ac.getCameraMode()
                                    
                                    if verbose == 1:
                                        ConsoleLog("Switching to camera %d, cameraSwitchDelay = %0.1f"%(nextCam, cameraSwitchDelay))
                                        
                                    if nextCam == 0 and currentCam == 0:
                                        #ConsoleLog("in next cam - currentcam is set to %d"%(currentCam))
                                        if verbose == 1:
                                            ConsoleLog("in next cam - nextcam is set to %d"%(nextCam))
                                    elif nextCam == 1:
                                        if True:
                                            #we need to pick a random camera from dicCars
                                            #dicCars[carName]
                                            carName = ac.getCarName(currentId)

                                            closestCarBehind = -1
                                            closestPoTGap = 1.0
                                            tempDistanceGap = 9999.0
                                            #forcibly select last cam when closest car behind is within some distance, otherwise pick a random cam
                                            for tmpCar in range(ac.getCarsCount()):
                                                if ac.isConnected(tmpCar) and not tmpCar == currentId:
                                                    currPoT = ac.getCarState(currentId,acsys.CS.NormalizedSplinePosition)
                                                    tempPoT = ac.getCarState(tmpCar,acsys.CS.NormalizedSplinePosition)
                                                    if abs(currPoT - tempPoT) < closestPoTGap:
                                                        if tempPoT < currPoT:
                                                            closestCarBehind = tmpCar
                                                            closestPoTGap = abs(currPoT - tempPoT)
                                                            tempDistanceGap = gapBetweenCars(currentId, closestCarBehind)                                                        
                                                        else:
                                                            closestPoTGap = abs(currPoT - tempPoT)
                                                            closestCarBehind = -1
                                                            tempDistanceGap = 9999.0
                                                        
                                            if tempDistanceGap > 2.0 and tempDistanceGap < 100.0 and ac.getCarState(currentId, acsys.CS.LapCount) > 0:
                                                ConsoleLog("Car Behind %0.1f, Forcing the last car cam"%(tempDistanceGap))
                                                intGuess = len(dicCars[carName])
                                            else:
                                                #no randomly picking the last car cam?
                                                intGuess = randInRange(1, len(dicCars[carName]) - 1)
                                                
                                            #ConsoleLog("GUESS 600")
                                            tmpKey = "Guess%d"%(intGuess)
                                            if verbose == 1:
                                                ConsoleLog("Car Camera tmpkey = %s"%(tmpKey))
                                            if tmpKey in dicCars[carName]:
                                                randomCamInt = dicCars[carName][tmpKey] #    randInRange(0,carCamCount)
                                                ac.setCameraCar(randomCamInt,ac.getFocusedCar())
                                                SetCamera(nextCam, nextCamReason)
                                                if verbose > 0:
                                                    ConsoleLog("Car Cameras setCamera = %d, carCamera is set to %d"%(setCamera, randomCamInt))
                                            else:
                                                ConsoleLog("dicCars[%s][%s] NOT FOUND"%(carName,tmpKey))
                                                
                                        else:
                                            carCamCount = ac.getCameraCarCount(currentId)
                                            randomCamInt = randInRange(0,carCamCount)
                                            ac.setCameraCar(randomCamInt,ac.getFocusedCar())
                                            SetCamera(nextCam, nextCamReason)
                                            if verbose > 0:
                                                ConsoleLog("carCamera is set to %d"%(randomCamInt))
                                    else:
                                        SetCamera(nextCam, nextCamReason)
                                        if ac.getCameraMode() != setCamera:
                                            ConsoleLog("Camera switch -> mode %d (%s)" % (setCamera, nextCamReason))
                                        ac.setCameraMode(setCamera)
                                        
                                else:
                                    ConsoleLog("Guess%d not found"%(intGuess))

                if noDrivableCamWithVirtualMirror == 1 and (ac.getCameraMode() == 0 or ac.getCameraMode() == 2):
                    #do not allow the cockpit or the drivable cameras when a virtual mirror is detected
                    SetCamera(1, "virtual mirror override")
                    try:
                        if verbose > 0:
                            ConsoleLog("noDrivableCamWithVirtualMirror == 1 not allowing cockpit/drivable cams")
                        #bmw_m3_e30_dtm: 0 = Roof Out Front, 1 = Front Left Tire, 2 = Interior/Driver Out Front, 3 = Passenger Dash Out Front, 4 = Passenger Dash Showing Driver, 5 = Roof Showing Rear
                        ac.setCameraCar(dicCars[ac.getCarName(ac.getFocusedCar())]["Guess1"],ac.getFocusedCar())
                        ConsoleLog("Camera switch -> mode 1 (virtual mirror override)")
                        ac.setCameraMode(setCamera)
                        if verbose > 0:
                            ConsoleLog("ac.setCameraMode - SET Car Camera Default to %d completed"%(dicCars[ac.getCarName(ac.getFocusedCar())]["Guess1"]))
                    except:
                        pass
                    

                        
                        
            #else:
            #    ConsoleLog("no camera switching defined")
            
        return True
                
    except Exception as e:
        ConsoleLog("Error(%s): %s"%(strErr, e))

#I'm assuming we can put this in both .PY files        
def gapBetweenCars(car1, car2):
    trackLength = ac.getTrackLength(0)

    carsGap = 999.0
    
    try:
        #closestCarGap
        car1LapCount = ac.getCarState(car1, acsys.CS.LapCount)
        car1CurrPoT = ac.getCarState(car1,acsys.CS.NormalizedSplinePosition)
        car1Distance = (car1LapCount + car1CurrPoT) * trackLength

        car2LapCount = ac.getCarState(car2, acsys.CS.LapCount)
        car2CurrPoT = ac.getCarState(car2,acsys.CS.NormalizedSplinePosition)
        car2Distance = (car2LapCount + car2CurrPoT) * trackLength
        
        carsGap = abs(car1Distance - car2Distance) / (((ac.getCarState(car1,acsys.CS.SpeedKMH) + ac.getCarState(car2,acsys.CS.SpeedKMH)) / 2) / 3.6)

    except:
        pass
        
    #ConsoleLog("Cars Gap = %0.2f"%(carsGap))
    
    return carsGap
        
        
def InitCars():
    global cars

    carCount = ac.getCarsCount()

    cars = {}
    for car in range(0,carCount):
        cars[car] = AutoCamCar.AutoCamCar(car)
        #ConsoleLog("Initializing cars[%d] for %s"%(car, cars[car].driverName))
        
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
                    #ac.console('loadPitEntryToDict Read Pit_Entry Error (logged to file)')
                    #ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                    ConsoleLog(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
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
        
    