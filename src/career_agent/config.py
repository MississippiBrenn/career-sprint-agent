"""Configuration and settings for Career Sprint Agent."""

from pathlib import Path

# Data storage location
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
LIBRARY_STATE_FILE = DATA_DIR / "library_state.json"

# Libraries to monitor
LIBRARIES = [
    # Tier 1: Core Infrastructure
    "torch",           # PyTorch - Production ML standard
    "transformers",    # Hugging Face - LLM/multimodal standard
    "ultralytics",     # YOLOv8/v9 - Object detection
    "fastapi",         # API framework - ML deployment
    "opencv-python",   # OpenCV - Computer vision
    "ray",             # Distributed ML - Production scale

    # Tier 2: Strategic
    "supervision",     # Roboflow utilities
    "onnxruntime",     # Model optimization/edge inference
]

# Library metadata for learning context
LIBRARY_CONTEXT = {
    "torch": {
        "display_name": "PyTorch",
        "category": "ML Framework",
        "relevance": ["portfolio", "interview", "production"],
    },
    "transformers": {
        "display_name": "Hugging Face Transformers",
        "category": "LLM/NLP",
        "relevance": ["portfolio", "interview", "production"],
    },
    "ultralytics": {
        "display_name": "Ultralytics (YOLOv8)",
        "category": "Object Detection",
        "relevance": ["portfolio", "production"],
    },
    "fastapi": {
        "display_name": "FastAPI",
        "category": "API Framework",
        "relevance": ["portfolio", "interview", "production"],
    },
    "opencv-python": {
        "display_name": "OpenCV",
        "category": "Computer Vision",
        "relevance": ["portfolio", "interview"],
    },
    "ray": {
        "display_name": "Ray",
        "category": "Distributed ML",
        "relevance": ["production", "interview"],
    },
    "supervision": {
        "display_name": "Supervision (Roboflow)",
        "category": "CV Utilities",
        "relevance": ["portfolio"],  # Targeting Roboflow
    },
    "onnxruntime": {
        "display_name": "ONNX Runtime",
        "category": "Model Optimization",
        "relevance": ["production"],
    },
}

# PyPI API endpoint
PYPI_API_URL = "https://pypi.org/pypi/{package}/json"
