import json
import pathlib

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            # default to config.json in parent directory
            current_file = pathlib.Path(__file__).resolve()
            config_path = current_file.parent / "config.json"
        
        self.config_path = pathlib.Path(config_path)
        self._config = {}
        self.load()

        # fixed screen size
        self.SCREEN_WIDTH = 1280
        self.SCREEN_HEIGHT = 720
    
    def load(self):
        try:
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
            print(f"Configuration loaded from {self.config_path}")
        except FileNotFoundError:
            print(f"Config file not found: {self.config_path}")
            print("Using default configuration")
            self._create_default_config()
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
            print("Using default configuration")
            self._create_default_config()
    
    def save(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            print(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def _create_default_config(self):
        self._config = {
            "display": {
                "fps": 120,
                "physics_fps": 240
            },
            "physics": {
                "gravity": 9.81,
                "pixels_per_meter": 100,
                "time_scale": 1.0
            },
            "colors": {
                "WHITE": [255, 255, 255],
                "BLACK": [0, 0, 0],
                "RED": [255, 0, 0],
                "GREEN": [0, 255, 0],
                "BLUE": [0, 0, 255],
                "GRAY": [128, 128, 128],
                "DARK_GRAY": [64, 64, 64]
            },
        }
        self.save()
    
    def get(self, *keys, default=None):
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, *keys, value):
        if len(keys) == 0:
            return False
        
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        return True
    
    @property
    def FPS(self):
        return self.get("display", "fps")
    
    @FPS.setter
    def FPS(self, value):
        self.set("display", "fps", value=value)
    
    @property
    def PHYSICS_FPS(self):
        return self.get("display", "physics_fps")
    
    @PHYSICS_FPS.setter
    def PHYSICS_FPS(self, value):
        self.set("display", "physics_fps", value=value)
    
    @property
    def GRAVITY(self):
        return self.get("physics", "gravity")
    
    @GRAVITY.setter
    def GRAVITY(self, value):
        self.set("physics", "gravity", value=value)
    
    @property
    def PIXELS_PER_METER(self):
        return self.get("physics", "pixels_per_meter")
    
    @PIXELS_PER_METER.setter
    def PIXELS_PER_METER(self, value):
        self.set("physics", "pixels_per_meter", value=value)
    
    @property
    def TIME_SCALE(self):
        return self.get("physics", "time_scale")
    
    @TIME_SCALE.setter
    def TIME_SCALE(self, value):
        self.set("physics", "time_scale", value=value)
    
    @property
    def COLORS(self):
        colors = self.get("colors", default={})
        # convert lists to tuples for pygame compatibility
        return {k: tuple(v) if isinstance(v, list) else v for k, v in colors.items()}


# create a global instance
_config_manager = ConfigManager()

# export values from json
SCREEN_WIDTH = _config_manager.SCREEN_WIDTH
SCREEN_HEIGHT = _config_manager.SCREEN_HEIGHT
FPS = _config_manager.FPS
PHYSICS_FPS = _config_manager.PHYSICS_FPS
GRAVITY = _config_manager.GRAVITY
PIXELS_PER_METER = _config_manager.PIXELS_PER_METER
TIME_SCALE = _config_manager.TIME_SCALE
COLORS = _config_manager.COLORS


def get_config_manager():
    return _config_manager
