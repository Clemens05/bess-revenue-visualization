from dataclasses import dataclass
from typing import List, Literal
import json
import pulp
import math

@dataclass
class DataPoint:
    date: str
    value: float

@dataclass 
class InputData:
    unit: str
    data: List[DataPoint]

@dataclass
class OutputDataPoint:
    date: str
    net_flow_kWh: float
    SoC_kWh: float
    action: Literal['BUY', 'SELL', 'HOLD']
    price: float  # Added price attribute

@dataclass
class OutputData:
    total_cycles: int
    revenue: int
    data: List[OutputDataPoint]

def optimize_storage(data: InputData, power_limit: float = 500, capacity: float = 1000, initial_soc: float = 0, interval_minutes: int = 60) -> OutputData:

    import os
    import json
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = 'out/__input__'
    os.makedirs(output_dir, exist_ok=True)
    
    input_data = {
        "power_limit": power_limit,
        "capacity": capacity,
        "initial_soc": initial_soc,
        "interval_minutes": interval_minutes,
        "data": [data_point.__dict__ for data_point in data.data]
    }
    
    with open(os.path.join(output_dir, f"{timestamp}.json"), 'w') as json_file:
        json.dump(input_data, json_file, indent=4)

    # Berechnete Konstanten
    INTERVAL_FRACTION = interval_minutes / 60
    POWER_LIMIT_PER_INTERVAL = power_limit * INTERVAL_FRACTION

    # Prices are in €/MWh, convert to €/kWh for calculations
    prices = [entry.value / 1000 for entry in data.data]
    dates = [entry.date for entry in data.data]
    N = len(prices)

    # MILP-Problem erstellen
    prob = pulp.LpProblem("Maximize_Profit", pulp.LpMaximize)

    # Entscheidungsvariablen
    ChargeAmount = [pulp.LpVariable(f'ChargeAmount_{t}', 0, POWER_LIMIT_PER_INTERVAL) for t in range(N)]
    DischargeAmount = [pulp.LpVariable(f'DischargeAmount_{t}', 0, POWER_LIMIT_PER_INTERVAL) for t in range(N)]
    NetFlow = [pulp.LpVariable(f'NetFlow_{t}', -POWER_LIMIT_PER_INTERVAL, POWER_LIMIT_PER_INTERVAL) for t in range(N)]
    SoC = [pulp.LpVariable(f'SoC_{t}', 0, capacity) for t in range(N)]
    Charge = [pulp.LpVariable(f'Charge_{t}', cat='Binary') for t in range(N)]
    Discharge = [pulp.LpVariable(f'Discharge_{t}', cat='Binary') for t in range(N)]

    # Zielfunktion
    profit = pulp.lpSum([
        (-ChargeAmount[t] * prices[t] + DischargeAmount[t] * prices[t])
        for t in range(N)
    ])
    prob += profit

    # Constraints
    # Anfangszustand des Speichers
    prob += SoC[0] == initial_soc + NetFlow[0]

    # Dynamik des Ladezustands
    for t in range(1, N):
        prob += SoC[t] == SoC[t-1] + NetFlow[t]

    # NetFlow Definition
    for t in range(N):
        prob += NetFlow[t] == ChargeAmount[t] - DischargeAmount[t]

    # Verbindung zwischen Aktionen und Mengen
    for t in range(N):
        # Laden
        prob += ChargeAmount[t] <= POWER_LIMIT_PER_INTERVAL * Charge[t]
        # Entladen
        prob += DischargeAmount[t] <= POWER_LIMIT_PER_INTERVAL * Discharge[t]
        # Exklusivität von Laden und Entladen
        prob += Charge[t] + Discharge[t] <= 1

    # Ladezustand Begrenzung
    for t in range(N):
        prob += SoC[t] >= 0
        prob += SoC[t] <= capacity

    # LP-Problem lösen
    solver = pulp.PULP_CBC_CMD(msg=False)
    result = prob.solve(solver)

    # Überprüfen, ob die Lösung optimal ist
    if result != pulp.LpStatusOptimal:
        # print("Optimale Lösung nicht gefunden!")
        pass
    else:
        # print("Optimale Lösung gefunden!")
        pass

    # Ergebnisse extrahieren
    ChargeAmount_values = [ChargeAmount[t].varValue for t in range(N)]
    DischargeAmount_values = [DischargeAmount[t].varValue for t in range(N)]
    NetFlow_values = [NetFlow[t].varValue for t in range(N)]
    SoC_values = [SoC[t].varValue for t in range(N)]
    Charge_values = [Charge[t].varValue for t in range(N)]
    Discharge_values = [Discharge[t].varValue for t in range(N)]

    # Gesamtprofit berechnen
    total_profit = sum([
        (-ChargeAmount_values[t] * prices[t] + DischargeAmount_values[t] * prices[t])
        for t in range(N)
    ])

    # Output-Daten vorbereiten
    output_data = []
    for i in range(N):
        action: Literal['BUY', 'SELL', 'HOLD'] = 'HOLD'
        if Charge_values[i] == 1:
            action = 'BUY'
        elif Discharge_values[i] == 1:
            action = 'SELL'
        output_data.append(OutputDataPoint(
            date=dates[i],
            net_flow_kWh=NetFlow_values[i],
            SoC_kWh=SoC_values[i],
            action=action,
            price=prices[i]  # Include price in the output
        ))

    # Berechnung der Gesamtladungen
    total_charge = sum(ChargeAmount_values)
    total_discharge = sum(DischargeAmount_values)
    total_cycles = min(total_charge, total_discharge) / capacity

    return OutputData(total_cycles=math.floor(total_cycles), revenue=math.floor(total_profit), data=output_data)

if __name__ == "__main__":
    with open('data.json', 'r') as file:
        json_data = json.load(file)
        data_points = [DataPoint(d['date'], d['value']) for d in json_data['data']]
        data = InputData(json_data['unit'], data_points)
    
        output_data = optimize_storage(data)

        print(f"Total cycles: {output_data.total_cycles}")
        print(f"Total revenue: {output_data.revenue}€")

        with open("out.json", "w") as f:
            json.dump(vars(output_data), f)
