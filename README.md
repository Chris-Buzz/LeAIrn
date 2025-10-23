# 🎓 AI Mentor Hub - LeAIrn Booking System

A professional AI learning session booking system built with Flask and Firestore.

## ✨ Features

- 📅 **Smart Scheduling** - Book AI mentoring sessions with Christopher Buzaid
- 🔥 **Cloud Database** - Firestore integration for reliable data storage
- 👥 **Multiple Admins** - Support for student and professor accounts
- 🎨 **Dark Mode** - Beautiful dark theme by default
- 🤖 **AI Insights** - Gemini AI-powered student assessments
- 📧 **Email Confirmations** - Automatic booking confirmations
- 📊 **Admin Dashboard** - Manage bookings and time slots
- 🚀 **Production Ready** - Optimized for Vercel deployment

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Firestore

Follow [FIRESTORE_SETUP.md](FIRESTORE_SETUP.md) to:
- Create Firebase project
- Download credentials
- Save as `firebase-credentials.json`

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```env
# Your credentials
ADMIN1_USERNAME=yourUsername
ADMIN1_PASSWORD=YourSecurePassword

ADMIN2_USERNAME=professorsUsername
ADMIN2_PASSWORD=ProfessorPassword

EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password

GEMINI_API_KEY=your-gemini-api-key

FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

### 4. Run the App

```bash
python app.py
```

Visit: **http://localhost:5000**

---

## 👥 Admin Accounts

Two admin accounts are configured:

| Account | Default Username | Default Password |
|---------|------------------|------------------|
| **You** | `username` | `ChangeThisPassword123!` |
| **Professor** | `professor` | `ProfessorPassword123!` |

**⚠️ Change these passwords in `.env` before deploying!**

**Admin Dashboard:** http://localhost:5000/admin

---

## 📁 Project Structure

```
AI Management System/
├── app.py                    # Main Flask application
├── firestore_db.py          # Firestore database module
├── requirements.txt          # Python dependencies
├── vercel.json              # Vercel deployment config
├── .env                     # Your environment variables (not in git)
├── .env.example             # Template for environment variables
├── .gitignore               # Git ignore rules
├── firebase-credentials.json # Firestore credentials (not in git)
│
├── templates/               # HTML templates
│   ├── index.html          # Main booking page
│   ├── admin.html          # Admin dashboard
│   └── admin_login.html    # Admin login page
│
├── static/                  # Static assets
│   ├── style.css           # Main stylesheet
│   └── script.js           # Frontend JavaScript
│
├── backup/                  # Old/backup files
│
└── docs/                    # Documentation
    ├── FIRESTORE_SETUP.md
    ├── ADMIN_ACCOUNTS.md
    ├── QUICK_START.md
    ├── README_DEPLOYMENT.md
    └── UPDATES_SUMMARY.md
```

---

## 🔧 Admin Features

### Manage Time Slots

**Generate Recurring Slots** (Purple Button):
- Automatically creates weekly schedule:
  - **Tuesday:** 11:00 AM, 12:00 PM, 1:00 PM
  - **Wednesday:** 2:00 PM, 3:00 PM
  - **Thursday:** 12:00 PM, 1:00 PM
  - **Friday:** 11:00 AM, 12:00 PM, 1:00 PM
- Choose 1-52 weeks ahead
- Auto-skips duplicates

**Add Single Slot** (Green Button):
- Add one-off special sessions

**Delete Slot**:
- Remove unbooked slots (booked slots protected)

### View Bookings

- See all student bookings
- Generate AI insights with Gemini
- Export to CSV
- Edit or delete bookings

---

## 🚀 Deploy to Vercel

See [README_DEPLOYMENT.md](docs/README_DEPLOYMENT.md) for complete deployment guide.

**Quick deploy:**

```bash
vercel
```

**Set environment variables in Vercel Dashboard:**
- All variables from `.env`
- Convert `firebase-credentials.json` to base64 or JSON string

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [FIRESTORE_SETUP.md](docs/FIRESTORE_SETUP.md) | Set up Firebase/Firestore |
| [ADMIN_ACCOUNTS.md](docs/ADMIN_ACCOUNTS.md) | Manage admin accounts |
| [QUICK_START.md](docs/QUICK_START.md) | Fast setup guide |
| [README_DEPLOYMENT.md](docs/README_DEPLOYMENT.md) | Deploy to Vercel |
| [UPDATES_SUMMARY.md](docs/UPDATES_SUMMARY.md) | Latest changes |

---

## 🔐 Security

- ✅ Passwords in environment variables
- ✅ Firestore credentials not in git
- ✅ Session-based authentication
- ✅ Production-ready security rules
- ✅ Gmail app passwords (not regular passwords)

---

## 🎯 Future Integration

This booking system is designed to integrate with the full **LeAIrn** AI learning platform:
- Shared Firestore database
- Unified user management
- Integrated scheduling
- Cross-platform AI insights

---

## 🆘 Support

**Questions?** Check the documentation or contact:
- Email: cjpbuzaid@gmail.com

---

## 📝 License

Built for educational purposes at [Your University].

**Powered by:**
- Flask (Python web framework)
- Firestore (Cloud database)
- Google Gemini AI (Insights generation)
- Vercel (Hosting)

---

**Made with ❤️ for AI education**
