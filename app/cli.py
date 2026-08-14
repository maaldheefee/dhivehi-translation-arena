from pathlib import Path

import click
from flask.cli import with_appcontext

from app.config import Config
from app.database import Base, db_session, engine
from app.models import User
from app.services.user_service import create_user, delete_user


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Initialize the database with default users."""
    Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)

    print("Initializing database...")
    if engine is None:
        msg = "Database engine is not initialized. Ensure init_db(app) was called."
        raise RuntimeError(msg)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    from app.schema_migrations import run_schema_migrations

    run_schema_migrations(engine)
    print("Database schema checked/created successfully.")

    default_users = [
        # No default users - use `flask add-user <username> <password>` to create users
    ]

    user_count = db_session.query(User).count()
    if user_count == 0 and default_users:
        print("No users found, creating default users...")
        for user_data in default_users:
            create_user(
                username=user_data["username"],
                password=user_data["password"],
                is_admin=user_data["is_admin"],
            )
        print("Default users created successfully!")
    elif user_count == 0:
        print("No users found. Use 'flask add-user <username> <password>' to create users.")
    else:
        print(f"{user_count} users already exist.")


@click.command("add-user")
@click.argument("username")
@click.argument("password")
@click.option("--admin", is_flag=True, help="Set user as admin")
@with_appcontext
def add_user_command(username, password, admin) -> None:
    """Add a new user."""
    try:
        create_user(username, password, is_admin=admin)
        click.echo(f"User '{username}' added successfully.")
    except Exception as e:
        click.echo(f"Error adding user: {e}")


@click.command("remove-user")
@click.argument("username")
@with_appcontext
def remove_user_command(username) -> None:
    """Remove a user."""
    if delete_user(username):
        click.echo(f"User '{username}' removed successfully.")
    else:
        click.echo(f"User '{username}' not found.")


@click.command("list-users")
@with_appcontext
def list_users_command() -> None:
    """List all users."""
    users = db_session.query(User).all()
    if not users:
        click.echo("No users found.")
        return

    click.echo(f"{'Username':<20} {'Role':<10}")
    click.echo("-" * 30)
    for user in users:
        role = "Admin" if user.is_admin else "User"
        click.echo(f"{user.username:<20} {role:<10}")


@click.command("derive-elo")
@click.option("--user-id", type=int, default=None, help="Filter by user ID")
@with_appcontext
def derive_elo_command(user_id) -> None:
    """Deprecated alias for rebuilding the deterministic rating projection."""
    from app.services.elo_service import get_elo_service

    try:
        elo_service = get_elo_service()
        if user_id is not None:
            raise click.UsageError("Per-user derivation is no longer supported; ballots are immutable source evidence")
        print("Rebuilding deterministic ratings from ballot periods...")
        count = elo_service.rebuild_ratings_from_comparisons()
        print(f"Successfully replayed {count} comparisons.")
    except Exception as e:
        print(f"Error deriving ELO comparisons: {e}")


@click.command("rebuild-ratings")
@with_appcontext
def rebuild_ratings_command() -> None:
    """Rebuild all Glicko-2 ratings from stored comparisons."""
    from app.services.elo_service import get_elo_service

    try:
        elo_service = get_elo_service()
        print("Rebuilding Glicko-2 ratings from comparisons...")
        count = elo_service.rebuild_ratings_from_comparisons()
        print(f"Replayed {count} comparisons.")
        rankings = elo_service.get_all_rankings()
        print("\nUpdated Rankings:")
        for i, r in enumerate(rankings, 1):
            print(
                f"  {i}. {r['model']}: {r['elo_rating']:.1f} "
                f"(RD={r['rating_deviation']:.1f}, "
                f"{r['wins']}W/{r['losses']}L/{r['ties']}T)"
            )
    except Exception as e:
        print(f"Error rebuilding ratings: {e}")


@click.command("correct-vote")
@click.argument("user_id", type=int)
@click.argument("query_id", type=int)
@click.argument("translation_id", type=int)
@click.argument("rating", type=click.Choice(["3", "2", "1", "-1"]))
@click.confirmation_option(prompt="This exceptional action rewrites recorded evidence. Continue?")
@with_appcontext
def correct_vote_command(user_id: int, query_id: int, translation_id: int, rating: str) -> None:
    """Correct a mistaken immutable vote and rebuild its projections."""
    from app.services.vote_service import correct_vote

    correct_vote(user_id, query_id, translation_id, int(rating))
    click.echo("Vote corrected and ratings rebuilt.")


def register_commands(app) -> None:
    app.cli.add_command(init_db_command)
    app.cli.add_command(add_user_command)
    app.cli.add_command(remove_user_command)
    app.cli.add_command(list_users_command)
    app.cli.add_command(derive_elo_command)
    app.cli.add_command(rebuild_ratings_command)
    app.cli.add_command(correct_vote_command)
