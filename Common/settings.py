import os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.txt")


def load_settings():
    """
    Read key=value pairs from settings.txt and return the parsed values.
    Raises FileNotFoundError if the file is missing, ValueError if a required key is absent.
    """
    settings = {}

    with open(SETTINGS_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            settings[key.strip()] = value.strip()

    required = ("server_ip", "server_port", "video_port", "audio_port", "dh_p", "dh_g")
    for key in required:
        if key not in settings:
            raise ValueError(f"settings.txt is missing '{key}'")

    return (
        settings["server_ip"],
        int(settings["server_port"]),
        int(settings["video_port"]),
        int(settings["audio_port"]),
        int(settings["dh_p"]),
        int(settings["dh_g"]),
    )
