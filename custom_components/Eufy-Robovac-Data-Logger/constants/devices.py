"""Device constants for Eufy Robovac Data Logger - Simplified for X10 focus."""

# Eufy X10 and related robovac models
EUFY_CLEAN_DEVICES = {
    # X10 Series (Primary focus for debugging)
    'T2351': 'X10 Pro Omni',
    'T2320': 'X10 Pro',
    
    # X8 Series (Related models)
    'T2262': 'X8',
    'T2261': 'X8 Hybrid',
    'T2266': 'X8 Pro',
    'T2276': 'X8 Pro SES',
    
    # G Series (Common models)
    'T2250': 'G30',
    'T2251': 'G30',
    'T2252': 'G30 Verge',
    'T2253': 'G30 Hybrid',
    'T2254': 'G35',
    'T2255': 'G40',
    'T2256': 'G40 Hybrid',
    'T2270': 'G35+',
    'T2273': 'G40 Hybrid+',
    
    # L Series
    'T2190': 'L70 Hybrid',
    'T2267': 'L60',
    'T2268': 'L60 Hybrid',
    
    # Legacy models
    'T2080': 'S1'
}

# X10 Series specifically (for focused debugging)
EUFY_X10_SERIES = [
    'T2351',  # X10 Pro Omni (primary target)
    'T2320',  # X10 Pro
]

# X8 Series (similar architecture)
EUFY_X8_SERIES = [
    'T2262',  # X8
    'T2261',  # X8 Hybrid
    'T2266',  # X8 Pro
    'T2276',  # X8 Pro SES
]

# Models that likely support NEW Android app features
EUFY_NEW_APP_MODELS = [
    'T2351',  # X10 Pro Omni
    'T2320',  # X10 Pro
    'T2266',  # X8 Pro
    'T2276',  # X8 Pro SES
]

def get_device_name(model_code: str) -> str:
    """Get human-readable device name from model code."""
    return EUFY_CLEAN_DEVICES.get(model_code, f"Unknown Model ({model_code})")

def is_x10_series(model_code: str) -> bool:
    """Check if device is X10 series."""
    return model_code in EUFY_X10_SERIES

def supports_new_app_features(model_code: str) -> bool:
    """Check if device likely supports NEW Android app features."""
    return model_code in EUFY_NEW_APP_MODELS
