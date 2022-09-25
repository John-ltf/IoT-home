from abc import ABCMeta, abstractmethod
from typing import List, Dict

class collectorI:
    __metaclass__ = ABCMeta

    @abstractmethod
    def getID(self) -> str: raise NotImplementedError
    @abstractmethod
    def dataCollected(self) -> str: raise NotImplementedError
    @abstractmethod
    def collectData(self) -> None: raise NotImplementedError
    @abstractmethod
    def retrieveData(self,*argv) -> tuple: raise NotImplementedError
    @abstractmethod
    def getData(self) -> str: raise NotImplementedError
    @abstractmethod
    def getPureData(self) -> str: raise NotImplementedError
    @abstractmethod
    def setRetentionPolicy(self) -> str: raise NotImplementedError
    @abstractmethod
    def getPropertyData(self) -> List[Dict]: raise NotImplementedError
    @abstractmethod
    def handleDesiredProperties(self, twinPatch: Dict): raise NotImplementedError
