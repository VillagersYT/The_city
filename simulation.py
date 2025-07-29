import random
import sqlite3


# Classe Pioche : gère la pioche et la défausse
class Pioche:
    def __init__(self):
        conn = sqlite3.connect('city.db')
        cursor = conn.cursor()
        self.pioche = []
        cursor.execute("SELECT name, how_many FROM users")
        list_pioche = cursor.fetchall()
        for name, count in list_pioche:
            self.pioche.extend([name] * count)
        conn.close()
        self.defausse = []

    def pioche_aleatoire(self):
        if not self.pioche:
            self.pioche = self.defausse[:]
            self.defausse = []
        item = random.choice(self.pioche)
        self.pioche.remove(item)
        return item


pioche = Pioche()


class Player:
    def __init__(self, name):
        self.deck = []
        self.city = []
        self.point = 0
        self.name = name


    def piocher(self, cmb):
        for _ in range(cmb):
            item = pioche.pioche_aleatoire()
            self.deck.append(item)

    def check_if_can_build(self, carte):
        conn = sqlite3.connect('city.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT price, reduction_if, can_build_if FROM users WHERE name = ?",
            (carte,)
        )
        result = cursor.fetchone()

        if result is None:
            print(f"La carte {carte} n'existe pas.")
            return False, None

        price, reduction, can_build_if = result

        if carte not in self.deck:
            print(f"La carte {carte} n'est pas dans ton deck.")
            return False, None

        if reduction:
            for item in reduction.split(","):
                if item.strip() in self.city and price > 0:
                    price -= 1

        if price + 1 > len(self.deck):
            manque = (price + 1) - len(self.deck)
            print(f"Tu n'as pas assez de cartes. Il te manque {manque} carte(s).")
            return False, None

        if can_build_if and can_build_if not in self.city:
            print(f"Tu dois construire {can_build_if} avant de construire {carte} !")
            return False, None

        return True, price

    def build(self, carte):
        conn = sqlite3.connect('city.db')
        cursor = conn.cursor()
        try:
            can_build, price = self.check_if_can_build(carte)
            if not can_build:
                return

            print(f"Tu dois utiliser {price} carte(s) pour construire {carte}.")
            for i, c in enumerate(self.deck):
                if c != carte:
                    print(f"{i}: {c}")

            try:
                choix = input("Entre les numéros : ").split()
                indices = list(map(int, choix))
            except ValueError:
                print("Entrée invalide.")
                return

            if len(indices) != price:
                print(f"{len(indices)} carte(s) sélectionnées, mais {price} requises.")
                return

            cartes_utilisées = [self.deck[i] for i in indices]
            for i in sorted(indices, reverse=True):
                pioche.defausse.append(self.deck[i])
                del self.deck[i]

            self.deck.remove(carte)
            self.city.append(carte)
            print(f"Carte {carte} construite avec succès.")
            print(f"Cartes utilisées : {', '.join(cartes_utilisées)}")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            conn.close()

    def calc_score(self):
        self.point = 0
        try:
            conn = sqlite3.connect('city.db')
            cursor = conn.cursor()
            for card in self.city:
                cursor.execute("SELECT points FROM users WHERE name = ?", (card,))
                result = cursor.fetchone()
                if not result:
                    continue

                points = result[0]

                if str(points).isdigit():
                    self.point += int(points)
                elif points in ("red", "green", "blue"):
                    for c in self.city:
                        cursor.execute(f"SELECT special_{points} FROM users WHERE name = ?", (c,))
                        bonus = cursor.fetchone()
                        if bonus and bonus[0]:
                            self.point += int(bonus[0])
            print(f"Points totaux pour {self.name} : {self.point}")
        except Exception as e:
            print(f"Erreur dans le calcul des points : {e}")
        finally:
            conn.close()

    def calc_money(self):
        money = 0
        try:
            conn = sqlite3.connect('city.db')
            cursor = conn.cursor()
            for card in self.city:
                cursor.execute("SELECT money FROM users WHERE name = ?", (card,))
                result = cursor.fetchone()
                if not result:
                    continue

                value = result[0]

                if str(value).isdigit():
                    money += int(value)
                elif value in ("red", "green", "blue"):
                    for c in self.city:
                        cursor.execute(f"SELECT special_{value} FROM users WHERE name = ?", (c,))
                        bonus = cursor.fetchone()
                        if bonus and bonus[0]:
                            money += int(bonus[0])
        except Exception as e:
            print(f"Erreur dans le calcul de l'argent : {e}")
        finally:
            conn.close()
        return money

    def __str__(self):
        return f"Player {self.name} - Deck: {self.deck}, City: {self.city}, Points: {self.point}, Money: {self.calc_money()}"

    def check_carte(self):
        if len(self.deck) > 12:
            print(f"Tu as trop de cartes ({len(self.deck)}), tu dois en défausser {len(self.deck) - 12} !")
            for i, c in enumerate(self.deck):
                print(f"{i}: {c}")
            try:
                choix = input("Entre les numéros des cartes à défausser : ").split()
                indices = list(map(int, choix))
                for i in sorted(indices, reverse=True):
                    pioche.defausse.append(self.deck[i])
                    self.deck.remove(self.deck[i])
                if len(self.deck) > 12:
                    self.check_carte()
            except ValueError:
                print("Entrée invalide.")


class Game:
    def __init__(self):
        self.players = []
        self.current_turn = 0
        self.current_player_index = 0

    def add_player(self, player):
        self.players.append(player)

    def next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def current_player(self):
        return self.players[self.current_player_index]

    def run(self):
        nb_players = int(input("Combien de joueurs ? "))
        for i in range(nb_players):
            name = input(f"Nom du joueur {i + 1} : ")
            player = Player(name)
            self.add_player(player)
            player.piocher(5)

        while True:
            current_player = self.current_player()
            print(f"\nC'est le tour de {current_player.name}.")
            current_player.piocher(current_player.calc_money())
            choice = True
            print(current_player)
            while choice not in ["piocher", "construire"]:

                choice = input("Que voulez-vous faire ? (piocher, construire) : ").strip().lower()

                if choice == "piocher":
                    current_player.piocher(5)
                    finished = False
                    while not finished:
                        print("Tu dois défausser 4 cartes parmi celles-ci :")
                        for i, c in enumerate(current_player.deck[-5:]):
                            print(f"{i}: {c}")
                        try:
                            choix = input("Entre les numéros des cartes à défausser : ").split()
                            indices = list(map(int, choix))
                            if len(indices) != 4:
                                print("Tu dois défausser exactement 4 cartes.")
                                continue
                            for i in sorted(indices, reverse=True):
                                pioche.defausse.append(current_player.deck[-5:][i])
                                current_player.deck.remove(current_player.deck[-5:][i])
                            finished = True

                        except ValueError:
                            print("Entrée invalide.")
                elif choice == "construire":
                    finished = False
                    while not finished:
                        carte = input("Quelle carte voulez-vous construire ? ")
                        can_build, _ = current_player.check_if_can_build(carte)
                        if not can_build:
                            continue
                        current_player.build(carte)
                        finished = True
                    current_player.check_carte()
                    choice
                else:
                    print("Choix invalide, essayez à nouveau.")

            current_player.calc_score()
            print(current_player)
            self.next_turn()
Game().run()
