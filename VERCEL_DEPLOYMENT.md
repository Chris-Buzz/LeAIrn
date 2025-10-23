# Vercel Deployment Guide with Firestore

This guide will help you deploy your AI Management System to Vercel with Firestore integration.

## Prerequisites

- Vercel account (free tier works fine)
- Firebase project with Firestore enabled
- Your Firebase service account credentials

## Step-by-Step Deployment

### 1. Install Vercel CLI (Optional)

```bash
npm install -g vercel
```

Or deploy via the Vercel website dashboard.

### 2. Prepare Environment Variables

You need to set up the following environment variables in Vercel. The most important one for Firestore is `FIREBASE_CREDENTIALS_BASE64`.

#### Get Your Base64-Encoded Credentials

You already have this value in your `.env` file! Copy the value from:

```
FIREBASE_CREDENTIALS_BASE64=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsC...
```

### 3. Set Environment Variables in Vercel

#### Option A: Via Vercel Dashboard (Recommended)

1. Go to https://vercel.com/dashboard
2. Select your project (or create a new one by importing from Git)
3. Go to **Settings** → **Environment Variables**
4. Add the following variables:

| Variable Name | Value | Environment |
|--------------|-------|-------------|
| `SECRET_KEY` | Your Flask secret key | Production, Preview, Development |
| `FLASK_ENV` | `production` | Production |
| `ADMIN1_USERNAME` | Your admin username | Production, Preview, Development |
| `ADMIN1_PASSWORD` | Your admin password | Production, Preview, Development |
| `ADMIN2_USERNAME` | Professor username | Production, Preview, Development |
| `ADMIN2_PASSWORD` | Professor password | Production, Preview, Development |
| `EMAIL_HOST` | `smtp.gmail.com` | Production, Preview, Development |
| `EMAIL_PORT` | `587` | Production, Preview, Development |
| `EMAIL_USER` | Your Gmail address | Production, Preview, Development |
| `EMAIL_PASSWORD` | Your Gmail app password | Production, Preview, Development |
| `EMAIL_FROM` | `LeAIrn <your-email@gmail.com>` | Production, Preview, Development |
| `EMAIL_RECIPIENT` | Your email address | Production, Preview, Development |
| `GEMINI_API_KEY` | Your Gemini API key | Production, Preview, Development |
| `FIREBASE_CREDENTIALS_BASE64` | Your base64-encoded Firebase credentials | Production, Preview, Development |

**IMPORTANT:** For `FIREBASE_CREDENTIALS_BASE64`, copy the entire base64 string from your `.env` file (it's very long, that's normal!).

#### Option B: Via Vercel CLI

```bash
vercel env add FIREBASE_CREDENTIALS_BASE64
# Paste your base64-encoded credentials when prompted

vercel env add SECRET_KEY
# Enter your secret key

# Repeat for all other environment variables...
```

### 4. Deploy to Vercel

#### Option A: Deploy via Git (Recommended)

1. **Initialize Git Repository** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Push to GitHub/GitLab/Bitbucket:**
   ```bash
   git remote add origin https://github.com/yourusername/your-repo.git
   git push -u origin main
   ```

3. **Connect to Vercel:**
   - Go to https://vercel.com/new
   - Import your repository
   - Vercel will auto-detect the configuration from `vercel.json`
   - Click **Deploy**

#### Option B: Deploy via Vercel CLI

```bash
cd "d:\Projects\AI Management System"
vercel
# Follow the prompts
```

### 5. Verify Deployment

After deployment, check the deployment logs:

1. Go to your Vercel dashboard
2. Click on your project
3. Go to the latest deployment
4. Check the **Function Logs** tab
5. Look for:
   ```
   OK: Using base64-encoded Firebase credentials
   OK: Firestore initialized successfully!
   ```

### 6. Test Your Application

1. Visit your Vercel URL (e.g., `https://your-app.vercel.app`)
2. Try logging in with your admin credentials
3. Check if bookings and time slots are working
4. Verify data is being stored in Firestore

## Troubleshooting

### Issue: "Firebase credentials not found"

**Solution:** Make sure you've set `FIREBASE_CREDENTIALS_BASE64` in Vercel environment variables and it's available in all environments (Production, Preview, Development).

### Issue: "Error initializing Firestore"

**Possible causes:**
1. Base64 credentials are malformed (check for line breaks or missing characters)
2. Firebase project doesn't have Firestore enabled
3. Service account doesn't have proper permissions

**Solution:**
- Verify your base64 string is complete and has no line breaks
- Enable Firestore in Firebase Console
- Check service account permissions in Firebase Console

### Issue: "Module not found: firebase_admin"

**Solution:** Ensure `firebase-admin==6.3.0` is in your `requirements.txt` file (it already is!).

### Issue: "Cold start is slow"

This is normal for Vercel's serverless functions. First request after inactivity will be slower. Consider upgrading to Vercel Pro for better performance.

## How It Works

### Local Development
- Uses `FIREBASE_CREDENTIALS_PATH` to load credentials from `firebase-credentials.json` file
- Fast and easy for development

### Production (Vercel)
- Uses `FIREBASE_CREDENTIALS_BASE64` environment variable
- No file system needed - perfect for serverless
- Credentials are securely stored in Vercel environment variables

### Automatic Fallback
- If Firestore fails to initialize, app falls back to JSON file storage
- Ensures your app keeps running even if there are credential issues

## Security Notes

1. **Never commit credentials to Git:**
   - `firebase-credentials.json` is already in `.gitignore`
   - `.env` is already in `.gitignore`

2. **Use environment variables:**
   - Always use Vercel's environment variables for sensitive data
   - Never hardcode credentials in your code

3. **Firestore Security Rules:**
   - Make sure your Firestore has proper security rules
   - Currently using Admin SDK which bypasses security rules (server-side only)

## Performance Tips

1. **Enable caching:**
   - Vercel automatically caches static assets
   - Consider implementing request caching for frequently accessed data

2. **Optimize Firestore queries:**
   - Use indexes for complex queries
   - Limit the number of documents fetched

3. **Monitor usage:**
   - Check Vercel dashboard for function execution times
   - Monitor Firebase usage in Firebase Console

## Need Help?

- Vercel Documentation: https://vercel.com/docs
- Firebase Documentation: https://firebase.google.com/docs
- Firestore Documentation: https://firebase.google.com/docs/firestore

## Next Steps

After successful deployment:

1. Set up custom domain (optional)
2. Configure Firestore security rules
3. Set up monitoring and alerts
4. Consider setting up CI/CD for automatic deployments
5. Back up your Firestore data regularly

---

**Your app is production-ready with Firestore!** 🚀
