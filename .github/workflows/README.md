# Smart Municipality Complaint Management System (SMCMS)

Flask + SQLite web app jisme citizens complaint darj karte hain aur email
notifications (registration confirmation + status updates) unke email pe
automatically jaati hain — phone pe Gmail/Outlook app khula ho toh turant dikh jaati hai.

## Features
- User Register/Login (password hashed, secure via Werkzeug)
- Complaint filing form (category, location, description)
- Instant confirmation email on complaint submission
- Admin panel to change complaint status (Pending → In Progress → Resolved)
- Automatic email to citizen on every status change
- Status tracking dashboard

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure email (Gmail example)**
   - Google Account → Security → 2-Step Verification ON karo
   - "App Passwords" section se ek app password generate karo
   - Environment variables set karo (ya seedha `app.py` mein edit karo):
   ```bash
   export MAIL_USERNAME="youraddress@gmail.com"
   export MAIL_PASSWORD="your-16-digit-app-password"
   export ADMIN_EMAIL="municipality-office@gmail.com"
   export SECRET_KEY="any-random-secret-string"
   ```

3. **Run the app**
   ```bash
   python app.py
   ```
   App `http://127.0.0.1:5000` pe chalega.

4. **Default admin login** (first run pe auto-create hota hai)
   - Email: value of `ADMIN_EMAIL` (default `admin@example.com`)
   - Password: `admin123` (login ke baad change kar lena — production mein
     change-password feature add karna recommended hai)

## Project Structure
```
municipal-complaint-portal/
├── app.py                  # Main Flask app (routes, models, email logic)
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── new_complaint.html
│   ├── complaint_detail.html
│   └── admin.html
└── static/
    └── style.css
```

## Deployment
Ye Flask app easily deploy ho sakta hai:
- **Render** ya **Railway** — free tier pe Flask + SQLite ke liye best (background worker/DB persist rehta hai)
- **Vercel** — serverless hai, isliye SQLite persist nahi hoga; agar Vercel use karna hai toh DB ko PostgreSQL (e.g. Supabase/Neon) mein switch karna padega
- Environment variables (`MAIL_USERNAME`, `MAIL_PASSWORD`, `ADMIN_EMAIL`, `SECRET_KEY`) hosting platform ke dashboard mein set karna na bhoolna

## Possible Extensions
- Photo upload with complaint (Flask + `werkzeug.utils.secure_filename`)
- SMS notification via Twilio (email ke saath)
- Complaint upvoting (agar multiple log same issue report karein)
- Map integration (Google Maps API) location select karne ke liye
