#!/usr/bin/env python3

import json
import sys
from typing import Optional, Dict, Any


def write_line_to_new_file(line: str, output_file: str = "filtered.log") -> None:
    """
    Extract and write the output to a new line to the specified output file.
    Args:
        line (str): The line to write to the output file.
        output_file (str): The name of the output file. Defaults to "filtered.log".
    """
    with open(output_file, "a") as f_output:
        f_output.write(line + "\n")


def filter_logs_by_timestamp(
    logfile: str, start_timestamp: str, end_timestamp: str
) -> None:
    """
    Read mongod logs line by line and match by timestamp
    Args:
        logfile (str): Path to the mongod logfile
        start_timestamp (str): The starting timestamp (in ISODate format)
        end_timestamp (str): The end timestamp (in ISODate format)
    """
    total_count = 0
    filtered_count = 0
    first_matching_entry: Optional[Dict[str, Any]] = None
    try:
        with open(logfile, "r") as f:
            for line in f:
                total_count += 1
                entry = json.loads(line)
                timestamp = entry.get("t", {}).get("$date")
                if timestamp and start_timestamp <= timestamp <= end_timestamp:
                    if first_matching_entry is None:
                        first_matching_entry = entry
                    filtered_count += 1
                    write_line_to_new_file(json.dumps(entry))
        print_summary(total_count, filtered_count, first_matching_entry)
    except FileNotFoundError:
        print("File not found:", logfile)
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error decoding JSON at line", logfile)
        sys.exit(1)


def print_summary(
    total_count: int,
    filtered_count: int,
    first_matching_entry: Optional[Dict[str, Any]],
) -> None:
    """
    Print a summary of the logs.
    Args:
        total_count (int): Total number of log lines read
        filtered_count (int): Number of log lines that matched the filter
        first_matching_entry (Optional[Dict[str, Any]]): The first matching log entry, if any.
    """
    print("\r\nNumber of log entries read:", total_count)
    if first_matching_entry:
        print("\r\nFirst matching log entry:", first_matching_entry)
    else:
        print("\nNo matching entries found")
    print("\r\nNumber of filtered log entries:", filtered_count)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python split.py logfile start_timestamp end_timestamp")
        sys.exit(1)

    logfile = sys.argv[1]
    start_timestamp = sys.argv[2]
    end_timestamp = sys.argv[3]

    filtered_logfile = filter_logs_by_timestamp(logfile, start_timestamp, end_timestamp)
