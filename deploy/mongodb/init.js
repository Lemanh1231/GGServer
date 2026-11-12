// First initialization of a NEW volume only; never changes existing accounts.
const password = require('fs').readFileSync('/run/secrets/app_password', 'utf8').trim();
db.getSiblingDB('ggserver').createUser({
    user: 'ggserver_app',
    pwd: password,
    roles: [{role: 'readWrite', db: 'ggserver'}]
});
