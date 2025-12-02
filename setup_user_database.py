"""
Database Schema Setup for Multi-User Dashboard

This script creates the necessary tables for:
1. User accounts (Discord OAuth)
2. MT5 account linking
3. User-specific partial exit strategies
"""

import sqlite3
import os
from datetime import datetime

def create_user_tables(db_path="telegram_messages.db"):
    """Create user management tables"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table - stores Discord user information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT UNIQUE NOT NULL,
            discord_username TEXT NOT NULL,
            discord_avatar TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # MT5 Accounts table - links MT5 accounts to users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mt5_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_number TEXT NOT NULL,
            account_name TEXT,
            broker TEXT,
            server TEXT,
            is_primary BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sync TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, account_number)
        )
    ''')
    
    # User Strategies table - stores custom partial exit strategies per user
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            strategy_name TEXT NOT NULL,
            tp1_percent INTEGER NOT NULL DEFAULT 50,
            tp2_percent INTEGER NOT NULL DEFAULT 20,
            tp3_percent INTEGER NOT NULL DEFAULT 10,
            tp4_percent INTEGER NOT NULL DEFAULT 10,
            tp5_percent INTEGER NOT NULL DEFAULT 10,
            tp6_percent INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (tp1_percent + tp2_percent + tp3_percent + tp4_percent + tp5_percent + tp6_percent = 100)
        )
    ''')
    
    # Sessions table - for managing user sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mt5_accounts_user_id ON mt5_accounts(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mt5_accounts_account_number ON mt5_accounts(account_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)')
    
    conn.commit()
    conn.close()
    
    print("✅ User management tables created successfully!")
    print("\nTables created:")
    print("  - users: Discord user accounts")
    print("  - mt5_accounts: MT5 account linkage")
    print("  - user_strategies: Custom partial exit strategies")
    print("  - sessions: User session management")


def add_sample_data(db_path="telegram_messages.db"):
    """Add sample data for testing (optional)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add a test user
    cursor.execute('''
        INSERT OR IGNORE INTO users (discord_id, discord_username, discord_avatar, email)
        VALUES (?, ?, ?, ?)
    ''', ('123456789', 'TestUser', None, 'test@example.com'))
    
    user_id = cursor.lastrowid or cursor.execute('SELECT id FROM users WHERE discord_id = ?', ('123456789',)).fetchone()[0]
    
    # Add test MT5 account
    cursor.execute('''
        INSERT OR IGNORE INTO mt5_accounts (user_id, account_number, account_name, broker, server, is_primary)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, '11060034', 'Demo Account', 'Exness', 'ExnessDemo-MT5', 1))
    
    # Add default strategy
    cursor.execute('''
        INSERT OR IGNORE INTO user_strategies (
            user_id, strategy_name, 
            tp1_percent, tp2_percent, tp3_percent, tp4_percent, tp5_percent, tp6_percent,
            is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, 'Default Strategy', 50, 20, 10, 10, 10, 0, 1))
    
    conn.commit()
    conn.close()
    
    print("\n✅ Sample data added for testing!")


if __name__ == "__main__":
    print("="*70)
    print("Setting up Multi-User Dashboard Database")
    print("="*70)
    print()
    
    # Check if database exists
    db_path = "telegram_messages.db"
    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}")
        print("Creating new database...")
    
    # Create tables
    create_user_tables(db_path)
    
    # Ask if user wants sample data
    print("\n" + "="*70)
    print("Setup complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Set up Discord OAuth application")
    print("2. Configure environment variables")
    print("3. Deploy to Railway")
    print("4. Test authentication flow")
