# cw-tail

**cw-tail** is a Python-based CLI tool that tails AWS CloudWatch logs and displays them in a colored, simplified two‑column layout. It's designed to help you quickly monitor log activity directly from your terminal.

## Features

- **Multiple Named Configurations:** Store different configurations for various environments or use cases in a single YAML file
- **Colored Output:** Uses ANSI escape codes to colorize output, making it easier to spot important messages
- **Flexible Filtering:** Filter, highlight, or exclude logs based on user‑specified tokens
- **Configurable Time Window:** Tail logs from a specified duration (e.g., the last 1 hour, 15 minutes, etc.)
- **Stream Name Shortening:** Automatically shortens container/log stream names for a cleaner display

## Requirements

- Python 3.12 or later
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

It's best to install `cw-tail` inside a virtual environment to avoid any system conflicts.

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

The `install.sh` script will create a virtual environment and install the package:

```bash
./install.sh
```

## Configuration

Create a configuration file at `/cw-tail/config.yml`. There is an example configuration file in the repository in the correct location. The tool will create a default configuration if none exists. Here's an example configuration:

```yaml
default:
  region: us-east-1
  since: 1h
  colorize: true

prod:
  log_group: production-logs
  since: 10m
  highlight_tokens: [301, 302, 429, 500, error, warning, critical]
  exclude_tokens: []
  exclude_streams: []
  formatter: json_formatter
  format_options:
    remove_keys: logger
    key_value_pairs: level:info,level:debug,ip:my-ip-address

dev:
  log_group: development-logs
  since: 10m
  highlight_tokens: [429, 500, error, warning, critical]
  exclude_tokens: []
  formatter: json_formatter
  format_options:
    remove_keys: logger,request_id
    key_value_pairs: ip:my-ip-address
```

Any values provided via command‑line arguments will override these configuration values.

## Usage

After installation, run the tool using the command‑line script `cw-tail`. To view the help text with all available options, run:

```bash
source env/bin/activate  # On Windows: env\Scripts\activate
cw-tail --help
```

### Examples

```bash
# Use the prod configuration
cw-tail --config prod

# Use the dev configuration but override the time window
cw-tail --config dev --since 30m

# Use default configuration with a specific log group
cw-tail --log-group my-logs --colorize
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
