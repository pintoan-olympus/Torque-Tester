from dataclasses import dataclass

class AutoCaptureState:
    IDLE = "IDLE"
    RISING = "RISING"
    CAPTURED = "CAPTURED"


@dataclass
class CaptureEvent:
    state: str
    tracked_peak: float
    sample_captured: bool = False
    captured_value: float = 0.0


class AutoCaptureStateMachine:
    """
    Pure business logic state machine for automatic torque sample capture.
    Handles IDLE -> RISING -> CAPTURED -> IDLE transitions based on torque readings and snap-back thresholds.
    """
    def __init__(self, target_value: float, snapback_ratio: float = 0.85, min_delta_cnm: float = 0.5):
        self.target_value = target_value
        self.snapback_ratio = snapback_ratio
        self.min_delta_cnm = min_delta_cnm
        
        self.state = AutoCaptureState.IDLE
        self.tracked_peak = 0.0
        
        self.start_threshold = max(0.5, 0.15 * target_value)
        self.reset_threshold = max(0.3, 0.08 * target_value)

    def process_reading(self, abs_torque: float) -> CaptureEvent:
        sample_captured = False
        captured_val = 0.0

        if self.state == AutoCaptureState.IDLE:
            if abs_torque >= self.start_threshold:
                self.state = AutoCaptureState.RISING
                self.tracked_peak = abs_torque
                
        elif self.state == AutoCaptureState.RISING:
            if abs_torque > self.tracked_peak:
                self.tracked_peak = abs_torque
            
            # Snap back condition
            if abs_torque < self.tracked_peak * self.snapback_ratio and (self.tracked_peak - abs_torque >= self.min_delta_cnm):
                self.state = AutoCaptureState.CAPTURED
                sample_captured = True
                captured_val = self.tracked_peak
                
        elif self.state == AutoCaptureState.CAPTURED:
            if abs_torque < self.reset_threshold:
                self.state = AutoCaptureState.IDLE
                self.tracked_peak = 0.0

        return CaptureEvent(
            state=self.state,
            tracked_peak=self.tracked_peak,
            sample_captured=sample_captured,
            captured_value=captured_val
        )

    def reset(self, new_state: str = AutoCaptureState.IDLE):
        self.state = new_state
        self.tracked_peak = 0.0
