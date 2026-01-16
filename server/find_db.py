import sqlite3
import os

root_dir = "/Users/macbook/Documents/shell/server"

print(f"Scanning {root_dir}...")

for dirpath, _, filenames in os.walk(root_dir):
    for f in filenames:
        if f.endswith(".db"):
            full_path = os.path.join(dirpath, f)
            print(f"\n--- Checking {full_path} ---")
            try:
                conn = sqlite3.connect(full_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"Tables: {[t[0] for t in tables]}")
                
                if ('cases',) in tables or ('cases',) in [t for t in tables]: # check tuple
                    # Simplified check
                    table_names = [t[0] for t in tables]
                    if 'cases' in table_names:
                        print("FOUND 'cases' TABLE!")
                        cursor.execute("SELECT * FROM cases WHERE slug='lapik'")
                        row = cursor.fetchone()
                        print(f"Lapik Row: {row}")
                        
                        # Fix it right here
                        cursor.execute("UPDATE cases SET price=10, currency='paw' WHERE slug='lapik'")
                        conn.commit()
                        print("UPDATED Lapik to 10 Paws!")
                        
                        cursor.execute("SELECT * FROM cases WHERE slug='lapik'")
                        print(f"New Lapik Row: {cursor.fetchone()}")
                    else:
                        print("'cases' table not found.")
                else:
                     print("No tables found.")
                conn.close()
            except Exception as e:
                print(f"Error: {e}")
