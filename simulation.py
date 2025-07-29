import random
import sqlite3
from typing import List, Tuple, Optional
from contextlib import contextmanager


@contextmanager
def get_db_connection():
    """Context manager pour gérer les connexions à la base de données"""
    conn = sqlite3.connect('city.db')
    try:
        yield conn
    finally:
        conn.close()


class Pioche:
    """Gère la pioche et la défausse du jeu"""
    
    def __init__(self):
        self.pioche: List[str] = []
        self.defausse: List[str] = []
        self._load_cards_from_db()
    
    def _load_cards_from_db(self):
        """Charge les cartes depuis la base de données"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, how_many FROM users")
            list_pioche = cursor.fetchall()
            
            for name, count in list_pioche:
                self.pioche.extend([name] * count)
        
        random.shuffle(self.pioche)  # Mélanger dès le départ
    
    def pioche_aleatoire(self) -> str:
        """Pioche une carte aléatoirement"""
        if not self.pioche:
            if not self.defausse:
                raise ValueError("Plus de cartes disponibles !")
            self.pioche = self.defausse[:]
            self.defausse = []
            random.shuffle(self.pioche)
        
        return self.pioche.pop()  # Plus efficace que remove()


class Player:
    """Représente un joueur du jeu"""
    
    def __init__(self, name: str):
        self.deck: List[str] = []
        self.city: List[str] = []
        self.point: int = 0
        self.name: str = name
        self._pioche = None  # Sera injecté
    
    def set_pioche(self, pioche: Pioche):
        """Injecte la dépendance pioche"""
        self._pioche = pioche
    
    def piocher(self, nb_cartes: int):
        """Pioche un nombre donné de cartes"""
        if not self._pioche:
            raise ValueError("Pioche non initialisée")
            
        for _ in range(nb_cartes):
            try:
                item = self._pioche.pioche_aleatoire()
                self.deck.append(item)
            except ValueError as e:
                print(f"Erreur lors de la pioche : {e}")
                break
    
    def _get_card_info(self, carte: str) -> Optional[Tuple]:
        """Récupère les informations d'une carte depuis la DB"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT price, reduction_if, can_build_if FROM users WHERE name = ?",
                (carte,)
            )
            return cursor.fetchone()
    
    def check_if_can_build(self, carte: str) -> Tuple[bool, Optional[int]]:
        """Vérifie si on peut construire une carte"""
        result = self._get_card_info(carte)
        
        if result is None:
            print(f"La carte {carte} n'existe pas.")
            return False, None
        
        price, reduction, can_build_if = result
        
        if carte not in self.deck:
            print(f"La carte {carte} n'est pas dans ton deck.")
            return False, None
        
        # Calcul des réductions
        if reduction:
            reduction_cards = [item.strip() for item in reduction.split(",")]
            for card in reduction_cards:
                if card in self.city and price > 0:
                    price -= 1
        
        # Vérification du nombre de cartes disponibles
        if price + 1 > len(self.deck):
            manque = (price + 1) - len(self.deck)
            print(f"Tu n'as pas assez de cartes. Il te manque {manque} carte(s).")
            return False, None
        
        # Vérification des prérequis
        if can_build_if and can_build_if not in self.city:
            print(f"Tu dois construire {can_build_if} avant de construire {carte} !")
            return False, None
        
        return True, price
    
    def _select_cards_to_discard(self, nb_required: int) -> List[int]:
        """Sélectionne les cartes à défausser (interface utilisateur)"""
        while True:
            print(f"Tu dois utiliser {nb_required} carte(s) :")
            available_cards = [(i, c) for i, c in enumerate(self.deck)]
            
            for i, c in available_cards:
                print(f"{i}: {c}")
            
            try:
                choix = input("Entre les numéros : ").split()
                indices = [int(x) for x in choix]
                
                if len(indices) != nb_required:
                    print(f"{len(indices)} carte(s) sélectionnées, mais {nb_required} requises.")
                    continue
                
                # Vérifier que tous les indices sont valides
                if all(0 <= i < len(self.deck) for i in indices):
                    return indices
                else:
                    print("Indices invalides.")
                    
            except ValueError:
                print("Entrée invalide.")
    
    def build(self, carte: str) -> bool:
        """Construit une carte"""
        can_build, price = self.check_if_can_build(carte)
        if not can_build:
            return False
        
        if price == 0:
            # Construction gratuite
            self.deck.remove(carte)
            self.city.append(carte)
            print(f"Carte {carte} construite gratuitement.")
            return True
        
        indices = self._select_cards_to_discard(price)
        
        # Défausser les cartes sélectionnées (en ordre décroissant pour éviter les problèmes d'index)
        cartes_utilisees = []
        for i in sorted(indices, reverse=True):
            if i < len(self.deck):  # Sécurité supplémentaire
                carte_defaussee = self.deck.pop(i)
                self._pioche.defausse.append(carte_defaussee)
                cartes_utilisees.append(carte_defaussee)
        
        # Construire la carte
        self.deck.remove(carte)
        self.city.append(carte)
        
        print(f"Carte {carte} construite avec succès.")
        print(f"Cartes utilisées : {', '.join(cartes_utilisees)}")
        return True
    
    def _calculate_special_points(self, color: str) -> int:
        """Calcule les points spéciaux pour une couleur donnée"""
        points = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for card in self.city:
                cursor.execute(f"SELECT special_{color} FROM users WHERE name = ?", (card,))
                result = cursor.fetchone()
                if result and result[0]:
                    points += int(result[0])
        return points
    
    def calc_score(self):
        """Calcule le score du joueur"""
        self.point = 0
        
        with get_db_connection() as conn:
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
                    self.point += self._calculate_special_points(points)
        
        print(f"Points totaux pour {self.name} : {self.point}")
    
    def calc_money(self) -> int:
        """Calcule l'argent du joueur"""
        money = 0
        
        with get_db_connection() as conn:
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
                    money += self._calculate_special_points(value)
        
        return money
    
    def check_carte(self):
        """Vérifie et gère la limite de cartes en main"""
        MAX_CARDS = 12
        
        while len(self.deck) > MAX_CARDS:
            nb_to_discard = len(self.deck) - MAX_CARDS
            print(f"Tu as trop de cartes ({len(self.deck)}), tu dois en défausser {nb_to_discard} !")
            
            indices = self._select_cards_to_discard(nb_to_discard)
            
            # Défausser les cartes sélectionnées
            for i in sorted(indices, reverse=True):
                carte_defaussee = self.deck.pop(i)
                self._pioche.defausse.append(carte_defaussee)
    
    def __str__(self) -> str:
        return f"Player {self.name} - Deck: {len(self.deck)} cartes, City: {self.city}, Points: {self.point}, Money: {self.calc_money()}"


