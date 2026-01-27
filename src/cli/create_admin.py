#!/usr/bin/env python
"""CLI script to create the first admin user.

Usage:
    python -m src.cli.create_admin admin@example.com

This creates an admin user with a randomly generated password.
The password is printed to stdout - save it securely!

This script is idempotent - running it again with the same email
will do nothing if the user already exists.
"""

import asyncio
import sys
from uuid import uuid4

from sqlmodel import SQLModel

from src.domain.services.auth import hash_password, generate_temp_password
from src.storage.database import engine, async_session
from src.storage.models import User


async def create_first_admin(email: str) -> tuple[bool, str]:
    """Create the first admin user.

    Args:
        email: Email address for the admin account

    Returns:
        Tuple of (created: bool, message: str)
        - If created=True, message contains the temporary password
        - If created=False, message explains why (e.g., already exists)
    """
    # Ensure tables exist
    from src.storage import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as db:
        # Check if email already exists
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.is_superuser:
                return False, f"Admin user {email} already exists"
            else:
                # User exists but is not admin - upgrade them
                existing.is_superuser = True
                await db.commit()
                return False, f"User {email} upgraded to admin (password unchanged)"

        # Generate temp password (longer for first admin)
        temp_password = generate_temp_password(16)

        # Create admin user
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hash_password(temp_password),
            is_active=True,
            is_superuser=True,
            must_change_password=True,
            failed_login_attempts=0,
        )
        db.add(user)
        await db.commit()

        return True, temp_password


def main():
    """Main entry point for CLI."""
    if len(sys.argv) != 2:
        print("Usage: python -m src.cli.create_admin <email>")
        print("Example: python -m src.cli.create_admin admin@example.com")
        sys.exit(1)

    email = sys.argv[1]

    # Basic email validation
    if "@" not in email or "." not in email:
        print(f"Error: Invalid email address: {email}")
        sys.exit(1)

    print(f"Creating admin user: {email}")

    created, message = asyncio.run(create_first_admin(email))

    if created:
        print("\n" + "=" * 50)
        print("ADMIN USER CREATED SUCCESSFULLY")
        print("=" * 50)
        print(f"Email:    {email}")
        print(f"Password: {message}")
        print("=" * 50)
        print("\nIMPORTANT: Save this password securely!")
        print("You will be required to change it on first login.")
    else:
        print(f"\n{message}")


if __name__ == "__main__":
    main()
