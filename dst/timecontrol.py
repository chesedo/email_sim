from pathlib import Path
from datetime import datetime
import threading
from rich.console import Console

console = Console()

class TimeControl:
    """Controls time synchronization across services via a shared file"""

    def __init__(self, initial_time: datetime):
        self.time_file = Path("./tmp/faketime")
        self.time_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.set_time(initial_time)

    def set_time(self, new_time: datetime) -> None:
        """Set the current time in the shared file"""
        with self._lock:
            timestamp = new_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            self.time_file.write_text(timestamp)
            console.print(f"[cyan]Updated shared time to:[/] [yellow]{timestamp}[/]")

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
