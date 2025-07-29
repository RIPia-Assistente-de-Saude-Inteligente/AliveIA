"""
Database connection and initialization for SQLite.
"""
import aiosqlite
import sqlite3
from pathlib import Path
from src.config.settings import DATABASE_PATH, DATABASE_SCHEMA_PATH
import asyncio
from typing import AsyncGenerator

class DatabaseManager:
    """Database manager for SQLite operations."""
    
    def __init__(self):
        self.database_path = DATABASE_PATH
        self.schema_path = DATABASE_SCHEMA_PATH
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Get async database connection."""
        conn = await aiosqlite.connect(self.database_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    async def initialize_database(self):
        """Initialize database with schema."""
        try:
            # Create database directory if it doesn't exist
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read schema file
            if self.schema_path.exists():
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # Execute schema
                conn = await self.get_connection()
                try:
                    await conn.executescript(schema_sql)
                    await conn.commit()
                    print(f"Database initialized successfully at {self.database_path}")
                finally:
                    await conn.close()
            else:
                print(f"Schema file not found at {self.schema_path}")
                
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
    
    def get_sync_connection(self) -> sqlite3.Connection:
        """Get synchronous database connection for non-async operations."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

# Global database manager instance
db_manager = DatabaseManager()

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency for getting database connection."""
    await db_manager.initialize_database() # Ensure schema is applied
    conn = await db_manager.get_connection()
    try:
        yield conn
    finally:
        await conn.close()

# Initialize database on module import
async def init_db():
    """Initialize database if needed."""
    if not DATABASE_PATH.exists():
        await db_manager.initialize_database()

# Run initialization
if __name__ == "__main__":
    asyncio.run(init_db())
