"""Small deterministic examples used by the CLI and presentation demo."""

EXAMPLES = {
    "already-close": {
        "pi": [(0, 0), (1, 1), (2, 0), (3, 1)],
        "sigma": [(0, 0.2), (1, 0.8), (2, 0.2), (3, 0.8)],
        "delta": 0.3,
    },
    "delete-outlier": {
        "pi": [(0, 0), (1, 1), (2, 0), (3, 1)],
        "sigma": [(0, 0), (1, 1), (1.5, 4), (2, 0), (3, 1)],
        "delta": 0.25,
    },
    "insert-gap": {
        "pi": [(0, 0), (1, 1), (2, 0), (3, 1)],
        "sigma": [(0, 0), (3, 1)],
        "delta": 0.25,
    },
    "repair-both": {
        "pi": [(0, 0), (1, 1), (2, 0), (3, 1)],
        "sigma": [(0, 0), (1.5, 4), (3, 1)],
        "delta": 0.25,
    },
}

