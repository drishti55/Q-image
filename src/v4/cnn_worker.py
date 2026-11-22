"""Stand-alone worker for the CNN Feature Studio: `python -m src.v4.cnn_worker`.

Runs torch in a process that never imports Qiskit / Qiskit-Aer: on macOS their bundled OpenMP runtimes can deadlock or
segfault each other once both are loaded. Protocol: one JSON request per stdin line {"fn": "images"|"analyse"|"hybrid", "args": []},
one JSON reply per stdout line {"ok": true, "result": ...} or {"ok": false, "kind": "KeyError"|..., "error": "..."}.
"""
import json
import sys


def main():
    from src.v4 import cnn_maps
    out = sys.stdout
    sys.stdout = sys.stderr  # keep stray prints out of the reply channel
    for line in sys.stdin:
        try:
            req = json.loads(line)
            if req.get("fn") not in ("images", "analyse", "hybrid"):
                raise ValueError("unknown function")
            reply = {"ok": True, "result": getattr(cnn_maps, req["fn"])(*req.get("args", []))}
        except Exception as e:  # reported to the API process, which maps it to an HTTP status
            reply = {"ok": False, "kind": type(e).__name__, "error": str(e)}
        out.write(json.dumps(reply) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
