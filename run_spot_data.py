import sys
import subprocess
from convert_spot_data import convert_spot_data_to_json

if len(sys.argv) != 2:
    print("Usage: python run_spot_data.py <spot_data_file>")
    sys.exit(1)

spot_data_file = sys.argv[1]

# Convert spot data to JSON format
convert_spot_data_to_json(spot_data_file)

# Run main2.py
subprocess.run(["python", "main2.py"], check=True)

# Run visualize_actions.py
subprocess.run(["python", "visualize_actions.py"], check=True)
