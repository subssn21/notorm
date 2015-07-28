import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
db = None

def setup_package():
    conn = psycopg2.connect("dbname=postgres user=dramus")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)    
    
    #create the test database
    cur = conn.cursor()
    cur.execute("SELECT * from pg_catalog.pg_database where datname = 'test_notorm'")
    if(cur.rowcount):
        cur.execute('DROP DATABASE test_notorm') 
    cur.execute('CREATE DATABASE test_notorm')
    
    conn.close()
    
    global db
    db = psycopg2.connect("dbname=test_notorm user=dramus")
    
    cursor = db.cursor()
    cursor.execute("""create table users (
                          id serial,
                          username text,
                          password text,
                          email text
                      )
                   """)

def teardown_package():
    db.close()

    conn = psycopg2.connect("dbname=postgres user=dramus")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)    
    
    #drop the test database
    cur = conn.cursor()
    cur.execute('DROP DATABASE test_notorm')
    