# What now? — Proje Rehberi (CLAUDE.md)

> Bu dosya Claude Code için proje bağlamıdır. Her oturumda önce bunu oku, sonra yalnızca **aktif faz** üzerinde çalış.
> Amaç bir **prototip**. Basit, okunabilir, az bağımlılıklı çözümleri tercih et. Gereksiz soyutlama, ekstra kütüphane veya "ileride lazım olur" kodu ekleme.

---

## 1. Proje Özeti

**What now?** — "Şimdi ne izlesem, ne okusam?" Film ve kitap paylaşım platformu; üstüne okuma/izleme **meydan okumaları** eklenir.

> Faz 0–4'te proje bir anket uygulamasıydı ve canlıya çıktı. Faz 5'ten itibaren film & kitap konseptine dönüşüyor; anket kodu kaldırılır (git geçmişinde kalır).

- **Raf:** Kullanıcı rafına film/kitap ekler. Durumlar: **İzleyeceğim / Okuyacağım**, **Şu an**, **Bitti**. "Bitti" olunca 1–5 yıldız ve kısa yorum (en fazla 280 karakter) eklenebilir.
- **Akış (ana sayfa):** Topluluğun son hareketleri — "ayse, *Dune*'u bitirdi ★★★★★ — Çölü hiç bu kadar özlememiştim."
- **"Ben de ekleyeyim":** Akışta veya öğe sayfasında, başkasının paylaştığı öğeyi tek tıkla kendi rafına ("İzleyeceğim/Okuyacağım") alma.
- **Temalı listeler:** Kullanıcının oluşturduğu, paylaşılabilir listeler ("Yağmurlu pazar filmleri"); her öğeye kısa not.
- **Meydan okumalar:** "Bu ay 4 kitap" gibi; tarih aralığı + hedef sayı. Katılımcının rafındaki uygun öğe "Bitti" olunca ilerleme **otomatik** artar. Katılımcılar, ilerleme çubukları ve günlük seriler görünür; isteğe bağlı günlük işaretleme + kısa not.
- **Film/kitap bilgisi elle girilir:** başlık, yazar/yönetmen, yıl, tür. Otomatik arama (Open Library / TMDB) sonraki fikirlerde.
- **Gizlilik:** Her şey herkese açık. Misafirler akışı, öğeleri, rafları, listeleri ve meydan okumaları **görebilir**; ekleme/düzenleme/katılma için **giriş zorunlu**.
- Takip / arkadaşlık / bildirim mekanizması **yoktur**.

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
├── manage.py               # Vercel Django'yu bu dosyadan otomatik tanır (vercel.json / api/ gerekmez)
├── .env.example
├── .gitignore
├── config/                 # Django proje ayarları (settings.py, urls.py, wsgi.py)
├── accounts/               # Kullanıcı modeli, kayıt, giriş, çıkış, profil
├── shelf/                  # Item, ShelfEntry, ThemeList, ThemeListItem; akış, raf, listeler
│   ├── models.py  forms.py  views.py  urls.py  admin.py  tests.py
│   └── templatetags/shelf_extras.py   # yıldız gösterimi, "3 saat önce" vb.
├── challenges/             # Challenge, Participant, CheckIn (Faz 8)
├── polls/                  # GEÇİCİ: yalnızca tabloları silen migration'lar (bkz. Bölüm 8, Faz 7'de kaldırılır)
├── templates/
│   ├── base.html
│   ├── accounts/   (login.html, signup.html, profile.html)
│   ├── shelf/      (feed.html, item_detail.html, item_form.html, entry_form.html, list_*.html)
│   └── challenges/ (list.html, detail.html, form.html)
└── static/
    ├── css/main.css
    ├── js/main.js
    └── img/pattern.svg     # Özgün arka plan deseni
