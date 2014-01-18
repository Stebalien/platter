from .app import PlatterQt

def main():
    import sys
    app = PlatterQt(sys.argv)
    return app.exec()
