#!/usr/bin/env python3

import argparse
import logging
import random
import sys
from collections import deque
from typing import List

from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from dst.actions import get_available_actions
from dst.simulation import HEADER, run_simulation

# Create a custom console for our layout
console = Console()


# Create a custom rich handler for the layout
class LayoutLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.messages = deque()

    def emit(self, record: logging.LogRecord):
        # Special case for step headers - no level name
        if record.levelno == HEADER:
            self.messages.append(Text.from_markup(f"{record.getMessage()}"))
            return

        # Color based on log level, but don't add markup - let Rich handle it
        if record.levelno >= logging.ERROR:
            style = "bold red"
        elif record.levelno >= logging.WARNING:
            style = "yellow"
        elif record.levelno >= logging.INFO:
            style = "cyan"
        # Don't show anything in the UI below INFO level
        else:
            return

        # Pad the log level name to a consistent width (7 covers "WARNING")
        level_name = record.levelname.ljust(7)

        # Create a Text object with markup enabled - no timestamp
        self.messages.append(
            Text.from_markup(f"[{style}]{level_name}[/] {record.getMessage()}")
        )

    def get_renderables(self, height=None) -> List[RenderableType]:
        # If height is provided, return only the most recent messages that fit
        if height is not None and height > 0:
            # Account for panel borders and title - approximately 6 lines
            available_lines = max(1, height - 6)
            # Return only the most recent messages that will fit
            return list(self.messages)[-available_lines:]
        # Otherwise return all messages
        return list(self.messages)


class LogPanel:
    """Panel that shows the logs from our custom handler"""

    def __init__(self, log_handler: LayoutLogHandler):
        self.log_handler = log_handler

    def __rich__(self) -> Panel:
        # Try to get the current terminal height
        height = None
        try:
            _, height = console.size
        except:
            # If we can't get the size, don't limit messages
            pass

        return Panel(
            Group(*self.log_handler.get_renderables(height)),
            title="Logs",
            border_style="blue",
        )


# Set up our custom log handler
layout_handler = LayoutLogHandler()
logging.basicConfig(
    level=logging.DEBUG, format="%(message)s", handlers=[layout_handler]
)
logger = logging.getLogger("dst")

# Also add a console handler for main screen logs
console_handler = RichHandler(
    console=console,
    rich_tracebacks=True,
    markup=True,
    enable_link_path=False,  # For some reason this messes with the randomness and causes the second run to have a different sequence of random numbers
    log_time_format="[%H:%M:%S.%f]",  # Add milliseconds with %f
)
logger.addHandler(console_handler)


def create_layout(steps: int) -> tuple[Layout, Progress, TaskID, TaskID]:
    """Create Rich layout for simulation display"""
    layout = Layout()
    layout.split(Layout(name="header", size=4), Layout(name="body"))
    # Setup header with title and progress
    layout["header"].split_row(
        Layout(name="title", ratio=1),
        Layout(name="progress", ratio=2),
    )

    layout["title"].update(
        Panel(Text("DST Simulation", style="bold magenta"), border_style="magenta")
    )
    # Create progress panel
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
    )
    sim_number_id = progress.add_task("", total=2)
    action_id = progress.add_task("", total=steps)
    layout["progress"].update(Panel(progress, title="Progress", border_style="green"))
    # Set up the log panel in the body
    layout["body"].update(LogPanel(layout_handler))

    return layout, progress, sim_number_id, action_id


def main():
    parser = argparse.ArgumentParser(description="Run time simulation")
    parser.add_argument("--seed", type=int, help="Seed for random time generation")
    parser.add_argument(
        "--steps", type=int, default=20, help="Number of simulation steps"
    )
    args = parser.parse_args()

    if args.seed is None:
        args.seed = random.randint(1, 1_000_000_000)

    layout, progress, sim_number_id, action_id = create_layout(steps=args.steps)

    with Live(layout, console=console, refresh_per_second=10):
        # Display initial configuration
        console.print(
            Panel.fit(
                f"[cyan]Random Seed:[/] [yellow]{args.seed}[/]\n"
                f"[cyan]Simulation Steps:[/] [yellow]{args.steps}[/]",
                title="DST Configuration",
                border_style="blue",
            )
        )

        # Get all registered actions and instantiate them
        action_classes = get_available_actions()

        # Instantiate actions to get their weights
        actions = [cls() for cls in action_classes.values()]

        # Calculate total weight for normalization
        total_weight = sum(action.weight for action in actions)

        # Display available actions in a table with weights
        table = Table(title="Available Actions", border_style="blue")
        table.add_column("Action", style="green")
        table.add_column("Weight", style="yellow")
        table.add_column("Normalized Weight", style="cyan")

        for i, action in enumerate(actions):
            action_name = action.__class__.__name__
            normalized_weight = action.weight / total_weight
            table.add_row(
                action_name, f"{action.weight:.2f}", f"{normalized_weight:.4f}"
            )

        console.print(table)
        console.print()

        success = run_simulation(
            actions, progress, sim_number_id, action_id, args.seed, args.steps
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
