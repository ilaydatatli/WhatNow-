# What now? — Proje Rehberi (CLAUDE.md)

> Bu dosya Claude Code için proje bağlamıdır. Her oturumda önce bunu oku, sonra yalnızca **aktif faz** üzerinde çalış.
> Amaç bir **prototip**. Basit, okunabilir, az bağımlılıklı çözümleri tercih et. Gereksiz soyutlama, ekstra kütüphane veya "ileride lazım olur" kodu ekleme.

---

## 1. Proje Özeti

**What now?**, kararsız kalınan konularda topluluğa danışmak için basit bir anket uygulamasıdır.

- Kullanıcı bir soru sorar (ör. "Bugün makarna mı yapsam pilav mı?") ve **en az 2, en fazla 5** seçenek ekler.
- **Tüm anketler herkese açıktır.** Ana sayfada en yeni anketler listelenir.
- **Oy vermek için üyelik gerekmez.** Misafirler de oy verebilir.
- **Anket açmak için üyelik zorunludur.**
- Takip / arkadaşlık / bildirim mekanizması **yoktur**.
- Anketi açan kişinin ve oy veren kayıtlı kullanıcıların **kullanıcı adı görünür**. Kayıtsız oy verenler "Misafir" olarak görünür.

---

## 2. Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.12, Django 5.x |
| Veritabanı | Supabase (yalnızca **PostgreSQL** olarak; Supabase Auth/SDK kullanılmayacak) |
| Kimlik doğrulama | Django'nun yerleşik auth sistemi (custom user model) |
| Frontend | Django şablonları + sade HTML, CSS, vanilla JavaScript (framework yok, aynı repo) |
| Statik dosyalar | WhiteNoise |
| Deployment | Vercel (Python serverless runtime) |

**İzin verilen bağımlılıklar** (`requirements.txt`):
```
Django>=5.0,<6.0
psycopg[binary]
dj-database-url
whitenoise
python-dotenv
```
Bunların dışında paket eklemeden önce kullanıcıya sor.

---

## 3. Klasör Yapısı (hedef)

```
what-now/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── manage.py
├── vercel.json
├── .env.example
├── .gitignore
├── api/
│   └── index.py            # Vercel giriş noktası (WSGI app)
├── config/                 # Django proje ayarları
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/               # Kullanıcı modeli, kayıt, giriş, çıkış
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   └── urls.py
├── polls/                  # Anket, seçenek, oy
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── accounts/  (login.html, signup.html)
│   └── polls/     (list.html, detail.html, create.html)
└── static/
    ├── css/main.css
    ├── js/main.js
    └── img/pattern.svg     # Özgün arka plan deseni
```

---

## 4. Veri Modeli

### `accounts.User` (AbstractUser'dan türet)
- `email` — **unique**, zorunlu; giriş e-posta + şifre ile yapılır (`USERNAME_FIELD = "email"`).
- `username` — **unique**, zorunlu; 3–20 karakter, harf/rakam/alt çizgi. Arayüzde görünen isim budur.
- `REQUIRED_FIELDS = ["username"]`
- `AUTH_USER_MODEL = "accounts.User"` — **ilk migration'dan önce** ayarlanmalı.

### `polls.Poll`
- `author` → FK User (CASCADE)
- `question` — CharField(max 200)
- `created_at` — auto_now_add
- Sıralama: `-created_at`

### `polls.Option`
- `poll` → FK Poll (CASCADE, related_name="options")
- `text` — CharField(max 100)
- `order` — PositiveSmallIntegerField
- Kural: Bir ankette **2–5** seçenek. Boş ve tekrarlayan (büyük/küçük harf duyarsız) seçenekler reddedilir.

### `polls.Vote`
- `poll` → FK Poll (CASCADE)
- `option` → FK Option (CASCADE)
- `user` → FK User (null=True, blank=True, SET_NULL)
- `voter_token` — CharField(max 64) — tarayıcı bazlı anonim kimlik
- `created_at` — auto_now_add
- Kısıtlar:
  - `UniqueConstraint(fields=["poll", "user"], condition=Q(user__isnull=False))`
  - `UniqueConstraint(fields=["poll", "voter_token"])`
