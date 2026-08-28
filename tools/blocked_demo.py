"""Harmless long-running process used to demonstrate policy detection."""

import time


if __name__ == "__main__":
    print("Blocked demo process is running. Press Ctrl+C to stop it.")
    while True:
        time.sleep(1)

