"""
GPU detection utility. TensorFlow automatically uses a GPU if one is available
and properly configured (CUDA + cuDNN installed) — no code changes are needed
to "enable" it. This module just detects and reports what's actually being used,
so you can confirm whether training is running on CPU or GPU.
"""


def get_device_info():
    """Returns a dict describing available compute devices for training."""
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices("GPU")
        return {
            "tensorflow_version": tf.__version__,
            "gpu_available": len(gpus) > 0,
            "gpu_count": len(gpus),
            "gpu_names": [g.name for g in gpus],
            "note": (
                "Training will use GPU automatically." if gpus else
                "No GPU detected — training will run on CPU. This project's headline "
                "classification task is small enough that CPU training (5-15 min) is fine; "
                "a GPU mainly helps for much larger models/datasets."
            ),
        }
    except ImportError:
        return {"error": "tensorflow not installed"}


if __name__ == "__main__":
    import json
    print(json.dumps(get_device_info(), indent=2))