- `option.poll == poll` olduğu view'da doğrulanmalı.

### Tekrar oy engelleme (prototip seviyesi)
- Her ziyaretçiye ilk girişte `voter_token` adlı, uzun ömürlü (1 yıl), `HttpOnly`, `SameSite=Lax` bir çerez ver (`secrets.token_urlsafe(32)`).
- Kayıtlı kullanıcı: `user` üzerinden tek oy. Misafir: `voter_token` üzerinden tek oy.
- Bu yöntem kesin değildir (çerez silinebilir); prototip için yeterli. Kodda bunu kısa bir yorumla belirt.

---

## 5. Sayfalar ve URL'ler

| URL | Erişim | Açıklama |
|---|---|---|
| `/` | Herkes | Anket listesi (en yeni üstte, sayfa başı 20, basit sayfalama). Her kartta: soru, yazar kullanıcı adı, toplam oy, zaman ("3 saat önce"). |
| `/polls/<id>/` | Herkes | Anket detayı. Oy verilmediyse seçenekler; verildiyse sonuçlar (yüzde çubukları) + her seçeneğe oy verenlerin kullanıcı adları ("Misafir" olanlar sayı olarak: "+3 misafir"). |
| `/polls/<id>/vote/` | Herkes (POST) | Oy kaydeder, detaya yönlendirir. |
| `/polls/new/` | Giriş zorunlu | Anket oluşturma. Giriş yoksa login'e `?next=` ile yönlendir. |
| `/accounts/signup/` | Misafir | Kullanıcı adı + e-posta + şifre (+ şifre tekrar). Başarılı kayıt sonrası otomatik giriş. |
| `/accounts/login/` | Misafir | E-posta + şifre. |
| `/accounts/logout/` | Giriş yapmış (POST) | Çıkış. |
| `/admin/` | Superuser | Django admin (Poll, Option, Vote kayıtlı). |

---

## 6. Tasarım Rehberi

**Hedef his:** Sıcak, samimi, hafif nostaljik ama "retro oyun" değil. Defter/kâğıt hissi. Ne parlak SaaS modernliği ne de aşırı piksel retro.

**Yasak:** Neon/fosforlu renkler (parlak yeşil, cyan, magenta, elektrik mavisi), glassmorphism, ağır gradyanlar, koyu siber tema.

### Renk paleti (CSS değişkenleri olarak `:root`'ta tanımla)
```css
--bg:          #FBF3E4;  /* krem kâğıt */
--surface:     #FFF9EF;  /* kart zemini */
--ink:         #3D2C2E;  /* koyu kahve metin */
--ink-soft:    #7A6563;  /* ikincil metin */
--primary:     #C8553D;  /* kiremit */
--primary-dk:  #A4412D;  /* hover */
--accent:      #E0A458;  /* hardal */
--olive:       #6B705C;  /* zeytin, rozetler */
--line:        #E6D5BC;  /* kenarlıklar */
```

### Tipografi
- Başlıklar: **Fraunces** (Google Fonts, serif, sıcak karakter)
- Gövde: **Nunito** (yuvarlak, okunaklı)
- Taban font boyutu 17px, satır yüksekliği 1.6.

### Bileşen dili
- Kartlar: `--surface` zemin, 1.5px `--line` kenarlık, 14px köşe yuvarlaklığı, hafif ofset gölge (`3px 3px 0 var(--line)`), — "kâğıt üstüne yapıştırılmış not" hissi.
- Butonlar: dolu `--primary`, yuvarlak köşe, hover'da hafif yukarı kayma (1px). Abartılı animasyon yok.
- Sonuç çubukları: `--accent` dolgu, kazanan seçenek `--primary`.
- Mobil öncelikli; 640px üstünde içerik maksimum 720px genişlikte ortalanır.

