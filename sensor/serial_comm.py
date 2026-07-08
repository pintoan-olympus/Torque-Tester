import serial
import serial.tools.list_ports
import re
import time
import threading
from utils.logger import get_logger
from sensor.sensor_interface import TorqueSensorInterface

logger = get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# ng-TTS50-xu frame protocol
#   STX  = 0x06
#   ETX  = 0x08  (backspace / ETX used as frame terminator)
#   Payload: <mode(1)><status(10)><sci torque>...
#   Example payload: AIDLE      +00123E-02+000000E-0111000TT0A4A+00000E-02+00000E-05
#   First scientific field after the 11-char header is the torque in cNm.
# ──────────────────────────────────────────────────────────────────────────────
_STX = 0x06
_ETX = 0x08
_SCI_RE = re.compile(rb'([+-]\d+E[+-]\d{1,3})', re.IGNORECASE)
_MAX_FRAME = 256      # bytes – discard frames longer than this (noise)
_MAX_BUF   = 4096     # ring buffer cap


def _parse_torque(payload: bytes) -> float | None:
    """
    Extract the torque value from a ng-TTS50-xu frame payload.

    Frame layout (after stripping STX/ETX delimiters):
      Byte 0      : mode char  ('A')
      Bytes 1-10  : status field – EITHER text (e.g. 'IDLE      ') when idle
                    OR a 10-char scientific value (e.g. '+08021E-05') when measuring.
      Bytes 11+   : additional fields (velocity, flags, counter …)

    Strategy: skip only the mode byte, then find the FIRST scientific-notation
    match.  The regex will skip any non-numeric status text automatically.
    Returns the value in whatever unit the sensor uses (shown in the raw monitor
    so the user can verify scaling).
    """
    try:
        body = payload[1:]          # skip mode char only
        m = _SCI_RE.search(body)
        if m:
            val = float(m.group(1))
            return round(max(-500.0, min(500.0, val)), 4)
    except Exception:
        pass
    return None


