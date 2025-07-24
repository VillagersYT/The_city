import random
import sqlite3


class Pioche:
    def __init__(self):
        conn = sqlite3.connect('city.db')
        cursor = conn.cursor()
        self.pioche = []
        cursor.execute("SELECT name,how_many FROM users")

        list_pioche = cursor.fetchall()
        for i in range(len(list_pioche)):
            for j in range(list_pioche[i][1]):
                self.pioche.append(list_pioche[i][0])
        conn.close()

        self.defausse = []

  
    def pioche_aleatoire(self):
        if len(self.pioche) == 0:
            self.pioche = self.defausse
            self.defausse = []
        item = random.choice(self.pioche)
        self.pioche.remove(item)
        return item
    
pioche = Pioche()


class Player: #il faut raouter un check pour savoir si on peux le construire et si il y a des reduc 
    def __init__(self, name):
        self.deck = []        # Liste de cartes possédées
        self.city = {}        # Ville construite (pas encore utilisée)
        self.point = 0        # Points du joueur
        self.name = name      # Nom du joueur
    
    def piocher(self, cmb):
        # Pioche un nombre donné de cartes aléatoires
        for _ in range(cmb):
            item = pioche.pioche_aleatoire()
            self.deck.append(item)

    def build(self, carte):
        # Essaie de construire une carte depuis le deck du joueur
        conn = sqlite3.connect('city.db')
        cursor = conn.cursor()

        if carte not in self.deck:
            print(f"Tu n'as pas la carte {carte} !")
            return None
        
        try:
            # Récupère le prix de la carte dans la base de données
            cursor.execute("SELECT price FROM users WHERE name=?", (carte,))
            result = cursor.fetchone()
            if result is None:
                print(f"La carte {carte} n'existe pas dans la base de données.")
                return
            price = result[0]
        except Exception as e:
            print(f"Erreur lors de l'accès à la base de données : {e}")
            return

        if price + 1 > len(self.deck):
            manque = (price + 1) - len(self.deck)
            print(f"Tu n'as pas assez de cartes. Il te manque {manque} carte(s).")
            return
        else:
            print(f"Il faut utiliser {price} carte(s). Tape leurs numéros séparés par un espace.")

            # Affiche toutes les cartes sauf celle à construire
            for i in range(len(self.deck)):
                if self.deck[i] != carte:
                    print(f"{i}: {self.deck[i]}")

        # Récupère les index des cartes à utiliser pour construire
        try:
            carte_choisies = input("Entre les numéros : ").split(" ")
            carte_choisies = list(map(int, carte_choisies))
        except ValueError:
            print("Entrée invalide. Veuillez entrer des nombres valides.")
            return

        if len(carte_choisies) == price:
            print(f"La carte {carte} a été construite. Les cartes utilisées : " +
                  ", ".join(str(self.deck[i]) for i in carte_choisies))

            # On trie les indices à supprimer à l'envers pour éviter les erreurs d'index
            for i in sorted(carte_choisies, reverse=True):
                del self.deck[i]

            # Supprime une seule occurrence de la carte construite
            self.deck.remove(carte)
        else:
            print(f"{len(carte_choisies)} carte(s) ont été sélectionnées, mais {price} sont requises.")



coolocactus = Player("coolocactus")
coolocactus.piocher(5)
print(coolocactus.deck)
coolocactus.build(coolocactus.deck[2])
print(coolocactus.deck)