### Arka plan deseni
- `static/img/pattern.svg` içinde **özgün**, küçük, el çizimi tarzı doodle'lar: pati izleri, küçük kemikler, minik yıldızlar ve kalpler.
- Tekrarlayan desen (`background-image` + `background-repeat`), opaklık düşük (~%8–10), renk `--ink-soft`. İçeriğin okunabilirliğini asla bozmamalı.
- Telifli karakterler (Snoopy vb.) veya onları andıran figürler **kullanılmaz**; desen tamamen özgün olmalı.

---

## 7. Kodlama Kuralları

- Türkçe arayüz metinleri; kod, değişken ve yorumlar İngilizce.
- Gizli bilgiler yalnızca ortam değişkenlerinde: `SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`. `.env.example` güncel tutulur, `.env` git'e girmez.
- Tüm formlar CSRF korumalı. JS ile `fetch` yapılırsa CSRF token header'da gönderilir.
- Form doğrulaması **sunucu tarafında** yapılır; JS yalnızca kolaylık sağlar.
- Sorgularda N+1'den kaçın (`select_related`, `prefetch_related`, `annotate(Count(...))`).
- Her faz sonunda: `python manage.py check`, migration'lar ve kısa bir manuel test listesi.
- Her faz bitince yapılanları ve kullanıcının yapması gerekenleri kısaca özetle; bir sonraki faza kendiliğinden geçme.

---

## 8. Supabase ve Vercel Notları

- Supabase panelinden **Connection string** al:
  - **Uygulama (Vercel, serverless):** Transaction pooler (port **6543**).
  - **Migration (lokal):** Session pooler veya direct connection (port **5432**).
- Transaction pooler ile Django ayarları:
  ```python
  DATABASES["default"]["CONN_MAX_AGE"] = 0
  DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
  ```
- Lokal geliştirmede `DATABASE_URL` yoksa SQLite'a düş (hızlı başlangıç için).
- Migration'lar Vercel build'inde **çalıştırılmaz**; lokalden Supabase'e karşı elle çalıştırılır.
- Vercel yapılandırması zamanla değişebilir: Faz 4'te kurulumdan önce **Vercel'in güncel Python/Django dokümantasyonunu kontrol et** ve ona uy.

---

## 9. Fazlar

Her faz bağımsız bir Claude Code oturumunda çalıştırılabilir. Aşağıdaki promptları sırayla kopyalayıp yapıştır.

### ✅ Faz 0 — İskelet ve Ortam
**Hedef:** Çalışan boş Django projesi.

**Prompt:**
> CLAUDE.md'yi oku. Faz 0'ı uygula: Django projesini `config` adıyla oluştur, `accounts` ve `polls` app'lerini ekle, `requirements.txt`, `.gitignore`, `.env.example` dosyalarını hazırla. settings.py'yi ortam değişkenlerinden okuyacak şekilde ayarla (DATABASE_URL yoksa SQLite). WhiteNoise'u ekle, `templates/` ve `static/` klasörlerini yapılandır. Henüz migration çalıştırma. Sonunda `python manage.py check` çalıştır ve README'ye lokal kurulum adımlarını yaz.

**Bitti sayılır:** `manage.py check` hatasız, `runserver` açılıyor.

---

### ✅ Faz 1 — Kullanıcı Sistemi
**Hedef:** Kayıt, giriş, çıkış.

**Prompt:**
> CLAUDE.md'yi oku. Faz 1'i uygula: Bölüm 4'teki custom User modelini oluştur (e-posta ile giriş, benzersiz kullanıcı adı), AUTH_USER_MODEL'i ayarla, ilk migration'ları oluştur ve SQLite'ta çalıştır. Kayıt, giriş ve çıkış view'larını, formlarını ve basit şablonlarını yaz (henüz tasarım yok, sade base.html yeterli). Kayıttan sonra otomatik giriş yapılsın. Navbar'da giriş yapan kullanıcının adı ve çıkış butonu görünsün. Admin'e User'ı kaydet.

