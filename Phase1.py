import requests
import csv
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Function to process individual rows
def process_row(row):
    try:
        longitude = float(row['Longitute'])
        latitude = float(row['Latitude'])
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            road = address.get('road', 'N/A')
            street = address.get('street', 'N/A')
            if road == 'N/A' and street == 'N/A':
                return None  # Don't send back if both road and street are 'N/A'
            else:
                return (latitude, longitude, road, street)
        else:
            return (latitude, longitude, 'Request failed', 'Request failed')
    except ValueError as e:
        print(f"Error processing row: {e}")
        return None

def process_chunk(chunk):
    # Apply filters as per your requirements
    scenario_1_filtered = chunk[~((chunk['Di1'] == 0) & (chunk['Di3'] == 1))]
    scenario_2_filtered = chunk[~((chunk['Di1'] == 0) & (chunk['Di3'] == 0))]
    chunk = pd.concat([scenario_1_filtered, scenario_2_filtered])
    chunk = chunk.drop_duplicates(subset=['Longitute', 'Latitude'])

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_row, [row for _, row in chunk.iterrows() if not pd.isnull(row['Latitude']) and not pd.isnull(row['Longitute'])]))
    return [result for result in results if result is not None]

# Input path for CSV file and output filename
input_path = input("Enter the path to your CSV file: ")
output_filename = input("Enter the path to your output file: ")

# Read the CSV file into a DataFrame
df = pd.read_csv(input_path, parse_dates=['DeviceDateTime'])

unique_dates = df['DeviceDateTime'].dt.date.unique()

for date in unique_dates:
    # Filter the DataFrame for the current date
    filtered_df = df[df['DeviceDateTime'].dt.date == date]

    # Apply the process_chunk function to the filtered DataFrame
    filtered_results = process_chunk(filtered_df)

    # Extract unique road names from filtered results
    unique_roads = list(set(result[2] for result in filtered_results))

    # Sanitize road names by replacing spaces with underscores
    sanitized_unique_roads = [road.replace(' ', '_') for road in unique_roads]

    # Concatenate unique road names into a single string with spaces
    unique_roads_str = '\n'.join(sanitized_unique_roads)

    # Write unique road names to a new CSV file for the current date
    with open(output_filename, 'a', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([f'Date: {date}'])
        csvwriter.writerow(['Traveled Roads:'])
        csvwriter.writerow([unique_roads_str])

    print(f"Processing complete for {date}. Results saved in {output_filename}")
