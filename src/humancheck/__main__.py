"""CLI interface for Humancheck.

This module provides a command-line interface for managing the Humancheck
platform, including initialization, server management, and status checks.
"""
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

import click
import uvicorn

from .config import HumancheckConfig, get_config, init_config


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Humancheck - Human-in-the-Loop Operations Platform for AI Agents.

    A universal platform that enables AI agents to escalate uncertain or
    high-stakes decisions to human reviewers for approval.
    """
    pass


@cli.command()
@click.option(
    "--config-path",
    "-c",
    type=click.Path(dir_okay=False),
    default="humancheck.yaml",
    help="Path to configuration file",
)
@click.option("--force", "-f", is_flag=True, help="Force overwrite existing config")
def init(config_path: str, force: bool):
    """Initialize Humancheck configuration.

    Creates a default configuration file with recommended settings.
    """
    config_file = Path(config_path)

    if config_file.exists() and not force:
        click.echo(f"Configuration file already exists: {config_path}")
        click.echo("Use --force to overwrite")
        return

    try:
        # Create default config
        config = HumancheckConfig.create_default_config(config_file)

        click.echo(f"✓ Created configuration file: {config_path}")
        click.echo("\nDefault configuration:")
        click.echo(f"  API Server: {config.api_host}:{config.api_port}")
        click.echo(f"  Dashboard: {config.streamlit_host}:{config.streamlit_port}")
        click.echo(f"  Database: {config.get_database_url()}")
        click.echo(f"\nEdit {config_path} to customize settings.")

    except Exception as e:
        click.echo(f"Error creating configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to configuration file",
)
@click.option("--host", help="Override API host")
@click.option("--port", type=int, help="Override API port")
@click.option("--dashboard/--no-dashboard", default=True, help="Launch dashboard")
def start(config: str, host: str, port: int, dashboard: bool):
    """Start Humancheck API server and dashboard.

    This launches both the FastAPI REST API server and the Streamlit
    dashboard for reviewing requests.
    """
    try:
        # Initialize configuration
        app_config = init_config(config) if config else init_config()

        # Override with CLI options
        if host:
            app_config.api_host = host
        if port:
            app_config.api_port = port

        click.echo("🚀 Starting Humancheck...")
        click.echo(f"   API: http://{app_config.api_host}:{app_config.api_port}")

        if dashboard:
            click.echo(f"   Dashboard: http://{app_config.streamlit_host}:{app_config.streamlit_port}")

        click.echo("\nPress Ctrl+C to stop\n")

        # Start dashboard in background if requested
        dashboard_process = None
        if dashboard:
            import os
            from pathlib import Path

            # Find the streamlit app
            frontend_dir = Path(__file__).parent.parent.parent / "frontend"
            streamlit_app = frontend_dir / "streamlit_app.py"

            if not streamlit_app.exists():
                click.echo(f"Warning: Dashboard app not found at {streamlit_app}", err=True)
            else:
                dashboard_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "streamlit",
                        "run",
                        str(streamlit_app),
                        "--server.port",
                        str(app_config.streamlit_port),
                        "--server.address",
                        app_config.streamlit_host,
                        "--server.headless",
                        "true",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

        try:
            # Start API server
            uvicorn.run(
                "humancheck.api:app",
                host=app_config.api_host,
                port=app_config.api_port,
                log_level=app_config.log_level.lower(),
            )
        finally:
            # Clean up dashboard process
            if dashboard_process:
                dashboard_process.terminate()
                dashboard_process.wait()

    except KeyboardInterrupt:
        click.echo("\n\nStopping Humancheck...")
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to configuration file",
)
def mcp(config: str):
    """Run Humancheck as an MCP server.

    This starts Humancheck in MCP (Model Context Protocol) mode for
    integration with Claude Desktop and other MCP clients.
    """
    try:
        from .mcp_server import main as mcp_main

        # Set config path if provided
        if config:
            import os
            os.environ["HUMANCHECK_CONFIG_PATH"] = config

        click.echo("🔌 Starting Humancheck MCP Server...")
        click.echo("   Waiting for MCP client connections...\n")

        mcp_main()

    except KeyboardInterrupt:
        click.echo("\n\nStopping MCP server...")
    except Exception as e:
        click.echo(f"Error starting MCP server: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to configuration file",
)
def status(config: str):
    """Check Humancheck system status.

    Displays configuration and database information.
    """
    try:
        app_config = init_config(config) if config else init_config()

        click.echo("Humancheck Status")
        click.echo("=" * 50)
        click.echo(f"Configuration: {config or 'default'}")
        click.echo(f"Database URL: {app_config.get_database_url()}")
        click.echo(f"API Server: {app_config.api_host}:{app_config.api_port}")
        click.echo(f"Dashboard: {app_config.streamlit_host}:{app_config.streamlit_port}")
        click.echo(f"Log Level: {app_config.log_level}")

        # Try to connect to database
        from .database import init_db

        db = init_db(app_config.get_database_url())
        click.echo("\n✓ Database connection successful")

        # Get review counts
        async def get_counts():
            async with db.session() as session:
                from sqlalchemy import func, select

                from .models import Review, ReviewStatus

                result = await session.execute(select(func.count(Review.id)))
                total = result.scalar_one()

                result = await session.execute(
                    select(func.count(Review.id)).where(
                        Review.status == ReviewStatus.PENDING.value
                    )
                )
                pending = result.scalar_one()

                return total, pending

        total, pending = asyncio.run(get_counts())
        click.echo(f"\nReviews: {total} total, {pending} pending")

    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to configuration file",
)
@click.option("--limit", "-n", type=int, default=20, help="Number of reviews to show")
@click.option("--status-filter", type=str, help="Filter by status")
def logs(config: str, limit: int, status_filter: str):
    """View recent reviews and decisions.

    Displays a log of recent review requests and their outcomes.
    """
    try:
        app_config = init_config(config) if config else init_config()
        from .database import init_db

        db = init_db(app_config.get_database_url())

        async def get_recent_reviews():
            async with db.session() as session:
                from sqlalchemy import select

                from .models import Review

                query = select(Review).order_by(Review.created_at.desc()).limit(limit)

                if status_filter:
                    query = query.where(Review.status == status_filter.lower())

                result = await session.execute(query)
                return list(result.scalars().all())

        reviews = asyncio.run(get_recent_reviews())

        if not reviews:
            click.echo("No reviews found")
            return

        click.echo(f"\nRecent Reviews (showing {len(reviews)}):")
        click.echo("=" * 80)

        for review in reviews:
            status_icon = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
                "modified": "✏️",
            }.get(review.status, "❓")

            click.echo(
                f"\n{status_icon} Review #{review.id} - {review.task_type} [{review.status.upper()}]"
            )
            click.echo(f"   Created: {review.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"   Action: {review.proposed_action[:100]}...")
            if review.confidence_score:
                click.echo(f"   Confidence: {review.confidence_score:.1%}")

    except Exception as e:
        click.echo(f"Error retrieving logs: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
