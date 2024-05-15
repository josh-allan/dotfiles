#!/usr/bin/env python3

import json
import sys


def filter_between_timestamps(logs, start_timestamp, end_timestamp):
    filtered_logs = []
    for log_entry in logs:
        timestamp = log_entry.get("t", {}).get("$date")
        if timestamp and timestamp >= start_timestamp and timestamp <= end_timestamp:
            filtered_logs.append(log_entry)
    return filtered_logs


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python filter.py logfile start_timestamp end_timestamp")
        sys.exit(1)

    logfile = sys.argv[1]
    start_timestamp = sys.argv[2]
    end_timestamp = sys.argv[3]

    try:
        with open(logfile, "r") as f:
            logs = [json.loads(line) for line in f]
    except FileNotFoundError:
        print("File not found:", logfile)
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error decoding JSON at line", logfile)
        sys.exit(1)

    filtered_logs = filter_between_timestamps(logs, start_timestamp, end_timestamp)
    for log_entry in filtered_logs:
        print(json.dumps(log_entry))

    # Print some valuable information about what was actually filtered
    print("\r\nNumber of log entries read:", len(logs))
    print("\r\nFirst matching log entry:", logs[0])  # Check the first log entry
    print("\r\nNumber of filtered log entries:", len(filtered_logs))
