import sqlite3
import requests
from datetime import datetime, timedelta
import os
from dateutil import parser

# Function to fetch data from the API
# def fetch_leaderboard_data(api_url,headers):
#     response = requests.get(api_url,headers=headers)
#     if response.status_code == 200:
#         return response.json()["leaderboard_array"]
#     else:
#         print("Failed to fetch data from API:", response.status_code)
#         return None
def fetch_leaderboard_data(api_url, headers):
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        results = json_data.get("results", {})
        leaderboard = results.get("leaderboard", [])
        #print(json_data)  # Print the JSON response
        return leaderboard  # Use .get() method to safely access the key
    else:
        print("Failed to fetch data from API:", response.status_code)
        return None

# Function to create SQLite database and table
def create_database_table(database_file):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS leaderboard_array (
                    position INTEGER,
                    player_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    country TEXT,
                    holes_played INTEGER,
                    current_round INTEGER,
                    status TEXT,
                    strokes INTEGER,
                    updated TIMESTAMP,
                    prize_money TEXT,
                    ranking_points TEXT,
                    total_to_par TEXT
                    )''')
    conn.commit()
    conn.close()

# Function to insert data into SQLite database
def insert_data_into_database(database_file, data):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    for player in data:
        cursor.execute('''INSERT OR REPLACE INTO leaderboard_array (
                        position, player_id, first_name, last_name, country,
                        holes_played, current_round, status, strokes, updated,
                        prize_money, ranking_points, total_to_par
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (player["position"], player["player_id"], player["first_name"],
                        player["last_name"], player["country"], player["holes_played"],
                        player["current_round"], player["status"], player["strokes"],
                        parser.parse(player["updated"]),
                        player["prize_money"], player["ranking_points"], player["total_to_par"]))
    conn.commit()
    conn.close()

# Function to check if API can be called based on last call timestamp
def can_call_api(last_call_timestamp):
    if last_call_timestamp is None:
        return True
    else:
        return datetime.now() - last_call_timestamp > timedelta(minutes=1)

# Function to get the last API call timestamp from SQLite database
def get_last_call_timestamp(database_file):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_call_timestamp) FROM api_calls")
    result = cursor.fetchone()[0]
    conn.close()
    if result:
        return datetime.strptime(result, "%Y-%m-%dT%H:%M:%S")
    else:
        return None

# Function to update the last API call timestamp in SQLite database
def update_last_call_timestamp(database_file, timestamp):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO api_calls (last_call_timestamp) VALUES (?)", (timestamp,))
    conn.commit()
    conn.close()

# Main function to orchestrate the process
def main():
    api_url = "https://golf-leaderboard-data.p.rapidapi.com/leaderboard/651"  # Replace with your actual API URL
    headers = {
        "X-RapidAPI-Key": "ec34e27eb0mshc4a776c20e717bfp127602jsn97ffbe5d0d3a",
        "X-RapidAPI-Host": "golf-leaderboard-data.p.rapidapi.com"
    }
    database_file = "flask_app.db"  # SQLite database file

    # Check if API can be called based on last call timestamp
    last_call_timestamp = get_last_call_timestamp(database_file)
    if can_call_api(last_call_timestamp):
        # Fetch data from the API
        data = fetch_leaderboard_data(api_url,headers)
        if data:
            # Create SQLite database and table
            create_database_table(database_file)

            # Insert data into SQLite database
            insert_data_into_database(database_file, data)
            print("Data inserted into SQLite database successfully!")

            # Update last API call timestamp
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            update_last_call_timestamp(database_file, formatted_datetime)
        else:
            print("Failed to fetch data from the API.")
    else:
        print("API can only be called once every 5 minutes.")

if __name__ == "__main__":
    main()
