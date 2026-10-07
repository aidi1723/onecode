#!/usr/bin/env bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [push-n100|pull-n100]"
    exit 1
fi

ACTION="$1"
REMOTE_HOST="n100"
REMOTE_WORKSPACE="~/onecode-linux-test"
LOCAL_WORKSPACE=$(pwd)

if [ "$ACTION" == "push-n100" ]; then
    echo "Synchronizing workspace to n100..."
    rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
          --exclude '.mypy_cache' --exclude '.ruff_cache' \
          --exclude 'node_modules' --exclude '.DS_Store' \
          "${LOCAL_WORKSPACE}/" "${REMOTE_HOST}:${REMOTE_WORKSPACE}/"

    echo "Synchronizing approval secret to n100..."
    ssh "${REMOTE_HOST}" "mkdir -p ~/.onecode && chmod 700 ~/.onecode"
    if [ -f ~/.onecode/approval-secret.key ]; then
        rsync -avz ~/.onecode/approval-secret.key "${REMOTE_HOST}:~/.onecode/approval-secret.key"
    else
        echo "No local approval-secret.key to sync."
    fi
    
    echo "Push complete. .onecode/pending-cycle/ is implicitly included in the workspace sync."
    
elif [ "$ACTION" == "pull-n100" ]; then
    echo "Synchronizing workspace from n100..."
    rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
          --exclude '.mypy_cache' --exclude '.ruff_cache' \
          --exclude 'node_modules' --exclude '.DS_Store' \
          "${REMOTE_HOST}:${REMOTE_WORKSPACE}/" "${LOCAL_WORKSPACE}/"

    echo "Synchronizing approval secret from n100..."
    mkdir -p ~/.onecode && chmod 700 ~/.onecode
    if ssh "${REMOTE_HOST}" "[ -f ~/.onecode/approval-secret.key ]"; then
        rsync -avz "${REMOTE_HOST}:~/.onecode/approval-secret.key" ~/.onecode/approval-secret.key
    else
        echo "No remote approval-secret.key to sync."
    fi
    
    echo "Pull complete. .onecode/pending-cycle/ is implicitly included in the workspace sync."
    
else
    echo "Unknown action: $ACTION. Use push-n100 or pull-n100."
    exit 1
fi
