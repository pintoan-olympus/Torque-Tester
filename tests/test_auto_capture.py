import unittest
from engine.auto_capture import AutoCaptureStateMachine, AutoCaptureState

class TestAutoCaptureStateMachine(unittest.TestCase):
    def setUp(self):
        # Target = 10.0 cNm -> start threshold max(0.5, 1.5) = 1.5 cNm
        # reset threshold max(0.3, 0.8) = 0.8 cNm
        self.sm = AutoCaptureStateMachine(target_value=10.0, snapback_ratio=0.85, min_delta_cnm=0.5)

    def test_initial_state_is_idle(self):
        self.assertEqual(self.sm.state, AutoCaptureState.IDLE)
        self.assertEqual(self.sm.tracked_peak, 0.0)

    def test_reading_below_threshold_remains_idle(self):
        event = self.sm.process_reading(1.0)
        self.assertEqual(event.state, AutoCaptureState.IDLE)
        self.assertFalse(event.sample_captured)

    def test_rising_edge_transitions_to_rising(self):
        event = self.sm.process_reading(2.0)
        self.assertEqual(event.state, AutoCaptureState.RISING)
        self.assertEqual(event.tracked_peak, 2.0)

    def test_peak_tracking_in_rising_state(self):
        self.sm.process_reading(2.0)
        event = self.sm.process_reading(5.0)
        self.assertEqual(event.state, AutoCaptureState.RISING)
        self.assertEqual(event.tracked_peak, 5.0)

    def test_snapback_triggers_sample_capture(self):
        self.sm.process_reading(2.0)
        self.sm.process_reading(10.0)
        # Snapback: reading drops below 10.0 * 0.85 = 8.5 cNm with delta >= 0.5
        event = self.sm.process_reading(8.0)
        self.assertEqual(event.state, AutoCaptureState.CAPTURED)
        self.assertTrue(event.sample_captured)
        self.assertEqual(event.captured_value, 10.0)

    def test_wait_cooldown_resets_to_idle(self):
        self.sm.process_reading(2.0)
        self.sm.process_reading(10.0)
        self.sm.process_reading(8.0) # CAPTURED
        
        # Load drops below reset threshold 0.8 cNm
        event = self.sm.process_reading(0.2)
        self.assertEqual(event.state, AutoCaptureState.IDLE)
        self.assertEqual(event.tracked_peak, 0.0)

if __name__ == "__main__":
    unittest.main()
