# tictactoe.py
import time
import random
from config import USER_ID, TTL_DEFAULT
from parser import build_message
from network import send_broadcast
from logger import log, print_non_verbose
from storage import storage_lock

# Game storage
games = {}  # {game_id: GameState}
game_lock = storage_lock

class GameState:
    def __init__(self, game_id, player1, player2, first_player):
        self.game_id = game_id
        self.player1 = player1  # X player
        self.player2 = player2  # O player
        self.board = [' '] * 9  # 0-8 positions
        self.current_turn = first_player
        self.turn_number = 1
        self.game_over = False
        self.result = None
        self.winning_line = None
        self.accepted = False  # Track if game has been accepted by invitee
        
    def make_move(self, player, position, symbol):
        """Make a move and return if successful"""
        if self.game_over:
            return False
        if self.board[position] != ' ':
            return False
        if player != self.current_turn:
            return False
        if (player == self.player1 and symbol != 'X') or (player == self.player2 and symbol != 'O'):
            return False
            
        self.board[position] = symbol
        self.turn_number += 1
        
        # Check for win/draw
        winner = self.check_winner()
        if winner:
            self.game_over = True
            
            if winner == self.player1:
                self.result = "PLAYER1_WIN"
            else:
                self.result = "PLAYER2_WIN"
            return True
        elif self.is_draw():
            self.game_over = True
            self.result = "DRAW"
            return True
            
        # Switch turns
        self.current_turn = self.player2 if self.current_turn == self.player1 else self.player1
        return True
    
    def check_winner(self):
        """Check for winner and set winning_line"""
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
            [0, 4, 8], [2, 4, 6]              # diagonals
        ]
        
        for combo in winning_combinations:
            if (self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != ' '):
                self.winning_line = combo
                # Return the player who has this symbol
                symbol = self.board[combo[0]]
                return self.player1 if symbol == 'X' else self.player2
        return None
    
    def is_draw(self):
        """Check if board is full (draw)"""
        return ' ' not in self.board
    
    def print_board(self):
        """Print the current board state"""
        board_str = ""
        for i in range(0, 9, 3):
            row = " | ".join(self.board[i:i+3])
            board_str += row + "\n"
            if i < 6:
                board_str += "---------\n"
        
        print_non_verbose(board_str.rstrip())
        
        if not self.game_over:
            current_player_name = get_display_name(self.current_turn)
            symbol = 'X' if self.current_turn == self.player1 else 'O'
            print_non_verbose(f"{current_player_name}'s turn ({symbol})")

def get_display_name(user_id):
    """Get display name from peers storage"""
    from storage import peers
    return peers.get(user_id, {}).get("display_name", user_id)

def print_game_result(game):
    """Print the final game result message"""
    winner = game.check_winner()
    
    if game.result == "PLAYER1_WIN" or game.result == "PLAYER2_WIN":
        if winner == USER_ID:
            print_non_verbose("You won!")
        else:
            winner_name = get_display_name(winner)
            print_non_verbose(f"{winner_name} wins!")
    elif game.result == "DRAW":
        print_non_verbose("It's a draw!")
    elif game.result == "FORFEIT":
        print_non_verbose("Game forfeited!")

def send_tictactoe_invite(target_user: str):
    """Send a TicTacToe game invitation"""
    try:
        # Generate game ID (g + number 0-255)
        game_id = f"g{random.randint(0, 255)}"
        
        # Create game state - INVITEE goes first (to accept by playing)
        with game_lock:
            games[game_id] = GameState(game_id, USER_ID, target_user, target_user)
        
        timestamp = int(time.time())
        message_id = hex(random.getrandbits(64))[2:]
        token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|game"
        
        invite_msg = build_message({
            "TYPE": "TICTACTOE_INVITE",
            "FROM": USER_ID,
            "TO": target_user,
            "GAMEID": game_id,
            "MESSAGE_ID": message_id,
            "SYMBOL": "X",
            "TIMESTAMP": timestamp,
            "TOKEN": token
        })
        
        send_broadcast(invite_msg)
        log(f"TicTacToe invite sent to {target_user} for game {game_id}")
        
    except Exception as e:
        log(f"Error sending TicTacToe invite: {e}")

