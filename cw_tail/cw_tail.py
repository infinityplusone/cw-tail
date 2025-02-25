#!/usr/bin/env python3
import argparse
import boto3
import datetime
import re
import shutil
import sys
import time
import traceback
from rich.text import Text
from rich.console import Console
from . import formatters
from .utils import *

console = Console()


STREAM_COLORS = [
    lambda text: Text(text, style=f"rgb(0,135,0)"),
    lambda text: Text(text, style=f"rgb(175,135,0)"),
    lambda text: Text(text, style=f"rgb(135,0,135)"),
    lambda text: Text(text, style=f"rgb(0,135,175)"),
    lambda text: Text(text, style=f"rgb(215,95,135)"),
    lambda text: Text(text, style=f"rgb(95,175,175)"),
    lambda text: Text(text, style=f"rgb(95,95,175)"),
    lambda text: Text(text, style=f"rgb(255,175,135)"),
    lambda text: Text(text, style=f"rgb(0,95,135)"),
    lambda text: Text(text, style=f"rgb(215,215,0)"),
    lambda text: Text(text, style=f"rgb(0,135,175)"),
    lambda text: Text(text, style=f"rgb(255,135,95)"),
    lambda text: Text(text, style=f"rgb(87,87,255)"),
]

# Ensure UTF-8 encoding for stdout (helps with emojis, etc.)
sys.stdout.reconfigure(encoding="utf-8")

class CloudWatchTailer:
    """
    Tail an AWS CloudWatch log group with a simplified layout.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        if hasattr(self, "filter_tokens"):
            if isinstance(self.filter_tokens, str):
                self.filter_tokens = self.filter_tokens.split(",")
            self.filter_tokens = [str(t).strip().lstrip("?") for t in self.filter_tokens]
        else:
            self.filter_tokens = []
        self.filter_pattern = " ".join(f"?{t}" for t in self.filter_tokens)

        try:
            if self.formatter:
                self.formatter = getattr(formatters, self.formatter)
        except AttributeError:
            print(f"Formatter {self.formatter} not found")
            print(traceback.format_exc(), file=sys.stderr)
            raise ValueError(f"Formatter {self.formatter} not found")

        # Create a boto3 session and CloudWatch logs client
        self.session = boto3.Session(region_name=self.region)
        self.logs_client = self.session.client("logs")

        # For assigning consistent colors per container
        self.containers = {}
        self.colors = color_funcs()
        
    def _scroll_up(self, min_lines: int = 10):
        """
        Scrolls up the terminal by printing blank lines to push existing content off the screen.
        Ensures that the scroll effect is only as much as necessary.

        Args:
            min_lines (int): Minimum blank lines to print if terminal height is unknown.
        """
        # Get terminal size (fallback to 24 rows if it can't be determined)
        _, rows = shutil.get_terminal_size(fallback=(80, 24))
        
        # Adjust the scroll amount based on estimated prior output
        scrolled_lines = 0
        try:
            while scrolled_lines < max(rows - 5, min_lines):
                scrolled_lines += 1
                sys.stdout.write("\n")
                sys.stdout.flush()
                sleep(0.005)
        except KeyboardInterrupt:
            # If interrupted, finish the scroll immediately
            remaining_lines = max(rows - 5, min_lines) - scrolled_lines
            if remaining_lines > 0:
                sys.stdout.write("\n" * remaining_lines)
                sys.stdout.flush()
            raise

    def _print_header(self):
        """
        Print the header of the log group.
        """
        cols, _ = shutil.get_terminal_size(fallback=(80, 24))

        header = f"""
            {("=" * cols)}
            Starting tail of log group: {self.log_group}
            Region: {self.region}
            Filter pattern: {self.filter_pattern or '(none)'}
            Highlight tokens: {self.highlight_tokens or '(none)'}
            Exclude tokens: {self.exclude_tokens or '(none)'}
            Exclude streams: {self.exclude_streams or '(none)'}
            Fetching logs since: {self.since} seconds ago
            Press Ctrl+C to stop.
            {("=" * cols)}
        """
        print("\n".join([line.lstrip() for line in header.split("\n")]))

    def _format_log_line(self, timestamp_str: str, message: str, container: str) -> str:
        """
        Format a log line with a left column for the container and timestamp,
        and the message in the right column.
        """
        spacing = 1
        separator = " " * spacing + "|" + " " * spacing

        if container not in self.containers:
            self.containers[container] = (
                STREAM_COLORS[len(self.containers) % len(STREAM_COLORS)]
                if self.colorize else lambda x: x
            )
        container_color = self.containers[container]
        left_col = f"{container_color(container)}{separator}{timestamp_str}{separator}"

        # Create a Text object combining all parts
        line = Text()
        line.append(container_color(left_col))
        # If message is already a Text object, append it directly
        if isinstance(message, Text):
            line.append(message)
        else:
            line.append(str(message))
        line.append("\n")
        
        return line

    def _format_message(self, message: str) -> str:
        """
        Format the log message to remove ANSI escape codes and ensure proper line breaks.
        
        Overriding this method is your best bet to customize the log message.
        """
        message = message.rstrip("\n")
        if self.formatter and callable(self.formatter):
            message = self.formatter(message, **self.format_options)
        return message

    def _highlight(self, message: str, tokens: list[str], style: str) -> Text:
        """
        Highlight tokens in a message using a style.
        Tokens can be either literal strings or regular expressions.
        """
        text = Text(message)

        for token in tokens:
            token = str(token)
            try:
                # Try to compile as regex first
                pattern = re.compile(rf"\b{token}\b", flags=re.IGNORECASE)
            except re.error:
                # If it's not a valid regex, escape it for literal matching
                pattern = re.compile(rf"\b{re.escape(token)}\b", flags=re.IGNORECASE)
            
            for match in pattern.finditer(message):
                start, end = match.span()
                text.stylize(style, start, end)
        return text

    def _highlight_multiple(self, message: str, token_styles: list[tuple[str, str]]) -> Text:
        """
        Highlight multiple sets of tokens in a message using their respective styles.
        Tokens can be either literal strings or regular expressions.
        
        Args:
            message: The message to highlight
            token_styles: List of (token, style) tuples
        """
        text = Text(message)

        for token, style in token_styles:
            token = str(token)
            try:
                # Try to compile as regex first
                pattern = re.compile(rf"\b{token}\b", flags=re.IGNORECASE)
            except re.error:
                # If it's not a valid regex, escape it for literal matching
                pattern = re.compile(rf"\b{re.escape(token)}\b", flags=re.IGNORECASE)
            
            for match in pattern.finditer(message):
                start, end = match.span()
                text.stylize(style, start, end)
        return text


    def tail(self):
        """
        Continuously poll CloudWatch Logs for new events in the log group and print them.
        """
        next_token = None
        start_time = int(time.time() - self.since) * 1000
        self._scroll_up()
        self._print_header()

        while True:
            try:
                kwargs = {
                    "logGroupName": self.log_group,
                    "startTime": start_time,
                    "interleaved": True,
                }
                if self.filter_pattern:
                    kwargs["filterPattern"] = self.filter_pattern
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

                    message_text = self._format_message(event["message"])
                    if self.colorize:
                        message_text = Text(message_text)
                        # Apply both highlights in a single Text object
                        if self.highlight_tokens or self.filter_tokens:
                            all_highlights = []
                            if self.highlight_tokens:
                                all_highlights.extend((token, "black on yellow") for token in self.highlight_tokens)
                            if self.filter_tokens:
                                all_highlights.extend((token, "cyan") for token in self.filter_tokens)
                            message_text = self._highlight_multiple(str(message_text), all_highlights)

                    formatted = self._format_log_line(ts_str, message_text, stream_name)
                    console.print(formatted, end="")

                sleep(20)
                if events:
                    max_ts = max(e["timestamp"] for e in events)
                    if max_ts > start_time:
                        start_time = max_ts + 1
            except KeyboardInterrupt:
                print("\nExiting tail...")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                # use a sleep to avoid busy-waiting
                sleep(10)

def main():
    """
    Main entry point for the cw-tail command.
    """
    parser = argparse.ArgumentParser(
        usage="cw-tail [options]",
        description="Tail AWS CloudWatch logs with a colored, simplified layout.",
        epilog="""