```

---

## 4. Veri Modeli

### `accounts.User` (mevcut, değişmez)
- `email` — **unique** (büyük/küçük harf duyarsız), giriş e-posta + şifre ile (`USERNAME_FIELD = "email"`).
- `username` — **unique**, 3–20 karakter, harf/rakam/alt çizgi. Arayüzde görünen isim budur.
- `AUTH_USER_MODEL = "accounts.User"`.

### `shelf.Item` — bir film ya da kitap (ortak katalog)
- `kind` — CharField, choices: `film` (Film), `book` (Kitap)
- `title` — CharField(max 200), baştaki/sondaki boşluk kırpılır
- `creator` — CharField(max 100) — yazar ya da yönetmen
- `year` — PositiveSmallIntegerField, zorunlu, 1000–(bu yıl + 1)
- `genre` — CharField(max 50, blank) — serbest metin ("bilim kurgu")
- `added_by` → FK User (null, SET_NULL)
- `created_at` — auto_now_add
- **Tekrar engeli:** `UniqueConstraint(Lower("title"), "year", "kind", name="unique_item_title_year_kind")`. Form, kaydetmeden önce aynı öğeyi `title__iexact` + `year` + `kind` ile arar; varsa yeni kayıt açmaz, kullanıcıyı mevcut öğeye yönlendirir ("Bu zaten var — rafına ekle").

### `shelf.ShelfEntry` — bir kullanıcının rafındaki öğe
- `user` → FK User (CASCADE, related_name="shelf")
- `item` → FK Item (CASCADE, related_name="entries")
- `status` — choices: `want` (İzleyeceğim/Okuyacağım — etiket `kind`'a göre), `current` (Şu an), `done` (Bitti)
- `rating` — PositiveSmallIntegerField(null), 1–5
- `review` — CharField(max 280, blank)
- `finished_at` — DateField(null) — `done` olunca bugüne set edilir (formda değiştirilebilir); `done`'dan çıkınca temizlenir
- `created_at` — auto_now_add, `updated_at` — auto_now
- Kısıtlar: `UniqueConstraint(fields=["user", "item"])`; `CheckConstraint`: `rating` null ya da 1–5.
- Kural: `rating` ve `review` yalnızca `status == done` iken tutulur (formda doğrula, değilse temizle).

### `shelf.ThemeList` — temalı liste
- `owner` → FK User (CASCADE, related_name="theme_lists")
- `title` — CharField(max 100), `description` — CharField(max 300, blank)
- `created_at`, `updated_at`

### `shelf.ThemeListItem`
- `theme_list` → FK ThemeList (CASCADE, related_name="items")
- `item` → FK Item (CASCADE)
- `note` — CharField(max 200, blank)
- `added_at` — auto_now_add; sıralama `added_at`
- Kısıt: `UniqueConstraint(fields=["theme_list", "item"])`

### `challenges.Challenge`
- `creator` → FK User (SET_NULL, null)
- `title` — CharField(max 100), `description` — CharField(max 300, blank)
- `kind` — choices: `film`, `book`, `any` (Hepsi)
- `target` — PositiveSmallIntegerField, 1–100 ("4 kitap")
- `start_date`, `end_date` — DateField; `end_date >= start_date`, süre en fazla 366 gün
- `created_at`
- Durum hesaplanır (alan değil): Yakında / Devam ediyor / Bitti.

### `challenges.Participant`
- `challenge` → FK Challenge (CASCADE, related_name="participants"), `user` → FK User (CASCADE)
- `joined_at` — auto_now_add
- Kısıt: `UniqueConstraint(fields=["challenge", "user"])`

### `challenges.CheckIn` — isteğe bağlı günlük işaretleme
- `participant` → FK Participant (CASCADE, related_name="checkins")
- `date` — DateField (yalnızca bugün; geçmişe işaretleme yok)
- `note` — CharField(max 200, blank) ("Bugün 30 sayfa")
- Kısıt: `UniqueConstraint(fields=["participant", "date"])`

### Hesaplanan değerler (veritabanında sayaç tutulmaz)
- **İlerleme:** katılımcının `status=done`, `finished_at` meydan okuma aralığında ve `item.kind` uygun (`any` ise hepsi) `ShelfEntry` sayısı. Böylece "Bitti" işaretlenince ilerleme kendiliğinden artar, geri alınınca düşer. Liste sayfalarında `annotate(Count(..., filter=Q(...)))` ile tek sorguda hesapla.
- **Seri (streak):** meydan okuma aralığında, bugünden (ya da bugün henüz işaret yoksa dünden) geriye doğru **kesintisiz** "aktif gün" sayısı. Aktif gün = o gün `CheckIn` var **ya da** uygun bir öğe o gün bitirilmiş. **Kaçırılan gün seriyi sıfırlar.** Ayrıca "en uzun seri" gösterilir. Basit Python ile, tarih kümesi üzerinden hesapla.

---

## 5. Sayfalar ve URL'ler

| URL | Erişim | Açıklama |
|---|---|---|
| `/` | Herkes | **Akış.** Son güncellenen `ShelfEntry`'ler (`-updated_at`, sayfa başı 20). Kart metni duruma göre: "X, *Y*'yi rafına ekledi" / "X şu an *Y*'yi okuyor/izliyor" / "X, *Y*'yi bitirdi ★★★★☆ — yorum". Her kartta "Ben de ekleyeyim" (girişliyse ve rafında yoksa). Üstte Film / Kitap / Hepsi filtresi (`?kind=`). |
| `/items/new/` | Giriş | Öğe ekleme: tür, başlık, yazar/yönetmen, yıl, tür (genre) + kendi rafın için durum. Öğe zaten varsa mevcut öğeye yönlendirir ve rafa ekler. |
| `/items/<id>/` | Herkes | Öğe sayfası: bilgiler, ortalama puan, rafına ekleyen sayısı, yorumlar (bitirenlerin yıldız + yorumları), bu öğeyi içeren listeler. Girişliyse: "Rafıma ekle" ya da kendi kaydını düzenleme bağlantısı; "Listeye ekle". |
| `/items/<id>/add/` | Giriş (POST) | "Ben de ekleyeyim": `want` durumunda `ShelfEntry` oluşturur (varsa dokunmaz). `next`'e döner. |
| `/shelf/<entry_id>/edit/` | Sahibi | Durum, bitiş tarihi, yıldız, yorum düzenleme. |
| `/shelf/<entry_id>/remove/` | Sahibi (GET onay, POST sil) | Rafından kaldırır (Item kalır). |
| `/u/<username>/` | Herkes | **Profil / raf:** sekmeler Şu an / Bitti / İzleyeceğim-Okuyacağım (`?status=`), kullanıcının listeleri ve katıldığı meydan okumalar. |
| `/accounts/profile/` | Giriş | Kendi `/u/<username>/` sayfasına yönlendirir. |
| `/lists/` | Herkes | Tüm temalı listeler (en yeni üstte, öğe sayısıyla). |
| `/lists/new/` | Giriş | Liste oluşturma. |
| `/lists/<id>/` | Herkes | Liste detayı: öğeler + notlar; her öğede "Ben de ekleyeyim". Sahibine düzenle/sil/öğe çıkar. |
| `/lists/<id>/edit/`, `/lists/<id>/delete/` | Sahibi | Başlık/açıklama düzenleme; silme (onaylı). |
| `/lists/<id>/items/add/` | Sahibi (POST) | Öğe sayfasındaki "Listeye ekle"den gelir (`item_id`, `note`). |
| `/lists/<id>/items/<item_id>/remove/` | Sahibi (POST) | Listeden öğe çıkarır. |
| `/challenges/` | Herkes | Devam eden ve yaklaşan meydan okumalar (katılımcı sayısıyla), altta bitenler. |
| `/challenges/new/` | Giriş | Meydan okuma oluşturma (oluşturan otomatik katılır). |
| `/challenges/<id>/` | Herkes | Detay: hedef, tarih, katılımcılar listesi (ilerleme çubuğu, seri 🔥), girişliyse katıl/ayrıl, bugünü işaretle + not, son işaretlemeler. |
| `/challenges/<id>/join/`, `/leave/`, `/checkin/` | Giriş (POST) | Katıl / ayrıl / bugünü işaretle. İşaretleme yalnızca "Devam ediyor" durumunda. |
| `/accounts/signup/`, `/login/`, `/logout/` | — | Mevcut (değişmez). |
| `/admin/` | Superuser | Tüm modeller kayıtlı. |

---

## 6. Tasarım Rehberi

**Hedef his:** Sıcak, samimi, hafif nostaljik ama "retro oyun" değil. Defter/kâğıt hissi — kütüphane fişi, ajanda, sinema bileti koçanı. Ne parlak SaaS modernliği ne de aşırı piksel retro.

**Yasak:** Neon/fosforlu renkler (parlak yeşil, cyan, magenta, elektrik mavisi), glassmorphism, ağır gradyanlar, koyu siber tema.

### Renk paleti (CSS değişkenleri olarak `:root`'ta tanımla)
```css
--bg:          #FBF3E4;  /* krem kâğıt */
--surface:     #FFF9EF;  /* kart zemini */
--ink:         #3D2C2E;  /* koyu kahve metin */
--ink-soft:    #7A6563;  /* ikincil metin */
--primary:     #C8553D;  /* kiremit */
--primary-dk:  #A4412D;  /* hover */
--accent:      #E0A458;  /* hardal — yıldızlar, ilerleme çubukları */
--olive:       #6B705C;  /* zeytin, rozetler */
--line:        #E6D5BC;  /* kenarlıklar */
```

### Tipografi
- Başlıklar: **Fraunces** (Google Fonts, serif, sıcak karakter)
- Gövde: **Nunito** (yuvarlak, okunaklı)
- Taban font boyutu 17px, satır yüksekliği 1.6.

### Bileşen dili
- Kartlar: `--surface` zemin, 1.5px `--line` kenarlık, 14px köşe yuvarlaklığı, hafif ofset gölge (`3px 3px 0 var(--line)`) — "kâğıt üstüne yapıştırılmış not" hissi.
- Butonlar: dolu `--primary`, yuvarlak köşe, hover'da hafif yukarı kayma (1px). Abartılı animasyon yok. "Ben de ekleyeyim" ikincil (kenarlıklı) buton.
- Rozetler: Film / Kitap ve durumlar `--olive` zeminli küçük etiketler.
- Yıldızlar: `--accent` dolu, `--line` boş; puan girişi radyo butonlarıyla (JS'siz çalışmalı).
- İlerleme çubukları: `--accent` dolgu, hedefe ulaşan `--primary` + "Tamamlandı" rozeti.
- Mobil öncelikli; 640px üstünde içerik maksimum 720px genişlikte ortalanır.

### Arka plan deseni
- `static/img/pattern.svg` içinde **özgün**, küçük, el çizimi tarzı doodle'lar (mevcut: pati izi, kemik, yıldız, kalp; istenirse minik kitap ve film şeridi eklenebilir).
- Tekrarlayan desen, opaklık düşük (~%8–10), renk `--ink-soft`. Okunabilirliği asla bozmamalı.
- Telifli karakterler, film afişleri veya kitap kapakları **kullanılmaz**; desen tamamen özgün olmalı.

---

## 7. Kodlama Kuralları

- Türkçe arayüz metinleri; kod, değişken ve yorumlar İngilizce.
- Gizli bilgiler yalnızca ortam değişkenlerinde: `SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`. `.env.example` güncel tutulur, `.env` git'e girmez.
- Tüm formlar CSRF korumalı. Durum değiştiren her işlem POST. JS ile `fetch` yapılırsa CSRF token header'da gönderilir.
- Form doğrulaması **sunucu tarafında** yapılır; JS yalnızca kolaylık sağlar.
- Sahiplik kontrolü view'da: başkasının kaydı/listesi için 404 döndür.
- Sorgularda N+1'den kaçın (`select_related`, `prefetch_related`, `annotate(Count(...))`).
- Her faz sonunda: `python manage.py check`, `makemigrations --check`, `python manage.py test`, kısa bir manuel test listesi.
- Her faz bitince yapılanları ve kullanıcının yapması gerekenleri kısaca özetle; bir sonraki faza kendiliğinden geçme.
- **Canlı Supabase veritabanına migration** ve **commit/push** yalnızca kullanıcı onayıyla.

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
- Lokal geliştirmede `DATABASE_URL` yoksa SQLite'a düş.
- Migration'lar Vercel build'inde **çalıştırılmaz**; lokalden Supabase'e karşı elle (ve kullanıcı onayıyla) çalıştırılır.
- **Yeni şema canlıya çıkmadan push yapılırsa canlı site bozulur.** Sıra: (1) lokalde testler geçer → (2) kullanıcı onayıyla Supabase'e `migrate` → (3) push/deploy.
- **Anket tablolarının kaldırılması:** `polls` app'i Faz 5'te boş bir kabuğa indirilir (modeller silinir, tabloları düşüren migration üretilir, view/şablon/middleware kaldırılır). Supabase'e bu migration Faz 7'de uygulanınca `polls` klasörü ve `INSTALLED_APPS` girdisi tamamen silinir.
- Vercel Django'yu `manage.py` → `WSGI_APPLICATION` üzerinden **sıfır yapılandırmayla** tanır; `vercel.json` ve `api/index.py` kullanılmıyor. `STATIC_ROOT` tanımlı olduğu için `collectstatic`'i build'de Vercel çalıştırır; WhiteNoise lokal ve yedek. Python: Vercel varsayılanı (3.12). Yapılandırma değişirse önce Vercel'in güncel dokümantasyonuna bak.
- Canlı adres: https://what-now-ashen.vercel.app — Vercel ortam değişkenleri: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=what-now-ashen.vercel.app`, `CSRF_TRUSTED_ORIGINS=https://what-now-ashen.vercel.app`, `DATABASE_URL` (Transaction pooler, 6543).
- Ortam değişkeni değişince Vercel'de **Redeploy** gerekir; kod değişikliğinde `git push` yeterli.

