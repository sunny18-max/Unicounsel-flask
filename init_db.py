from db_config import create_database, create_tables, get_db_connection


def main():
    print("Creating database (if not exists) and tables...")
    create_database()
    create_tables()

    # Verify by listing tables
    conn = get_db_connection()
    if not conn:
        print("Unable to connect to database for verification.")
        return

    cursor = conn.cursor()
    try:
        # SQLite way to list tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        if tables:
            print("Tables in database:")
            for t in tables:
                print(" - ", t[0])
        else:
            print("No tables found.")
    except Exception as e:
        print("Error verifying tables:", e)
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
