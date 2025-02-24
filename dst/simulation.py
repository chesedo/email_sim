import random
import shutil
import subprocess
import time
from typing import List
from collections import deque
from rich.console import Console, Group
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TextColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.logging import RichHandler
from rich.console import RenderableType
from dst.controller import DockerTimeController
from dst.actions import SimulationAction
from dst.generator import DataGenerator
from pathlib import Path
import logging

# Create a custom console for our layout
console = Console()

# Create a custom rich handler for the layout
class LayoutLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.messages = deque()
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')

    def emit(self, record):
        # Get the formatted log message
        log_entry = self.formatter.format(record)

        # Color based on log level, but don't add markup - let Rich handle it
        if record.levelno >= logging.ERROR:
            style = "bold red"
        elif record.levelno >= logging.WARNING:
            style = "yellow"
        elif record.levelno >= logging.INFO:
            style = "cyan"
        else:
            style = "dim"

        # Create a Text object with markup enabled
        self.messages.append(Text.from_markup(log_entry, style=style))

    def get_renderables(self, height=None) -> List[RenderableType]:
        # If height is provided, return only the most recent messages that fit
        if height is not None and height > 0:
            # Account for panel borders and title - approximately 7 lines
            available_lines = max(1, height - 15)
            # Return only the most recent messages that will fit
            return list(self.messages)[-available_lines:]
        # Otherwise return all messages
        return list(self.messages)

# Set up our custom log handler
layout_handler = LayoutLogHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[layout_handler]
)
logger = logging.getLogger("dst")

# Also add a console handler for main screen logs
console_handler = RichHandler(console=console, rich_tracebacks=True, show_time=False, markup=True)
logger.addHandler(console_handler)

class LogPanel:
    """Panel that shows the logs from our custom handler"""
    def __init__(self, log_handler):
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
            border_style="blue"
        )

class SimulationRunner:
    def __init__(self, actions: List[SimulationAction], seed: int, steps: int = 100):
        random.seed(seed)

        weights = [action.weight for action in actions]
        total_weight = sum(weights)

        self.actions = actions
        self.normalized_weights = [w/total_weight for w in weights]
        self.steps = steps
        self.controller = DockerTimeController()
        self.data_generator = DataGenerator(seed)
        self.completed_steps = 0
        self.layout = self._create_layout()

    def _create_layout(self):
        """Create Rich layout for simulation display"""
        layout = Layout()
        layout.split(
            Layout(name="header", size=4),
            Layout(name="body")
        )

        # Setup header with title and progress
        layout["header"].split_row(
            Layout(name="title", ratio=1),
            Layout(name="progress", ratio=2),
        )

        layout["title"].update(
            Panel(Text("DST Simulation", style="bold magenta"), border_style="magenta")
        )

        # Create progress panel
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeElapsedColumn(),
        )
        self.task_id = self.progress.add_task("[cyan]Running simulation...", total=self.steps)

        layout["progress"].update(
            Panel(self.progress, title="Progress", border_style="green")
        )

        # Set up the log panel in the body
        layout["body"].update(LogPanel(layout_handler))

        return layout

    def execute_action(self) -> bool:
        """Execute a single action with enhanced step display"""
        try:
            # Select action based on weights
            action = random.choices(self.actions, weights=self.normalized_weights, k=1)[0]

            action_name = action.__class__.__name__
            self.completed_steps += 1

            # Create a step header with clear visual separation
            step_header = f"{'=' * 30}\n"
            step_header += f"STEP {self.completed_steps}/{self.steps}"
            step_header += f"\n{'-' * 30}"
            logger.info(step_header)

            # Log action details with more context
            logger.info(f"✓ Action: [bold]{action_name}[/bold] (weight: {action.weight:.2f})")
            logger.info(f"✓ Time: {self.controller.get_time().strftime('%Y-%m-%d %H:%M:%S')}")

            # Update progress in the UI
            self.progress.update(
                self.task_id,
                advance=0,
                description=f"[cyan]Running: {action_name} ({self.completed_steps}/{self.steps})"
            )

            # Execute the action
            start_time = time.time()
            success = action(self.controller, self.data_generator)
            execution_time = time.time() - start_time

            # Log execution result with timing
            if success:
                logger.info(f"✅ Completed: {action_name} in {execution_time:.2f}s")
            else:
                logger.error(f"❌ Failed: {action_name} after {execution_time:.2f}s")

            # Update progress again after completion
            self.progress.update(
                self.task_id,
                advance=1,
                description=f"[cyan]Running simulation... ({self.completed_steps}/{self.steps})"
            )

            return success

        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            return False

    def run(self) -> bool:
        """Run the simulation synchronously with enhanced summary"""
        success = True
        start_time = time.time()
        action_counts = {}  # Track how many times each action was executed

        try:
            with Live(self.layout, console=console, refresh_per_second=10):
                # Initial delay to let layout render
                time.sleep(0.1)

                logger.info(f"Starting simulation with {len(self.actions)} actions")

                while self.completed_steps < self.steps:
                    # Select action based on weights
                    action = random.choices(self.actions, weights=self.normalized_weights, k=1)[0]
                    action_name = action.__class__.__name__

                    # Track action counts
                    action_counts[action_name] = action_counts.get(action_name, 0) + 1

                    if not self.execute_action():
                        success = False
                        break

                    # Small sleep to prevent UI refresh issues
                    time.sleep(0.05)

                # Final status message
                total_time = time.time() - start_time

                # Print simulation summary with separator for visibility
                logger.info(f"\n{'#' * 50}")
                logger.info(f"SIMULATION SUMMARY")
                logger.info(f"{'-' * 50}")

                if success:
                    logger.info(f"✨ Status: Completed successfully!")
                else:
                    logger.error(f"Status: Failed!")

                logger.info(f"Total time: {total_time:.2f} seconds")
                logger.info(f"Steps completed: {self.completed_steps}/{self.steps}")

                # Show action distribution
                logger.info(f"\nAction distribution:")
                for action_name, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / self.completed_steps) * 100
                    logger.info(f"  • {action_name}: {count} times ({percentage:.1f}%)")

                logger.info(f"{'#' * 50}")

                # Give time for final logs to appear
                time.sleep(0.5)

            return success
        finally:
            self.controller.cleanup()

