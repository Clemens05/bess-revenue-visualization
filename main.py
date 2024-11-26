from fastapi import FastAPI, HTTPException
from pathlib import Path
import json
from typing import List
from pydantic import BaseModel
from optimize_storage import optimize_storage, InputData, DataPoint
from fastapi.middleware.cors import CORSMiddleware
from convert_spot_data import convert_spot_data, SpotData


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, you can specify a list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

class Market(BaseModel):
    id: str
    name: str
    year: str
    interval: int

class StorageConfig(BaseModel):
    name: str
    power_limit: float
    capacity: float
    initial_soc: float

class RevenueCalculationResult(BaseModel):
    total_cycles: int
    revenue: int
    data: List[dict]

@app.get("/v1/markets", response_model=List[Market])
async def get_markets():
    """
    Returns list of available markets from data/markets directory.
    Extracts market details from the file content instead of the filename.
    """
    markets_dir = Path("data/markets")
    
    if not markets_dir.exists():
        raise HTTPException(status_code=404, detail="Markets directory not found")
        
    markets = []
    
    for file in markets_dir.glob("*.json"):
        try:
            with open(file) as f:
                market_data = json.load(f)
                if not all(key in market_data for key in ['metadata', 'interval', 'data']):
                    continue
                
                metadata = market_data['metadata']
                markets.append(Market(
                    id=file.stem,
                    name=metadata.get('market', 'Unknown'),
                    year=metadata.get('year', 'Unknown'),
                    interval=market_data.get('interval', 0) or 0  # Ensure interval is not None
                ))
        except:
            continue
            
    return markets

@app.post("/v1/calculate-revenue/{market_id}", response_model=RevenueCalculationResult)
async def calculate_revenue(market_id: str, config: StorageConfig):
    """
    Calculates potential revenue for given market and storage configuration.
    """
    market_file = Path(f"data/markets/{market_id}.json")
    if not market_file.exists():
        raise HTTPException(status_code=404, detail=f"Market {market_id} not found")
    
    print(config)
        
    try:
        with open(market_file) as f:
            market_data = json.load(f)
            
        # Convert market data to InputData format
        data_points = [
            DataPoint(str(i), value) 
            for i, value in enumerate(market_data['data'])
        ]
        spot_data = SpotData(data=market_data['data'], interval=market_data['interval'])
        input_data = convert_spot_data(spot_data)
        
        print("HERE", input_data.data)
        # Calculate revenue using optimization
        result = optimize_storage(
            data=input_data,
            power_limit=config.power_limit,
            capacity=config.capacity,
            initial_soc=config.initial_soc,
            interval_minutes=market_data['interval']
        )
        print("HERE2")

        
        # Convert result to dict for JSON response
        return {
            "total_cycles": result.total_cycles,
            "revenue": result.revenue,
            "data": [vars(point) for point in result.data]
        }
        
    except Exception as e:
        print(e.with_traceback(None))
        raise HTTPException(status_code=500, detail=str(e))
