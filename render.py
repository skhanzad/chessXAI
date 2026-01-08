import pygame as pg
import chess
import sys

class Render:
    def __init__(self, width: int, height: int):
        pg.init()
        self.width = width
        self.height = height
        self.screen = pg.display.set_mode((width, height))
        
        # Try to find a font that supports chess symbols
        # Windows fonts that support chess symbols: Segoe UI Symbol, Arial Unicode MS
        # Linux fonts: DejaVu Sans, Liberation Sans, Noto Sans Symbols
        self.piece_font_name = None
        font_names = ['Segoe UI Symbol', 'Arial Unicode MS', 'DejaVu Sans', 
                     'Liberation Sans', 'Noto Sans Symbols', 'Symbola', 'FreeSerif']
        
        for font_name in font_names:
            try:
                test_font = pg.font.SysFont(font_name, 24, bold=True)
                # Test if font can render chess symbols by checking if it produces visible output
                test_text = test_font.render('♔', True, (0, 0, 0), (255, 255, 255))
                # Check if we got a reasonable size (not just a fallback rectangle)
                if test_text.get_width() > 10 and test_text.get_height() > 10:
                    self.piece_font_name = font_name
                    break
            except Exception as e:
                continue
        
        # If no suitable font found, use None (will fall back to letters)
        if self.piece_font_name is None:
            self.piece_font_name = None  # Will use default font with letter fallback

    def render(self, board: chess.Board, reason: str = None, move = None, goal: str = None):
        # handle events
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return False
        
        # Convert move to string if it's a chess.Move object
        if move is not None:
            if isinstance(move, chess.Move):
                move = move.uci()
            elif not isinstance(move, str):
                move = str(move)
        
        # Ensure reason and goal are strings
        if reason is not None and not isinstance(reason, str):
            reason = str(reason)
        if goal is not None and not isinstance(goal, str):
            goal = str(goal)
        
        # fill the screen with white
        self.screen.fill((255, 255, 255))
        
        # Calculate square size and board dimensions
        square_size = min(self.width, self.height) // 8
        board_width = square_size * 8
        board_height = square_size * 8
        
        # Calculate text area on the right
        text_area_x = board_width + 20
        text_area_width = self.width - text_area_x - 20
        
        # Board colors (light and dark squares)
        colors = [(240, 217, 181), (181, 136, 99)]  # light, dark
        
        # Unicode pieces dictionary
        piece_unicode = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }
        
        # Font for rendering pieces - use bold for better visibility
        font_size = int(square_size * 0.7)
        if self.piece_font_name:
            piece_font = pg.font.SysFont(self.piece_font_name, font_size, bold=True)
        else:
            piece_font = pg.font.SysFont(None, font_size, bold=True)
        
        # Letter fallback map
        letter_map = {
            'P': 'P', 'N': 'N', 'B': 'B', 'R': 'R', 'Q': 'Q', 'K': 'K',
            'p': 'p', 'n': 'n', 'b': 'b', 'r': 'r', 'q': 'q', 'k': 'k'
        }
        
        # Draw the board and pieces
        for i in range(8):
            for j in range(8):
                # Calculate rectangle for this square
                rect = pg.Rect(j * square_size, i * square_size, square_size, square_size)
                
                # Draw square background
                color = colors[(i + j) % 2]
                pg.draw.rect(self.screen, color, rect)
                
                # Get the chess square (file j, rank 7-i to flip board)
                square = chess.square(j, 7 - i)  # chess.square(file, rank)
                
                # Get piece at this square
                piece = board.piece_at(square)
                
                # Draw piece if present
                if piece:
                    # Try Unicode symbol first if we have a good font
                    if self.piece_font_name:
                        piece_symbol = piece_unicode.get(piece.symbol(), '?')
                        text = piece_font.render(piece_symbol, True, (0, 0, 0))
                        
                        # Check if Unicode rendered properly (width should be reasonable)
                        # If it's too narrow, it's probably a fallback rectangle
                        if text.get_width() < font_size * 0.3:
                            # Fallback to letter
                            fallback_symbol = letter_map.get(piece.symbol(), '?')
                            text = piece_font.render(fallback_symbol, True, (0, 0, 0))
                    else:
                        # No Unicode font, use letters directly
                        fallback_symbol = letter_map.get(piece.symbol(), '?')
                        text = piece_font.render(fallback_symbol, True, (0, 0, 0))
                    
                    text_rect = text.get_rect(center=(rect.centerx, rect.centery))
                    self.screen.blit(text, text_rect)
        
        # Render text information on the right side
        if text_area_width > 100:  # Only render if there's enough space
            self._render_text_info(text_area_x, text_area_width, reason, move, goal)
        
        pg.display.flip()
        return True
    
    def _render_text_info(self, x: int, width: int, reason: str = None, move: str = None, goal: str = None):
        """Render reason, move, and goal text on the right side of the board"""
        # Font for text rendering
        text_font = pg.font.SysFont('Arial', 16)
        title_font = pg.font.SysFont('Arial', 18, bold=True)
        
        y_offset = 20
        line_height = 25
        section_spacing = 30
        
        # Render Goal
        if goal:
            goal_title = title_font.render("Goal:", True, (0, 0, 0))
            self.screen.blit(goal_title, (x, y_offset))
            y_offset += line_height + 5
            
            goal_lines = self._wrap_text(goal, text_font, width)
            for line in goal_lines:
                goal_text = text_font.render(line, True, (50, 50, 50))
                self.screen.blit(goal_text, (x, y_offset))
                y_offset += line_height
            y_offset += section_spacing
        
        # Render Move
        if move:
            move_title = title_font.render("Last Move:", True, (0, 0, 0))
            self.screen.blit(move_title, (x, y_offset))
            y_offset += line_height + 5
            
            move_text = text_font.render(move, True, (0, 100, 200))
            self.screen.blit(move_text, (x, y_offset))
            y_offset += line_height + section_spacing
        
        # Render Reason
        if reason:
            reason_title = title_font.render("Reason:", True, (0, 0, 0))
            self.screen.blit(reason_title, (x, y_offset))
            y_offset += line_height + 5
            
            reason_lines = self._wrap_text(reason, text_font, width)
            for line in reason_lines:
                reason_text = text_font.render(line, True, (80, 80, 80))
                self.screen.blit(reason_text, (x, y_offset))
                y_offset += line_height
    
    def _wrap_text(self, text: str, font, max_width: int) -> list:
        """Wrap text to fit within max_width"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            # Test if adding this word would exceed width
            test_line = ' '.join(current_line + [word])
            test_surface = font.render(test_line, True, (0, 0, 0))
            
            if test_surface.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]


if __name__ == "__main__":
    board = chess.Board()

    # Make window wider to accommodate text on the right
    render = Render(1000, 600)
    
    # Example usage with text
    test_reason = "Opening up the center of the board and gaining control of key squares."
    test_move = "e2e4"
    test_goal = "Win the game of chess by making the best moves."
    
    while True:
        if not render.render(board, reason=test_reason, move=test_move, goal=test_goal):
            break
        pg.time.wait(100)