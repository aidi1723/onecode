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
    echo "Synchronizing approval secret to n100..."
    ssh "${REMOTE_HOST}" "mkdir -p ~/.onecode && chmod 700 ~/.onecode"
    if [ -f ~/.onecode/approval-secret.key ]; then
        rsync -avz ~/.onecode/approval-secret.key "${REMOTE_HOST}:~/.onecode/approval-secret.key"
    else
        echo "No local approval-secret.key to sync."
    fi
    
    echo "Synchronizing pending approvals to n100..."
    if [ -d "${LOCAL_WORKSPACE}/.onecode/pending-cycle" ]; then
        ssh "${REMOTE_HOST}" "mkdir -p ${REMOTE_WORKSPACE}/.onecode"
        rsync -avz "${LOCAL_WORKSPACE}/.onecode/pending-cycle/" "${REMOTE_HOST}:${REMOTE_WORKSPACE}/.onecode/pending-cycle/"
    else
        echo "No local pending approvals to sync."
    fi
    
    echo "Push complete."
    
elif [ "$ACTION" == "pull-n100" ]; then
    echo "Synchronizing approval secret from n100..."
    mkdir -p ~/.onecode && chmod 700 ~/.onecode
    if ssh "${REMOTE_HOST}" "[ -f ~/.onecode/approval-secret.key ]"; then
        rsync -avz "${REMOTE_HOST}:~/.onecode/approval-secret.key" ~/.onecode/approval-secret.key
    else
        echo "No remote approval-secret.key to sync."
    fi
    
    echo "Synchronizing pending approvals from n100..."
    if ssh "${REMOTE_HOST}" "[ -d ${REMOTE_WORKSPACE}/.onecode/pending-cycle ]"; then
        mkdir -p "${LOCAL_WORKSPACE}/.onecode"
        rsync -avz "${REMOTE_HOST}:${REMOTE_WORKSPACE}/.onecode/pending-cycle/" "${LOCAL_WORKSPACE}/.onecode/pending-cycle/"
    else
        echo "No remote pending approvals to sync."
    fi
    
    echo "Pull complete."
    
else
    echo "Unknown action: $ACTION. Use push-n100 or pull-n100."
    exit 1
fi
