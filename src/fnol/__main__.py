"""
Make src.fnol runnable as a module.

Usage: python -m src.fnol --text "..." --images ...
"""

from .cli import main

if __name__ == '__main__':
    main()
