#!/usr/bin/env python3
import argparse
import time
import datetime
import boto3
import re
import sys
import shutil
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# ANSI color codes
BLUE    = "\033[34m"
CYAN    = "\033[36m"
GREEN   = "\033[32m"
PURPLE  = "\033[35m"
RED     = "\033[31m"
RESET   = "\033[0m"
WHITE   = "\033[37m"
YELLOW  = "\033[33m"

COLORS = [
    "\033[38;5;28m",   # rgb(0,135,0)
    "\033[38;5;136m",  # rgb(175,135,0)
    "\033[38;5;90m",   # rgb(135,0,135)
    "\033[38;5;31m",   # rgb(0,135,175)
    "\033[38;5;168m",  # rgb(215,95,135)
    "\033[38;5;73m",   # rgb(95,175,175)
    "\033[38;5;61m",   # rgb(95,95,175)
    "\033[38;5;216m",  # rgb(255,175,135)
    "\033[38;5;24m",   # rgb(0,95,135)
    "\033[38;5;184m",  # rgb(215,215,0)
    "\033[38;5;31m",   # rgb(0,135,175)
    "\033[38;5;209m",  # rgb(255,135,95)
    "\033[38;5;93m",   # rgb(87,87,255)
]

# Ensure UTF-8 encoding for stdout (helps with emojis, etc.)
sys.stdout.reconfigure(encoding="utf-8")


class CloudWatchTailer:
    def __init__(
        self,
        log_group: str,
        region: str = "us-east-1",
        filter_tokens: list[str] = None,
        highlight_tokens: list[str] = None,
        exclude_tokens: list[str] = None,
        exclude_streams: list[str] = None,
        since_seconds: int = 3600,
        colorize: bool = False,
    ):
        self.log_group = log_group
        self.region = region
        self.filter_tokens = filter_tokens or []
        self.highlight_tokens = highlight_tokens or []
        self.exclude_tokens = exclude_tokens or []
        self.exclude_streams = exclude_streams or []
        self.since_seconds = since_seconds
        self.colorize = colorize

        # Create a boto3 session and CloudWatch logs client
        self.session = boto3.Session(region_name=self.region)
        self.logs_client = self.session.client("logs")

        # For assigning consistent colors per container
        self.containers = {}
        
    def _scroll_up(self, min_lines: int = 10):
        """
        Scrolls up the terminal by printing blank lines to push existing content off the screen.
        Ensures that the scroll effect is only as much as necessary.

        Args:
            min_lines (int): Minimum blank lines to print if terminal height is unknown.
        """
        # Get terminal size (fallback to 24 rows if it can't be determined)
        rows, _ = shutil.get_terminal_size(fallback=(24, 80))
        
        # Adjust the scroll amount based on estimated prior output
        scroll_lines = max(rows - 5, min_lines)  # Leave some buffer
        sys.stdout.write("\n" * scroll_lines)
        sys.stdout.flush()

    def _format_log_line(self, timestamp_str: str, message: str, container: str) -> str:
        """
        Format a log line with a left column for the container and timestamp,
        and the message in the right column.
        """
        terminal_size = shutil.get_terminal_size((80, 20))
        spacing = 1
        separator = " " * spacing + "|" + " " * spacing

        if container not in self.containers:
            self.containers[container] = (
                COLORS[len(self.containers) % len(COLORS)] if self.colorize else ""
            )
        container_color = self.containers[container]

        left_col = f"{container_color}{container}{separator}{timestamp_str}{separator}{RESET}"
        left_width = len(left_col)
        indentation = " " * left_width
        wrapped_message = message.replace("\n", "\n" + indentation)
        return f"{left_col}{wrapped_message}\n"

    def tail(self):
        """
        Continuously poll CloudWatch Logs for new events in the log group and print them.
        """
        next_token = None
        start_time = int(time.time() - self.since_seconds) * 1000
        filter_pattern = " ".join(f"?{t}" for t in self.filter_tokens) if self.filter_tokens else ""
        
        self._scroll_up()

        print(f"Starting tail of log group: {self.log_group}")
        print(f"Region: {self.region}")
        print(f"Filter pattern: {filter_pattern or '(none)'}")
        print(f"Fetching logs since: {self.since_seconds} seconds ago")
        print("Press Ctrl+C to stop.\n")

        while True:
            try:
                kwargs = {
                    "logGroupName": self.log_group,
                    "startTime": start_time,
                    "interleaved": True,
                }
                if filter_pattern:
                    kwargs["filterPattern"] = filter_pattern
                if next_token:
                    kwargs["nextToken"] = next_token

                resp = self.logs_client.filter_log_events(**kwargs)
                next_token = resp.get("nextToken")
                events = resp.get("events", [])

                if self.exclude_tokens:
                    events = [
                        e for e in events if not any(token in e["message"] for token in self.exclude_tokens)
                    ]

                for event in events:
                    dt_local = datetime.datetime.fromtimestamp(event["timestamp"] / 1000.0)
                    ts_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    stream_name = event["logStreamName"]

                    if self.exclude_streams and any(stream in stream_name for stream in self.exclude_streams):
                        continue
                    stream_name = stream_name.split("/")[-1][:9]

                    message = event["message"].rstrip("\n")
                    if self.colorize:
                        if self.highlight_tokens:
                            for token in self.highlight_tokens:
                                message = re.sub(
                                    rf"({token})", f"{CYAN}\\1{RESET}", message, flags=re.IGNORECASE
                                )
                        if self.filter_tokens:
                            pattern = "|".join(self.filter_tokens)
                            message = re.sub(
                                rf"({pattern})", f"{GREEN}\\1{RESET}", message, flags=re.IGNORECASE
                            )

                    formatted = self._format_log_line(ts_str, message, stream_name)
                    print(formatted, end="")

                time.sleep(2)
                if events:
                    max_ts = max(e["timestamp"] for e in events)
                    if max_ts > start_time:
                        start_time = max_ts + 1

            except KeyboardInterrupt:
                print("\nExiting tail...")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                time.sleep(5)


