import os

# Run Qt without a display, e.g. in WSL or CI. Must be set before pytest-qt
# creates the QApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
