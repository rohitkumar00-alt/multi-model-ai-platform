"""
Tiny shared helper so the mock adapter and the mock coordinator agree on
a deterministic "stance" per model id, without any real understanding of
the question. This exists only to give the mock demo something concrete
to compare - a real (LLM-backed) coordinator would compare actual meaning
instead of this label.
"""
import zlib

STANCES = ["confident", "cautious", "detailed"]


def stance_for(model_id: str) -> str:
    return STANCES[zlib.crc32(model_id.encode()) % len(STANCES)]
