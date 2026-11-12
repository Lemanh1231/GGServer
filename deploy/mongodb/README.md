# Authenticated local MongoDB (optional)

This creates a **new** dedicated database/volume. It does not restore or migrate
any existing players. Do not use this setup over an existing deployment or an
occupied port 27017. Java itself remains independent of Docker and Python.

From the checkout root, create separate local secrets:

```bash
mkdir -p deploy/mongodb/secrets
chmod 700 deploy/mongodb/secrets
openssl rand -hex 32 > deploy/mongodb/secrets/root_password
openssl rand -hex 32 > deploy/mongodb/secrets/app_password
chmod 444 deploy/mongodb/secrets/root_password deploy/mongodb/secrets/app_password
docker compose -f deploy/mongodb/compose.yaml up -d --wait
```

The host directory is private (0700). Files are readable inside the read-only
secret mounts for the MongoDB container user. **Never commit these files**.
Use a different secure secret-management method on shared/containerized hosts.

MongoDB listens on `127.0.0.1:27017` only, with authentication. The application
user `ggserver_app` has only `readWrite` on `ggserver`. Set your private Java config
to backend `mongo` / name `ggserver`, then provide its connection without printing
the secret (the generated password is hexadecimal and safe in a URI):

```bash
export GG_MONGO_URI="mongodb://ggserver_app:$(cat deploy/mongodb/secrets/app_password)@127.0.0.1:27017/ggserver?authSource=ggserver"
```

Do not pass the root credentials to Java. Initialization only runs for a fresh
volume; replacing a secret file does not rotate an existing MongoDB password.
Use MongoDB's authenticated administration procedure for rotation.

```bash
docker compose -f deploy/mongodb/compose.yaml ps
docker compose -f deploy/mongodb/compose.yaml stop
```

Never delete the named volume or use `down -v` to repair connectivity. Back up
**all collections** and keep credentials securely backed up separately. This is
standalone MongoDB: stop every writer before a consistent cross-collection dump
or restore. Test restores on a separate database before changing a live server.
