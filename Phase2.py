import os
import pandas as pd
import requests


def read_csv_files(input_folder):
    csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]
    dataframes = {}
    for file in csv_files:
        path = os.path.join(input_folder, file)
        dataframes[file] = pd.read_csv(path)
    return dataframes


def find_nodes_for_location(lat, lon):
    nominatim_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"

    # Make the request to the Nominatim API for reverse geocoding
    response = requests.get(nominatim_url)

    # Parse the JSON response
    data = response.json()

    # Extract the osm_id and street name from the response
    osm_id = None
    street_name = None
    if 'osm_id' in data:
        osm_id = data['osm_id']
    if 'address' in data and 'road' in data['address']:
        street_name = data['address']['road']

    return osm_id, street_name


def find_segment_for_location(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"

    # Find the street ID and street name using reverse geocoding
    street_id, street_name = find_nodes_for_location(lat, lon)

    if not street_id:
        print("No street found based on the provided coordinates.")
        return None, None

    # Define the Overpass query to get all nodes for the given street ID
    overpass_query = f"""
        [out:json];
        way({street_id});
        node(w);
        out;
    """

    # Make the request to the Overpass API
    response = requests.post(overpass_url, data=overpass_query)

    # Parse the JSON response
    data = response.json()

    # Extract the nodes from the response
    nodes = []
    if 'elements' in data:
        for element in data['elements']:
            if element['type'] == 'node':
                nodes.append({
                    'id': element['id'],
                    'latitude': element['lat'],
                    'longitude': element['lon']
                })

    # Find the segment of the street based on proximity to the provided coordinates
    segment_info = find_segment_info(lat, lon, nodes)

    return segment_info, street_name


def find_segment_info(lat, lon, nodes):
    # Find the two nodes closest to the specified coordinates
    closest_nodes = sorted(nodes, key=lambda node: distance(lat, lon, node['latitude'], node['longitude']))[:2]

    if len(closest_nodes) != 2:
        return None

    # Sort the nodes by their order in the way
    closest_nodes.sort(key=lambda x: nodes.index(x))

    # Find the segment index and length
    segment_index = nodes.index(closest_nodes[0])
    segment_length = distance(closest_nodes[0]['latitude'], closest_nodes[0]['longitude'],
                              closest_nodes[1]['latitude'], closest_nodes[1]['longitude'])

    return {
        'segment_index': segment_index,
        'segment_length': segment_length
    }


def distance(lat1, lon1, lat2, lon2):
    # Calculate the Haversine distance between two sets of coordinates
    from math import radians, sin, cos, sqrt, atan2

    # Radius of the Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Calculate the differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat / 2) * 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) * 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Distance in kilometers
    distance_km = R * c

    return distance_km


def process_csv_files(csv_data, output_folder):
    csv_file_counter = 1

    for filename, df in csv_data.items():
        print(f"Processing {filename}...")

        passengerPickedUp = False
        segment_list = []

        for index, row in df.iterrows():
            # Check if passenger is picked up
            if row['Di2'] == 1:
                passengerPickedUp = True
                latitude = float(row['Latitude'])
                longitude = float(row['Longitude'])

                segment_info, street_name = find_segment_for_location(latitude, longitude)

                if segment_info and street_name:

                    segment = f"{segment_info['segment_index']} {street_name}_{segment_info['segment_index']}"

                    if segment not in segment_list:
                        segment_list.append(segment)

            elif row['Di2'] == 0 and passengerPickedUp:
                # When passenger is dropped off
                passengerPickedUp = False
                output_file = os.path.join(output_folder, f"output_{csv_file_counter}.txt")

                with open(output_file, 'a') as file:
                    for element in segment_list:
                        file.write(element + '\n')

                    if len(segment_list) > 0:
                        file.write(f"{len(segment_list)} ")
                        formatted_elements = [element.split(' ', 1)[1] for element in segment_list]
                        file.write(', '.join(formatted_elements))
                        file.write('\n')

                segment_list.clear()

        csv_file_counter += 1


def main():
    input_folder = input("Please enter the path to the input folder: ")
    output_folder = input("Please enter the path to the output folder: ")

    if not os.path.exists(input_folder):
        print(f"Input folder {input_folder} does not exist.")
        return
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    csv_data = read_csv_files(input_folder)
    process_csv_files(csv_data, output_folder)

    print("Operation completed.")

if __name__ == "__main__":
    main()
