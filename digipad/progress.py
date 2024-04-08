class Progress:
    """A utility that print a progress message and its confirmation."""

    def __init__(self, message):
        self.message = message
        self.first = True
        self.ended = True

    def start(self, message):
        """Display a message that indicates progress."""
        if not self.ended:
            self.end()
        self.ended = False
        print(f"{'' if self.first else ' -- '}{message}... ", end="", flush=True)
        self.first = False

    def end(self):
        """Write "OK" to indicate that progress is done."""
        if not self.ended:
            print("OK", end="", flush=True)
            self.ended = True

    def __enter__(self):
        self.start(self.message)
        return self

    def __exit__(self, exc, value, tb):
        if not exc:
            self.end()
            print()
        else:
            self.ended = True
            print("ERROR: ", end="")
