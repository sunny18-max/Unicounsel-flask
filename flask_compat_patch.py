# Patch pkgutil to add get_loader for Flask compatibility on Python 3.14+
import sys
import importlib.util

if sys.version_info >= (3, 14):
    import pkgutil
    
    # Store original get_loader if it exists
    _original_get_loader = getattr(pkgutil, 'get_loader', None)
    
    def _get_loader(name):
        # Handle __main__ module specially
        if name == "__main__":
            # For __main__, try to get the loader from sys.modules
            if "__main__" in sys.modules:
                main_module = sys.modules["__main__"]
                if hasattr(main_module, "__loader__"):
                    loader = getattr(main_module, "__loader__", None)
                    if loader is not None:
                        return loader
                if hasattr(main_module, "__spec__"):
                    spec = getattr(main_module, "__spec__", None)
                    if spec is not None and hasattr(spec, "loader"):
                        return spec.loader
            # Return None for __main__ if no loader found
            return None
        
        # For other modules, try find_spec
        try:
            spec = importlib.util.find_spec(name)
            if spec is not None and hasattr(spec, "loader"):
                return spec.loader
        except (ValueError, AttributeError):
            # If find_spec fails or spec is invalid, return None
            pass
        
        # Fallback to original implementation if available
        if _original_get_loader:
            try:
                return _original_get_loader(name)
            except:
                pass
        
        return None
    
    # Only patch if get_loader doesn't exist or needs patching
    if not hasattr(pkgutil, 'get_loader') or _original_get_loader is None:
        pkgutil.get_loader = _get_loader