class Game:
    """Gère le déroulement du jeu"""
    
    def __init__(self):
        self.players: List[Player] = []
        self.current_player_index: int = 0
        self.pioche = Pioche()
    
    def add_player(self, player: Player):
        """Ajoute un joueur au jeu"""
        player.set_pioche(self.pioche)  # Injection de dépendance
        self.players.append(player)
    
    def next_turn(self):
        """Passe au joueur suivant"""
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
    
    def current_player(self) -> Player:
        """Retourne le joueur actuel"""
        return self.players[self.current_player_index]
    
    def _handle_pioche_action(self, player: Player):
        """Gère l'action de pioche"""
        CARDS_TO_DRAW = 5
        CARDS_TO_DISCARD = 4
        
        initial_deck_size = len(player.deck)
        player.piocher(CARDS_TO_DRAW)
        
        # Défausser 4 cartes parmi les 5 piochées
        while True:
            print("Tu dois défausser 4 cartes parmi celles-ci :")
            last_cards = player.deck[-CARDS_TO_DRAW:]
            
            for i, c in enumerate(last_cards):
                print(f"{i}: {c}")
            
            try:
                choix = input("Entre les numéros des cartes à défausser : ").split()
                indices = [int(x) for x in choix]
                
                if len(indices) != CARDS_TO_DISCARD:
                    print(f"Tu dois défausser exactement {CARDS_TO_DISCARD} cartes.")
                    continue
                
                # Défausser les cartes sélectionnées
                cards_to_remove = []
                for i in indices:
                    if 0 <= i < len(last_cards):
                        cards_to_remove.append(last_cards[i])
                
                for card in cards_to_remove:
                    player.deck.remove(card)
                    self.pioche.defausse.append(card)
                
                break
                
            except ValueError:
                print("Entrée invalide.")
    
    def _handle_human_build_action(self, player: Player):
        """Gère l'action de construction pour un humain"""
        while True:
            carte = input("Quelle carte voulez-vous construire ? ").strip()
            if not carte:
                continue
                
            if player.build(carte):
                player.check_carte()
                break
    
    def _handle_ai_turn(self, ai_player: AIPlayer):
        """Gère le tour complet d'un joueur IA"""
        game_state = self.create_game_state()
        
        print(f"\n{ai_player.name} (IA {ai_player.personality.value}) réfléchit...")
        
        # Pioche automatique basée sur l'argent
        money = ai_player.calc_money()
        if money > 0:
            ai_player.piocher(money)
            print(f"{ai_player.name} pioche {money} carte(s) grâce à son argent.")
        
        # Décision de l'IA
        decision = ai_player.make_decision(game_state)
        print(f"{ai_player.name} décide de : {decision}")
        
        if decision == "piocher":
            ai_player.ai_handle_pioche_action()
            print(f"{ai_player.name} pioche 5 cartes et en défausse 4.")
        
        elif decision == "construire":
            card_to_build = ai_player.choose_card_to_build(game_state)
            if card_to_build:
                if ai_player.ai_build(card_to_build):
                    print(f"{ai_player.name} construit : {card_to_build}")
                    ai_player.ai_check_carte()
                else:
                    print(f"{ai_player.name} n'arrive pas à construire {card_to_build}")
            else:
                print(f"{ai_player.name} n'a aucune carte constructible")
        
        # Calcul et affichage du score
        ai_player.calc_score()
        print(f"État de {ai_player.name} : {ai_player}")
    
    def _setup_players(self):
        """Configure les joueurs du jeu"""
        print("=== Configuration des joueurs ===")
        
        try:
            nb_players = int(input("Combien de joueurs au total ? "))
            if nb_players <= 0 or nb_players > 6:
                print("Nombre de joueurs invalide (1-6).")
                return False
        except ValueError:
            print("Nombre de joueurs invalide.")
            return False
        
        for i in range(nb_players):
            print(f"\n--- Joueur {i + 1} ---")
            is_ai = input("Joueur IA ? (o/n) : ").lower().startswith('o')
            
            if is_ai:
                # Configuration IA
                name = input(f"Nom de l'IA {i + 1} : ").strip()
                if not name:
                    name = f"IA-{i + 1}"
                
                print("Personnalités disponibles :")
                for j, personality in enumerate(AIPersonality, 1):
                    print(f"{j}. {personality.value}")
                
                try:
                    choice = int(input("Choisissez une personnalité (1-5) : ")) - 1
                    personalities = list(AIPersonality)
                    if 0 <= choice < len(personalities):
                        personality = personalities[choice]
                    else:
                        personality = AIPersonality.BALANCED
                except ValueError:
                    personality = AIPersonality.BALANCED
                
                try:
                    difficulty = float(input("Difficulté (0.0=facile, 1.0=expert) : "))
                    difficulty = max(0.0, min(1.0, difficulty))
                except ValueError:
                    difficulty = 1.0
                
                ai_player = self.add_ai_player(name, personality, difficulty)
                print(f"IA {name} ajoutée (personnalité: {personality.value}, difficulté: {difficulty})")
            
            else:
                # Joueur humain
                name = input(f"Nom du joueur {i + 1} : ").strip()
                if not name:
                    name = f"Joueur-{i + 1}"
                
                player = Player(name)
                self.add_player(player)
                print(f"Joueur humain {name} ajouté")
        
        return True
    
    def _check_end_conditions(self) -> bool:
        """Vérifie les conditions de fin de partie"""
        # Exemple de conditions de fin (à adapter selon vos règles)
        
        # Fin si un joueur a construit 8 cartes
        for player in self.players:
            if len(player.city) >= 8:
                print(f"\n{player.name} a construit 8 cartes ! Fin de partie.")
                return True
        
        # Fin si plus de cartes disponibles
        if self.pioche.cards_remaining() == 0:
            print("\nPlus de cartes disponibles ! Fin de partie.")
            return True
        
        # Fin après 50 tours (sécurité)
        if self.turn_counter >= 50:
            print("\nLimite de tours atteinte ! Fin de partie.")
            return True
        
        return False
    
    def _display_final_scores(self):
        """Affiche les scores finaux et détermine le gagnant"""
        print("\n" + "="*60)
        print("🏆 SCORES FINAUX 🏆")
        print("="*60)
        
        # Calculer les scores finaux
        for player in self.players:
            player.calc_score()
        
        # Trier par score décroissant
        sorted_players = sorted(self.players, key=lambda p: p.point, reverse=True)
        
        for i, player in enumerate(sorted_players, 1):
            trophy = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            player_type = "(IA)" if player.is_ai else ""
            print(f"{trophy} {i}. {player.name} {player_type}: {player.point} points")
            print(f"   Cartes construites: {len(player.city)} | Argent: {player.calc_money()}")
            print(f"   Ville: {', '.join(player.city)}")
            print()
        
        winner = sorted_players[0]
        print(f"🎉 Félicitations à {winner.name} qui remporte la partie ! 🎉")
    
    def _display_game_status(self):
        """Affiche l'état actuel du jeu"""
        print(f"\n{'='*50}")
        print(f"🎮 TOUR {self.turn_counter + 1} 🎮")
        print(f"Cartes restantes dans la pioche: {self.pioche.cards_remaining()}")
        print(f"{'='*50}")
        
        # Afficher un résumé de tous les joueurs
        for player in self.players:
            player_type = "(IA)" if player.is_ai else ""
            marker = "👉" if player == self.current_player() else "  "
            print(f"{marker} {player.name} {player_type}: {len(player.city)} cartes construites, {player.point} points")
        print()
    
    def run(self):
        """Lance le jeu principal"""
        print("🏛️  Bienvenue dans le jeu de construction de ville ! 🏛️")
        print()
        
        # Configuration des joueurs
        if not self._setup_players():
            return
        
        if not self.players:
            print("Aucun joueur configuré.")
            return
        
        # Distribution initiale
        print("\n🎴 Distribution des cartes initiales...")
        for player in self.players:
            player.piocher(5)
        
        print("🎲 Le jeu commence !")
        
        # Boucle de jeu principale
        try:
            while not self._check_end_conditions():
                current_player = self.current_player()
                
                self._display_game_status()
                
                if isinstance(current_player, AIPlayer):
                    # Tour de l'IA
                    self._handle_ai_turn(current_player)
                else:
                    # Tour du joueur humain
                    print(f"C'est le tour de {current_player.name}")
                    
                    # Pioche automatique basée sur l'argent
                    money = current_player.calc_money()
                    if money > 0:
                        current_player.piocher(money)
                        print(f"Tu pioches {money} carte(s) grâce à ton argent.")
                    
                    print(f"Ton état actuel : {current_player}")
                    
                    # Choix de l'action
                    while True:
                        choice = input("Que veux-tu faire ? (piocher/construire/info) : ").strip().lower()
                        
                        if choice == "info":
                            print("\n📊 Informations du jeu :")
                            for p in self.players:
                                p_type = "(IA)" if p.is_ai else ""
                                print(f"- {p.name} {p_type}: {len(p.city)} cartes, {p.point} points")
                            print()
                            continue
                        
                        elif choice == "piocher":
                            self._handle_human_pioche_action(current_player)
                            break
                        
                        elif choice == "construire":
                            buildable = current_player.get_buildable_cards()
                            if not buildable:
                                print("Tu n'as aucune carte constructible.")
                                continue
                            
                            print("Cartes constructibles :")
                            for card, cost in buildable:
                                print(f"- {card} (coût: {cost})")
                            
                            self._handle_human_build_action(current_player)
                            break
                        
                        else:
                            print("Choix invalide. Tapez 'piocher', 'construire' ou 'info'.")
                    
                    # Calculer le score
                    current_player.calc_score()
                    print(f"Ton état final : {current_player}")
                
                self.next_turn()
                
                # Pause pour les parties avec IA (optionnel)
                if any(isinstance(p, AIPlayer) for p in self.players) and not isinstance(current_player, AIPlayer):
                    input("\nAppuyez sur Entrée pour continuer...")
        
        except KeyboardInterrupt:
            print("\n\n⏸️  Jeu interrompu par l'utilisateur.")
            print("Calcul des scores actuels...")
        
        # Affichage des scores finaux
        self._display_final_scores()


