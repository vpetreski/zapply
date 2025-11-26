# GitHub Secrets Setup - Quick Guide

Follow these steps to configure GitHub secrets for automated deployment.

## Step 1: Get the SSH Private Key

The SSH private key has been generated at: `.github-deploy-key`

Copy its content:

```bash
cat .github-deploy-key
```

You should see output like:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAA...
(many lines)
...AAAAGmdpdGh1Yi1hY3Rpb25zLWRlcGxveQEC
-----END OPENSSH PRIVATE KEY-----
```

**Copy the ENTIRE output** (including BEGIN and END lines).

## Step 2: Add to GitHub Repository

1. Go to your GitHub repository: https://github.com/vpetreski/zapply

2. Click on **Settings** (top menu, far right)

3. In the left sidebar, click **Secrets and variables** → **Actions**

4. Click the **New repository secret** button (green button, top right)

5. Fill in:
   - **Name**: `NAS_SSH_KEY`
   - **Secret**: Paste the ENTIRE private key you copied in Step 1

6. Click **Add secret**

## Step 3: Verify Setup

After adding the secret, you should see:

- `NAS_SSH_KEY` listed in Repository secrets
- Shows "Updated X seconds ago"

**That's it!** GitHub Actions will now be able to deploy to your NAS.

## What This Key Does

- Allows GitHub Actions to SSH into your NAS (192.168.0.188)
- Copies deployment files
- Runs the deployment script
- Restarts services with new Docker images

## Security Notes

- ✅ Private key is stored securely in GitHub (encrypted)
- ✅ Public key has been added to your NAS `~/.ssh/authorized_keys`
- ✅ Private key is in `.gitignore` (won't be committed to repo)
- ✅ Key is only used for deployment automation

## Troubleshooting

### "Secret already exists" error
If you see this error, the secret is already added. You can:
- Click on the existing secret to update it
- Or delete and re-add it

### Deployment fails with "Permission denied (publickey)"
- Verify you copied the ENTIRE private key (including BEGIN/END lines)
- Check for no extra whitespace or characters
- Try re-adding the secret

### Can't find Settings tab
Make sure you're:
- On the repository page (not your profile)
- Logged in as repository owner or have admin access

## Next Steps

Once this is complete, you're ready for automated deployments!

Next: Implement authentication (see DEPLOYMENT.md Security section)

---

**Questions?** Check DEPLOYMENT.md for full deployment guide.
