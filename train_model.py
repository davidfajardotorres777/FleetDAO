import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression
from dao import FleetDAO

def train_and_save():
    dao = FleetDAO()
    trucks = dao.get_trucks()
    if not trucks:
        print("No trucks found, seed the DB first.")
        return
    
    truck_id = str(trucks[0]["_id"])
    telemetry = dao.get_telemetry(truck_id)
    if not telemetry:
        print("No telemetry found.")
        return
        
    df = pd.DataFrame(telemetry)
    X = df[['speed_kmh', 'engine_rpm']]
    y = df['engine_temp_c']
    
    model = LinearRegression()
    model.fit(X, y)
    
    joblib.dump(model, 'fleet_model.joblib')
    print("Modelo guardado como fleet_model.joblib")

if __name__ == '__main__':
    train_and_save()
