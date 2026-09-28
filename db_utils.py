"""
Database startup helpers.

These functions keep MySQL validation and friendly failure messages in one
place so run.py and seed_data.py behave consistently.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.schema import CreateColumn
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app import db


def get_database_url_info(database_uri):
    """Return parsed and masked SQLAlchemy database URI details."""
    url = make_url(database_uri)
    return {
        "driver": url.drivername,
        "username": url.username or "",
        "host": url.host or "localhost",
        "port": url.port,
        "database": url.database or "",
        "masked_uri": url.render_as_string(hide_password=True),
    }


def validate_sqlalchemy_uri(database_uri):
    """Validate the configured SQLAlchemy URI before connecting."""
    try:
        info = get_database_url_info(database_uri)
    except Exception as exc:
        raise RuntimeError(f"Invalid SQLALCHEMY_DATABASE_URI: {exc}") from exc

    if info["driver"].startswith("mysql"):
        if info["driver"] != "mysql+pymysql":
            raise RuntimeError(
                "Use the PyMySQL SQLAlchemy driver for this project: "
                "mysql+pymysql://user:password@host:3306/database"
            )
        if not info["database"]:
            raise RuntimeError("DB_NAME is missing from the MySQL connection URI.")

    return info


def create_database_sql(database_name):
    """Generate SQL for creating the configured MySQL database."""
    escaped_name = database_name.replace("`", "``")
    return (
        f"CREATE DATABASE IF NOT EXISTS `{escaped_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )


def assert_database_ready(app):
    """Validate config and perform a lightweight database connection check."""
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    info = validate_sqlalchemy_uri(database_uri)
    info["created_database"] = False

    if info["driver"].startswith("sqlite"):
        return info

    try:
        with app.app_context():
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        if _get_operational_error_code(exc) == 1049 and info["driver"].startswith("mysql"):
            _create_missing_mysql_database(database_uri, info)
            info["created_database"] = True
            with app.app_context():
                with db.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            return info

        raise RuntimeError(format_database_error(exc, info)) from exc
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database startup check failed.\n"
            f"Configured URI: {info['masked_uri']}\n"
            f"SQLAlchemy error: {exc}"
        ) from exc

    return info


def synchronize_existing_schema(app):
    """
    Add model columns that are missing from an existing development database.

    SQLAlchemy's create_all() creates missing tables but intentionally does not
    alter existing tables. This project began as an auth/dashboard scaffold, so
    local databases may have an older employees table without HRMS columns.
    """
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql"):
        return []

    changes = []
    with app.app_context():
        from app.models import Employee, User

        models = [Employee, User]
        with db.engine.begin() as connection:
            for model in models:
                table = model.__table__
                existing_columns = {
                    row["COLUMN_NAME"]
                    for row in connection.execute(
                        text(
                            """
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = DATABASE()
                              AND TABLE_NAME = :table_name
                            """
                        ),
                        {"table_name": table.name},
                    ).mappings()
                }
                for column in table.columns:
                    if column.name in existing_columns:
                        continue
                    ddl = str(CreateColumn(column).compile(dialect=db.engine.dialect))
                    connection.execute(text(f"ALTER TABLE `{table.name}` ADD COLUMN {ddl}"))
                    changes.append(f"{table.name}.{column.name}")
    return changes


def _create_missing_mysql_database(database_uri, info):
    """Create the configured database by connecting to the MySQL server."""
    server_url = make_url(database_uri).set(database="mysql")
    engine = create_engine(server_url)

    try:
        with engine.begin() as connection:
            connection.execute(text(create_database_sql(info["database"])))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "MySQL accepted the credentials, but the configured database is missing "
            "and could not be created automatically.\n"
            f"Configured URI: {info['masked_uri']}\n"
            "Run this SQL manually with a privileged MySQL account:\n"
            f"{create_database_sql(info['database'])}\n"
            f"Create attempt failed with: {exc}"
        ) from exc
    finally:
        engine.dispose()


def _get_operational_error_code(exc):
    original = getattr(exc, "orig", None)
    if original is not None and getattr(original, "args", None):
        return original.args[0]
    return None


def format_database_error(exc, info):
    """Convert common MySQL connection failures into actionable messages."""
    code = None
    message = str(exc)

    original = getattr(exc, "orig", None)
    code = _get_operational_error_code(exc)
    if original is not None and getattr(original, "args", None):
        if len(original.args) > 1:
            message = original.args[1]

    base = [
        "Database startup check failed.",
        f"Configured URI: {info['masked_uri']}",
    ]

    if code == 1045:
        base.extend(
            [
                "MySQL rejected the username or password.",
                "Fix .env so DB_USER and DB_PASSWORD match your local MySQL account.",
                "If the password contains special characters, keep it in DB_PASSWORD; config.py URL-encodes it safely.",
            ]
        )
    elif code == 1049:
        base.extend(
            [
                f"MySQL database '{info['database']}' does not exist.",
                "Create it with:",
                create_database_sql(info["database"]),
            ]
        )
    elif code in {2003, 2005}:
        base.extend(
            [
                "MySQL is not reachable at the configured host/port.",
                "Start MySQL and check DB_HOST and DB_PORT in .env.",
            ]
        )
    else:
        base.append(f"MySQL error: {message}")

    return "\n".join(base)
