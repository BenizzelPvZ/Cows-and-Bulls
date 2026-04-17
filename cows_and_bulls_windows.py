import random
import time
import threading
import sys
import socket
import json
import msvcrt

class NetworkManager:
    def __init__(self, is_server=False, host='0.0.0.0', port=12345):
        self.is_server = is_server
        self.host = host
        self.port = port
        self.socket = None
        self.connection = None
        self.connected = False
    
    def start_server(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"\nWarte auf Verbindung auf {self.host}:{self.port}...")
        self.connection, client_address = self.socket.accept()
        print(f"Verbindung von {client_address} hergestellt!")
        self.connected = True
        return self.connection
    
    def connect_to_server(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.connection = self.socket
        self.connected = True
        print(f"\nVerbunden mit {host}:{port}")
        return self.connection
    
    def send(self, data):
        if self.connection:
            self.connection.sendall(json.dumps(data).encode('utf-8'))
    
    def receive(self):
        if self.connection:
            data = self.connection.recv(1024).decode('utf-8')
            return json.loads(data)
        return None
    
    def close(self):
        if self.connection:
            self.connection.close()
        if self.socket:
            self.socket.close()
        self.connected = False

class CowsAndBullsGame:
    def __init__(self):
        self.time_limit = None
        self.num_digits = None
        self.base = None
        self.allow_duplicates = False
        self.players = [
            {"name": "Spieler1", "time_left": 0, "hidden": False, "target_number": None},
            {"name": "Spieler2", "time_left": 0, "hidden": False, "target_number": None}
        ]
        self.current_player = 0
        self.attempts = [0, 0]
        self.game_active = False
        self.timer_thread = None
        self._stop_timer_flag = False
        self.network_manager = None
        self.is_network_game = False
        self.is_server = False
    
    def get_key(self):
        if msvcrt.kbhit():
            key = msvcrt.getch()
            # Pfeiltasten senden zwei Bytes: 0xE0 oder 0x00 gefolgt von einem weiteren Byte
            if key in (b'\x00', b'\xe0'):
                # Lese das nächste Byte, um die Richtung zu bestimmen
                next_key = msvcrt.getch()
                if next_key == b'H':
                    return '\x00H'  # Pfeil nach oben
                elif next_key == b'P':
                    return '\x00P'  # Pfeil nach unten
            # Versuche, das Byte als UTF-8 zu decodieren
            try:
                return key.decode('utf-8')
            except UnicodeDecodeError:
                # Falls UTF-8 fehlschlägt, versuche latin-1
                try:
                    return key.decode('latin-1')
                except:
                    # Falls alles andere fehlschlägt, gib das Byte als Hex-String zurück
                    return f"\x{key.hex()}"
        return ''
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def menu_selection(self, options, prompt):
        selected = 0
        print(f"\n{prompt}")
        for i, option in enumerate(options):
            if i == selected:
                print(f"> {option}")
            else:
                print(f"  {option}")
        
        while True:
            key = self.get_key()
            if key == '\x00H':  # Pfeil nach oben
                selected = (selected - 1) % len(options)
                # Clear the current selection lines
                for i in range(len(options)):
                    print("\033[F\033[K", end="")
                
                # Print the options with the current selection
                for i, option in enumerate(options):
                    if i == selected:
                        print(f"> {option}")
                    else:
                        print(f"  {option}")
            elif key == '\x00P':  # Pfeil nach unten
                selected = (selected + 1) % len(options)
                # Clear the current selection lines
                for i in range(len(options)):
                    print("\033[F\033[K", end="")
                
                # Print the options with the current selection
                for i, option in enumerate(options):
                    if i == selected:
                        print(f"> {option}")
                    else:
                        print(f"  {option}")
            elif key in ['\r', ' ']:  # Enter oder Leertaste
                return selected
    
    def setup_game(self):
        print("Willkommen zu Cows and Bulls!")
        
        # Spielmodus auswählen
        game_mode_options = ["Lokales Spiel", "Netzwerkspiel"]
        game_mode_choice = self.menu_selection(game_mode_options, "Spielmodus auswählen:")
        
        if game_mode_choice == 1:  # Netzwerkspiel
            self.is_network_game = True
            network_options = ["Spiel erstellen", "Spiel beitreten"]
            network_choice = self.menu_selection(network_options, "Netzwerkspiel:")
            
            if network_choice == 0:  # Spiel erstellen (Server)
                self.is_server = True
                self.network_manager = NetworkManager(is_server=True)
                print(f"\nVerbindungsinformationen:")
                print(f"IP-Adresse: {self.get_local_ip()}")
                print(f"Port: {self.network_manager.port}")
                print("\nWarte auf zweiten Spieler...")
                self.network_manager.start_server()
                
                # Setup-Daten an Client senden
                self.setup_network_game(is_server=True)
            else:  # Spiel beitreten (Client)
                self.is_server = False
                host = input("IP-Adresse des Servers: ")
                port = int(input("Port des Servers: "))
                self.network_manager = NetworkManager(is_server=False)
                self.network_manager.connect_to_server(host, port)
                
                # Setup-Daten vom Server empfangen
                self.setup_network_game(is_server=False)
        else:  # Lokales Spiel
            self.is_network_game = False
            # Zeitlimit festlegen
            time_options = [3600, 2700, 1800, 900, 600, 300]
            time_option_labels = [f"{t//60} Minuten" for t in time_options]
            choice = self.menu_selection(time_option_labels, "Zeitlimit festlegen:")
            self.time_limit = time_options[choice]
            
            # Anzahl der Stellen festlegen
            digit_options = list(range(3, 11))
            digit_option_labels = [str(d) for d in digit_options]
            self.num_digits = digit_options[self.menu_selection(digit_option_labels, "Anzahl der Stellen festlegen (3-10):")]
            
            # Zahlenformat auswählen
            base_options = ["Binär", "Oktal", "Dezimal", "Hexadezimal"]
            base_choice = self.menu_selection(base_options, "Zahlenformat auswählen:")
            self.base = [2, 8, 10, 16][base_choice]
            
            # Doppelte Zahlen erlauben oder nicht
            duplicate_options = ["Doppelte Zahlen erlauben", "Doppelte Zahlen verbieten"]
            if self.base == 2:
                print("\nDoppelte Zahlen sind bei Binärzahlen automatisch erlaubt.")
                self.allow_duplicates = True
            elif self.base == 8 and self.num_digits > 8:
                print("\nDoppelte Zahlen sind bei Oktalzahlen mit mehr als 8 Stellen automatisch erlaubt.")
                self.allow_duplicates = True
            else:
                duplicate_choice = self.menu_selection(duplicate_options, "Doppelte Zahlen:")
                self.allow_duplicates = (duplicate_choice == 0)
            
            # Spieler wählen ihre Zahlen
            print("\n" * 50)
            for i, player in enumerate(self.players):
                while True:
                    try:
                        player_number = input(f"{player['name']}, gib deine {self.num_digits}-stellige Zahl ein (Base {self.base}): ")
                        if not self.validate_input(player_number):
                            continue
                        player_number_int = int(player_number, self.base)
                        player["target_number"] = player_number_int
                        break
                    except ValueError:
                        print(f"Ungültige Eingabe. Bitte gib eine gültige Zahl im Base {self.base} ein.")
                print("\n" * 50)
            
            # Spielerzeit initialisieren
            for player in self.players:
                player["time_left"] = self.time_limit
            
            self.game_active = True
            self.start_game()
    
    def setup_network_game(self, is_server):
        if is_server:
            # Server wählt Setup
            time_options = [3600, 2700, 1800, 900, 600, 300]
            time_option_labels = [f"{t//60} Minuten" for t in time_options]
            choice = self.menu_selection(time_option_labels, "Zeitlimit festlegen:")
            self.time_limit = time_options[choice]
            
            digit_options = list(range(3, 11))
            digit_option_labels = [str(d) for d in digit_options]
            self.num_digits = digit_options[self.menu_selection(digit_option_labels, "Anzahl der Stellen festlegen (3-10):")]
            
            base_options = ["Binär", "Oktal", "Dezimal", "Hexadezimal"]
            base_choice = self.menu_selection(base_options, "Zahlenformat auswählen:")
            self.base = [2, 8, 10, 16][base_choice]
            
            duplicate_options = ["Doppelte Zahlen erlauben", "Doppelte Zahlen verbieten"]
            if self.base == 2:
                self.allow_duplicates = True
            elif self.base == 8 and self.num_digits > 8:
                self.allow_duplicates = True
            else:
                duplicate_choice = self.menu_selection(duplicate_options, "Doppelte Zahlen:")
                self.allow_duplicates = (duplicate_choice == 0)
            
            # Setup-Daten an Client senden
            setup_data = {
                "time_limit": self.time_limit,
                "num_digits": self.num_digits,
                "base": self.base,
                "allow_duplicates": self.allow_duplicates
            }
            self.network_manager.send(setup_data)
        else:
            # Client empfängt Setup-Daten
            setup_data = self.network_manager.receive()
            self.time_limit = setup_data["time_limit"]
            self.num_digits = setup_data["num_digits"]
            self.base = setup_data["base"]
            self.allow_duplicates = setup_data["allow_duplicates"]
            print("\nSetup-Daten vom Server empfangen:")
            print(f"Zeitlimit: {self.time_limit//60} Minuten")
            print(f"Anzahl der Stellen: {self.num_digits}")
            base_names = ["Binär", "Oktal", "Dezimal", "Hexadezimal"]
            base_index = 0
            if self.base == 2:
                base_index = 0
            elif self.base == 8:
                base_index = 1
            elif self.base == 10:
                base_index = 2
            else:
                base_index = 3
            print(f"Zahlenformat: {base_names[base_index]}")
            print(f"Doppelte Zahlen: {'Erlaubt' if self.allow_duplicates else 'Verboten'}")
        
        # Bei Netzwerkspiel: Zahlen austauschen
        if self.is_network_game:
            if self.is_server:
                # Server wählt seine Zahl
                while True:
                    try:
                        player_number = input(f"{self.players[0]['name']}, gib deine {self.num_digits}-stellige Zahl ein (Base {self.base}): ")
                        if not self.validate_input(player_number):
                            continue
                        player_number_int = int(player_number, self.base)
                        self.players[0]["target_number"] = player_number_int
                        break
                    except ValueError:
                        print(f"Ungültige Eingabe. Bitte gib eine gültige Zahl im Base {self.base} ein.")
                print("\n" * 50)
                
                # Warte auf die Zahl des Clients
                print("Warte auf die Zahl des Gegners...")
                data = self.network_manager.receive()
                if data["type"] == "target_number":
                    self.players[1]["target_number"] = data["number"]
                    print("Zahl des Gegners empfangen.")
            else:
                # Client wählt seine Zahl
                while True:
                    try:
                        player_number = input(f"{self.players[1]['name']}, gib deine {self.num_digits}-stellige Zahl ein (Base {self.base}): ")
                        if not self.validate_input(player_number):
                            continue
                        player_number_int = int(player_number, self.base)
                        self.players[1]["target_number"] = player_number_int
                        break
                    except ValueError:
                        print(f"Ungültige Eingabe. Bitte gib eine gültige Zahl im Base {self.base} ein.")
                print("\n" * 50)
                
                # Sende die Zahl an den Server
                self.network_manager.send({"type": "target_number", "number": self.players[1]["target_number"]})
                print("Zahl an den Server gesendet.")
        else:
            # Lokales Spiel: Beide Spieler wählen ihre Zahlen
            print("\n" * 50)
            for i, player in enumerate(self.players):
                while True:
                    try:
                        player_number = input(f"{player['name']}, gib deine {self.num_digits}-stellige Zahl ein (Base {self.base}): ")
                        if not self.validate_input(player_number):
                            continue
                        player_number_int = int(player_number, self.base)
                        player["target_number"] = player_number_int
                        break
                    except ValueError:
                        print(f"Ungültige Eingabe. Bitte gib eine gültige Zahl im Base {self.base} ein.")
                print("\n" * 50)
        
        # Spielerzeit initialisieren
        for player in self.players:
            player["time_left"] = self.time_limit
        
        self.game_active = True
        self.start_game()
    
    def start_game(self):
        print("\nSpiel beginnt!")
        self.current_player = 0
        self.start_timer()
        self.play_turn()
    
    def start_timer(self):
        self._stop_timer_flag = False
        self.timer_thread = threading.Thread(target=self.update_timer)
        self.timer_thread.start()
    
    def update_timer(self):
        while not self._stop_timer_flag and self.players[self.current_player]["time_left"] > 0:
            time.sleep(1)
            self.players[self.current_player]["time_left"] -= 1
            if not self.players[self.current_player]["hidden"]:
                time_display = self.format_time(self.players[self.current_player]["time_left"])
                player = self.players[self.current_player]
                print(f"\r[{time_display}] {player['name']} ({self.attempts[self.current_player]}) ", end="", flush=True)
            if self.players[self.current_player]["time_left"] <= 0:
                print(f"\n{self.players[self.current_player]['name']}, deine Zeit ist abgelaufen!")
                self.game_active = False
                break
    
    def stop_timer(self):
        self._stop_timer_flag = True
        if self.timer_thread:
            self.timer_thread.join()
    
    def play_turn(self):
        while self.game_active:
            player = self.players[self.current_player]
            opponent = self.players[1 - self.current_player]
            
            # Bei Netzwerkspiel: Warten, bis der Spieler dran ist
            if self.is_network_game:
                if self.is_server and self.current_player != 0:
                    print("\nWarte auf den Zug des Gegners...")
                    data = self.network_manager.receive()
                    if data["type"] == "guess":
                        guess = data["guess"]
                        cows, bulls = self.calculate_cows_and_bulls(guess, self.players[0]["target_number"])
                        self.network_manager.send({"type": "result", "cows": cows, "bulls": bulls})
                        print(f"\nGegner hat {format(guess, f'0{self.num_digits}')} geraten -> {cows} Cow(s) {bulls} Bull(s)")
                        if bulls == self.num_digits:
                            print(f"\n{self.players[1]['name']} hat gewonnen!")
                            self.game_active = False
                            self.stop_timer()
                            break
                        self.current_player = 0
                    elif data["type"] == "exit":
                        print("\nGegner hat das Spiel verlassen.")
                        self.game_active = False
                        self.stop_timer()
                        break
                elif not self.is_server and self.current_player != 1:
                    print("\nWarte auf deinen Zug...")
                    while self.current_player != 1 and self.game_active:
                        time.sleep(1)
                    if not self.game_active:
                        break
                    player = self.players[1]
                    opponent = self.players[0]
            
            self.attempts[self.current_player] += 1
            
            # Anzeige
            time_display = "***" if player["hidden"] else self.format_time(player["time_left"])
            print(f"\n[{time_display}] {player['name']} ({self.attempts[self.current_player]}) ", end="", flush=True)
            
            # Eingabe
            user_input = input("").strip()
            
            # Kommandos
            if user_input.lower() == "exit":
                print("\nSpiel wird beendet.")
                self.game_active = False
                self.stop_timer()
                if self.is_network_game:
                    self.network_manager.send({"type": "exit"})
                sys.exit(0)
            elif user_input.lower() == "hide":
                player["hidden"] = True
                print(f"\r[{time_display}] {player['name']} ({self.attempts[self.current_player]}) Zeit versteckt.")
                continue
            elif user_input.lower() == "show":
                player["hidden"] = False
                time_display = self.format_time(player["time_left"])
                print(f"\r[{time_display}] {player['name']} ({self.attempts[self.current_player]}) Zeit angezeigt.")
                continue
            
            # Zahl prüfen
            if not self.validate_input(user_input):
                print(f"\r[{time_display}] {player['name']} ({self.attempts[self.current_player]}) ", end="", flush=True)
                continue
            
            guess = int(user_input, self.base)
            
            # Bei Netzwerkspiel: Sende die geratene Zahl an den Gegner
            if self.is_network_game:
                self.network_manager.send({"type": "guess", "guess": guess})
                # Empfange das Ergebnis
                result = self.network_manager.receive()
                if result["type"] == "result":
                    cows, bulls = result["cows"], result["bulls"]
                elif result["type"] == "win":
                    print(f"\n{result['winner']} hat gewonnen!")
                    self.game_active = False
                    self.stop_timer()
                    break
                elif result["type"] == "exit":
                    print("\nGegner hat das Spiel verlassen.")
                    self.game_active = False
                    self.stop_timer()
                    break
            else:
                # Cows und Bulls berechnen
                cows, bulls = self.calculate_cows_and_bulls(guess, opponent["target_number"])
            
            # Ergebnis anzeigen
            print(f"{user_input} -> {cows} Cow(s) {bulls} Bull(s)")
            
            # Gewinner prüfen
            if bulls == self.num_digits:
                print(f"\n{player['name']} hat gewonnen!")
                self.game_active = False
                self.stop_timer()
                if self.is_network_game:
                    self.network_manager.send({"type": "win", "winner": player["name"]})
                break
            
            # Spieler wechseln
            self.stop_timer()
            if self.is_network_game:
                if self.is_server:
                    self.current_player = 1
                else:
                    self.current_player = 0
            else:
                self.current_player = 1 - self.current_player
            self.start_timer()
    
    def validate_input(self, user_input):
        # Überprüfe die Länge
        if len(user_input) != self.num_digits:
            print(f"Die Zahl muss genau {self.num_digits} Stellen haben.")
            return False
        
        # Überprüfe die Zeichen für das gewählte Zahlenformat
        valid_chars = {
            2: set('01'),
            8: set('01234567'),
            10: set('0123456789'),
            16: set('0123456789abcdefABCDEF')
        }
        
        for char in user_input:
            if char not in valid_chars[self.base]:
                if self.base == 2:
                    print("Ungültige Zeichen. Binärzahlen dürfen nur 0 und 1 enthalten.")
                elif self.base == 8:
                    print("Ungültige Zeichen. Oktalzahlen dürfen nur 0-7 enthalten.")
                elif self.base == 10:
                    print("Ungültige Zeichen. Dezimalzahlen dürfen nur 0-9 enthalten.")
                elif self.base == 16:
                    print("Ungültige Zeichen. Hexadezimalzahlen dürfen nur 0-9 und A-F enthalten.")
                return False
        
        # Überprüfe auf doppelte Zeichen, wenn nicht erlaubt
        if not self.allow_duplicates and len(set(user_input)) != self.num_digits:
            print("Die Zahl darf keine doppelten Zeichen enthalten.")
            return False
        
        return True
    
    def calculate_cows_and_bulls(self, guess, target_number):
        target_str = format(target_number, f'0{self.num_digits}')
        guess_str = format(guess, f'0{self.num_digits}')
        
        cows = 0
        bulls = 0
        
        # Zuerst Bullen zählen
        for i in range(self.num_digits):
            if guess_str[i] == target_str[i]:
                bulls += 1
        
        # Dann Kühe zählen (ohne Bullen)
        for i in range(self.num_digits):
            if guess_str[i] != target_str[i] and guess_str[i] in target_str:
                # Zähle nur, wenn die Ziffer in target_str vorkommt, aber nicht bereits als Bulle gezählt wurde
                # Um sicherzustellen, dass wir nicht mehr Kühe zählen als tatsächlich vorhanden sind
                count_in_target = target_str.count(guess_str[i])
                count_in_guess_bulls = sum(1 for j in range(self.num_digits) if guess_str[j] == guess_str[i] and guess_str[j] == target_str[j])
                count_in_guess_cows = sum(1 for j in range(i) if guess_str[j] == guess_str[i] and guess_str[j] != target_str[j] and guess_str[j] in target_str)
                
                if count_in_guess_bulls + count_in_guess_cows < count_in_target:
                    cows += 1
        
        return cows, bulls
    
    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        return f"{mins:02d}:{secs:02d}"

if __name__ == "__main__":
    game = CowsAndBullsGame()
    game.setup_game()