class TorqueSensorSerial(TorqueSensorInterface):

    def __init__(self, port="COM1", baudrate=9600, bytesize=8,
                 parity="N", stopbits=1, timeout=0.2, value_pattern=None):
        self.port     = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity   = parity
        self.stopbits = stopbits
        self.timeout  = timeout          # short timeout → responsive reads
        self.value_pattern = value_pattern
        self._compiled_pattern = re.compile(value_pattern) if value_pattern else None

        self._serial: serial.Serial | None = None
        self._lock   = threading.Lock()
        self._current_torque = 0.0
        self._peak_torque    = 0.0
        self._running        = False
        self._thread: threading.Thread | None = None
        self._connected      = False     # explicit flag, avoids relying on .is_open
        self._last_raw_frame = b''       # last raw frame payload for diagnostics

    # ── port enumeration ──────────────────────────────────────────────────────
    @staticmethod
    def list_available_ports():
        return [p.device for p in serial.tools.list_ports.comports()]

    # ── mapping helpers ───────────────────────────────────────────────────────
    def _map_parity(self, p):
        return {"N": serial.PARITY_NONE,
                "E": serial.PARITY_EVEN,
                "O": serial.PARITY_ODD}.get(str(p), serial.PARITY_NONE)

    def _map_bytesize(self, b):
        return {7: serial.SEVENBITS,
                8: serial.EIGHTBITS}.get(int(b), serial.EIGHTBITS)

    def _map_stopbits(self, s):
        return {1:   serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2:   serial.STOPBITS_TWO}.get(float(s), serial.STOPBITS_ONE)

    # ── connection ────────────────────────────────────────────────────────────
    def connect(self) -> bool:
        logger.info(f"Serial: Connecting to {self.port} "
                    f"({self.baudrate}bps, {self.bytesize}{self.parity}{self.stopbits})…")
        for attempt in range(1, 4):
            try:
                self._serial = serial.Serial(
                    port      = self.port,
                    baudrate  = self.baudrate,
                    bytesize  = self._map_bytesize(self.bytesize),
                    parity    = self._map_parity(self.parity),
                    stopbits  = self._map_stopbits(self.stopbits),
                    timeout   = self.timeout,
                )
                logger.info(f"Serial: Connected to {self.port} (attempt {attempt}/3)")
                with self._lock:
                    self._current_torque = 0.0
                    self._peak_torque    = 0.0
                    self._connected      = True
                self._running = True
                self._thread = threading.Thread(target=self._read_loop, daemon=True)
                self._thread.start()
                return True

            except PermissionError as e:
                if attempt < 3:
                    logger.warning(f"Serial: Access denied on {self.port} "
                                   f"(attempt {attempt}/3) – retrying in 0.5 s… ({e})")
                    time.sleep(0.5)
                else:
                    logger.error(f"Serial: Permanent access denied on {self.port} – {e}")
                    self._serial = None
                    return False
            except Exception as e:
                logger.error(f"Serial: Cannot open {self.port} – {e}")
                self._serial = None
                return False
        return False

    def disconnect(self) -> None:
        self._running = False
        with self._lock:
            self._connected = False
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None
        logger.info(f"Serial: Disconnected from {self.port}")

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    # ── background read loop ──────────────────────────────────────────────────
    def _read_loop(self):
        """
        Bulk-read from serial, search for 0x06…0x08 frames, parse torque.
        Using bulk reads (in_waiting) is far faster and more reliable than
        byte-by-byte reads, and handles backpressure gracefully.
        """
        logger.debug(f"Serial: Read thread started for {self.port}")
        buf = bytearray()
        frames_parsed = 0

        while self._running:
            # ── guard: is port still open? (with auto-reconnect retry) ─────
            if not (self._serial and self._serial.is_open):
                with self._lock:
                    self._connected = False
                    self._current_torque = 0.0
                
                logger.warning(f"Serial: Connection lost or not open on {self.port}. Attempting auto-reconnect...")
                try:
                    self._serial = serial.Serial(
                        port      = self.port,
                        baudrate  = self.baudrate,
                        bytesize  = self._map_bytesize(self.bytesize),
                        parity    = self._map_parity(self.parity),
                        stopbits  = self._map_stopbits(self.stopbits),
                        timeout   = self.timeout,
                    )
                    with self._lock:
                        self._connected = True
                        self._current_torque = 0.0
                        self._peak_torque = 0.0
                    logger.info(f"Serial: Reconnected successfully to {self.port}!")
                except Exception as reconnect_err:
                    logger.debug(f"Serial: Reconnect attempt failed on {self.port}: {reconnect_err}")
                    time.sleep(2.0)  # Back-off for 2 seconds before retrying
                continue


            try:
                if self._compiled_pattern:
                    # Custom line-based parsing using the compiled regex
                    line_bytes = self._serial.readline()
                    if line_bytes:
                        with self._lock:
                            self._last_raw_frame = line_bytes
                        line_str = line_bytes.decode('utf-8', errors='ignore').strip()
                        m = self._compiled_pattern.search(line_str)
                        if m:
                            val_str = m.group(1) if m.groups() else m.group(0)
                            try:
                                val = float(val_str)
                                with self._lock:
                                    self._current_torque = val
                                    if val > self._peak_torque:
                                        self._peak_torque = val
                                frames_parsed += 1
                                if frames_parsed == 1 or frames_parsed % 500 == 0:
                                    logger.debug(f"Serial (Custom): Parsing OK – {val:.2f} cNm "
                                                 f"(frame #{frames_parsed})")
                            except ValueError:
                                pass
                else:
                    # Standard ng-TTS50-xu STX/ETX logic
                    # Read all available bytes; at least try to read 1 (blocks up to timeout)
                    waiting = self._serial.in_waiting
                    n_read  = max(1, min(waiting, 512))
                    data = self._serial.read(n_read)

                    if data:
                        buf.extend(data)

                        # Cap ring buffer to avoid unbounded growth
                        if len(buf) > _MAX_BUF:
                            # Trim to the last STX so we start clean
                            last_stx = buf.rfind(_STX)
                            buf = buf[last_stx:] if last_stx >= 0 else bytearray()

                        # ── Extract complete frames from the buffer ────────────
                        while True:
                            stx_pos = buf.find(_STX)
                            if stx_pos == -1:
                                buf.clear()
                                break

                            # Discard anything before STX
                            if stx_pos > 0:
                                buf = buf[stx_pos:]

                            etx_pos = buf.find(_ETX, 1)
                            if etx_pos == -1:
                                break  # Frame incomplete – wait for more data

                            frame_payload = bytes(buf[1:etx_pos])  # content between STX and ETX
                            buf = buf[etx_pos + 1:]                # advance past ETX

                            if len(frame_payload) > _MAX_FRAME:
                                continue  # noise / garbage frame

                            val = _parse_torque(frame_payload)
                            # Always store the last raw frame for the live monitor
                            with self._lock:
                                self._last_raw_frame = frame_payload
                            if val is not None:
                                # Scale parsed torque from Nm (sensor default) to cNm (application default)
                                scaled_val = round(val * 100.0, 2)
                                with self._lock:
                                    self._current_torque = scaled_val
                                    if scaled_val > self._peak_torque:
                                        self._peak_torque = scaled_val
                                frames_parsed += 1
                                if frames_parsed == 1 or frames_parsed % 500 == 0:
                                    logger.debug(f"Serial: Parsing OK – {scaled_val:.2f} cNm "
                                                 f"(frame #{frames_parsed})")

            except Exception as e:
                if self._running:
                    logger.error(f"Serial: Read error – {e}")
                with self._lock:
                    self._connected = False
                    self._current_torque = 0.0
                try:
                    if self._serial:
                        self._serial.close()
                except Exception:
                    pass
                time.sleep(2.0)  # back-off before next loop iteration

        logger.debug(f"Serial: Read thread stopped (parsed {frames_parsed} frames total)")

    # ── public interface ──────────────────────────────────────────────────────
    def read_torque(self) -> float:
        with self._lock:
            return self._current_torque if self._connected else 0.0

    def get_peak(self) -> float:
        with self._lock:
            return round(self._peak_torque, 3) if self._connected else 0.0

    def reset_peak(self) -> None:
        with self._lock:
            self._peak_torque = 0.0
        logger.debug("Serial: Peak reset")

    def get_last_raw_frame(self) -> str:
        """Return the last received raw frame payload as a printable string."""
        with self._lock:
            raw = self._last_raw_frame
        try:
            return raw.decode('ascii', errors='replace')
        except Exception:
            return repr(raw)

    def get_status_info(self) -> dict:
        connected = self.is_connected()
        dev_name = f"Custom ({self.value_pattern})" if self.value_pattern else "ng-TTS50-xu (Serial)"
        if connected:
            return {
                "device"  : dev_name,
                "port"    : self.port,
                "baudrate": self.baudrate,
                "config"  : f"{self.bytesize}{self.parity}{self.stopbits}",
                "status"  : "CONNECTED",
            }
        return {
            "device": dev_name,
            "port"  : self.port,
            "status": "DISCONNECTED",
        }
