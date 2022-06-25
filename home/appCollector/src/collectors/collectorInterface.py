from abc import ABCMeta, abstractmethod

class collectorI:
    __metaclass__ = ABCMeta

    @abstractmethod
    def collectData(self): raise NotImplementedError
    @abstractmethod
    def getData(self) -> str: raise NotImplementedError
    @abstractmethod
    def getID(self) -> str: raise NotImplementedError
    @abstractmethod
    def dataCollected(self) -> str: raise NotImplementedError
