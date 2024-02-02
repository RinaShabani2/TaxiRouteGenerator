
import csv
import os
from datetime import datetime
import requests
from requests.exceptions import HTTPError, ConnectTimeout, ReadTimeout
import time

def read_csv_file(file_path):
    data = []
    with open(file_path, 'r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data

def filter_data(data):
    return [row for row in data if row['Di1'] == '1' and row['Di3'] == '1']

def calculate_duration(start_time, end_time):
    start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
    end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S.%f')
    return int((end - start).total_seconds())

def get_osm_id_and_name(latitude, longitude, max_attempts=5):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            osm_id = data.get('osm_id', 'Unknown_ID')
            road_name = data.get('address', {}).get('road', 'Unknown_Road').replace(' ', '_')
            return osm_id, road_name
        except (HTTPError, ConnectTimeout, ReadTimeout):
            attempt += 1
            time.sleep(2 ** attempt)
        except Exception:
            return 'Unknown_ID', 'Unknown_Road'

def divide_roads_into_segments(data):
    segments = {}
    passenger_routes = []
    current_route = []
    current_route_set = set()
    total_segments_count = 0

    for i in range(len(data) - 1):
        if data[i]['Di2'] == '1':
            start_lat, start_lon = data[i]['Latitude'], data[i]['Longitute']
            end_lat, end_lon = data[i + 1]['Latitude'], data[i + 1]['Longitute']
            start_id, start_name = get_osm_id_and_name(start_lat, start_lon)
            end_id, end_name = get_osm_id_and_name(end_lat, end_lon)

            if start_id == 'Unknown_ID' or end_id == 'Unknown_ID' or start_name == 'Unknown_Road' or end_name == 'Unknown_Road':
                continue

            segment_key = (start_id, end_id, start_name)
            duration = calculate_duration(data[i]['DeviceDateTime'], data[i + 1]['DeviceDateTime'])
            if segment_key not in segments:
                segments[segment_key] = duration
                current_route.append(segment_key)
                current_route_set.add(segment_key)
                total_segments_count += 1
            else:
                segments[segment_key] += duration

        elif data[i]['Di2'] == '0' and current_route:
            if current_route:
                passenger_routes.append(current_route)
                current_route = []
                current_route_set = set()

    if current_route:
        passenger_routes.append(current_route)

    unique_segments = [(key[0], key[1], key[2], duration) for key, duration in segments.items()]
    return unique_segments, passenger_routes, total_segments_count

def write_output_file(output_filename, unique_segments, passenger_routes, total_segments_count, bonus_points):
    with open(output_filename, 'w') as file:
        total_duration = sum(duration for _, _, _, duration in unique_segments)
        file.write(f"{total_duration} {total_segments_count} {len(unique_segments)} {len(passenger_routes)} {bonus_points}\n")
        for segment in unique_segments:
            file.write(f"{segment[0]} {segment[1]} {segment[2]}_{segment[0]}_{segment[1]} {segment[3]}\n")
        for route in passenger_routes:
            route_str = " ".join([f"{seg[2]}_{seg[0]}_{seg[1]}" for seg in route])
            file.write(f"{len(route)} {route_str}\n")

def main():
    input_file = input("Enter the path to your CSV file: ")
    output_folder = input("Enter the path to your output folder: ")
    output_filename = os.path.join(output_folder, "output.txt")
    bonus_points = 100
    data = read_csv_file(input_file)
    filtered_data = filter_data(data)
 
    unique_segments, passenger_routes, total_segments_count = divide_roads_into_segments(filtered_data)
    
    write_output_file(output_filename, unique_segments, passenger_routes, total_segments_count, bonus_points)
    
if __name__ == "__main__":
    main()
