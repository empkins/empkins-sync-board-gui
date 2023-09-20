"""Handles communication with the EmpkinS Sync Board."""
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Union

from PySide2 import QtCore
from PySide2.QtCore import QObject, Signal
from PySide2.QtWidgets import QApplication, QProgressBar
from serial import Serial
from serial.serialutil import SerialException

from empkins_sync_board_gui.config import HardwareConfig
from empkins_sync_board_gui.constants import (
    BOARD_ERROR_LIST,
    BOARD_EVENT_LIST,
    BOARD_STATUS_LIST,
    MESSAGE_ERROR,
    MESSAGE_EVENT,
    MESSAGE_FILE_PATH,
    MESSAGE_HELLO,
    MESSAGE_STATUS,
    PAYLOAD_TIME,
    PAYLOAD_TYPE,
)

logging.basicConfig(filename="logs/board_connector.log", level=logging.DEBUG)


class SyncBoardMessageSignal(QObject):
    """Signal for notifying user about messages from the board."""

    sig = Signal(dict)


class BoardConnector(QtCore.QThread):
    """Class for handling communication with the EmpkinS Sync Board."""

    HELLO_REQUEST = bytearray(bytes.fromhex("aa") + bytes.fromhex("ff"))
    HELLO_RESPONSE = bytearray(bytes.fromhex("aa") + bytes.fromhex("aa"))
    HELLO_LENGTH = 2

    def __init__(self, parent, config: HardwareConfig, mock: bool = True, timeout=3):
        super().__init__(parent=parent)
        self.error_signal = SyncBoardMessageSignal()
        self.status_signal = SyncBoardMessageSignal()
        self.event_signal = SyncBoardMessageSignal()
        self.config = config
        self.message_dict = {}
        self._mock = mock
        self._ser = None
        self._port = ""
        self._timeout = timeout

    def setup(self, progress: QProgressBar):
        """Initialize the board connector."""
        logging.debug("Connector setup")
        try:
            self._setup_message_dict()
        except Exception as e:  # noqa: BLE001
            raise BoardConnectionError(
                f"Reading of message file failed with the following error: {e}. "
                f"Make sure a file {Path(MESSAGE_FILE_PATH[self.config.version]).absolute()} exists!"
            ) from e
        if not self._mock:
            try:
                self._port = self._get_port_from_list(BoardConnector._get_port_list(), progress)
                self._ser = Serial(self._port, timeout=self._timeout)
                logging.debug(f"Serial openend: {self._ser}")
            except (OSError, SerialException) as e:
                raise BoardConnectionError("No suitable device found!") from e
        else:
            progress.setValue(100)  # make progress bar disappear

    def _setup_message_dict(self):
        try:
            with Path.open(Path(MESSAGE_FILE_PATH[self.config.version])) as fp:
                self.message_dict = json.load(fp)
        except Exception:
            raise

    def run(self) -> None:
        """Run main loop of the board connector thread."""
        while True:
            if self._mock:
                pass
                """
                time.sleep(5)
                self._handle_event_message(187)
                time.sleep(5)
                self._handle_event_message(4)
                time.sleep(5)
                self._handle_event_message(204)
                time.sleep(20)
                """
            else:
                logging.debug("Waiting for board messages")
                out = self._ser.read(self.config.message_size)
                logging.debug(f"Board message received: {out}")
                self._read_data(out)

            if self.isInterruptionRequested():
                logging.debug("Connector thread received interruption request")
                return

    def _read_data(self, out: bytearray):
        if len(out) == self.config.message_size and out[0] == self.message_dict[MESSAGE_HELLO]:
            if out[1] == self.message_dict[MESSAGE_ERROR]:
                self._handle_error_message(out[2])
            elif out[1] == self.message_dict[MESSAGE_EVENT] or out[1] == self.message_dict[MESSAGE_STATUS]:
                self._handle_event_message(out[2])
            else:
                logging.debug(f"Unknown message type {out[1]}")
                self.error_signal.sig.emit(self.message_dict[BOARD_ERROR_LIST][0])

    def _handle_error_message(self, error_type: int):
        if error_type < len(self.message_dict[BOARD_ERROR_LIST]):
            payload = self._create_signal_payload(self.message_dict[BOARD_ERROR_LIST][error_type], time.time())
            self.error_signal.sig.emit(payload)
        else:
            logging.debug(f"Unknown error type {error_type}")
            payload = self._create_signal_payload(self.message_dict[BOARD_ERROR_LIST][0], time.time())
            self.error_signal.sig.emit(payload)

    def _handle_event_message(self, event_type: int):
        if event_type in self.message_dict[BOARD_STATUS_LIST]:
            payload = self._create_signal_payload(self.message_dict[str(event_type)], time.time())
            self.status_signal.sig.emit(payload)
        elif event_type in self.message_dict[BOARD_EVENT_LIST]:
            payload = self._create_signal_payload(self.message_dict[f"{event_type:02}"], time.time())
            self.event_signal.sig.emit(payload)
        else:
            logging.debug(f"Unknown event type {event_type}")
            self.error_signal.sig.emit(self.message_dict[BOARD_ERROR_LIST][0])

    @staticmethod
    def _create_signal_payload(msg_type: str, msg_time: float) -> Dict[str, Union[str, float]]:
        return {PAYLOAD_TYPE: msg_type, PAYLOAD_TIME: msg_time}

    @staticmethod
    def _get_port_list() -> List[str]:
        if sys.platform.startswith("win"):
            from serial.tools.list_ports import comports

            ports = [p.name for p in comports()]
        elif sys.platform.startswith("linux"):
            import glob

            ports = glob.glob("/dev/tty[A-Za-z]*")
        else:
            raise BoardConnectionError(f"Sorry, your OS {sys.platform} is currently not supported!")
        logging.debug(f"Port list: {ports}")
        return ports

    def _get_port_from_list(self, port_list: List[str], progress: QProgressBar) -> str:
        logging.debug("retrieving port from port list")
        for i, port in enumerate(port_list):
            progress.setValue(int(i / len(port_list) * 100))
            # needs to be called manually after every progress update bc. main event loop is blocked
            QApplication.processEvents()
            try:
                ser = Serial(port, timeout=1)
            except SerialException:
                logging.debug(f"No permission for {port}")
                # when logged-in user does not have the permission to read/write for this port
                continue
            packet = self.HELLO_REQUEST  # whoami message
            ser.write(packet)
            logging.debug("Hello was sent")
            resp = ser.read(self.HELLO_LENGTH)  # expecting "\xaa\xaa" as response
            logging.debug("Reading was finished")
            if resp == self.HELLO_RESPONSE:
                logging.debug(f"Correct port found: {port}")
                progress.setValue(100)
                QApplication.processEvents()
                return port
        logging.debug("No port found")
        progress.setValue(100)
        QApplication.processEvents()
        raise BoardConnectionError("No port seems to be connected to SyncBoard!")

    def send_command(self, cmd: bytes):
        """Send a command to the board."""
        logging.debug(f"Sending: {cmd}")
        print(f"Sending: {cmd}")
        if not self._mock:
            self._ser.flush()
            self._ser.write(bytearray(cmd))


class BoardConnectionError(Exception):
    """Exception raised when no board is connected."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)
