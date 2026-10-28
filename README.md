# What now?

Kararsız kaldığın konularda topluluğa danışmak için basit bir anket uygulaması (prototip).
Proje kuralları ve fazlar için `CLAUDE.md` dosyasına bak.

## Lokal kurulum

Gereksinim: Python 3.12

```bash
# 1. Proje klasörüne gir
cd what-now

# 2. Sanal ortam oluştur ve etkinleştir
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Bağımlılıkları kur
pip install -r requirements.txt

# 4. Ortam değişkenlerini hazırla
cp .env.example .env
# .env içinde DEBUG=True bırak; SECRET_KEY'i doldur:
python -c "import secrets; print(secrets.token_urlsafe(50))"

# 5. Projeyi kontrol et ve veritabanını hazırla
python manage.py check
python manage.py migrate

# 6. (İsteğe bağlı) Admin kullanıcısı oluştur — e-posta ile giriş yapılır
python manage.py createsuperuser

# 7. Geliştirme sunucusunu başlat
python manage.py runserver
```

Tarayıcıda http://127.0.0.1:8001 adresini aç. Admin paneli: http://127.0.0.1:8001/admin/

> `DATABASE_URL` boşsa proje lokal SQLite (`db.sqlite3`) kullanır.

## Testler

```bash
python manage.py test
```

## Uygulama adimlari    
 
1. Supabase'de proje aç; Connect->Direct'ten iki adres al:
Session pooler (5432) ve Transaction pooler (6543).

2. '.env' içinde 'DATABASE_URL' = Session pooler adres ve şu 2 komut;

```bash
python manage.py migrate
python manage.py createsuperuser
```

3. Vercel'de repoyu import et (GitHub ile giriş yap) ve şu ortam değişkenlerini tek tek ekle; 

```bash 
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

- 'SECRET_KEY' -> yukarıdaki komutun çıktısı
- 'ALLOWED_HOSTS' -> 'what-now-ashen.vercel.app'
- 'DEBUG' -> 'False' 
- 'DATABASE_URL' -> Transaction pooler adresi (6543)
- 'CSRF_TRUSTED_ORIGINS' -> 'https://what-now-ashen.vercel.app'

4. Ortam değişkeni değişirse: Redeploy. Kod değişirse: 'git push'