class AITester:
    """Classe pour tester et comparer les IA"""
    
    @staticmethod
    def run_ai_battle(personalities: List[AIPersonality], nb_games: int = 10):
        """Lance plusieurs parties entre IAs pour tester leurs performances"""
        print(f"🤖 Bataille d'IA - {nb_games} parties")
        print("="*50)
        
        results = {personality: {"wins": 0, "points": 0, "games": 0} for personality in personalities}
        
        for game_num in range(nb_games):
            print(f"\nPartie {game_num + 1}/{nb_games}")
            
            game = Game()
            
            # Ajouter les IA
            for i, personality in enumerate(personalities):
                ai_name = f"IA-{personality.value.capitalize()}"
                game.add_ai_player(ai_name, personality, difficulty=1.0)
            
            # Distribution initiale
            for player in game.players:
                player.piocher(5)
            
            # Simuler la partie (version accélérée)
            max_turns = 30
            turn = 0
            
            while turn < max_turns and not game._check_end_conditions():
                current = game.current_player()
                
                if isinstance(current, AIPlayer):
                    game_state = game.create_game_state()
                    
                    # Pioche basée sur l'argent
                    money = current.calc_money()
                    if money > 0:
                        current.piocher(money)
                    
                    # Décision IA
                    decision = current.make_decision(game_state)
                    
                    if decision == "piocher":
                        current.ai_handle_pioche_action()
                    elif decision == "construire":
                        card_to_build = current.choose_card_to_build(game_state)
                        if card_to_build:
                            current.ai_build(card_to_build)
                            current.ai_check_carte()
                
                game.next_turn()
                if game.current_player_index == 0:
                    turn += 1
            
            # Calculer les scores
            for player in game.players:
                player.calc_score()
            
            # Enregistrer les résultats
            sorted_players = sorted(game.players, key=lambda p: p.point, reverse=True)
            winner = sorted_players[0]
            
            # Trouver la personnalité du gagnant
            if isinstance(winner, AIPlayer):
                results[winner.personality]["wins"] += 1
            
            # Enregistrer les points de tous
            for player in game.players:
                if isinstance(player, AIPlayer):
                    results[player.personality]["points"] += player.point
                    results[player.personality]["games"] += 1
        
        # Afficher les statistiques
        print(f"\n📊 Résultats après {nb_games} parties :")
        print("="*60)
        
        sorted_results = sorted(results.items(), key=lambda x: x[1]["wins"], reverse=True)
        
        for personality, stats in sorted_results:
            avg_points = stats["points"] / max(stats["games"], 1)
            win_rate = (stats["wins"] / nb_games) * 100
            
            print(f"{personality.value.capitalize():12} | "
                  f"Victoires: {stats['wins']:2d} ({win_rate:5.1f}%) | "
                  f"Points moy: {avg_points:5.1f}")


