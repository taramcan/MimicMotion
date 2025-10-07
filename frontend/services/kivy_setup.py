# Author: RD7
# Purpose: Small patch to setup required Kivy environment variable
# Created: 2025-10-03

import os

# Better practice is to put these in the command line
# They are put here for convenience of testing in IDEs
# e.g. $env:KIVY_NO_ARGS='1'; python main.py <args>
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_CAMERA", "opencv")
