from abc import ABCMeta, abstractmethod
from typing import List, Dict

class collectorI:
    __metaclass__ = ABCMeta

    #Get Device Id
    @abstractmethod
    def getID(self) -> str: raise NotImplementedError

    #Check id new data has been collected
    @abstractmethod
    def dataCollected(self) -> str: raise NotImplementedError

    #Collect new data
    @abstractmethod
    def collectData(self) -> None: raise NotImplementedError

    #Collect data (deprecated)
    @abstractmethod
    def retrieveData(self,*argv) -> tuple: raise NotImplementedError

    #Get collected data
    @abstractmethod
    def getData(self) -> str: raise NotImplementedError

    #Get collected data (only telemetry)
    @abstractmethod
    def getPureData(self) -> str: raise NotImplementedError

    #Set TTL of telemetry data on cloud
    @abstractmethod
    def setRetentionPolicy(self) -> str: raise NotImplementedError

    #Get a property value from synced desired properties
    @abstractmethod
    def getPropertyData(self) -> List[Dict]: raise NotImplementedError

    #Handle desired property changes
    @abstractmethod
    def handleDesiredProperties(self, twinPatch: Dict): raise NotImplementedError
