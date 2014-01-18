from .app import PlatterQt, AlreadyRunning

def main():
    import sys
    try:
        app = PlatterQt(sys.argv)
    except AlreadyRunning:
        return 0
    else:
        return app.exec_()
