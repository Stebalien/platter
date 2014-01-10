from .app import PlatterQt

def main():
    import sys
    try:
        app = PlatterQt(sys.argv)
    except IllegalArgumentException as e:
        print(e, file=sys.stderr)
        return 1
    else:
        return app.exec()
