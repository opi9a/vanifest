#!/usr/bin/env python3

"""
A script to launch the app (or serve as an entry point, whatever)
"""

# NB this import does not work until my_package has been installed, and is
# available in the PYTHONPATH
from my_package import main

def launch():
    main.main()


# setup.py will by default enter at launch() but to run this script:
if __name__ == "__main__":
    launch()    
