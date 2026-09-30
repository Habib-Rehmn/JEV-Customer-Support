"""Create a support user.

    docker compose exec backend python -m scripts.create_user --name "Admin" --email admin@example.com --role ADMIN

The password is prompted for (or pass --password).
"""
import argparse
import asyncio
import getpass

from pydantic import ValidationError

from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.schemas.auth import UserCreate
from app.services.auth_service import AuthService, EmailTaken


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=[r.value for r in UserRole], default=UserRole.AGENT.value)
    parser.add_argument("--password")
    args = parser.parse_args()
    password = args.password or getpass.getpass("Password (min 8 chars): ")

    try:
        data = UserCreate(name=args.name, email=args.email, password=password, role=args.role)
    except ValidationError as exc:
        raise SystemExit("\n".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()))
    async with SessionLocal() as session:
        try:
            user = await AuthService(session).create_user(data)
        except EmailTaken:
            raise SystemExit(f"User {args.email} already exists")
    print(f"Created {user.role} user #{user.id} <{user.email}>")


if __name__ == "__main__":
    asyncio.run(main())
