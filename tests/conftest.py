import os
import pathlib

# Fix for Windows Python 3.10 _NormalAccessor.mkdir bug where os.mkdir becomes a bound method
pathlib._NormalAccessor.mkdir = staticmethod(os.mkdir)