def main():
    """Fonction principale avec menu"""
    while True:
        print("\n🏛️  JEU DE CONSTRUCTION DE VILLE 🏛️")
        print("="*50)
        print("1. 🎮 Nouvelle partie")
        print("2. 🤖 Bataille d'IA")
        print("3. 📖 Aide sur les personnalités IA")
        print("4. 🚪 Quitter")
        print("="*50)
        
        choice = input("Votre choix : ").strip()
        
        if choice == "1":
            try:
                game = Game()
                game.run()
            except Exception as e:
                print(f"Erreur pendant le jeu : {e}")
        
        elif choice == "2":
            print("\nSélection des personnalités pour la bataille :")
            personalities = []
            
            for i, personality in enumerate(AIPersonality, 1):
                print(f"{i}. {personality.value}")
            
            selected = input("Entrez les numéros séparés par des espaces (ex: 1 2 3) : ").split()
            
            try:
                for num in selected:
                    idx = int(num) - 1
                    if 0 <= idx < len(list(AIPersonality)):
                        personalities.append(list(AIPersonality)[idx])
                
                if len(personalities) >= 2:
                    nb_games = int(input("Nombre de parties (défaut: 10) : ") or "10")
                    AITester.run_ai_battle(personalities, nb_games)
                else:
                    print("Il faut au moins 2 personnalités différentes.")
            
            except ValueError:
                print("Sélection invalide.")
        
        elif choice == "3":
            print("\n📖 GUIDE DES PERSONNALITÉS IA")
            print("="*50)
            print("🔥 AGGRESSIVE : Privilégie les points rapides et les cartes à forte valeur")
            print("💰 ECONOMIC : Se concentre sur l'argent et l'efficacité économique")
            print("⚖️  BALANCED : Stratégie équilibrée entre tous les aspects")
            print("🛡️  DEFENSIVE : Joue prudemment, évite les risques")
            print("🎯 OPPORTUNISTIC : S'adapte aux situations, saisit les opportunités")
            print("\n💡 Conseils :")
            print("- Difficulté 0.0 = IA imprévisible, fait parfois des erreurs")
            print("- Difficulté 1.0 = IA experte, joue optimalement")
            print("- Chaque personnalité a ses forces et faiblesses")
            
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == "4":
            print("👋 Au revoir et merci d'avoir joué !")
            break
        
        else:
            print("❌ Choix invalide, veuillez réessayer.")


