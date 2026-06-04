import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    # Try reading from web/.env or web/.env.local
    for env_path in ["../web/.env", "../web/.env.local"]:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        db_url = line.split("=", 1)[1].strip()
                        break
        if db_url:
            break

print(f"DATABASE_URL found: {db_url[:40]}...")

# Try to connect using psycopg2 or pg8000 or any available client
try:
    import psycopg2
    print("Using psycopg2...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM agent_reports;")
    print("Count:", cur.fetchone()[0])
    cur.close()
    conn.close()
except Exception as e:
    print(f"psycopg2 failed: {e}")
    
    try:
        import pg8000
        print("Using pg8000...")
        # Parse connection string
        # postgresql://user:password@host/dbname
        clean_url = db_url.split("://")[1]
        auth, host_port_db = clean_url.split("@")
        user, password = auth.split(":")
        host_port, dbname = host_port_db.split("/")
        if "?" in dbname:
            dbname = dbname.split("?")[0]
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = host_port
            port = 5432
            
        conn = pg8000.connect(user=user, password=password, host=host, port=port, database=dbname, ssl_context=True)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM agent_reports;")
        print("Count (pg8000):", cur.fetchone()[0])
        cur.close()
        conn.close()
    except Exception as e2:
        print(f"pg8000 failed: {e2}")
