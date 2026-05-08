from sqlalchemy import text

from app.core.database import engine


def ensure_schema_upgrades():
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS legal_name VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS email VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS phone VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS website VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS country VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS state VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS city VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS address_line1 VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS address_line2 VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS postal_code VARCHAR")
        )
        connection.execute(
            text(
                "ALTER TABLE companies "
                "ADD COLUMN IF NOT EXISTS timezone VARCHAR NOT NULL DEFAULT 'America/New_York'"
            )
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS use_work_schedules BOOLEAN NOT NULL DEFAULT FALSE")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active'")
        )
        connection.execute(
            text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS contact_type VARCHAR NOT NULL DEFAULT 'general'")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS position VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS email VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS phone VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT FALSE")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS notes VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE company_contacts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS timezone VARCHAR NOT NULL DEFAULT 'America/New_York'")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS country VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS state VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS city VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS address_line1 VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS address_line2 VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS postal_code VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS geo_radius_meters DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
        )
        connection.execute(
            text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS location_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS device_name VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS timezone VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active'")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE")
        )
        connection.execute(
            text("ALTER TABLE terminals ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
        )
        connection.execute(
            text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS qr_token VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS work_schedule_id INTEGER")
        )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS work_schedules ("
                "id SERIAL PRIMARY KEY, "
                "company_id INTEGER NOT NULL, "
                "name VARCHAR NOT NULL, "
                "shift_start VARCHAR NOT NULL DEFAULT '09:00', "
                "shift_end VARCHAR NOT NULL DEFAULT '17:00', "
                "lunch_start VARCHAR, "
                "lunch_end VARCHAR, "
                "breaks VARCHAR, "
                "workdays VARCHAR NOT NULL DEFAULT '0,1,2,3,4', "
                "is_default BOOLEAN NOT NULL DEFAULT FALSE, "
                "created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
                ")"
            )
        )
        connection.execute(
            text("ALTER TABLE work_schedules ADD COLUMN IF NOT EXISTS workdays VARCHAR NOT NULL DEFAULT '0,1,2,3,4'")
        )
        connection.execute(
            text("ALTER TABLE work_schedules ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS device_timezone VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS timezone_abbr VARCHAR")
        )
        connection.execute(
            text(
                "ALTER TABLE scan_logs "
                "ADD COLUMN IF NOT EXISTS scan_source VARCHAR NOT NULL DEFAULT 'terminal'"
            )
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS timezone_used VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS timezone_source VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS terminal_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS location_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS accuracy_meters DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE scan_logs ADD COLUMN IF NOT EXISTS geo_status VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS location_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS terminal_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR NOT NULL DEFAULT 'en'")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE")
        )
