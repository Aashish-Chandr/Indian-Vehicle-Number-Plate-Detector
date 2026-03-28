# Quick Start: Deploy to Vercel in 5 Minutes

## Prerequisites
- GitHub account with repository access
- Vercel account (free at https://vercel.com)

## Step 1: Commit Your Changes (1 minute)
```bash
cd /path/to/Indian-Vehicle-Number-Plate-Detector
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

## Step 2: Go to Vercel Dashboard (1 minute)
1. Visit https://vercel.com/dashboard
2. Click **"Add New..."** → **"Project"**
3. Click **"Import Git Repository"**
4. Search for: **Indian-Vehicle-Number-Plate-Detector**
5. Click **"Import"**

## Step 3: Configure Environment Variables (2 minutes)
In the "Configure Project" section, add these environment variables:

| Variable | Value | Required |
|----------|-------|----------|
| `FLASK_ENV` | `production` | ✅ Yes |
| `FLASK_DEBUG` | `0` | ✅ Yes |
| `SESSION_SECRET` | Any random string | ✅ Yes |
| `KAGGLE_USERNAME` | Your Kaggle username | ❌ Optional |
| `KAGGLE_KEY` | Your Kaggle API key | ❌ Optional |

## Step 4: Deploy! (1 minute)
1. Click **"Deploy"** button
2. Wait for build to complete (3-5 minutes)
3. Your app is live at: **https://your-app.vercel.app**

---

## What Gets Deployed

✅ Flask web application  
✅ Number plate detection models  
✅ OCR text recognition  
✅ Maharashtra plate detector  
✅ Static files and templates  
✅ All Python dependencies  

## After Deployment

### Test Your App
Visit: `https://your-app.vercel.app/`

### Common Operations

**View Deployment Logs**
- Dashboard → Select your project → Deployments → Click deployment → Logs

**Set Custom Domain**
- Settings → Domains → Add custom domain

**Update Environment Variables**
- Settings → Environment Variables → Edit

**Disable Auto-Deploy**
- Settings → Git → Turn off auto-deploy

## Troubleshooting

### Build Fails
→ Check build logs in Deployments tab
→ Verify all dependencies in requirements.txt

### App Crashes After Deploy
→ Check function logs in Deployments → Runtime Logs
→ Verify SESSION_SECRET is set

### Image Upload Not Working
→ Ensure uploads are under 5MB
→ Check /tmp directory permissions

### Can't Find My Deployment
→ Check if it's in the Deployments tab
→ Look for Failed deployments

## Environment Variables Cheat Sheet

```env
# Required
FLASK_ENV=production
FLASK_DEBUG=0
SESSION_SECRET=your-random-secret-string

# Optional (for Kaggle dataset download)
KAGGLE_USERNAME=your-username
KAGGLE_KEY=your-api-key
```

Generate SESSION_SECRET:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Vercel Limits (Free Tier)

| Limit | Value |
|-------|-------|
| Execution Time | 60 seconds |
| Memory | 3GB |
| Cold Start | ~2-5 seconds |
| File Upload | 5MB |

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| `Import Error` | Ensure all packages are in requirements.txt |
| `Timeout` | Reduce image size or optimize processing |
| `File not found` | Check paths are relative to project root |
| `Out of memory` | Upload smaller images (under 5MB) |

## Next Steps

1. ✅ Deploy to Vercel
2. 📧 Add custom domain (optional)
3. 🔐 Set up environment variables
4. 📊 Enable analytics (optional)
5. 🚀 Share your deployment URL!

## Useful Links

- 📖 [Full Deployment Guide](./DEPLOYMENT.md)
- 🔧 [Vercel Documentation](https://vercel.com/docs)
- 🐍 [Flask Documentation](https://flask.palletsprojects.com)
- 📦 [Project README](./README.md)

---

**Questions?** Check the [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed troubleshooting.

**Deployed successfully?** 🎉 Share your app with the world!
