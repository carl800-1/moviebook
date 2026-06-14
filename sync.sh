#!/bin/bash
# Sync local project to NFS share
LOCAL_DIR="/Users/frank/projects/moviebook"
REMOTE_DIR="/Volumes/nfs/project/moviebook"

echo "Syncing to NFS..."
rsync -av --exclude='__pycache__' \
             --exclude='*.pyc' \
             --exclude='.git' \
             --exclude='.env' \
             --exclude='logs/*.log' \
             "$LOCAL_DIR/" "$REMOTE_DIR/"

echo "Done"