Examples:
  cw-tail --config prod                      # Use the prod configuration
  cw-tail --config dev --since 30m           # Use dev config but override the time window
  cw-tail --log-group my-logs --colorize     # Use default config with specific log group
        """
    )
    
    parser.add_argument(
        "--config",
        help="Name of the configuration to use from ~/.config/cw-tail/config.yml"
    )
    parser.add_argument(
        "--log-group",
        help="Name of the CloudWatch log group to tail"
    )
    parser.add_argument(
        "--region",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--filter-tokens",
        help="Filter logs containing these comma-separated tokens (uses AWS's filter pattern syntax)"
    )
    parser.add_argument(
        "--highlight-tokens",
        help="Highlight logs containing these comma-separated tokens. Accepts regexes"
    )
    parser.add_argument(
        "--exclude-tokens",
        help="Exclude logs containing these comma-separated tokens"
    )
    parser.add_argument(
        "--exclude-streams",
        help="Exclude logs from these comma-separated stream names"
    )
    parser.add_argument(
        "--since",
        help="How far back to get logs (e.g., 1h, 15m, 30s)"
    )
    parser.add_argument(
        "--colorize",
        action="store_true",
        help="Enable colored output"
    )
    parser.add_argument(
        "--formatter",
        help="Formatter to use. (Set FORMATTER in your .env file)"
    )
    parser.add_argument(
        "--format-options",
        help="Querystring-like options to pass to the formatter. (Set FORMAT_OPTIONS in your .env file)"
    )

    args = parser.parse_args()
    
    # Load config and merge with command line arguments
    config = load_config(args.config) | parse_command_line_arguments(args)

    if not config.get("log_group"):
        parser.error("log-group is required. Provide via --log-group or config file")

    # Convert time strings to seconds
    config["since"] = parse_time_string(config.get("since", "1h"))

    tailer = CloudWatchTailer(**config)
    tailer.tail()


if __name__ == "__main__":
    main()