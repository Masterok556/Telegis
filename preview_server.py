"""Compatibility launcher: preview and production use the SAME Telegis API.

Run with the project dependencies installed:
    python preview_server.py --port 8080
Only static/ and presentation/ are served; the repository and .env are not.
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=args.port,
                access_log=False, use_colors=False)


if __name__ == "__main__":
    main()
