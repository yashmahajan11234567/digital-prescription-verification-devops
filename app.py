"""RxVerify - Backwards compatibility wrapper.
This file exists for backwards compatibility with existing imports.
The actual implementation is in src/__init__.py
"""
from src import create_app

# Create app instance for backwards compatibility
app = create_app()

if __name__ == "__main__":
    app.run()