def parse_time_string(time_str: str) -> int:
    """
    Converts a string like "1h", "15m", or "10s" to seconds. Defaults to 3600 seconds.
    """
    match = re.match(r"^(\d+)([hms])$", time_str.strip(), re.IGNORECASE)
    if not match:
        return 3600
    value, unit = match.groups()
    value = int(value)
    unit = unit.lower()
    if unit == "h":
        return value * 3600
    elif unit == "m":
        return value * 60
    elif unit == "s":
        return value
    return 3600


def main():
    parser = argparse.ArgumentParser(
        usage="cw-tail [options]",
        description="Tail an AWS CloudWatch log group with a simplified layout.",
        epilog="Example: cw-tail --log-group my-logs --since 30m --colorize"
    )
    # Default values come from environment variables (set in .env) if available
    parser.add_argument(
        "--log-group",
        default=os.getenv("LOG_GROUP"),
        help="Name of the CloudWatch log group to tail. (Set LOG_GROUP in your .env file)"
    )
    parser.add_argument(
        "--region",
        default=os.getenv("REGION", "us-east-1"),
        help="AWS region (default: us-east-1) or set REGION in your .env file"
    )
    parser.add_argument(
        "--filter-pattern",
        default=os.getenv("FILTER_PATTERN", ""),
        help="Space-separated words to filter on, e.g. 'Finished error fail'. (Set FILTER_PATTERN in your .env file)"
    )
    parser.add_argument(
        "--highlight-tokens",
        default=os.getenv("HIGHLIGHT_TOKENS", ""),
        help="Space-separated words to highlight. (Set HIGHLIGHT_TOKENS in your .env file)"
    )
    parser.add_argument(
        "--exclude-tokens",
        default=os.getenv("EXCLUDE_TOKENS", ""),
        help="Space-separated words to exclude. (Set EXCLUDE_TOKENS in your .env file)"
    )
    parser.add_argument(
        "--exclude-streams",
        default=os.getenv("EXCLUDE_STREAMS", ""),
        help="Space-separated tokens to exclude stream names. (Set EXCLUDE_STREAMS in your .env file)"
    )
    parser.add_argument(
        "--since",
        default=os.getenv("SINCE", "1h"),
        help="How far back to start (e.g. '10s', '15m', '2h'). Default '1h'. (Set SINCE in your .env file)"
    )
    colorize_default = os.getenv("COLORIZE", "true").lower() in ("true", "1", "yes")
    parser.add_argument(
        "--colorize",
        action="store_true",
        default=colorize_default,
        help="Enable ANSI color highlighting. (Set COLORIZE in your .env file to true to enable by default)"
    )

    args = parser.parse_args()
    if not args.log_group:
        parser.error("log-group is required. Provide via --log-group or set LOG_GROUP in your .env file")

    seconds_ago = parse_time_string(args.since)

    tailer = CloudWatchTailer(
        log_group=args.log_group,
        region=args.region,
        filter_tokens=args.filter_pattern.split(),
        highlight_tokens=args.highlight_tokens.split(),
        exclude_tokens=args.exclude_tokens.split(),
        exclude_streams=args.exclude_streams.split(),
        since_seconds=seconds_ago,
        colorize=args.colorize,
    )
    tailer.tail()


if __name__ == "__main__":
    main()