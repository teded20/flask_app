import sqlite3
import requests

# Function to fetch data from the API
def fetch_entry_list(api_url, headers):
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        entry_list = json_data.get("results", {}).get("entry_list", [])
        return entry_list
    else:
        print("Failed to fetch data from API:", response.status_code)
        return None

# Function to create SQLite database and entries table
def create_database_table(database_file):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM entries')
    conn.commit()
    cursor.execute('''CREATE TABLE IF NOT EXISTS entries (
                    player_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    country TEXT,
                    vegas INTEGER DEFAULT 21-- New column for Vegas data
                    )''')
    conn.commit()
    conn.close()

# Function to insert data into SQLite database
def insert_entry_list_into_database(database_file, entry_list):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    for entry in entry_list:
        # Ensure vegas data is within the range [1, 20]
        vegas = 21
        cursor.execute('''INSERT OR REPLACE INTO entries (
                        player_id, first_name, last_name, country, vegas
                        ) VALUES (?, ?, ?, ?, ?)''',
                        (entry["player_id"], entry["first_name"],
                        entry["last_name"], entry["country"],
                        vegas))
    conn.commit()
    conn.close()

# Main function to orchestrate the process
def main():
    api_url = "https://golf-leaderboard-data.p.rapidapi.com/entry-list/650"  # Replace with your actual API URL
    database_file = "flask_app.db"  # SQLite database file

    # Fetch data from the API
    headers = {
        "X-RapidAPI-Key": "ec34e27eb0mshc4a776c20e717bfp127602jsn97ffbe5d0d3a",
        "X-RapidAPI-Host": "golf-leaderboard-data.p.rapidapi.com"
    }
    entry_list = fetch_entry_list(api_url, headers)
    if entry_list:
        # Create SQLite database and table
        create_database_table(database_file)
        
        # Insert data into SQLite database
        insert_entry_list_into_database(database_file, entry_list)
        print("Data inserted into SQLite database successfully!")
    else:
        print("Failed to fetch data from the API.")

if __name__ == "__main__":
    main()
