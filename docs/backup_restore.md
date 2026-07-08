# QB Tracker Backup And Restore

This document is for the production server. Current default server path:

```bash
/srv/qbtracker
```

## Manual Backup

Run this on the production server:

```bash
cd /srv/qbtracker
chmod +x scripts/qbtracker_backup.sh
APP_DIR=/srv/qbtracker BACKUP_DIR=/srv/backups/qbtracker ./scripts/qbtracker_backup.sh
```

The script creates:

```bash
/srv/backups/qbtracker/qbtracker_db_<timestamp>.sql.gz
/srv/backups/qbtracker/qbtracker_files_<timestamp>.tar.gz
/srv/backups/qbtracker/qbtracker_manifest_<timestamp>.txt
```

The database backup comes from `DATABASE_URL` in `/srv/qbtracker/.env`.

## Automatic Daily Backup

Open root cron:

```bash
crontab -e
```

Add:

```bash
15 3 * * * cd /srv/qbtracker && APP_DIR=/srv/qbtracker BACKUP_DIR=/srv/backups/qbtracker /srv/qbtracker/scripts/qbtracker_backup.sh >> /var/log/qbtracker-backup.log 2>&1
```

This runs every day at 03:15 server time and keeps backups for 30 days by default.

## Check Backups

```bash
ls -lh /srv/backups/qbtracker
tail -100 /var/log/qbtracker-backup.log
```

## Restore To A Test Database First

Use this before restoring production data:

```bash
createdb qbtracker_restore_test
gunzip -c /srv/backups/qbtracker/qbtracker_db_<timestamp>.sql.gz | psql "postgresql://postgres:YOUR_PASSWORD@localhost:5432/qbtracker_restore_test"
```

Then inspect the restored test database.

## Production Restore

Only do this when you intentionally want to replace production data.

```bash
cd /srv/qbtracker
systemctl stop qbtracker.service
source .env
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c /srv/backups/qbtracker/qbtracker_db_<timestamp>.sql.gz | psql "$DATABASE_URL"
systemctl start qbtracker.service
systemctl status qbtracker.service --no-pager
```

## Restore Uploads

Extract files to a temporary directory first:

```bash
mkdir -p /tmp/qbtracker_restore_files
tar -xzf /srv/backups/qbtracker/qbtracker_files_<timestamp>.tar.gz -C /tmp/qbtracker_restore_files
```

Restore uploads:

```bash
cp -a /tmp/qbtracker_restore_files/uploads/. /srv/qbtracker/uploads/
```

Do not overwrite `/srv/qbtracker/.env` blindly. Compare it manually first.

## Good Pre-Deploy Habit

Before a risky deploy:

```bash
cd /srv/qbtracker
APP_DIR=/srv/qbtracker BACKUP_DIR=/srv/backups/qbtracker ./scripts/qbtracker_backup.sh
./deploy.sh
journalctl -u qbtracker.service --since "10 minutes ago" -p warning --no-pager
```
