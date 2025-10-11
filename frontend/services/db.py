import sqlite3

def init_db():
    #create or connect to db
    conn = sqlite3.connect('mydb.db')

    #create a cursor
    c = conn.cursor()

    #create a table
    c.execute("""CREATE TABLE if not exists users(
              name text)
    """)
    #save our changes
    conn.commit()

    #close our connection
    conn.close()

def submit(name):
     #create or connect to db
    conn = sqlite3.connect('mydb.db')

    #create a cursor
    c = conn.cursor()

    #Add a record
    c.execute("INSERT INTO users VALUES (:name)",
              {
                  'name': name,
              })
    
    #save our changes
    conn.commit()

    #close our connection
    conn.close()
    


def show_records(self):
    #create or connect to db
    conn = sqlite3.connect('mydb.db')

    #create a cursor
    c = conn.cursor()

    #grab records from db
    c.execute("SELECT * FROM users")
    records = c.fetchall()

    word = ''
    for record in records:
        word = f'{word}\n{record}'
        self.root.ids.name_label.text = f'{word}'

    #save our changes
    conn.commit()

    #close our connection
    conn.close()
