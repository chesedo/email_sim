# EmailSim: Deterministic Simulated Testing (DST) Framework

EmailSim is a framework for deterministic simulation testing (DST) of email delivery systems. It enables thorough testing of email branding and delivery services by creating reproducible testing scenarios that explore random edge cases consistently.

## Purpose

Traditional testing of email systems often struggles with:
- Inconsistent system state between test runs
- Time-dependent behaviors that are difficult to reproduce
- Limited coverage of edge cases due to predetermined test scenarios

DST solves these problems by:
1. **Deterministic time simulation**: Using libfaketime to control the flow of time across containers
2. **Random but reproducible exploration**: Utilizing seeded random number generators to explore a vast testing space while ensuring repeatability
3. **Realistic test data**: Generating authentic-looking emails and user behaviors that mimic real-world scenarios

## Getting Started

### Prerequisites

- Python 3.12+
- Docker and Docker Compose

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/email_sim.git
   cd email_sim
   ```

2. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies:
   ```bash
   poetry install
   ```

## Running EmailSim

Run a basic simulation:

```bash
poetry run dst
```

Run with specific parameters:

```bash
poetry run dst --steps 10 --seed 42
```

- `--steps`: Number of simulation steps to run (default: 2)
- `--seed`: Random seed for reproducibility (default: random)

## Understanding Determinism

The framework runs two identical simulations with the same seed and steps, then compares the results. When you see:

```
Success: Both runs produced identical results!
```

This confirms that the core elements of the system - from email generation to delivery - are behaving deterministically. Almost every aspect of the system is reproducible:

- **SMTP connection timestamps**: Both runs establish connections at precisely the same virtual time
- **Email delivery timestamps**: Every email is processed with identical timing
- **Email content**: The content, structure, and formatting of emails are identical
- **System behavior**: Most system responses and state changes occur at the same point in the simulation

It's important to note that a few elements are deliberately not deterministic:
- **Message IDs**: These may vary between runs
- **Filesystem operations**: Operations like file creation might occasionally fail differently due to OS-level non-determinism

Despite these controlled exceptions, the final diff comparison proves the overall determinism by showing that the emails generated, processed, and delivered in both runs are functionally identical. This level of determinism is crucial because it:

1. **Makes bugs reproducible**: If an issue occurs, you can reproduce it exactly by using the same seed
2. **Enables precise debugging**: You can isolate and fix issues in complex, time-dependent systems
3. **Provides confidence in testing**: You can be certain that fixes actually resolve the identified problems
4. **Tests time-sensitive workflows**: Email processing often depends on precise timing - this framework allows testing these scenarios reliably

The deterministic nature is achieved through careful time management (using libfaketime within containers), consistent random number generation (using seeded generators), and container isolation (using Docker).

## Simulation Actions

Actions are the building blocks of the simulation. Each action represents a specific operation that might occur in a real-world email system:

- **SendEmail**: Generates and sends an email through the system
- **AdvanceTime**: Moves the simulation clock forward by a random amount
- **AddUser**: Adds a new user to the simulation
- **RemoveUser**: Removes a random user from the simulation

Each action has a weight that determines how likely it is to be selected during simulation. The simulation randomly selects actions based on these weights, creating diverse but reproducible test scenarios.

### Adding New Actions

To add a new action:

1. Create a new file in `email_sim/actions/` directory
2. Define your action class and register it:

```python
from email_sim.actions import SimulationAction, register_action

@register_action
class MyNewAction(SimulationAction):
    weight = 1.0  # Probability weight
    
    def __call__(self, controller, data_generator):
        # Implement your action logic here
        return True  # Return success/failure
```

## Email Clients

The framework simulates different email clients to test how your system handles various email formats and structures. Each client implements a specific way of generating email content.

### Available Email Clients

- **DefaultEmailClient**: Basic email formatting with simple HTML
- **OutlookClient**: Simulates Microsoft Outlook's email formatting
- **GmailClient**: Simulates Gmail's email formatting

### Creating a New Email Client

To add a new email client:

1. Create a new file in `email_sim/email_clients/` directory
2. Define your email client class and register it:

```python
from email_sim.email_clients import EmailClient, register_email_client
from email_sim.generator.user import User

@register_email_client
class MyCustomClient(EmailClient):
    EMAIL_TEMPLATE = """
        <html>
        <body>
            <div style="font-family: Arial, sans-serif;">
                <p>{{ text_content }}</p>
                {% if signature %}
                <div style="color: #666;">
                    {{ signature }}
                </div>
                {% endif %}
            </div>
        </body>
        </html>
    """

    def generate_content(self, subject: str, sender: User, text_content: str) -> tuple[str, str]:
        # Implement your email generation logic
        # Return a tuple of (text_content, html_content)
        return text_content, html_content
```

## Project Structure

Project structure:
- `cli.py`: Command-line interface
- `email_sim/`: Core package
  - `actions/`: Simulation actions
  - `email_clients/`: Email client implementations
  - `generator/`: Test data generation
  - `controller.py`: Docker controller
  - `simulation.py`: Simulation runner
  - `timecontrol.py`: Time control utilities

## Architecture

EmailSim uses Docker containers to isolate testing components:
- `exim_send`: Mail Transfer Agent (MTA) for sending emails
- `exim_receive`: MTA for receiving and storing emails

The time synchronization between containers is managed via a shared timestamp file that the containers read using libfaketime, ensuring all components operate in the same simulated timeframe.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
