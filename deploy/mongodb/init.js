// Runs only on first initialization of this dedicated volume.
const password = require('fs').readFileSync('/run/secrets/app_password', 'utf8').trim();
db.getSiblingDB('ggserver').createUser({
    user: 'ggserver_app',
    pwd: password,
    roles: [{role: 'readWrite', db: 'ggserver'}]
});