if __name__ == "__main__":
    main()
                    self.pioche.defausse.append(card)
                
                break
                
            except ValueError:
                print("Entrée invalide.")
    
    def _handle_build_action(self, player: Player):
        """Gère l'action de construction"""
        while True:
            carte = input("Quelle carte voulez-vous construire ? ").strip()
            if not carte:
                continue
                
            if player.build(carte):
                player.check_carte()
                break
    
    def run(self):
        """Lance le jeu"""
        # Initialisation des joueurs
        try:
            nb_players = int(input("Combien de joueurs ? "))
            if nb_players <= 0:
                print("Le nombre de joueurs doit être positif.")
                return
        except ValueError:
            print("Nombre de joueurs invalide.")
            return
        
        for i in range(nb_players):
            name = input(f"Nom du joueur {i + 1} : ").strip()
            if not name:
                name = f"Joueur {i + 1}"
            
            player = Player(name)
            self.add_player(player)
            player.piocher(5)  # Distribution initiale
        
        # Boucle de jeu
        turn_counter = 0
        MAX_TURNS = 1000  # Sécurité contre les boucles infinies
        
        while turn_counter < MAX_TURNS:
            current_player = self.current_player()
            print(f"\n{'='*50}")
            print(f"Tour {turn_counter + 1} - C'est le tour de {current_player.name}")
            print(f"{'='*50}")
            
            # Pioche automatique basée sur l'argent
            money = current_player.calc_money()
            if money > 0:
                current_player.piocher(money)
                print(f"{current_player.name} pioche {money} carte(s) grâce à son argent.")
            
            print(current_player)
            
            # Choix de l'action
            while True:
                choice = input("Que voulez-vous faire ? (piocher/construire) : ").strip().lower()
                
                if choice == "piocher":
                    self._handle_pioche_action(current_player)
                    break
                elif choice == "construire":
                    self._handle_build_action(current_player)
                    break
                else:
                    print("Choix invalide. Tapez 'piocher' ou 'construire'.")
            
            current_player.calc_score()
            print(f"État final : {current_player}")
            
            self.next_turn()
            turn_counter += 1
        
        if turn_counter >= MAX_TURNS:
            print("Limite de tours atteinte. Fin du jeu.")


if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except KeyboardInterrupt:
        print("\nJeu interrompu par l'utilisateur.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
