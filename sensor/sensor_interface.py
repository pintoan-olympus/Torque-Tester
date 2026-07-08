from abc import ABC, abstractmethod

class TorqueSensorInterface(ABC):
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection with the sensor."""
        pass
        
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection with the sensor."""
        pass
        
    @abstractmethod
    def read_torque(self) -> float:
        """Read the current instantaneous torque value in cNm."""
        pass
        
    @abstractmethod
    def get_peak(self) -> float:
        """Get the peak torque measured since connection or last reset in cNm."""
        pass
        
    @abstractmethod
    def reset_peak(self) -> None:
        """Reset the peak torque value back to zero."""
        pass
        
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is currently active."""
        pass
        
    @abstractmethod
    def get_status_info(self) -> dict:
        """Get diagnostic/status information about the sensor connection."""
        pass
