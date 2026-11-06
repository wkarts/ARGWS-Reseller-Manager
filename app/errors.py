class BridgeError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, uncertain: bool = False):
        super().__init__(message)
        self.code, self.message, self.status, self.uncertain = code, message, status, uncertain
