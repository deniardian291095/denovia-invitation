# 🚀 Deploy Denovia Invitation ke Railway

## Langkah-langkah Deploy

### 1. Buat akun & install
- Daftar di **railway.app** (gratis, pakai akun GitHub)
- Install Railway CLI: `npm install -g @railway/cli`

### 2. Push ke GitHub dulu
```bash
git init
git add .
git commit -m "Initial commit — Denovia Invitation Platform"
git remote add origin https://github.com/NAMAMU/denovia-invitation.git
git push -u origin main
```

### 3. Deploy ke Railway
```bash
# Login Railway
railway login

# Buat project baru
railway init

# Deploy
railway up
```

### 4. Dapatkan URL
Setelah deploy, Railway akan memberikan URL seperti:
```
https://denovia-invitation-production.up.railway.app
```

### 5. Custom Domain (opsional)
Di Railway Dashboard:
- Settings → Domains → Add Custom Domain
- Masukkan: `wedding-website.com`
- Arahkan DNS domain ke Railway (ikuti instruksi yang muncul)

---

## Cara Kerja URL Cantik

Saat client **Saepul & Musdalifah** mendaftar, sistem otomatis membuat:
```
https://wedding-website.com/saepul_musdalifah
```

Format URL: `wedding-website.com/namapria_namawanita`

Di halaman Share Undangan dashboard admin, URL cantik ini sudah otomatis tampil
dan bisa langsung di-share ke WhatsApp, Instagram, dll.

---

## Persistent Database di Railway

Railway bisa merestart pod → database SQLite perlu disimpan ke Volume:

1. Railway Dashboard → project → Add Volume
2. Mount path: `/data`
3. Set environment variable:
   ```
   DATABASE_PATH=/data/wedding.db
   ```

Database tidak akan hilang saat Railway restart.

---

## Environment Variables di Railway

| Variable | Value | Keterangan |
|---|---|---|
| `PORT` | (otomatis dari Railway) | Port server |
| `DATABASE_PATH` | `/data/wedding.db` | Path database |
| `RAILWAY_PUBLIC_DOMAIN` | (otomatis dari Railway) | Domain publik |

---

## Reset Database
```bash
railway run python wedding_db.py --reset
```

## Cek Log
```bash
railway logs
```