def move_tmp_directory(seed: int, steps: int) -> Path:
    """Move tmp directory with seed and steps in name"""
    src = Path("./tmp/mail")
    if not src.exists():
        return None

    dst = Path(f"./tmp/seed{seed}_steps{steps}")
    if dst.exists():
        shutil.rmtree(dst)

    shutil.copytree(src, dst)
    return dst

def compare_runs(dir1: Path, dir2: Path) -> bool:
    """Compare two directories using system diff command"""
    try:
        result = subprocess.run(
            ["diff", "-ru", str(dir1), str(dir2)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("Success: Both runs produced identical results!")
            return True
        else:
            logger.warning("Warning: Differences found between runs!")
            # For large diffs, this would be better in a scrollable panel
            # but for now, just output the first few lines
            diff_output = result.stdout.split('\n')[:20]
            for line in diff_output:
                if line.startswith('+'):
                    logger.info(f"[green]{line}[/green]")
                elif line.startswith('-'):
                    logger.info(f"[red]{line}[/red]")
                else:
                    logger.info(line)
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running diff: {e}")
        return False

def run_simulation_with_comparison(actions: List[SimulationAction], seed: int, steps: int = 100) -> bool:
    """Run two identical simulations and compare results"""
    # First run
    logger.info("Running first simulation...")
    runner1 = SimulationRunner(actions, seed, steps)
    success1 = runner1.run()
    if not success1:
        return False

    # Move first run results
    dir1 = move_tmp_directory(seed, steps)

    # Second run
    logger.info("Running second simulation...")
    runner2 = SimulationRunner(actions, seed, steps)
    success2 = runner2.run()
    if not success2:
        return False

    # Compare results using system diff
    return compare_runs(dir1, Path("./tmp/mail"))

def run_simulation(actions: List[SimulationAction], seed: int, steps: int = 100) -> bool:
    """Main entry point for running a simulation with comparison"""
    return run_simulation_with_comparison(actions, seed, steps)