def send_tictactoe_move(game_id: str, position: int):
    """Send a TicTacToe move"""
    try:
        with game_lock:
            if game_id not in games:
                print_non_verbose("Game not found")
                return
            
            game = games[game_id]
            if game.game_over:
                print_non_verbose("Game is already over")
                return
            
            if game.current_turn != USER_ID:
                print_non_verbose("It's not your turn")
                return
            
            if position < 0 or position > 8:
                print_non_verbose("Invalid position (0-8)")
                return
            
            if game.board[position] != ' ':
                print_non_verbose("Position already taken")
                return
            
            # Determine our symbol and opponent
            our_symbol = 'O' if USER_ID == game.player2 else 'X'
            opponent = game.player2 if USER_ID == game.player1 else game.player1
            
            # Make the move
            if not game.make_move(USER_ID, position, our_symbol):
                print_non_verbose("Invalid move")
                return
            
            # Mark game as accepted if this is invitee's first move
            if not game.accepted and USER_ID == game.player2:
                game.accepted = True
            
            # Print board after our move
            game.print_board()
            
            # Check if game ended and print result
            if game.game_over:
                print_game_result(game)
                # Clean up the game
                del games[game_id]
        
        timestamp = int(time.time())
        message_id = hex(random.getrandbits(64))[2:]
        token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|game"
        
        move_msg = build_message({
            "TYPE": "TICTACTOE_MOVE",
            "FROM": USER_ID,
            "TO": opponent,
            "GAMEID": game_id,
            "MESSAGE_ID": message_id,
            "POSITION": position,
            "SYMBOL": our_symbol,
            "TURN": game.turn_number - 1, 
            "TOKEN": token
        })
        
        send_broadcast(move_msg)
        
        
        if game.game_over:
            send_tictactoe_result(game_id, opponent)
            
        log(f"TicTacToe move sent for game {game_id}: position {position}")
        
    except Exception as e:
        log(f"Error sending TicTacToe move: {e}")

def send_tictactoe_result(game_id: str, opponent: str):
    """Send game result message"""
    try:
        with game_lock:
            if game_id not in games:
                return
            game = games[game_id]
        
        timestamp = int(time.time())
        message_id = hex(random.getrandbits(64))[2:]
        
        our_symbol = 'X' if USER_ID == game.player1 else 'O'
        
        result_msg = build_message({
            "TYPE": "TICTACTOE_RESULT",
            "FROM": USER_ID,
            "TO": opponent,
            "GAMEID": game_id,
            "MESSAGE_ID": message_id,
            "RESULT": game.result,
            "SYMBOL": our_symbol,
            "WINNING_LINE": ",".join(map(str, game.winning_line)) if game.winning_line else "",
            "TIMESTAMP": timestamp
        })
        
        send_broadcast(result_msg)
        log(f"TicTacToe result sent for game {game_id}: {game.result}")
        
    except Exception as e:
        log(f"Error sending TicTacToe result: {e}")

def handle_tictactoe_invite(msg, sender_id):
    """Handle incoming TicTacToe invitation"""
    try:
        game_id = msg.get("GAMEID")
        
        
        with game_lock:
            games[game_id] = GameState(game_id, sender_id, USER_ID, USER_ID)
        
        sender_name = get_display_name(sender_id)
        print_non_verbose(f"{sender_name} is inviting you to play tic-tac-toe.")
        
        log(f"TicTacToe invite received from {sender_id} for game {game_id}")
        
    except Exception as e:
        log(f"Error handling TicTacToe invite: {e}")

def handle_tictactoe_move(msg, sender_id):
    """Handle incoming TicTacToe move"""
    try:
        game_id = msg.get("GAMEID")
        position = int(msg.get("POSITION"))
        symbol = msg.get("SYMBOL")
        turn = int(msg.get("TURN", 0))
        
        with game_lock:
            if game_id not in games:
                log(f"Unknown game: {game_id}")
                return
            
            game = games[game_id]
            
            # Make the move
            if game.make_move(sender_id, position, symbol):
                
                game.print_board()
                
                # Check if game ended and print result
                if game.game_over:
                    print_game_result(game)
                    # Clean up game
                    del games[game_id]
            else:
                log(f"Invalid move in game {game_id}")
        
        log(f"TicTacToe move received for game {game_id}: position {position}")
        
    except Exception as e:
        log(f"Error handling TicTacToe move: {e}")

def handle_tictactoe_result(msg, sender_id):
    """Handle incoming TicTacToe result"""
    try:
        game_id = msg.get("GAMEID")
        result = msg.get("RESULT")
        winning_line = msg.get("WINNING_LINE", "")
        
        with game_lock:
            if game_id in games:
                game = games[game_id]
                # Print final board state
                game.print_board()
                print_game_result(game)
                # Clean up game
                del games[game_id]
        
        log(f"TicTacToe result received for game {game_id}: {result}")
        
    except Exception as e:
        log(f"Error handling TicTacToe result: {e}")

def list_active_games():
    """List all active games"""
    with game_lock:
        if not games:
            print_non_verbose("No active games")
            return
        
        print_non_verbose("Active TicTacToe games:")
        for game_id, game in games.items():
            player1_name = get_display_name(game.player1)
            player2_name = get_display_name(game.player2)
            current_name = get_display_name(game.current_turn)
            print_non_verbose(f"  {game_id}: {player1_name} (X) vs {player2_name} (O) - {current_name}'s turn")