import json

FILE="commands.json"

def load_commands():
    with open(FILE) as f:
        return json.load(f)
