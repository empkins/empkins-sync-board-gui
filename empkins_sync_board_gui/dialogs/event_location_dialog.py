"""Dialog for setting event log file location."""
from datetime import datetime
from pathlib import Path

from PySide2.QtWidgets import QCompleter, QDialog, QDirModel, QFileDialog, QWidget

from empkins_sync_board_gui.components import Ui_EventLogDialog
from empkins_sync_board_gui.constants import DEFAULT_EVENT_LOG_PATH, EVENT_LOG_FILE_TYPE, EVENT_LOG_HEADER


class EventLogDialog(QDialog):
    """Dialog for setting event log file location."""

    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.ui = Ui_EventLogDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.create_log_file)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.select_location_button.clicked.connect(self.open_log_file_dialog)
        self.ui.log_path.editingFinished.connect(self.validate_input)
        self.ui.log_path.hasAcceptableInput()
        # set event log path
        self.event_log_path = None
        self._set_default_path()
        self.ui.log_path.setText(str(self.event_log_path))
        # set line edit options
        config_completer = QCompleter(self)
        config_completer.setModel(QDirModel(config_completer))  # autocomplete path
        self.ui.log_path.setCompleter(config_completer)  # allow drag&drop
        self.ui.log_path.setAcceptDrops(True)

    def _set_default_path(self):
        # set default path
        start = datetime.now()
        curr_date = str(datetime.date(start))
        curr_time = str(datetime.time(start)).replace(":", "-")[:8]
        event_file_name = f"events_{curr_date}_{curr_time}.csv"
        event_log_dir = Path.cwd().joinpath(Path(DEFAULT_EVENT_LOG_PATH))
        self.event_log_path = event_log_dir.joinpath(event_file_name)

    def get_data(self) -> Path:
        """Return the path to the event log file after dialog closes."""
        return self.event_log_path

    def create_log_file(self):
        """Create event log file."""
        # set paths to line edit value
        self.validate_input()
        if self.ui.log_path.text():
            self.event_log_path = Path(self.ui.log_path.text())
        with Path.open(self.event_log_path, "w+") as fp:
            fp.write(EVENT_LOG_HEADER)

    def is_path_valid(self):
        """Check if the given path is valid."""
        path = Path(self.ui.log_path.text())
        return all(
            [
                Path.exists(path.parent),
                Path.is_dir(path.parent),
                not Path.exists(path),
                str(path).endswith(EVENT_LOG_FILE_TYPE),
            ]
        )

    def validate_input(self):
        """Validate the input of the line edit."""
        is_enabled = self.is_path_valid()
        self.ui.buttonBox.setEnabled(is_enabled)

    def open_log_file_dialog(self):
        """Open file dialog to select event log file."""
        file_name = QFileDialog.getOpenFileName(
            self,
            caption="Select board configuration file",
            dir=DEFAULT_EVENT_LOG_PATH,
            filter=f"*{EVENT_LOG_FILE_TYPE}-files (*{EVENT_LOG_FILE_TYPE})",
        )[0]
        if file_name:
            self.ui.log_path.setText(file_name)

    def closeEvent(self, event):  # noqa: N802
        """Prevent closing the dialog when no valid path was entered."""
        if self.is_path_valid():
            super().closeEvent(event)
        else:
            event.ignore()
