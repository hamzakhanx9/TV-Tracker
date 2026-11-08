class ProviderError(Exception):
    def __init__(
        self,
        provider: str,
        message: str,
        *,
        unavailable: bool = False,
        not_found: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.unavailable = unavailable
        self.not_found = not_found
