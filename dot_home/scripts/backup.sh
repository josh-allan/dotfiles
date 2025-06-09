#!/bin/bash

BACKUP_DIR="/srv/backup/$HOSTNAME"
TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S')
HOSTNAME=$(hostname)
ARCHIVE_NAME="${HOSTNAME}_backup_${TIMESTAMP}.tar.gz"


## Make the backup dir if it doesn't already exist
if [ ! -d "${BACKUP_DIR}" ]; then
  sudo mkdir -p "${BACKUP_DIR}"
fi

sudo rsync -aAXHv --one-file-system \
  --exclude='/dev/*' \
  --exclude='/proc/*' \
  --exclude='/sys/*' \
  --exclude='/tmp/*' \
  --exclude='/run/*' \
  --exclude='/mnt/*' \
  --exclude='/media/*' \
  --exclude='**/node_modules' \
  --exclude='/lost+found/' \
  --exclude='/defvol/_active/.snapshots/' \
  --exclude='defvol/_active/.snapshots' / "${BACKUP_DIR}/rootfs"

sudo tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "${BACKUP_DIR}" rootfs


