from collections import UserDict
from json import dumps
from tomllib import TOMLDecodeError, load, loads

from deepmerge.exception import InvalidMerge
from deepmerge.merger import Merger


class Config(UserDict):
    """
    This class subclasses UserDict to represent the configuration that DOI Trace uses during its operation. There are a few key concepts:
    - There is a default configuration that the DOI Trace authors have stored in this class.
    - Users may supply a configuration file at a path defined in this class. The user-supplied configuration is optional, so DOI Trace can operate without it.
    - The two configurations will be merged together into the final configuration used by DOI Trace. The merge stragety is defined in this class.

    Helpful Links:
    - https://docs.python.org/3/library/collections.html#collections.UserDict
    - https://deepmerge.readthedocs.io/en/latest/strategies.html
    - https://docs.python.org/3/library/tomllib.html
    """

    default_config = """
    max_threads = 1           # limit the number of threads that we will use when multithreading tasks
    pretty_print_indent = 4   # set the level of indentation for pretty printing
    raise_stack_trace = false # determines whether critical exceptions should print a stacktrace
    log_level = "INFO"        # see types.py for literal options
    log_name = "DOI Trace"          # name of the logger the app uses
    providers = ["WoS", "Foo", "Bar"]

    """
    user_config_path = "config.toml"

    def __init__(self) -> None:
        """
        Load the default configuration and the user-supplied configuration (if any), merging the two.
        """
        self.data = self.merge_configs(
            base=loads(self.default_config), next=self.get_user_config()
        )

    def get_user_config(self):
        """
        Optionally, the user can supply a config file.
        We return an empty dictionary literal in case they have not supplied anything.
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
                f"The user-supplied configuration found in {self.user_config_path} is not valid TOML. The default configuration is being applied instead."
            )
            return {}

    def merge_configs(self, base: dict, next: dict):
        """
        Declare our merge strategy for merging default and user configs.
        https://deepmerge.readthedocs.io/en/latest/strategies.html
        """
        try:
            merger = Merger(
                [(list, ["append"]), (dict, ["merge"])], ["override"], ["override"]
            )

            return merger.merge(base=base, nxt=next)

        except InvalidMerge as error:
            print(
                f"An error occurred when merging the user-supplied config with the default config: {error}"
            )
            # If we want to "crash early" if the user provides and invalid config, raise the InvalidMerge error instead of returning the default config.
            return loads(self.default_config)

    def dump(self):
        return dumps(
            self.data, indent=self.data.get("utf", {}).get("pretty_print_indent")
        )


config = Config()
