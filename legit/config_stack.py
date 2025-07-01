import os
from pathlib import Path
from legit.config import ConfigFile

class ConfigStack:
    GLOBAL_CONFIG = os.path.expanduser("~/.gitconfig")
    SYSTEM_CONFIG = "/etc/gitconfig"

    def __init__(self, git_path):
        self.configs = {
            "local": ConfigFile(Path(git_path) / "config"),
            "global": ConfigFile(Path(self.GLOBAL_CONFIG)),
            "system": ConfigFile(Path(self.SYSTEM_CONFIG)),
        }

    def file(self, name):
        """
        Returns a specific config file object by name ('local', 'global', 'system')
        or a new ConfigFile object if the name is a path.
        """
        if name in self.configs:
            return self.configs[name]
        else:
            return ConfigFile(Path(name))

    def open(self):
        """Opens all configuration files in the stack."""
        for config in self.configs.values():
            config.open()

    def get(self, key):
        """
        Gets the last value for a key from the config stack.
        Searches in the order: system, global, local.
        """
        all_values = self.get_all(key)
        return all_values[-1] if all_values else None

    def get_all(self, key):
        """
        Gets all values for a key from the config stack.
        Combines values from system, global, and local configs.
        """
        all_values = []
        for name in ["system", "global", "local"]:
            config = self.configs[name]
            config.open()
            all_values.extend(config.get_all(key))
        return all_values
        
    def list(self):
        """
        Lists all variables from all config files.
        Local values override global, which override system.
        """
        all_vars = {}
        for name in ["system", "global", "local"]:
            config = self.configs[name]
            config.open()
            for item in config.list():
                key, value = item.split('=', 1)
                all_vars[key] = value
        
        return [f"{key}={value}" for key, value in all_vars.items()]


