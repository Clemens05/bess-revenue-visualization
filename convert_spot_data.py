import json
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import asdict
from optimize_storage import InputData, DataPoint
from dataclasses import dataclass

@dataclass
class SpotData:
    data: List[Optional[float]]
    interval: int

def convert_spot_data(spot_data: SpotData) -> InputData:
    # Create a list to store the formatted data
    formatted_data: List[DataPoint] = []

    # Set the start date (January 1, 2024)
    start_date: datetime = datetime(2024, 1, 1)

    # Process each data point
    for i, value in enumerate(spot_data.data):
        # Skip null values
        if value is None:
            continue
            
        # Calculate the date for this data point (adding i*interval minutes to start date)
        current_date: datetime = start_date + timedelta(minutes=i*spot_data.interval)
        
        # Format the date as ISO string and create the data point
        data_point = DataPoint(
            date=current_date.isoformat() + ".000Z",
            value=value
        )
        
        formatted_data.append(data_point)

    return InputData(
        unit="EUR/MWh",
        data=formatted_data
    )

if __name__ == "__main__":
    from sys import argv
    if len(argv) > 1:
        with open(argv[1], 'r') as f:
            spot_data: List[Optional[float]] = json.load(f)
        result = convert_spot_data(spot_data)
        with open('dist/__main__/data.json', 'w') as f:
            # Convert dataclass to dict before serializing
            result_dict = asdict(result)
            json.dump(result_dict, f, indent=2)
    else:
        print("Please provide an input file path as argument")
