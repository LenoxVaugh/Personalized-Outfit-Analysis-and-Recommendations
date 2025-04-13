import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from demo.env
env_path = os.path.join(os.path.dirname(__file__), 'demo.env')
load_dotenv(env_path)

# Debug logging
print("Database Configuration:")
print(f"ENV file path: {env_path}")
print(f"ENV file exists: {os.path.exists(env_path)}")
print(f"DATABASE_URL exists: {'DATABASE_URL' in os.environ}")

def get_db_connection():
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
            
        print(f"Attempting to connect to database...")
        connection = psycopg2.connect(database_url)
        print("Database connection established")
        return connection
        
    except Exception as e:
        print(f"Failed to connect to database: {str(e)}")
        print(f"Error type: {type(e)}")
        return None

def test_connection():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            # Test basic query
            cursor.execute("SELECT current_database(), current_user;")
            db, user = cursor.fetchone()
            print(f"Connected to database: {db}")
            print(f"Connected as user: {user}")
            
            # Test search_cache table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'search_cache'
                );
            """)
            table_exists = cursor.fetchone()[0]
            print(f"search_cache table exists: {table_exists}")
            
            cursor.close()
            conn.close()
            print("Connection closed successfully")
            return True
        return False
    except Exception as e:
        print(f"Error testing connection: {str(e)}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    test_connection()