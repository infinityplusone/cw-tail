# cw-tail

**cw-tail** is a Python-based CLI tool that tails AWS CloudWatch logs and displays them in a colored, simplified two‑column layout. It’s designed to help you quickly monitor log activity directly from your terminal.

## Features

- **Configurable via `.env`:** All options (log group, region, filter tokens, etc.) can be set in a `.env` file. Command‑line arguments override these defaults.
- **Colored Output:** Uses ANSI escape codes to colorize output, making it easier to spot important messages.
- **Flexible Filtering:** Filter, highlight, or exclude logs based on user‑specified tokens.
- **Configurable Time Window:** Tail logs from a specified duration (e.g., the last 1 hour, 15 minutes, etc.).
- **Stream Name Shortening:** Automatically shortens container/log stream names for a cleaner display.

## Requirements

- Python 3.8 or later
- AWS credentials configured (via environment variables, AWS CLI configuration, or IAM roles)
- [boto3](https://pypi.org/project/boto3/) (installed automatically with the package)

## AWS CLI Setup

- **Install AWS CLI:** Make sure the AWS CLI is installed. You can follow [these instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) for installation.
- **Configure AWS Credentials:** You must have a properly configured `~/.aws/credentials` file with valid `aws_access_key_id` and `aws_secret_access_key`. For example:

  ```ini
  [default]
  aws_access_key_id = YOUR_ACCESS_KEY_ID
  aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
  ```
  
Alternatively, you can set these values as environment variables.

## Installation

It’s best to install `cw-tail` inside a virtual environment to avoid any system conflicts.

1. **Create & Activate a Virtual Environment:**

   ```bash
   python3 -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

2. **Install the Package:**

   ```bash
   pip install .
   ```

### Simple Installation

The `install.sh` script will create a virtual environment, install the package, and set up the environment variables.

```bash
./install.sh
```

## Configuration

Create a `.env` file in the same directory as the tool with the following variables:

```ini
# Name of the CloudWatch log group (required)
LOG_GROUP=your-log-group

# AWS region (default is us-east-1)
REGION=us-east-1

# Optional filtering options (space-separated tokens)
FILTER_PATTERN=
HIGHLIGHT_TOKENS=
EXCLUDE_TOKENS=
EXCLUDE_STREAMS=

# How far back to start tailing logs (e.g., 1h, 15m, 10s)
SINCE=1h

# Enable color highlighting by default (true or false)
COLORIZE=true
```

There is a sample `.env` file in the root of the project.

Any values provided via command‑line arguments will override these defaults.

## Usage

After installation, run the tool using the command‑line script `cw-tail`. To view the help text with all available options, run:

```bash
source env/bin/activate  # On Windows: env\Scripts\activate
cw-tail --help
```

### Example

Tail logs from the log group specified in your .env file (or override it) from the last 30 minutes with color highlighting enabled:

```bash
cw-tail --log-group my-logs --since 30m --colorize
```

### AWS CLI Setup Reminder

- Install AWS CLI: Follow the [installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) for your operating system.
- Configure AWS Credentials: Run aws configure or manually edit your `~/.aws/credentials` file to ensure that your AWS credentials are correctly set up.

### Development & Packaging

The project uses a pyproject.toml for packaging. To reinstall locally after making changes:

```bash
pip install -e .
```

### Contributing

Pull requests, bug reports, and suggestions are welcome. Please follow the standard GitHub flow for contributions.

### License

This project is licensed under the [Unlicense](LICENSE).
