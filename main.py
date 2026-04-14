"""
Curse of Strahd VTT - Main Entry Point
Run: python main.py
Requires: pip install pygame
"""

import sys
import pygame
from src.app import App


def main():
    pygame.init()
    pygame.mixer.init()

    app = App()
    app.run()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
