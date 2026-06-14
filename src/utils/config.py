import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "config.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}，请先复制 config.example.yaml 为 config.yaml")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    # 环境变量覆盖
    _apply_env_overrides(config)
    return config


def _apply_env_overrides(config: dict, prefix: str = ""):
    for key, value in config.items():
        env_key = f"{prefix}{key}".upper() if prefix else key.upper()
        if isinstance(value, dict):
            _apply_env_overrides(value, prefix=f"{env_key}_")
        else:
            env_val = os.getenv(env_key)
            if env_val is not None:
                config[key] = type(value)(env_val) if value is not None else env_val
