"""Precompute the training density matrices of the frozen V4 FRQI model (seed 0) and save them as a .npy file, so the
live walkthrough and the upload lab can memory-map them instead of computing them at runtime. Used when building the
hosted demo image; values are identical to computing them live (checked here). Writes only to results/qml_v4/cache/."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.v4.api import _frqi_model, frozen_rho_path  # noqa: E402


def main():
    M = _frqi_model()
    out = frozen_rho_path(M["eid"], M["est"]._xtr_sha)
    if out.exists():
        print(f"exists: {out}")
        return
    R = np.ascontiguousarray(M["R"])  # computed live by _frqi_model (no file yet)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.npy")
    np.save(tmp, R)
    assert np.array_equal(np.load(tmp, mmap_mode="r"), R)
    tmp.rename(out)
    print(f"wrote {out} {R.shape} {R.dtype} {R.nbytes / 2**20:.0f} MB")


if __name__ == "__main__":
    main()
