import yaml

class Config:
    def __init__(self, config_file="config.yaml"):
        self.config_file = config_file
        self.load()

    def load(self):
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.API_ID = data.get("api_id")
        self.API_HASH = data.get("api_hash")
        self.PHONE = data.get("phone")
        self.SESSION_NAME = data.get("session_name", "exporter")
        
        self.START_DATE = data.get("start_date", "2024-01-01")
        self.OUTPUT_DIR = data.get("output_dir", "./tg_export")
        self.DOWNLOAD_MEDIA = data.get("download_media", True)
        self.MAX_MEDIA_SIZE_MB = data.get("max_media_size_mb", 50)
        self.VIDEO_COVER_ONLY = data.get("video_cover_only", False)
        self.MEDIA_TYPES_TO_DOWNLOAD = data.get("media_types_to_download", ["photo", "video", "document", "audio", "voice", "sticker"])
        self.REQUEST_DELAY = data.get("request_delay", 1.5)
        self.BATCH_SIZE = data.get("batch_size", 100)
        self.MAX_MESSAGES_PER_GROUP = data.get("max_messages_per_group", 0)
        self.OUTPUT_FORMATS = data.get("output_formats", ["html", "excel", "json"])
        
        self.CHECKPOINT_FILE = data.get("checkpoint_file", "checkpoint.json")
        self.ERROR_LOG_FILE = data.get("error_log_file", "export_errors.log")
        self.SUMMARY_FILE = data.get("summary_file", "export_summary.json")

    def save(self):
        data = {
            "api_id": self.API_ID,
            "api_hash": self.API_HASH,
            "phone": self.PHONE,
            "session_name": self.SESSION_NAME,
            "start_date": self.START_DATE,
            "output_dir": self.OUTPUT_DIR,
            "download_media": self.DOWNLOAD_MEDIA,
            "max_media_size_mb": self.MAX_MEDIA_SIZE_MB,
            "video_cover_only": self.VIDEO_COVER_ONLY,
            "media_types_to_download": self.MEDIA_TYPES_TO_DOWNLOAD,
            "request_delay": self.REQUEST_DELAY,
            "batch_size": self.BATCH_SIZE,
            "max_messages_per_group": self.MAX_MESSAGES_PER_GROUP,
            "output_formats": self.OUTPUT_FORMATS,
            "checkpoint_file": self.CHECKPOINT_FILE,
            "error_log_file": self.ERROR_LOG_FILE,
            "summary_file": self.SUMMARY_FILE
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

# Singleton instance to be used across modules
try:
    config = Config()
except FileNotFoundError:
    print("Warning: config.yaml not found. A dummy config is initialized.")
    # Initialize dummy so it doesn't break imports, but shouldn't be used until loaded
    class DummyConfig:
        pass
    config = DummyConfig()
    config.OUTPUT_DIR = "./tg_export"
    config.MAX_MEDIA_SIZE_MB = 50
    config.MEDIA_TYPES_TO_DOWNLOAD = ["photo"]
    config.DOWNLOAD_MEDIA = True
    config.START_DATE = "2024-01-01"
    config.OUTPUT_FORMATS = ["html"]
    config.REQUEST_DELAY = 1.5
    config.BATCH_SIZE = 100
    config.MAX_MESSAGES_PER_GROUP = 0
