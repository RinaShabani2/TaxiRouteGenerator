import csv
import os
from datetime import datetime, time
import requests
from math import radians, cos, sin, sqrt, atan2, degrees
from requests.exceptions import HTTPError, ConnectTimeout, ReadTimeout, ConnectionError, Timeout

def read_csv_file(file_path):
    data = []
    with open(file_path, 'r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data

def is_time_in_range(start_str, end_str):
    start_time = datetime.strptime(start_str.split()[1], '%H:%M:%S.%f').time()
    end_time = datetime.strptime(end_str.split()[1], '%H:%M:%S.%f').time()
    return time(7, 0) <= start_time <= time(21, 0) and time(7, 0) <= end_time <= time(21, 0)

def calculate_duration(start_time, end_time):
    start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
    end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S.%f')
    return int((end - start).total_seconds() / 60)  

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dLon = lon2 - lon1
    y = sin(dLon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dLon)
    initial_bearing = atan2(y, x)
    bearing = (degrees(initial_bearing) + 360) % 360
    return bearing

def get_street_name(latitude, longitude):
    try:
        response = requests.get(
            f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1",
            headers={'User-Agent': 'YourAppName/1.0'}
        )
        response.raise_for_status()
        data = response.json()
        address = data.get('address', {})

        return address.get('road', address.get('neighbourhood', 'Unknown Location'))
    except Exception as e:
        print(f"Error fetching street name: {e}")
        return "Unknown Location"

def detect_significant_direction_change(data):
    changes = []
    for i in range(1, len(data) - 1):
        bearing1 = calculate_bearing(float(data[i-1]['Latitude']), float(data[i-1]['Longitute']), float(data[i]['Latitude']), float(data[i]['Longitute']))
        bearing2 = calculate_bearing(float(data[i]['Latitude']), float(data[i]['Longitute']), float(data[i+1]['Latitude']), float(data[i+1]['Longitute']))
        if abs(bearing2 - bearing1) > 45:  
            changes.append(i)
    return changes

def divide_roads_into_segments(data):
    segments = {}
    passenger_routes = []
    current_route = []
    total_duration = 0  

    for i in range(len(data) - 1):
        if data[i]['Di2'] == '1':
            start_lat, start_lon = data[i]['Latitude'], data[i]['Longitute']
            end_lat, end_lon = data[i + 1]['Latitude'], data[i + 1]['Longitute']
            segment_name = get_street_name((float(start_lat) + float(end_lat)) / 2, (float(start_lon) + float(end_lon)) / 2)

            segment_key = (start_lat, start_lon, end_lat, end_lon)
            duration = calculate_duration(data[i]['DeviceDateTime'], data[i + 1]['DeviceDateTime'])
            total_duration += duration  

            if segment_key not in segments:
                segments[segment_key] = {'name': segment_name, 'durations': [duration]}
                current_route.append(segment_key)
            else:
                segments[segment_key]['durations'].append(duration)

        if data[i]['Di2'] == '0' and current_route:
            passenger_routes.append(current_route.copy())
            current_route.clear()

    if current_route:
        passenger_routes.append(current_route)

    unique_segments = []
    for key, info in segments.items():
        durations = info['durations']
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        unique_segments.append((key + (info['name'], avg_duration, min_duration, max_duration, len(durations))))

    total_segments_count = len(segments)

    return unique_segments, passenger_routes, total_duration, total_segments_count


def write_output_file(output_filename, unique_segments, passenger_routes, total_duration, total_segments_count):
    with open(output_filename, 'w', encoding='utf-8') as file:
        file.write(f"{total_duration} {total_segments_count} {len(unique_segments)} {len(passenger_routes)}, 100\n")
        for segment in unique_segments:
            start_lat, start_lon, end_lat, end_lon, name, avg_duration, min_duration, max_duration, count = segment
            file.write(f"{start_lat}_{start_lon} {end_lat}_{end_lon} {name} {avg_duration} {min_duration} {max_duration} {count}\n")

        for route in passenger_routes:
            if len(route) > 1:  
                route_str = " ".join([f"{start_lat}_{start_lon} {end_lat}_{end_lon} {name}" for start_lat, start_lon, end_lat, end_lon, name in route])
                file.write(f"{len(route)} {route_str}\n")


def main():
    input_file = input("Enter the path to your CSV file: ")
    output_folder = input("Enter the path to your output folder: ")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    output_filename = os.path.join(output_folder, "output.txt")
   
    data = read_csv_file(input_file)
    unique_segments, passenger_routes, total_duration, total_segments_count = divide_roads_into_segments(data)
   
    write_output_file(output_filename, unique_segments, passenger_routes, total_duration, total_segments_count)
   
    print(f"Output written to {output_filename}")


if __name__ == "__main__":
    main()
