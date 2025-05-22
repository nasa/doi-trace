from collections import UserDict
from json import dumps
from tomllib import TOMLDecodeError, load, loads
from pathlib import Path
from typing import Any, Dict, Optional

from deepmerge.exception import InvalidMerge
from deepmerge.merger import Merger


class Config(UserDict):
    """Configuration manager for DOI Trace.
    
    This class handles loading and merging configuration from multiple sources:
    1. Default configuration (built-in)
    2. User-supplied TOML configuration file
    3. Environment variables (for sensitive data like API keys)
    
    The merge strategy is defined in the merge_configs method.
    """
    
    default_config = """
    # Application Settings
    project_name = "DOI Trace"
    version = "May 2025"
    organization = "NASA"
    email = "info@disc.gsfc.nasa.gov"

    # General settings
    max_threads = 1           # limit the number of threads that we will use when multithreading tasks
    pretty_print_indent = 4   # set the level of indentation for pretty printing
    raise_stack_trace = false # determines whether critical exceptions should print a stacktrace
    log_level = "INFO"        # see types.py for literal options
    log_name = "DOI Trace"    # name of the logger the app uses
    
    # Data source settings
    providers = ["WoS", "Scopus", "Crossref", "Datacite", "Google Scholar"]
    
    # Directory settings
    [directories]
    wos = "WoS"
    eosdis = "eosdis_csv_files"
    output = "data"
    
    # API settings
    [api]
    serp_api_key = ""  # SerpAPI key for Google Scholar
    scopus_api_key = ""  # Scopus API key
    """
    
    user_config_path = "config.toml"
    
    def __init__(self, config_file: Optional[str] = None) -> None:
        """Initialize the configuration manager.
        
        Args:
            config_file: Optional path to a user configuration file
        """
        if config_file:
            self.user_config_path = config_file
            
        # Load and merge configurations
        self.data = self.merge_configs(
            base=loads(self.default_config),
            next=self.get_user_config()
        )

        # Override with environment variables
        self._load_env_vars()
    
    def get_user_config(self) -> Dict[str, Any]:
        """Load user-supplied configuration from TOML file.
        
        Returns:
            Dictionary containing user configuration or empty dict if no file exists
        """
        try:
            with open(self.user_config_path, "rb") as f:
                return load(f)
        except FileNotFoundError:
            print(
                "No user-supplied configuration was found, so default configuration is being applied."
            )
            return {}
        except TOMLDecodeError:
            print(
                f"The user-supplied configuration found in {self.user_config_path} is not valid TOML. "
                "The default configuration is being applied instead."
            )
            return {}
    
    def merge_configs(self, base: Dict[str, Any], next: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configurations using a defined strategy.
        
        Args:
            base: Base configuration (default)
            next: Next configuration to merge (user config)
            
        Returns:
            Merged configuration
        """
        try:
            merger = Merger(
                [(list, ["append"]), (dict, ["merge"])],
                ["override"],
                ["override"]
            )
            return merger.merge(base=base, nxt=next)
        except InvalidMerge as error:
            print(
                f"An error occurred when merging the user-supplied config with the default config: {error}"
            )
            return loads(self.default_config)
    
    def _load_env_vars(self) -> None:
        """Override configuration with environment variables."""
        # API keys
        serp_api_key = self._get_env("SERP_API_KEY")
        if serp_api_key is not None:
            self.data["api"]["serp_api_key"] = serp_api_key
        
        scopus_api_key = self._get_env("SCOPUS_API_KEY")
        if scopus_api_key is not None:
            self.data["api"]["scopus_api_key"] = scopus_api_key
        
        # Directories
        wos_dir = self._get_env("WOS_DIR")
        if wos_dir is not None:
            self.data["directories"]["wos"] = wos_dir
        
        eosdis_dir = self._get_env("EOSDIS_DIR")
        if eosdis_dir is not None:
            self.data["directories"]["eosdis"] = eosdis_dir
        
        output_dir = self._get_env("OUTPUT_DIR")
        if output_dir is not None:
            self.data["directories"]["output"] = output_dir
    
    def _get_env(self, key: str) -> Optional[str]:
        """Get environment variable if it exists.
        
        Args:
            key: Environment variable name
            
        Returns:
            Environment variable value or None
        """
        import os
        return os.getenv(key)
    
    def get_directory(self, name: str) -> Path:
        """Get a directory path from configuration.
        
        Args:
            name: Directory name (e.g., 'wos', 'eosdis', 'output')
            
        Returns:
            Path object for the directory
        """
        return Path(self.data["directories"].get(name, name))
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get an API key from configuration.
        
        Args:
            service: Service name (e.g., 'serp', 'scopus')
            
        Returns:
            API key or None if not found
        """
        return self.data["api"].get(f"{service}_key")
    
    def dump(self) -> str:
        """Dump configuration to JSON string.
        
        Returns:
            JSON string representation of configuration
        """
        return dumps(
            self.data,
            indent=self.data.get("pretty_print_indent", 4)
        )


config = Config()
