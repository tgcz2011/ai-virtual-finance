"""Entry point for AI Virtual Finance."""

from __future__ import annotations

from src.tui.app import AVFApp


def main() -> None:
    """Run the TUI application."""
    app = AVFApp()
    app.run()


if __name__ == "__main__":
    main()
