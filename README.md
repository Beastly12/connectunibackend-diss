# connectunibackend-diss

## Local environment

Copy `.env.example` to `.env` and fill in local values. Keep `.env` out of Git.

Generate replacement secrets with commands like:

```bash
openssl rand -base64 48
```

## Secret leak remediation

If `.env` or another secret file was committed or pushed:

1. Rotate the exposed credentials in the provider dashboards first:
   - Cloudinary API key / API secret
   - SMTP password
   - JWT signing secret
   - database and pgAdmin passwords
2. Update deployment secrets in GitHub Actions, hosting dashboards, and local `.env` files.
3. Remove secret files from Git history with `git filter-repo` or BFG.
4. Force-push the cleaned history only after coordinating with anyone else using the repo.
5. Ask collaborators to re-clone or hard-reset to the cleaned history.
