import json
import os
import sys

CONFIG_FILE = os.path.expanduser("~/.timemate_config")

pos_to_id = {}


def process_arguments():
    """
    Process sys.argv to get the necessary parameters, like the database file location.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            timemate_home = json.load(f).get("TIMEMATEHOME")
    else:
        envhome = os.environ.get("TIMEMATEHOME")
        if envhome:
            timemate_home = envhome
        else:
            userhome = os.path.expanduser("~")
            timemate_home = os.path.join(userhome, ".timemate_home/")

    backup_dir = os.path.join(timemate_home, "backup")
    log_dir = os.path.join(timemate_home, "logs")
    db_path = os.path.join(timemate_home, "timemate.db")

    os.makedirs(timemate_home, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    # os.makedirs(markdown_dir, exist_ok=True)

    return timemate_home, backup_dir, log_dir, db_path


# Get command-line arguments: Process the command-line arguments to get the database file location
timemate_home, backup_dir, log_dir, db_path = process_arguments()
