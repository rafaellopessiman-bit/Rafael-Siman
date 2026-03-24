class AtlasError(RuntimeError):
    pass

class AtlasConfigError(AtlasError):
    pass

class AtlasBlockedQueryError(AtlasError):
    pass

class AtlasValidationError(AtlasBlockedQueryError):
    pass

class AtlasExecutionError(AtlasError):
    pass

class AtlasProviderError(AtlasError):
    pass

class AtlasLoadError(AtlasError):
    pass

class AtlasProviderAuthError(AtlasProviderError):
    pass

class AtlasProviderRateLimitError(AtlasProviderError):
    pass

class AtlasProviderSchemaError(AtlasProviderError):
    pass

class AtlasProviderTransientError(AtlasProviderError):
    pass

class AtlasRetrieverError(AtlasError):
    pass
