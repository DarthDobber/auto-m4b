#!/bin/bash
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Starting auto-m4b with PUID=$PUID, PGID=$PGID"

# Create group if it doesn't exist
if ! getent group $PGID > /dev/null 2>&1; then
    echo "Creating group with GID $PGID"
    groupadd -g $PGID autom4b
else
    GROUP_NAME=$(getent group $PGID | cut -d: -f1)
    echo "Group $GROUP_NAME (GID $PGID) already exists"
fi

# Create user if it doesn't exist
if ! getent passwd $PUID > /dev/null 2>&1; then
    echo "Creating user with UID $PUID"
    useradd -u $PUID -g $PGID -m -s /bin/bash autom4b
else
    USER_NAME=$(getent passwd $PUID | cut -d: -f1)
    echo "User $USER_NAME (UID $PUID) already exists"
fi

# Fix ownership of app directory
echo "Setting ownership of /auto-m4b to $PUID:$PGID"
chown -R $PUID:$PGID /auto-m4b

# Get the actual username for the PUID
USERNAME=$(getent passwd $PUID | cut -d: -f1)

echo "Executing command as user $USERNAME (UID $PUID)"
# Run the app as the created user
exec gosu $USERNAME "$@"
