from optimize_storage import optimize_storage
from dataclasses import dataclass
from typing import List
import json
import os
from optimize_storage import OutputDataPoint
import inquirer
import time, datetime

from convert_spot_data import SpotData, convert_spot_data

@dataclass
class StorageConfig:
    name: str
    power_limit: float
    capacity: float
    initial_soc: float

@dataclass
class RunMarketResult:
    total_cycles: int
    revenue: int
    data: List[OutputDataPoint]
    configuration: StorageConfig

def run_market(spot_data: SpotData, config: StorageConfig) -> RunMarketResult:
    """
    Takes raw spot price data and returns optimized storage operation schedule
    
    Args:
        spot_data: List of spot prices
        config: Storage configuration parameters
        
    Returns:
        RunMarketResult containing optimization results and configuration
    """
    convert_data = convert_spot_data(spot_data)
    result = optimize_storage(convert_data,
                          power_limit=config.power_limit,
                          capacity=config.capacity,
                          initial_soc=config.initial_soc)
    
    return RunMarketResult(
        total_cycles=result.total_cycles,
        revenue=result.revenue,
        configuration=config,
        data=result.data
    )

if __name__ == "__main__":
    # List available market files
    market_dir = os.path.join("data", "markets")
    market_files = [f[:-5] for f in os.listdir(market_dir) if f.endswith('.json')]
    
    # Create market file selection question
    market_question = [
        inquirer.List('market',
                     message="Select market file",
                     choices=market_files,
                     carousel=True)
    ]
    market_answer = inquirer.prompt(market_question)
    selected_market = market_answer['market']
            
    # List available config files and their names
    config_dir = os.path.join("data", "configurations")
    config_choices = []
    config_file_map = {}
    for f in os.listdir(config_dir):
        if f.endswith('.json'):
            with open(os.path.join(config_dir, f), 'r') as cf:
                config_data = json.load(cf)
                config_name = config_data['name']
                config_choices.append(config_name)
                config_file_map[config_name] = f[:-5]
    
    # Create config file selection question using config names
    config_question = [
        inquirer.List('config',
                     message="Select configuration",
                     choices=config_choices,
                     carousel=True)
    ]
    config_answer = inquirer.prompt(config_question)
    selected_config = config_file_map[config_answer['config']]
            
    market_file = os.path.join(market_dir, selected_market + ".json")
    config_file = os.path.join(config_dir, selected_config + ".json")
    
    with open(market_file, 'r') as f:
        spot_data = json.load(f)
        
    with open(config_file, 'r') as f:
        config_dict = json.load(f)
        config = StorageConfig(
            name=config_dict['name'],
            power_limit=config_dict['power_limit'], 
            capacity=config_dict['capacity'],
            initial_soc=config_dict['initial_soc']
        )
        
    result = run_market(SpotData(data=spot_data['data'], interval=spot_data['interval']), config)

    # Print total cycles and revenue
    print(f"Total cycles: {result.total_cycles}")
    print(f"Revenue: {result.revenue} EUR")

    # Create out directory if it doesn't exist
    os.makedirs("out/data", exist_ok=True)
    
    timestamp = time.mktime(datetime.datetime.now().timetuple())
    
    # Write result to JSON file
    output_file = os.path.join("out/data", f"{timestamp}.json")
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=lambda x: x.__dict__)
