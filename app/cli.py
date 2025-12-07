from pathlib import Path

import click
from flask.cli import with_appcontext

from app.config import Config
from app.database import Base, db_session, engine
from app.models import User
from app.services.user_service import create_user, delete_user


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database with default users."""
    Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)

    print("Initializing database...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database schema checked/created successfully.")

    default_users = [
        {"username": "Hassaan", "password": "1234", "is_admin": True},
        {"username": "John", "password": "1234", "is_admin": False},
    ]

    user_count = db_session.query(User).count()
    if user_count == 0:
        print("No users found, creating default users...")
        for user_data in default_users:
            create_user(
                username=user_data["username"],
                password=user_data["password"],
                is_admin=user_data["is_admin"],
            )
        print("Default users created successfully!")
    else:
        print(f"{user_count} users already exist, skipping default user creation.")


@click.command("add-user")
@click.argument("username")
@click.argument("password")
@click.option("--admin", is_flag=True, help="Set user as admin")
@with_appcontext
def add_user_command(username, password, admin):
    """Add a new user."""
    try:
        create_user(username, password, is_admin=admin)
        click.echo(f"User '{username}' added successfully.")
    except Exception as e:
        click.echo(f"Error adding user: {e}")


@click.command("remove-user")
@click.argument("username")
@with_appcontext
def remove_user_command(username):
    """Remove a user."""
    if delete_user(username):
        click.echo(f"User '{username}' removed successfully.")
    else:
        click.echo(f"User '{username}' not found.")


@click.command("list-users")
@with_appcontext
def list_users_command():
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


def register_commands(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(add_user_command)
    app.cli.add_command(remove_user_command)
    app.cli.add_command(list_users_command)
