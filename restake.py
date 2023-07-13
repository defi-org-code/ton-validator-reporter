#!/usr/bin/python3 -u
import sys
import subprocess

# The path to the enterstake script
ENTERSTAKE_PATH = '/usr/src/reporter/enter.py'  # You need to replace this with the actual path

def get_last_stake():
    try:
        with open('last-stake', 'r') as f:
            lines = f.readlines()
            # Return the last non-empty line
            return next((line for line in reversed(lines) if line.strip()), None)
    except FileNotFoundError:
        print('last-stake file not found')
        return None

def restake():
    last_stake = get_last_stake()
    if last_stake is not None:
        subprocess.run([sys.executable, ENTERSTAKE_PATH, last_stake.strip()], check=True)

if __name__ == '__main__':
    restake()