**Manuel test:** Kayıt ol → otomatik giriş → çıkış → e-posta ile tekrar giriş. Aynı e-posta/kullanıcı adıyla ikinci kayıt reddedilmeli.

---

### ✅ Faz 2 — Anketler ve Oylama
**Hedef:** Uygulamanın çekirdeği.

**Prompt:**
> CLAUDE.md'yi oku. Faz 2'yi uygula: Bölüm 4'teki Poll, Option, Vote modellerini kısıtlarıyla birlikte oluştur. Bölüm 5'teki anket listesi, detay, oy verme ve oluşturma sayfalarını yaz. Oluşturma formunda varsayılan 2 seçenek alanı olsun; vanilla JS ile "Seçenek ekle" (en fazla 5) ve "Kaldır" (en az 2) butonları çalışsın, doğrulama sunucu tarafında da yapılsın. voter_token çerezini bir middleware ile ver. Oy verildikten sonra detay sayfası sonuçları yüzde çubuklarıyla ve oy verenlerin kullanıcı adlarıyla göstersin (misafirler "+N misafir" olarak). Admin kayıtlarını ekle. Sonunda kısa bir test dosyası yaz: seçenek sayısı sınırı, tekrar oy engeli, giriş yapmadan anket açamama.

**Manuel test:** Giriş yapmadan oy ver → sonuçlar görünür. Aynı tarayıcıdan tekrar oy verilemez. Giriş yapmadan `/polls/new/` login'e yönlendirir. 1 veya 6 seçenekle anket oluşturulamaz.

---

### ✅ Faz 3 — Arayüz ve Tasarım
**Hedef:** Bölüm 6'daki sıcak, samimi görünüm.

**Prompt:**
> CLAUDE.md'yi oku. Faz 3'ü uygula: Bölüm 6'daki tasarım rehberine göre `static/css/main.css` dosyasını yaz ve tüm şablonları güncelle. Renkleri CSS değişkenleriyle tanımla, Fraunces ve Nunito fontlarını Google Fonts'tan yükle. `static/img/pattern.svg` olarak tamamen özgün, düşük opaklıklı, tekrarlanan bir doodle deseni çiz (pati izi, kemik, yıldız, kalp; hiçbir telifli karakter yok). Anket kartlarını, butonları, form alanlarını, sonuç çubuklarını ve boş durumları ("Henüz anket yok — ilk soruyu sen sor!") tasarla. Sayfa mobilde 360px genişlikte düzgün görünmeli, yatay kaydırma olmamalı. Neon/fosforlu renk kullanma.

**Manuel test:** Telefon ve masaüstü genişliğinde tüm sayfaları gez; metinler desen üzerinde rahat okunuyor mu?

---

### ⬜ Faz 4 — Supabase ve Vercel'e Yayın
**Hedef:** Canlıya çıkmış prototip.

**Prompt:**
> CLAUDE.md'yi oku. Faz 4'ü uygula: Önce Vercel'in güncel Python/Django dağıtım dokümantasyonunu kontrol et. `api/index.py` (WSGI `app`) ve `vercel.json` dosyalarını oluştur, tüm istekleri Django'ya yönlendir, statik dosyaların WhiteNoise ile sunulduğunu doğrula (`collectstatic` adımını dahil et). Bölüm 8'deki Supabase pooler ayarlarını settings.py'ye ekle. Production güvenlik ayarlarını (DEBUG=False, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, secure cookie'ler) ortam değişkenlerine bağla. README'ye adım adım yaz: Supabase projesi oluşturma, connection string alma, lokalden migrate + createsuperuser, Vercel'de ortam değişkenlerini girme ve deploy.

**Bitti sayılır:** Vercel URL'sinde kayıt, anket açma ve misafir oylama çalışıyor; admin paneli stilli açılıyor.

---

### 💡 Sonraki fikirler (prototip sonrası, şimdilik yapma)
- Anketi kapatma / süre sınırı
- Kendi anketlerim sayfası
- Basit rate limit (spam anket engeli)
- Paylaşım linki için Open Graph önizlemesi
