from connection import db, client
import psycopg2


# Get all todos
def get_todos():
    try:
        db.execute("SELECT * FROM driver ORDER BY id ASC")
        print("Got all Driver successfully")
        return db.fetchall()  # [] or [{}, {}, {}]
    except psycopg2.Error as e:
        print("Error: ", e)
        return False

# Create a todo
def create_todo(no, name, loc_25, lat, lon):
    try:
        db.execute(
            "INSERT INTO driver (no, name, loc_25, lat, lon) VALUES (%s, %s, %s, %s, %s)", (no, name, loc_25, lat, lon))
        client.commit()
        print("Created Driver successfully")
    except psycopg2.Error as e:
        print("Error: ", e)
        return False

#  get a todo by id
def get_todo_by_id(id):
    try:
        db.execute("SELECT * FROM driver WHERE id = %s", (id,))
        print("Got todo by id successfully")
        return db.fetchone()
    except psycopg2.Error as e:
        print("Error: ", e)
        return False


#  update a todo
def update_todo_by_id(id, no, name, loc_25, lat, lon):
    try:
        db.execute(
            "UPDATE driver SET no = %s, name = %s, loc_25 = %s, lat = %s, lon = %s WHERE id = %s", (no, name, loc_25, lat, lon, id))
        client.commit()
        print("Updated driver by id successfully")
    except psycopg2.Error as e:
        print("Error: ", e)
        return False


#  delete a todo
def delete_todo_by_id(id):
    try:
        db.execute("DELETE FROM driver WHERE id = %s", (id,))
        client.commit()
        print("Deleted driver by id successfully")
    except psycopg2.Error as e:
        print("Error: ", e)
        return False

#  Search for a todo
def search_todos(search):
    try:
        db.execute(
            "SELECT * FROM driver WHERE no LIKE %s OR name LIKE %s OR loc_25 LIKE %s OR lat LIKE %s OR lon LIKE %s", (search, search))
        print("Searched for a todo successfully")
        return db.fetchall()
    except psycopg2.Error as e:
        print("Error: ", e)
        return False