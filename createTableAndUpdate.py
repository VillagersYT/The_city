import sqlite3 


def create_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Création de la table "users" corrigée
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            how_many INTEGER,
            price INTEGER NOT NULL,
            special_blue INTEGER DEFAULT 0,
            special_red INTEGER DEFAULT 0,
            special_green INTEGER DEFAULT 0,
            money TEXT DEFAULT '',
            points TEXT DEFAULT '',
            reduction_if TEXT DEFAULT '',
            can_build_if TEXT DEFAULT ''
        )
    ''')
    
    conn.commit()
    conn.close()


def insert_user(db_name, name, how_many, price, special_blue=None, special_red=None, special_green=None):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Insert a new user
    cursor.execute('''
        INSERT INTO users (name, how_many, price, special_blue, special_red, special_green)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, how_many, price, special_blue, special_red, special_green))
    
    conn.commit()
    conn.close()
    print(f"User {name} added with price {price} and special {special}")

def add_line():
    while True:
        name = input("Enter name card: ")
        if name.lower() == 'exit':
            print("Exiting the program.")
            sys.exit(0)
        if name == "":
            print("Name cannot be empty. Please try again.")
            continue
        how_many = input("Enter how many cards: ")
        price = input("Enter price: ")
        if price == "":
            price = 0
        else:
            price = int(price)
        special = input("Enter special (blue/red/green) with space between ").strip().split()

        
        insert_user('city.db', name, how_many, price, 
                    special_blue=special[0] if len(special) > 0 else None,
                    special_red=special[1] if len(special) > 1 else None,
                    special_green=special[2] if len(special) > 2 else None)
        
def add_reduc(db_name):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()

            # Sélectionne tous les utilisateurs avec une réduction spéciale
            cursor.execute("SELECT id, reduction_if FROM users WHERE special_blue > 0")
            rows = cursor.fetchall()

            for user_id, current_reduc in rows:
                if current_reduc and current_reduc.strip():
                    # On ajoute 'centre administratif' à la liste existante si elle n’y est pas déjà
                    reduc_list = [r.strip() for r in current_reduc.split(',')]
                    if 'centre administratif' not in reduc_list:
                        reduc_list.append('centre administratif')
                    new_reduc = ', '.join(reduc_list)
                else:
                    # Si aucun reduction_if, on met directement 'centre administratif'
                    new_reduc = 'centre administratif'

                # Mise à jour pour cet utilisateur
                cursor.execute(
                    "UPDATE users SET reduction_if = ? WHERE id = ?", (new_reduc, user_id)
                )

            conn.commit()

    except sqlite3.Error as e:
        print(f"Une erreur est survenue : {e}")


add_reduc('city.db')
