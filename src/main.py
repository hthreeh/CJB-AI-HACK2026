import argparse
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_args():
    parser = argparse.ArgumentParser(prog="os-agent")
    subparsers = parser.add_subparsers(dest="mode")

    web_parser = subparsers.add_parser("web")
    web_parser.add_argument("--host", default="0.0.0.0")
    web_parser.add_argument("--port", type=int, default=8000)

    return parser.parse_args()


def run_web(host: str, port: int):
    import uvicorn
    from src.web_api import app

    print("=" * 60)
    print("  鎿嶄綔绯荤粺鏅鸿兘浠ｇ悊 - Web鏈嶅姟")
    print("=" * 60)
    print(f"  璁块棶鍦板潃: http://{host}:{port}")
    print(f"  API鏂囨。: http://{host}:{port}/docs")
    print("=" * 60)

    uvicorn.run(app, host=host, port=port)


def run_cli():
    from src.cli import CLI

    CLI().run()


def main():
    args = parse_args()
    if args.mode == "web":
        run_web(host=args.host, port=args.port)
        return
    run_cli()


if __name__ == "__main__":
    main()
