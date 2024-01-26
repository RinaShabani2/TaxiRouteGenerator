import csv
import os
from datetime import datetime
import requests
import time

def read_csv_file(file_path):
    data = []
    with open(file_path, 'r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data

def filter_data(data):
    filtered_data = []
    for row in data:
        if row['Di1'] == '1' and row['Di3'] == '1':
            filtered_data.append(row)
    return filtered_data

def identify_intersections(data):
    intersections = {}
    intersection_id = 0
    for row in data:
        coordinates = (row['Latitude'], row['Longitute'])
        if coordinates not in intersections:
            intersections[coordinates] = intersection_id
            intersection_id += 1
    return intersections

def process_row(row):
    try:
        longitude = float(row['Longitute'])
        latitude = float(row['Latitude'])
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"

        for attempt in range(5):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()  
                data = response.json()
                address = data.get('address', {})
                road = address.get('road', 'N/A')
                street = address.get('street', 'N/A')
                if road == 'N/A' and street == 'N/A':
                    return None
                else:
                    return f"{road} {street}"
            except requests.exceptions.RequestException as e:
                print(f"Error processing row: {e}")
                time.sleep(1)  # Wait 1 second before retrying
        return 'Request failed'
    except ValueError as e:
        print(f"Error processing row: {e}")
        return None

def divide_roads_into_segments(data, intersections):
    segments = []
    for i in range(len(data) - 1):
        start_coordinates = (data[i]['Latitude'], data[i]['Longitute'])
        end_coordinates = (data[i + 1]['Latitude'], data[i + 1]['Longitute'])
        segment_name = process_row(data[i])
        duration_minutes = calculate_duration(data[i]['DeviceDateTime'], data[i + 1]['DeviceDateTime'])
        segments.append((start_coordinates, end_coordinates, segment_name, duration_minutes))
    return segments

def convert_to_datetime(timestamp_str):
    try:
        return datetime.strptime('01/01/1970 ' + timestamp_str, '%m/%d/%Y %M:%S.%f')
    except ValueError:
        return None

def calculate_duration(start_time, end_time):
    start_datetime = convert_to_datetime(start_time)
    end_datetime = convert_to_datetime(end_time)
    duration_minutes = (end_datetime - start_datetime).total_seconds() / 60
    return duration_minutes

def write_output_file(output_filename, total_duration, num_intersections, num_segments, num_paths, bonus_points, segments, vehicle_paths):
    with open(output_filename, 'w') as file:
        file.write(f"{total_duration} {num_intersections} {num_segments} {num_paths} {bonus_points}\n")
        for segment in segments:
            file.write(f"{segment[0]} {segment[1]} {segment[2]} {segment[3]}\n")
        for path in vehicle_paths:
            file.write(f"{len(path)} {' '.join(map(str, path))}\n")

def main():
    input_file = input("Enter the path to your csv file: ")
    output_folder = input("Enter the path to your output folder: ")
    output_filename = os.path.join(output_folder, "output.txt")
    data = read_csv_file(input_file)
    filtered_data = filter_data(data)
    intersections = identify_intersections(filtered_data)
    segments = divide_roads_into_segments(filtered_data, intersections)
    vehicle_paths = []
    total_duration = 0
    num_intersections = len(intersections)
    num_segments = len(segments)
    num_paths = len(vehicle_paths)
    bonus_points = 100
    write_output_file(output_filename, total_duration, num_intersections, num_segments, num_paths, bonus_points, segments, vehicle_paths)

if __name__ == "__main__":
    main()
