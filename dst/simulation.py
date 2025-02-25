import logging
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import List

from rich.progress import Progress, TaskID

from dst.actions import SimulationAction
from dst.controller import DockerTimeController
from dst.generator import DataGenerator

logger = logging.getLogger("dst")

# Define a custom log level
STEP_HEADER = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(STEP_HEADER, "STEP")


# Add a custom method to the logger class
def step_header(self, message, *args, **kwargs):
    if self.isEnabledFor(STEP_HEADER):
        self._log(STEP_HEADER, message, args, **kwargs)


# Add the method to the Logger class
logging.Logger.step_header = step_header


class SimulationRunner:
    def __init__(
        self,
        actions: List[SimulationAction],
        progress: Progress,
        action_id: TaskID,
        seed: int,
        steps: int = 100,
    ):
        random.seed(seed)

        weights = [action.weight for action in actions]
        total_weight = sum(weights)

        self.actions = actions
        self.normalized_weights = [w / total_weight for w in weights]
        self.progress = progress
        self.action_id = action_id
        self.steps = steps
        self.controller = DockerTimeController(progress, action_id)
        self.data_generator = DataGenerator(seed)
        self.completed_steps = 0

    def execute_action(self) -> bool:
        """Execute a single action with enhanced step display"""
        try:
            # Select action based on weights
            action = random.choices(self.actions, weights=self.normalized_weights, k=1)[
                0
            ]

            action_name = action.__class__.__name__
            self.completed_steps += 1

            # Create a step header with clear visual separation
            step_header = f"{'=' * 30}\n"
            step_header += f"STEP {self.completed_steps}/{self.steps}"
            step_header += f"\n{'-' * 30}"
            logger.step_header(step_header)

            # Log action details with more context
            logger.info(
                f"✓ Action: [bold]{action_name}[/bold] (weight: {action.weight:.2f})"
            )
            logger.info(
                f"✓ Time: {self.controller.get_time().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Update progress in the UI
            self.progress.update(
                self.action_id,
                advance=0,
                description=f"[cyan]{action_name} ({self.completed_steps}/{self.steps})",
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
                self.action_id,
                advance=1,
                description=f"Running simulation... ({self.completed_steps}/{self.steps})",
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
            # Initial delay to let layout render
            time.sleep(0.1)

            logger.info(f"Starting simulation with {len(self.actions)} actions")

            while self.completed_steps < self.steps:
                # Select action based on weights
                action = random.choices(
                    self.actions, weights=self.normalized_weights, k=1
                )[0]
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
            for action_name, count in sorted(
                action_counts.items(), key=lambda x: x[1], reverse=True
            ):
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
            ["diff", "-ru", str(dir1), str(dir2)], capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info("[green bold]Success: Both runs produced identical results![/]")
            return True
        else:
            logger.warning("Warning: Differences found between runs!")
            # For large diffs, this would be better in a scrollable panel
            # but for now, just output the first few lines
            diff_output = result.stdout.split("\n")[:20]
            for line in diff_output:
                if line.startswith("+"):
                    logger.info(f"[green]{line}[/green]")
                elif line.startswith("-"):
                    logger.info(f"[red]{line}[/red]")
                else:
                    logger.info(line)
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running diff: {e}")
        return False


def run_simulation_with_comparison(
    actions: List[SimulationAction],
    progress: Progress,
    sim_number_id,
    action_id: TaskID,
    seed: int,
    steps: int = 100,
) -> bool:
    """Run two identical simulations and compare results"""
    # First run
    logger.info("Running first simulation...")
    progress.update(sim_number_id, advance=0.5, description="1st simulation")
    runner1 = SimulationRunner(actions, progress, action_id, seed, steps)
    success1 = runner1.run()
    if not success1:
        return False

    # Move first run results
    dir1 = move_tmp_directory(seed, steps)

    # Second run
    logger.info("Running second simulation...")
    progress.update(sim_number_id, advance=1, description="2nd simulation")
    progress.reset(action_id)
    runner2 = SimulationRunner(actions, progress, action_id, seed, steps)
    success2 = runner2.run()
    if not success2:
        return False

    # Compare results using system diff
    progress.update(sim_number_id, advance=0.5, description="Getting diff")
    return compare_runs(dir1, Path("./tmp/mail"))


def run_simulation(
    actions: List[SimulationAction],
    progress: Progress,
    sim_number_id: TaskID,
    action_id: TaskID,
    seed: int,
    steps: int = 100,
) -> bool:
    """Main entry point for running a simulation with comparison"""
    return run_simulation_with_comparison(
        actions, progress, sim_number_id, action_id, seed, steps
    )
