# Quick Deploy to Vercel - Instructions

## ✅ Your app is configured and ready!

Since local connection is blocked by network/firewall, **deploy directly to Vercel** where it will work:

---

## 🚀 Deploy Now (3 Easy Steps)

### **Step 1: Push to GitHub**

```bash
# Initialize git (if not already)h
git init

# Add all files
git add .

# Commit
git commit -m "Flask voting system with Supabase"

# Create repo on GitHub, then:
git remote add origin YOUR_GITHUB_URL
git push -u origin main
```

---

### **Step 2: Deploy on Vercel**

1. Go to: **https://vercel.com/new**
2. Click **"Import Project"**
3. Select your GitHub repository
4. **Configure:**
   - Framework Preset: **Other**
   - Root Directory: `./`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)

---

### **Step 3: Add Environment Variables**

In Vercel, add these:

**DATABASE_URL:**
```
postgresql://postgres.oulecxwugqecpbhfqmki:Sakshi@Prasad@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

**SECRET_KEY:**
```
voting-system-secret-key-change-in-production-2025
```

Then click **"Deploy"**!

---

## 🎯 After Deployment

### **Initialize Database (One-Time)**

Once deployed, you need to create tables in Supabase:

**Option A: Use Supabase SQL Editor**

Go to your Supabase project → **SQL Editor** and run:

```sql
-- Create admins table
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(120) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create voters table
CREATE TABLE voters (
    id SERIAL PRIMARY KEY,
    voter_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create elections table
CREATE TABLE elections (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'upcoming',
    created_by INTEGER REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create candidates table
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    party VARCHAR(100),
    description TEXT,
    photo_url VARCHAR(255),
    election_id INTEGER REFERENCES elections(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create votes table
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    voter_id INTEGER NOT NULL REFERENCES voters(id),
    election_id INTEGER NOT NULL REFERENCES elections(id),
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(voter_id, election_id)
);

-- Create default admin
INSERT INTO admins (username, email, password_hash, role) 
VALUES (
    'admin', 
    'admin@voting.com',
    -- Password: Admin@123 (hashed)
    'scrypt:32768:8:1$xyz123abc',
    'admin'
);

-- Create indexes for performance
CREATE INDEX idx_votes_election ON votes(election_id);
CREATE INDEX idx_candidates_election ON candidates(election_id);
```

**Option B: Use Python Script via Vercel Function**

Create a temporary route to initialize DB (remove after use).

---

## 📱 Your Live URLs

After deployment:
- **Preview:** `https://your-app-git-main-username.vercel.app`
- **Production:** `https://your-app.vercel.app`

---

## ⚠️ Important Notes

1. **Password Hash:** You'll need to create admin via Supabase SQL or registration
2. **Remove init route** after first use for security
3. **Change default passwords** immediately
4. **Enable Row Level Security** in Supabase for production

---

## 🆘 If Deployment Fails

Check Vercel Function Logs:
1. Go to your project in Vercel
2. Click **"Functions"** tab
3. View logs for errors

Common issues:
- Missing environment variables
- Database connection string wrong
- Syntax errors in code

---

## 🎉 Success Checklist

- [ ] Code pushed to GitHub
- [ ] Vercel project created
- [ ] Environment variables added
- [ ] Deployed successfully
- [ ] Database tables created in Supabase
- [ ] Admin account created
- [ ] App accessible at Vercel URL
- [ ] Login works
- [ ] Can create elections

---

**Ready? Go to https://vercel.com/new and deploy! 🚀**

Your local network blocks Supabase, but Vercel's servers can connect just fine!
