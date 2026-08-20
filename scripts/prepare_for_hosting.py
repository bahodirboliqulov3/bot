import asyncio
import os
import shutil
from pathlib import Path
from sqlalchemy import text
from app.database.session import async_session_factory, engine


async def prepare():
    print("Preparing clean database while preserving users...")
    async with async_session_factory() as session:
        # Check user count before cleaning
        res = await session.execute(text("SELECT count(*) FROM users"))
        user_count = res.scalar()
        print(f"Preserving {user_count} registered users.")

        # Clean old tests, attempts, results, certificates, tickets
        await session.execute(text("DELETE FROM student_answers"))
        await session.execute(text("DELETE FROM test_attempts"))
        await session.execute(text("DELETE FROM certificates"))
        await session.execute(text("DELETE FROM results"))
        await session.execute(text("DELETE FROM test_questions"))
        await session.execute(text("DELETE FROM questions"))
        await session.execute(text("DELETE FROM tests"))
        await session.execute(text("DELETE FROM saved_tests"))
        await session.execute(text("DELETE FROM support_tickets"))
        await session.execute(text("DELETE FROM achievements"))
        await session.commit()

        # Vacuum database
        await session.execute(text("VACUUM"))
        print("Database vacuumed and cleaned!")

    # Clean storage folders
    storage_path = Path("storage")
    for sub in ["certificates", "exports", "uploads"]:
        folder = storage_path / sub
        if folder.exists():
            for item in folder.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"Error cleaning {item}: {e}")

    # Reset FSM storage
    fsm_file = storage_path / "data" / "fsm_storage.json"
    if fsm_file.exists():
        fsm_file.write_text("{}", encoding="utf-8")

    print("Storage cleaned successfully! Project is 100% fresh and hosting-ready.")

if __name__ == "__main__":
    asyncio.run(prepare())
