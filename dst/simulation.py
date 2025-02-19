import random
import time
import threading
import hashlib
import os
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from dst.controller import DockerTimeController
from dst.actions import SimulationAction, ValidationAction
from dst.generator import DataGenerator

console = Console()

class SimulationRunner:
    def __init__(self, actions: List[SimulationAction], data_generator: DataGenerator, steps: int = 100):
        weights = [action.weight for action in actions]
        total_weight = sum(weights)

        self.actions = actions
        self.normalized_weights = [w/total_weight for w in weights]
        self.steps = steps
        self.controller = DockerTimeController()
        self.data_generator = data_generator
        self.pending_validations: Queue[ValidationAction] = Queue()
        self.stop_event = threading.Event()
        self.validation_error = None
        self.action_error = None
        self.action_pool = ThreadPoolExecutor(max_workers=10)  # Allow multiple actions to run concurrently
        self.started_steps = 0
        self.progress = None
        self.progress_task = None

    def execute_action(self):
        """Execute a single action in the thread pool"""
        if self.stop_event.is_set():
            return

        try:
            # Select action based on weights
            action = random.choices(self.actions, weights=self.normalized_weights, k=1)[0]

            action_name = action.__class__.__name__
            self.started_steps += 1

            # Log step info with weight information
            table = Table(show_header=False, box=None)
            table.add_row(
                f"[bold cyan]Step {self.started_steps}/{self.steps}",
                f"[blue]Action: {action_name}",
                f"[dim](weight: {action.weight})"
            )
            console.print(table)

            # Execute the action
            execution_success, validator = action(self.controller, self.data_generator)
            if not execution_success:
                console.print("[bold red]Action execution failed! ❌")
                self.action_error = f"Action {action_name} failed to execute"
                self.stop_event.set()
                return

            # Queue validator if present
            if validator:
                self.pending_validations.put(validator)

            console.print(f"[dim cyan]Completed: {action_name}[/]")

            if self.progress and self.progress_task:
                self.progress.update(self.progress_task, advance=1)

        except Exception as e:
            console.print(f"[bold red]Error executing action: {e}")
            self.action_error = str(e)
            self.stop_event.set()

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

    def action_scheduler(self):
        """Schedules actions at fixed intervals regardless of execution time"""
        while self.started_steps < self.steps and not self.stop_event.is_set():
            next_delay = random.uniform(1.0, 3.0)
            self.action_pool.submit(self.execute_action)
            time.sleep(next_delay)

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
                self.progress = progress
                self.progress_task = progress.add_task("[cyan]Running simulation...", total=self.steps)

                # Start validation worker thread
                validation_thread = threading.Thread(target=self.validation_worker)
                validation_thread.start()

                # Start action scheduler thread
                scheduler_thread = threading.Thread(target=self.action_scheduler)
                scheduler_thread.start()

                # Wait for scheduler to complete
                scheduler_thread.join()

                # Wait for all pending actions to complete
                self.action_pool.shutdown(wait=True)

                # If actions completed normally, wait for validations to finish
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

def run_simulation(actions: List[SimulationAction], data_generator: DataGenerator, steps: int = 100) -> bool:
    """Main entry point for running a simulation"""
    runner = SimulationRunner(actions, data_generator, steps)
    success = runner.run()

    if success:
        dir_hash = hash_directory("./tmp")
        console.print(f"[cyan]Directory Hash:[/] {dir_hash}")

def hash_directory(path: str) -> str:
    """Generate a deterministic hash of a directory's contents"""
    sha256_hash = hashlib.sha256()

    # Walk directory in sorted order for determinism
    for root, dirs, files in sorted(os.walk(path)):
        # Hash directory names
        for dir_name in sorted(dirs):
            sha256_hash.update(dir_name.encode())

        # Hash file contents
        for file_name in sorted(files):
            file_path = os.path.join(root, file_name)
            # Hash file name
            sha256_hash.update(file_name.encode())
            # Hash file content
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
