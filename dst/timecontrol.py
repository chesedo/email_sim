import logging
import os
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("dst")


class TimeControl:
    """
    Controls time synchronization across services via a shared file.

    This class manages a shared timestamp file that libfaketime reads to determine
    the simulated time. Special care is taken to ensure the file is never empty
    during updates, as libfaketime will fall back to system time if it reads an
    empty file, breaking deterministic simulation.
    """

    def __init__(self, initial_time: datetime):
        self.time_file = Path("./tmp/faketime")
        self.time_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.set_time(initial_time)

    def set_time(self, new_time: datetime) -> None:
        """Set the current simulation time in the shared file."""
        with self._lock:
            timestamp = new_time.strftime("%Y-%m-%d %H:%M:%S.%f")

            # IMPORTANT: We use an append-then-truncate approach to prevent the file
            # from ever being empty. If libfaketime reads an empty file (which can happen
            # with standard write operations that truncate before writing), it will
            # revert to system time and break deterministic testing. Or it will just freeze
            # up exim (sending will timeout) and the exim debug logs will have something
            # like this after an SMTP transaction:
            #
            # 23:16:37.000    15 tick check: 1796944597.000000 1796944597.000000
            # 23:16:37.000    15 waiting 0.000500 sec
            # 07:47:08.613    15 tick check: 1796944597.000000 1740556028.613500
            # 07:47:08.613    15 waiting 56388568.386902 sec
            #
            # Running an `strace` will show this happened because the `faketime` file
            # was empty:
            #
            # [pid    69] openat(AT_FDCWD, "/tmp/faketime", O_RDONLY) = 9
            # [pid    69] fstat(9, {st_mode=S_IFREG|0644, st_size=0, ...}) = 0
            # [pid    69] read(9, "", 4096)           = 0
            # [pid    69] close(9)

            # First append to ensure the file is never empty
            with open(self.time_file, "a") as f:
                f.write("\n" + timestamp)
                f.flush()
                os.fsync(f.fileno())

            # Then truncate to keep only the last line
            with open(self.time_file, "r+") as f:
                lines = f.readlines()
                f.seek(0)
                f.write(lines[-1])
                f.truncate()
                f.flush()
                os.fsync(f.fileno())

            logger.info(f"Updated simulation time to: {timestamp}")

    def get_time(self) -> datetime:
        """Read the current time from the shared file"""
        with self._lock:
            timestamp = self.time_file.read_text().strip()
            # Remove @ prefix for parsing
            return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")

    def cleanup(self) -> None:
        """Clean up time control resources"""
        if self.time_file.exists():
            self.time_file.unlink()
