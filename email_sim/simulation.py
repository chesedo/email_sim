import logging
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import List

from rich.progress import Progress, TaskID

from email_sim.actions import SimulationAction
from email_sim.controller import DockerTimeController
from email_sim.generator import DataGenerator

logger = logging.getLogger("dst")

# Define a custom log level
HEADER = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(HEADER, "HEADER")


# Add a custom method to the logger class
def header(self, message, *args, **kwargs):
    if self.isEnabledFor(HEADER):
        self._log(HEADER, message, args, **kwargs)


# Add the method to the Logger class
logging.Logger.header = header


class SimulationRunner:
    def __init__(
        self,
        actions: List[SimulationAction],
        progress: Progress,
        action_id: TaskID,
        seed: int,
        steps: int = 100,
    ):
        # Make sure the seed is reset for each run
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

    def execute_action(self, action) -> bool:
        """Execute a single action with enhanced step display"""
        try:
            # Execute the action
            start_time = time.time()
            success = action(self.controller, self.data_generator)
            execution_time = time.time() - start_time

            # Log execution result with timing
            if success:
                logger.info(f"✅ Completed: in {execution_time:.2f}s")
            else:
                logger.error(f"❌ Failed: after {execution_time:.2f}s")

            return success

        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            return False

    def run(self) -> bool:
        """Run the simulation synchronously with enhanced summary"""
        success = True
        start_time = time.time()
        action_counts = {}  # Track how many times each action was executed
        current_step = 0

        try:
            logger.info(f"Starting simulation with {len(self.actions)} actions")

            while current_step < self.steps:
                # Select action based on weights
                action = random.choices(
                    self.actions, weights=self.normalized_weights, k=1
                )[0]
                action_name = action.__class__.__name__

                # Track action counts
                action_counts[action_name] = action_counts.get(action_name, 0) + 1
                current_step += 1

                # Create a step header with clear visual separation
                logger.header(f"{'=' * 30}")
                logger.header(f"STEP {current_step}/{self.steps}")
                logger.header(f"{'-' * 30}")

                # Log action details with more context
                logger.info(
                    f"✓ Action: [bold]{action_name}[/bold] (weight: {action.weight:.2f})"
                )
                logger.info(
                    f"✓ Time: {self.controller.get_time().strftime('%Y-%m-%d %H:%M:%S.%f')}"
                )

                # Update progress in the UI
                self.progress.update(
                    self.action_id,
                    advance=0,
                    description=f"[cyan]{action_name} ({current_step}/{self.steps})",
                )

                if not self.execute_action(action):
                    success = False
                    break

                # Update progress again after completion
                self.progress.update(
                    self.action_id,
                    advance=1,
                )

            # Final status message
            total_time = time.time() - start_time

            # Print simulation summary with separator for visibility
            logger.header("")
            logger.header(f"{'#' * 50}")
            logger.header(f"SIMULATION SUMMARY")
            logger.header(f"{'-' * 50}")

            if success:
                logger.header(f"✨ Status: Completed successfully!")
            else:
                logger.header(f"[red]Status: Failed![/]")

            logger.header(f"Total time: {total_time:.2f} seconds")
            logger.header(f"Steps completed: {current_step}/{self.steps}")

            # Show action distribution
            logger.header("")
            logger.header(f"Action distribution:")
            for action_name, count in sorted(
                action_counts.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / current_step) * 100
                logger.header(f"  • {action_name}: {count} times ({percentage:.1f}%)")

            logger.header(f"{'#' * 50}")

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
            logger.header(
                "[green bold]Success: Both runs produced identical results![/]"
            )
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
    result = compare_runs(dir1, Path("./tmp/mail"))

    # Give time for final logs to appear
    time.sleep(0.5)

    return result


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
