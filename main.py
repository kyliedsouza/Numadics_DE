from flask import Flask, request, jsonify, send_file
import os
import pandas as pd
import numpy as np
import time

app = Flask(__name__)

trip_info_df = pd.read_csv("Trip-Info.csv", low_memory=False)
vehicle_trails_path = "EOL-dump"
vehicle_files = [
    os.path.join(vehicle_trails_path, file)
    for file in os.listdir(vehicle_trails_path)
    if file.endswith(".csv")
]
vehicle_trail_dfs = [
    pd.read_csv(file, nrows=100, low_memory=False) for file in vehicle_files
]


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth Radius

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)

    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = R * c
    return distance


def compute_metrics(vehicle_trail_dfs, trip_info_df, start_time, end_time):
    results = {}

    for df in vehicle_trail_dfs:
        df["tis"] = pd.to_datetime(df["tis"], unit="s")
        start_date = pd.to_datetime(start_time, unit="s")
        end_date = pd.to_datetime(end_time, unit="s")
        search_range = df[(df["tis"] >= start_date) & (df["tis"] <= end_date)]

        if search_range.empty or len(search_range) < 2:
            continue

        search_range["lat_next"] = search_range["lat"].shift(-1)
        search_range["lon_next"] = search_range["lon"].shift(-1)
        search_range["distance"] = search_range.apply(
            lambda row: haversine(
                row["lat"], row["lon"], row["lat_next"], row["lon_next"]
            ),
            axis=1,
        )
        total_distance = search_range["distance"].sum()
        #!fix:currently doesnt count true flags, check avg speed calc
        avg_speed = search_range["spd"].mean()
        license_plate = search_range["lic_plate_no"].iloc[0]
        trips = trip_info_df[
            (trip_info_df["vehicle_number"] == license_plate)
            & (
                pd.to_datetime(trip_info_df["date_time"], format="%Y%m%d%H%M%S")
                >= pd.to_datetime(start_time, unit="s")
            )
            & (
                pd.to_datetime(trip_info_df["date_time"], format="%Y%m%d%H%M%S")
                <= pd.to_datetime(end_time, unit="s")
            )
        ]
        num_trips = len(trips)
        transporter_name = (
            trips["transporter_name"].iloc[0] if not trips.empty else "---"
        )

        if license_plate in results:
            results[license_plate]["Distance"] += total_distance
            results[license_plate]["Number of Trips Completed"] += num_trips
            results[license_plate]["Average Speed"] += avg_speed
        else:
            results[license_plate] = {
                "License plate number": license_plate,
                "Distance": total_distance,
                "Number of Trips Completed": num_trips,
                "Average Speed": avg_speed,
                "Transporter Name": transporter_name,
            }
    return pd.DataFrame(list(results.values()))


@app.route("/")
def home():
    start_time = "1523391121"
    end_time = "1553391121"
    return compute_metrics(
        vehicle_trail_dfs, trip_info_df, start_time, end_time
    ).to_html(header="true", table_id="table")


# @app.route("/report", methods=["GET"])
# def report_api():
#     try:
#         start_time = int(request.args.get("start_time"))
#         end_time = int(request.args.get("end_time"))

#         report_df = compute_metrics(
#             vehicle_trail_dfs, trip_info_df, start_time, end_time
#         )

#             return report_df.to_html(header="true", table_id="table")

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