---

## 9. Fazlar

Her faz bağımsız bir Claude Code oturumunda çalıştırılabilir.

### ✅ Faz 0–4 — Anket dönemi (tamamlandı)
Django iskeleti, e-posta ile giriş yapan custom User, anket/oylama, defter tasarımı, Supabase + Vercel yayını; sonrasında profil sayfası ve kendi anketini silme. Bu dönemin kodu Faz 5'te kaldırılır; `accounts`, tasarım (CSS, desen) ve deploy ayarları korunur.

---

### Faz 5 — Dönüşüm: Katalog ve Raf
**Hedef:** Anket kodu gider; kullanıcı film/kitap ekleyip rafını yönetebilir.

**Prompt:**
> CLAUDE.md'yi oku. Faz 5'i uygula: `polls` app'ini Bölüm 8'deki gibi boş kabuğa indir (modelleri sil, tabloları düşüren migration'ı üret; view, URL, şablon, templatetag, `VoterTokenMiddleware` ve testleri kaldır). `shelf` app'ini oluştur; Bölüm 4'teki `Item` ve `ShelfEntry` modellerini kısıtlarıyla yaz. `/items/new/` (tekrar engeliyle), `/items/<id>/` (temel bilgiler + "Rafıma ekle"), `/items/<id>/add/`, `/shelf/<id>/edit/` ve `/shelf/<id>/remove/` sayfalarını yaz. Geçici ana sayfa: son eklenen öğeler. Navbar'ı güncelle (Akış, Listeler, Meydan okumalar yer tutucu olmadan yalnızca var olan sayfalar; "Ekle" butonu). Mevcut profil sayfasını kullanıcının rafını duruma göre gösterecek şekilde uyarla. Admin kayıtları. Testler: tekrar öğe engeli (büyük/küçük harf), aynı öğeyi iki kez rafa ekleyememe, puan/yorumun yalnızca "Bitti"de tutulması, `finished_at` davranışı, başkasının kaydını düzenleyememe, girişsiz ekleyememe. Mevcut `accounts` testleri geçmeye devam etmeli.

**Manuel test:** Giriş yap → film ekle → aynı filmi "dune" / "DUNE" yazarak tekrar ekle → mevcut öğeye yönlendir. Durumu "Bitti" yap, 4 yıldız + yorum gir; "Okuyacağım"a geri al → puan/yorum temizlenir.

---

### Faz 6 — Akış, Öğe Sayfası ve Profil
**Hedef:** Topluluk görünürlüğü.

**Prompt:**
> CLAUDE.md'yi oku. Faz 6'yı uygula: `/` adresini Bölüm 5'teki akış olarak yaz (duruma göre kart metni, Film/Kitap filtresi, sayfalama, "Ben de ekleyeyim"). Öğe sayfasına ortalama puan, rafına ekleyen sayısı ve yorumları ekle. `/u/<username>/` herkese açık profil/raf sayfasını sekmelerle yaz; `/accounts/profile/` buna yönlendirsin. Akıştaki ve profildeki kullanıcı adları profile bağlansın. Yıldız gösterimi ve "3 saat önce" için templatetag. Boş durumlar ("Akış sessiz — ilk filmi/kitabı sen ekle!"). Testler: akışta durum metinleri, "Ben de ekleyeyim"in tekrar kayıt açmaması ve `next`'e dönmesi, filtre, misafirin profil görebilmesi. N+1 olmadığını `assertNumQueries` ile akış için doğrula.

**Manuel test:** İki kullanıcıyla: A bir kitap bitirir ve yorum yazar → B akışta görür → "Ben de ekleyeyim" → B'nin rafında "Okuyacağım". Mobil 360px'te akış kartları taşmıyor.

---

### Faz 7 — Canlıya Alma (MVP)
**Hedef:** Raf + akış canlıda; anket tabloları kaldırılmış.

**Prompt:**
> CLAUDE.md'yi oku. Faz 7'yi uygula: README'yi yeni konsepte göre güncelle. Lokalde `check`, `test` geçtikten sonra **kullanıcıdan onay al**, Supabase'e (Session pooler, 5432) `migrate` çalıştır. Ardından `polls` klasörünü ve `INSTALLED_APPS` girdisini tamamen kaldır, `check`/`test` tekrar. Commit ve push için onay iste. Deploy sonrası canlıda kayıt → öğe ekleme → akış → "Ben de ekleyeyim" akışını dene.

**Bitti sayılır:** Canlı adreste raf ve akış çalışıyor, admin stilli açılıyor, `polls_*` tabloları yok.

---

### Faz 8 — Temalı Listeler
**Prompt:**
> CLAUDE.md'yi oku. Faz 8'i uygula: Bölüm 4'teki `ThemeList` ve `ThemeListItem` modellerini ve Bölüm 5'teki `/lists/...` sayfalarını yaz. Öğe sayfasına "Listeye ekle" (kullanıcının listelerinden seçim + not) ve "Bu öğeyi içeren listeler" bölümünü, profile kullanıcının listelerini ekle. Listedeki her öğede "Ben de ekleyeyim". Testler: başkasının listesine öğe ekleyememe/silememe, aynı öğeyi listeye iki kez ekleyememe, misafirin listeyi görebilmesi. Canlıya alma Faz 7'deki sırayla ve onayla.

**Manuel test:** "Yağmurlu pazar filmleri" listesi oluştur → 3 film ekle, notlar yaz → çıkış yap → liste linkini aç, görünüyor.

---

### Faz 9 — Meydan Okumalar
**Prompt:**
> CLAUDE.md'yi oku. Faz 9'u uygula: `challenges` app'ini oluştur; Bölüm 4'teki `Challenge`, `Participant`, `CheckIn` modellerini ve Bölüm 5'teki `/challenges/...` sayfalarını yaz. İlerleme ve seriyi Bölüm 4'teki "Hesaplanan değerler" kurallarıyla hesapla (sayaç alanı yok). Detayda katılımcıları ilerlemeye göre sırala; ilerleme çubuğu, mevcut seri ve en uzun seri görünsün. "Bugünü işaretle" + kısa not. Profilde katıldığı meydan okumalar ve ilerlemesi. Navbar'a "Meydan okumalar". Testler: "Bitti" işaretlenince ilerlemenin artması / geri alınınca azalması, aralık dışı ve yanlış türdeki öğelerin sayılmaması, kaçırılan günün seriyi sıfırlaması, bitiş günü kaydının seriye katılması, aynı gün iki işaretleme yapılamaması, bitmiş meydan okumada işaretleme yapılamaması. Canlıya alma Faz 7'deki sırayla ve onayla.

**Manuel test:** "Kasım'da 4 kitap" oluştur → başka kullanıcıyla katıl → rafta bir kitabı "Bitti" yap → ilerleme 1/4. Bugünü işaretle → seri 1.

---

### 💡 Sonraki fikirler (prototip sonrası, şimdilik yapma)
- Open Library / TMDB'den otomatik arama ve kapak görseli (yeni bağımlılık gerekirse önce sor)
- Kullanıcı takip etme ve "takip ettiklerim" akışı
- Gizli raf / gizli liste seçeneği
- Listeye ortak katkı (birden fazla kişi)
- Basit rate limit (spam engeli)
- Paylaşım linki için Open Graph önizlemesi
