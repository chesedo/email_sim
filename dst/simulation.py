import random
import time
import threading
from queue import Queue
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from dst.controller import DockerTimeController
from dst.actions import SimulationAction, ValidationAction

console = Console()

class SimulationRunner:
    def __init__(self, actions: List[SimulationAction], steps: int = 100):
        self.actions = actions
        self.steps = steps
        self.controller = DockerTimeController()
        self.pending_validations: Queue[ValidationAction] = Queue()
        self.stop_event = threading.Event()
        self.validation_error = None
        self.action_error = None

    def validation_worker(self):
        """Worker thread that processes pending validations"""
        try:
            while not self.stop_event.is_set():
                # Get all current validations
                current_validations = []
                while not self.pending_validations.empty():
                    current_validations.append(self.pending_validations.get_nowait())

                # Process validations
                if current_validations:
                    current_time = self.controller.get_time()
                    still_pending = []

                    for validator in current_validations:
                        time_elapsed = (current_time - validator.start_time).total_seconds()
                        if time_elapsed >= validator.timeout:
                            # Time to validate
                            if not validator.validate(self.controller):
                                console.print(f"[bold red]Validation failed for {validator.__class__.__name__}! ❌")
                                self.validation_error = f"Validation failed for {validator.__class__.__name__}"
                                self.stop_event.set()
                                return
                        else:
                            still_pending.append(validator)

                    # Put back pending validations
                    for validator in still_pending:
                        self.pending_validations.put(validator)

                # Wait a bit before next check
                time.sleep(0.1)

        except Exception as e:
            console.print(f"[bold red]Error in validation worker: {e}")
            self.validation_error = str(e)
            self.stop_event.set()

    def action_worker(self, progress, task):
        """Worker thread that executes actions with deterministic timing"""
        try:
            for step in range(self.steps):
                if self.stop_event.is_set():
                    return

                # Calculate step timing
                step_delay = random.uniform(1.0, 3.0)
                step_start = time.time()
                step_end = step_start + step_delay

                # Execute action
                action = random.choice(self.actions)
                action_name = action.__class__.__name__

                # Log step info
                table = Table(show_header=False, box=None)
                table.add_row(
                    f"[bold cyan]Step {step + 1}/{self.steps}",
                    f"[blue]Action: {action_name}"
                )
                console.print(table)

                # Execute the action
                execution_success, validator = action(self.controller)
                if not execution_success:
                    console.print("[bold red]Action execution failed! ❌")
                    self.action_error = f"Action {action_name} failed to execute"
                    self.stop_event.set()
                    return

                # Queue validator if present
                if validator:
                    self.pending_validations.put(validator)

                progress.advance(task)

                # Wait until step should end
                time_remaining = step_end - time.time()
                if time_remaining > 0:
                    time.sleep(time_remaining)

        except Exception as e:
            console.print(f"[bold red]Error in action worker: {e}")
            self.action_error = str(e)
            self.stop_event.set()

    def run(self) -> bool:
        """Run the simulation with parallel action execution and validation"""
        console.print(Panel.fit("DST Simulation", style="bold magenta"))
        success = True

        try:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task("[cyan]Running simulation...", total=self.steps)

                # Start validation worker thread
                validation_thread = threading.Thread(target=self.validation_worker)
                validation_thread.start()

                # Start action worker thread
                action_thread = threading.Thread(target=self.action_worker, args=(progress, task))
                action_thread.start()

                # Wait for threads to complete
                action_thread.join()

                # If action thread completed normally, wait for validations to finish
                if not self.action_error:
                    console.print("[yellow]Waiting for pending validations to complete...[/]")
                    while not self.pending_validations.empty() and not self.stop_event.is_set():
                        time.sleep(0.1)

                # Signal validation thread to stop and wait for it
                self.stop_event.set()
                validation_thread.join()

                if self.action_error:
                    console.print(f"[bold red]Simulation failed: {self.action_error}")
                    success = False
                elif self.validation_error:
                    console.print(f"[bold red]Simulation failed: {self.validation_error}")
                    success = False
                else:
                    console.print("[bold green]Simulation completed successfully! ✨")

            return success
        finally:
            self.controller.cleanup()

def run_simulation(actions: List[SimulationAction], steps: int = 100) -> bool:
    """Main entry point for running a simulation"""
    runner = SimulationRunner(actions, steps)
    return runner.run()
