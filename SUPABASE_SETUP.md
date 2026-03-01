# Supabase Setup Guide for Flask Voting System

## 🎯 Connect Your App to Supabase

### **Step 1: Create Supabase Project**

1. Go to: **https://supabase.com**
2. Click **"Start your project"**
3. Sign in with **GitHub**
4. Click **"New Project"**
5. Fill in:
   - **Name:** `voting-system`
   - **Database Password:** (save this!)
   - **Region:** Choose closest to you
   - **Pricing Plan:** Free
6. Click **"Create new project"**
7. Wait 2-3 minutes for setup

---

### **Step 2: Get Database Connection String**

1. In Supabase dashboard, go to **Settings** (bottom left)
2. Click **"Database"**
3. Scroll to **"Connection string"**
4. Select **"URI"** tab
5. Copy the connection string:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your actual database password

---

### **Step 3: Add to Local Environment**

Create/update `.env` file in your project:

```env
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres
```

---

### **Step 4: Install PostgreSQL Driver**

I've already updated your `requirements.txt`, now install:

```bash
pip install psycopg2-binary
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

---

### **Step 5: Initialize Database Tables**

Create a script to set up your tables:

```python
# init_supabase_db.py
from app import app, db

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("✅ Database tables created successfully!")
    
    # Optional: Create default admin
    from app import Admin
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            email='admin@voting.com',
            role='admin'
        )
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created!")
        print("   Username: admin")
        print("   Password: Admin@123")
```

Run it:

```bash
python init_supabase_db.py
```

---

### **Step 6: Test Connection Locally**

```bash
python app.py
```

Visit: **http://localhost:5000**

If it works, you're connected to Supabase! 🎉

---

### **Step 7: Deploy to Vercel**

#### **Via Vercel Dashboard:**

1. Go to: **https://vercel.com**
2. Import your project
3. Add **Environment Variable**:
   - **Key:** `DATABASE_URL`
   - **Value:** Your Supabase connection string
   - **Key:** `SECRET_KEY`
   - **Value:** Your secret key
4. Click **"Deploy"**

#### **Via CLI:**

```bash
vercel env add DATABASE_URL
# Paste your Supabase connection string

vercel env add SECRET_KEY
# Enter your secret key

vercel --prod
```

---

## 📊 View Your Database

### **Using Supabase Dashboard:**

1. Go to **Table Editor** in Supabase
2. You'll see your tables:
   - `admins`
   - `voters`
   - `elections`
   - `candidates`
   - `votes`

### **Run SQL Queries:**

In Supabase, go to **SQL Editor** and run:

```sql
-- View all admins
SELECT * FROM admins;

-- View all elections
SELECT * FROM elections;

-- Count total votes
SELECT COUNT(*) FROM votes;
```

---

## 🔒 Security Best Practices

### **1. Use Connection Pooling**

Update your `config.py`:

```python
class Config:
    # ... existing config ...
    
    # Connection pool settings for Supabase
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
```

### **2. Enable SSL (Production)**

For production, use SSL connection:

```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### **3. Use Environment Variables**

**Never** commit your database URL to Git!

Add to `.gitignore`:
```
.env
.env.local
```

---

## 🚨 Troubleshooting

### **Issue 1: "Connection refused"**

**Solution:** 
- Check if your IP is allowed (Supabase allows all by default)
- Verify password is correct
- Check connection string format

### **Issue 2: "SSL required"**

**Solution:** Add `?sslmode=require` to connection string:
```
postgresql://postgres:pass@host:5432/postgres?sslmode=require
```

### **Issue 3: "Too many connections"**

**Solution:** Add connection pooling to config.py:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
```

### **Issue 4: "Tables not found"**

**Solution:** Run the init script:
```bash
python init_supabase_db.py
```

---

## 📈 Monitor Your Database

### **In Supabase Dashboard:**

1. **Database** → View size and connections
2. **Reports** → See query performance
3. **Logs** → Check for errors

### **Set Up Backups:**

1. Supabase auto-backups daily (Free tier)
2. Go to **Database** → **Backups**
3. Can restore anytime

---

## 💡 Pro Tips

1. **Use Row Level Security (RLS)** in Supabase for extra security
2. **Create indexes** for better performance:
   ```sql
   CREATE INDEX idx_votes_election ON votes(election_id);
   CREATE INDEX idx_candidates_election ON candidates(election_id);
   ```
3. **Monitor query performance** in Supabase Reports
4. **Use database functions** for complex queries
5. **Enable realtime** if you need live updates

---

## 🎯 Connection String Formats

### **For Vercel/Production:**
```
postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### **For Local Development:**
```
postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres
```

### **With Connection Pooling (Supavisor):**
```
postgresql://postgres:PASSWORD@pooler.supabase.com:6543/postgres?pgbouncer=true
```

---

## 🆘 Need Help?

- **Supabase Docs:** https://supabase.com/docs
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/

---

## ✅ Checklist

After setup, verify:

- [ ] Supabase project created
- [ ] Connection string copied
- [ ] `.env` file updated
- [ ] `psycopg2-binary` installed
- [ ] Database tables created
- [ ] Local app connects successfully
- [ ] Environment variables set in Vercel
- [ ] Deployed to Vercel
- [ ] Production app works

**Your Flask app is now powered by Supabase PostgreSQL!** 🚀
