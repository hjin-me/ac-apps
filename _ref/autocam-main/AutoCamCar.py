import time
import math
import ac
import acsys

def ConsoleLog(message):
    ac.console("AutoCamCar: %s"%(message))
    ac.log("AutoCamCar: %s"%(message))
    #ac.console("AutoCam: " + message)
    #ac.log("AutoCam: " + message)            

def safeName(car):
    validFilenameChars = "-_() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(c for c in ac.getDriverName(car) if c in validFilenameChars)
    
class AutoCamCar(object):
    slotId = 0
    driverName=''
    carName=''
    distanceToNextCar=0.0
    currentWorldPosition = None
    splineposition = 0.0
    laps = 0
    focusCount = 0

    def __init__(self,carId):
        self.slotId = carId
        self.driverName = safeName(carId)
        self.carName = ac.getCarName(carId)

        #ac.log("actionCam::InitCar {}-{} on {}".format(self.slotId, self.driverName, self.carName))

    def check(self):
        #first we'll check wether the slot has been re-assigned
        if self.driverName != safeName(self.slotId):
            laps = 0
            self.driverName = safeName(self.slotId)

        self.currentWorldPosition = ac.getCarState(self.slotId, acsys.CS.WorldPosition)
        self.splineposition = ac.getCarState(self.slotId, acsys.CS.NormalizedSplinePosition)


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
        
        
    def distanceTo(self, car):
        strErr = "100"
        try:
            strErr = "200"
            #self comparison: bad
            if self.slotId == car.slotId:
                return 10002

            strErr = "300"
            #return the vector length between both world positions
            #but we don't want to watch pitted cars:
            if ac.isCarInPit(self.slotId) == 1:
                return 10001

            strErr = "400"
            #same for standing cars
            if ac.getCarState(self.slotId, acsys.CS.SpeedKMH) < 1:
                return 10000

            strErr = "500 self %s, car %s"%(self.driverName, car.driverName)
            distance = math.hypot(car.currentWorldPosition[0] - self.currentWorldPosition[0], car.currentWorldPosition[2] - self.currentWorldPosition[2])

            strErr = "600"
            #closeups in the pitlane should be widely multiplied
            if ac.isCarInPitline(car.slotId) == 1:
                distance = distance * 50

            strErr = "700"
            return distance
        except:
            ConsoleLog("distanceTo %s"%(strErr))
            pass
            
        return 10003