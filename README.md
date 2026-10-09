# 🛒 Smart Basket

**Kassada növbə çəkmədən alış-veriş.** Səbətin içindəki skaner qoyulan hər
məhsulu özü oxuyur — müştəri heç nə etmir, sadəcə ekrandakı canlı yekuna
baxır. Kassada yalnız səbətin QR kodu oxudulur və məbləğ dərhal çıxır.
Mağaza isə səbətlərin hərəkətindən canlı analitika alır.

---

## Problem

Mağazalarda növbələr uzundur, çünki kassir hər məhsulu tək-tək skan edir.
Orta səbətdə 9 məhsul var — ənənəvi kassada bu, təxminən **47 saniyə** çəkir
(20 san hazırlıq + 3 san × məhsul). Müştəri gözləyir, kassir yorulur, mağaza
pik saatlarda sıxılır.

## Həll

Hər səbətə barkod oxuyucu və kiçik ekran bərkidilir. Müştəri məhsulu səbətə
qoyan kimi **skaner onu özü oxuyur** — nə düymə, nə toxunuş. Ekranda yalnız
canlı yekun görünür. Kassada səbətin QR kodu oxudulur, ödəniş bir toxunuşla
tamamlanır və səbət avtomatik sıfırlanır. **Faktiki ölçmə: ~8 saniyə.**

### Əlavə dəyər

| Kimə | Nə |
|---|---|
| **Müştəri** | Növbə yoxdur · skan etmək lazım deyil · yekun həmişə göz önündə · "Məhsul tap" ilə rəfə qədər yol göstərilir |
| **Mağaza** | Səbətlərin hərəkəti, zona konversiyası, birlikdə alınan məhsullar, **axtarılıb tapılmayanlar** (tələb siqnalı) |

---

## Funksiyalar

- **Səbət cihazı** (`/basket/:id`) — səbətin skaneri oxuduğu məhsulları canlı
  göstərir: siyahı, yekun, səs siqnalı və vibrasiya. Müştəri üçün giriş
  elementi yoxdur. Hardware olmadığı üçün demo zamanı skaner ayrıca
  **“Demo: səbətin skaneri”** panelindən simulyasiya olunur (kamera,
  USB skaner və ya demo məhsul siyahısı).
- **Məhsul tap** — yazdıqca axtarış (AZ/RU/EN sinonimlər, səhv yazılışlar),
  xəritədə yol və addım-addım təlimat: *"Sağa doğru 18 m gedin"*.
- **Kassa** (`/checkout`) — QR oxu, nəhəng yekun, nağd/kart, qəbz çapı,
  vaxt qənaəti nişanı.
- **Analitika** (`/admin`) — KPI-lar, saatlıq trafik, istilik xəritəsi, canlı
  səbətlər, zona konversiyası, birlikdə alınanlar, üç axtarış hesabatı və
  tövsiyələr.
- **Kataloq** (`/catalog`) — məhsul və barkodları əlavə edin, dəyişin, silin.
  Barkod yazıldıqca yoxlanılır (EAN-13/EAN-8, yoxlama rəqəmi, təkrarlanma),
  kamera ilə də oxuna bilər; rəf yeri avtomatik təyin olunur.
- **Proqnoz və ML** (`/insights`) — satış proqnozu, davranış qrupları,
  anomaliyalar, stok riski (sintetik data üzərində, səhifədə açıq yazılıb).
- **Çap** (`/print`) — səbət QR kodları və məhsul barkodları (EAN-13).
- **Demo** (`/demo`) — səbət və kassa bir ekranda, proyektor üçün.

> **Məhsulun yeri heç vaxt AI ilə təxmin edilmir.** Yer bazada dəqiq
> koordinat kimi saxlanılır, yol isə A\* alqoritmi ilə hesablanır.
> Nəticə deterministikdir, oflayn işləyir və API xərci yoxdur.

---

## Quraşdırma

### Tələblər

| Alət | Versiya |
|---|---|
| Node.js | ≥ 20 |
| Python | ≥ 3.11 |
| Git | — |

```bash
# Windows
winget install OpenJS.NodeJS.LTS Python.Python.3.12 Git.Git
# macOS
brew install node python@3.12 git
```

### Addımlar

```bash
git clone <repo-url> "Smart Basket"
cd "Smart Basket"

# 1. Backend: virtual mühit və paketlər
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -r requirements.txt
# macOS / Linux:
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
cd ..

# 2. Frontend və root paketləri
npm run install:all

# 3. Demo datası ilə bazanı qur (seed + 500 sessiya simulyasiya)
npm run reset-demo

# 4. Hər iki serveri işə sal
npm run dev
```

Açın: **http://localhost:5173**

| Ünvan | Nə |
|---|---|
| `/` | Ana səhifə — bütün ekranlara keçid |
| `/demo` | Proyektor üçün demo rejimi |
| `/basket/BSK-001` | Səbət cihazı |
| `/checkout` | Kassa |
| `/admin` | Analitika paneli |
| `/print` | QR və barkod çapı |
| http://localhost:8000/docs | Swagger (API sənədi) |

---

## Telefonla qoşulma

Telefon və noutbuk **eyni Wi-Fi şəbəkəsində** olmalıdır.

```bash
npm run dev
```

Terminalda `Network: http://192.168.x.x:5173/` sətrini tapın və həmin ünvanı
telefonda açın. `/api` sorğuları avtomatik backend-ə ötürülür.

### Kamera üçün HTTPS

Brauzerlər kameranı yalnız `localhost` və ya HTTPS üzərində açır. Telefonda
kamera ilə skan etmək üçün:

```bash
npm run dev:https
```

Telefonda `https://192.168.x.x:5173` açın. Sertifikat öz-özünə imzalandığı üçün
brauzer xəbərdarlıq verəcək — **"Advanced" → "Proceed"** seçin. Bu, yalnız
lokal şəbəkədə işləyən demo sertifikatıdır.

### Telefonu barkod skaneri kimi işlətmək

Fiziki səbət cihazı olmadığı üçün telefonun kamerası onun skanerini əvəz edir:

1. Telefonda `/basket/BSK-001` açın.
2. Aşağıda **"Demo: səbətin skaneri"** panelini açın.
3. **"Kamera"** tabına keçin və brauzer soruşanda **"Allow"** seçin.
4. Barkodu kameraya tutun — oxunan kimi səbətə düşür.

Kamera açılanda yuxarıda status zolağı görünür:

| Zolaq | Mənası |
|---|---|
| `Barkod axtarılır…` | Kamera işləyir, kadrda hələ barkod yoxdur |
| `Oxunmadı · 3 san — barkodu yaxınlaşdırın` | 3 saniyədir axtarır, tapmır — yaxınlaşdırın və ya işığı artırın |
| `✅ 🧃 Fuse Tea 500ml · 1.00 ₼` | Oxundu və səbətə əlavə olundu |

**Eyni məhsul təkrar sayılmır.** Barkod kadrda qaldığı müddətcə bir dəfə
sayılır; ikinci dəfə saymaq üçün onu kadrdan çıxarıb yenidən gətirmək lazımdır
(real skaner də belə işləyir).

**Vacib:** barkodu **kadrın təxminən yarısını dolduracaq qədər yaxın** tutun.
Ölçdük: barkod kadrın 50–80%-ini tutanda yarım saniyədə oxunur; 30%-ə düşəndə
(uzaqdan tutulanda) 640p kamerada ümumiyyətlə oxunmur, çünki barkodun hər
zolağına 2 pikseldən az düşür. Tətbiq kameradan 720p istəyir, ona görə müasir
telefonlarda nisbətən uzaqdan da oxuyur — amma yaxın tutmaq həmişə daha sürətlidir.

Kassada (`/checkout`) eyni kamera səbətin **QR kodunu** oxuyur.

### Kamera oxumursa

Əvvəlcə **bazanın deyil, kameranın** problem olduğunu təsdiqləyin: skaner
panelində **"Əl ilə"** tabına keçib barkodu yazın. Məhsul əlavə olunursa,
kataloq qaydasındadır.

Sonra kamera panelindəki **"Kadrı yoxla"** düyməsinə basın — o, hazırkı kadrı
tutub ayrıca dekodlamağa çalışır və nəticəni yazır:

| Nəticə | Mənası |
|---|---|
| `Bu kadrda oxundu: …` | Görüntü yaxşıdır; barkodu daha sabit tutun |
| `Bu kadrda barkod tapılmadı` | Görüntü dekoder üçün kifayət etmir — aşağıya baxın |

**Ən çox rast gəlinən səbəb: noutbuk kamerası.** Noutbuk veb-kameraları adətən
**sabit fokusludur** (~40–60 sm, üz məsafəsi) və maksimum 720p verir. EAN-13
cəmi ~3 sm enindədir; onu kadrı dolduracaq qədər böyütmək üçün ~10 sm-ə
gətirmək lazımdır — bu, fokus sahəsinin içindədir, görüntü bulanıq olur.
Panelin altındakı `1280×720 · zoom yoxdur` yazısı kameranızın nə verdiyini
göstərir.

Üç həll yolu:

1. **Telefon (ən yaxşısı).** Avtofokus və 1080p+ kamera. `npm run dev:https`
   ilə başladın, telefonda `https://<IP>:5173` açın. Telefonda zoom və işıq
   (torch) düymələri də görünür.
2. **Böyük barkod.** `/print` → **"Böyük barkod (ekrandan skan)"** → məhsulu
   seçin. Barkod ekranda ~700 piksel enində çıxır; ekranı kameraya **30–40 sm**
   məsafədən tutun — bu, sabit fokusun içinə düşür.
3. **"Əl ilə" və ya "Demo məhsullar".** Həmişə işləyir, demo heç vaxt dayanmır.

Digər səbəblər: zəif işıq, ekrandan skan edəndə parıltı (ekran parlaqlığını
azaldın), barkodun əyri səthdə olması.

### Real məhsulla yoxlama

Kataloqda real barkodlu bir məhsul var ki, mağazadan alınmış şüşəni birbaşa
skan edə biləsiniz:

| Məhsul | Barkod | Qiymət |
|---|---|---|
| 🧃 Fuse Tea 500ml | `5449000189349` | 1.00 ₼ |

Başqa real məhsul əlavə etmək üçün `backend/app/seed.py`-dəki `PRODUCTS`
siyahısına `"barcode": "..."` sahəsi olan sətir əlavə edin və `npm run seed`
işlədin. Barkod etibarlı EAN-13 olmalıdır (test bunu yoxlayır).

> Kamera işləməsə, demo dayanmır: "Demo məhsullar" siyahısı, əl ilə barkod
> girişi və USB skaner həmişə əlçatandır.

---

## Komandalar

| Komanda | Nə edir |
|---|---|
| `npm run dev` | Hər iki serveri işə salır |
| `npm run dev:https` | Frontend HTTPS ilə (telefon kamerası üçün) |
| `npm run reset-demo` | Bazanı sıfırlayır + seed + 500 sessiya simulyasiya |
| `npm run seed` | Yalnız kataloqu sıfırlayıb yenidən qurur |
| `npm test` | Backend testləri (pytest) |
| `npm run build` | Frontend-i production üçün yığır |

Admin panelindəki **"Demo data"** və **"Sıfırla"** düymələri eyni işi
brauzerdən görür.

---

## Canlı demo

**https://hackathon-smartbasket.vercel.app**

Telefon kamerası orada sertifikat xəbərdarlığı olmadan işləyir.

---

## Deploy (Vercel)

Daimi HTTPS linki — telefon kamerası sertifikat xəbərdarlığı olmadan işləyir
və kassa ekranı ilə eyni sistemə qoşulur.

Addım-addım təlimat: **[docs/DEPLOY.md](docs/DEPLOY.md)**

Qısaca: pulsuz Neon Postgres yaradın, `DATABASE_URL`, `STORE_NAME` və
`ADMIN_PIN` mühit dəyişənlərini Vercel-ə əlavə edin, `npx vercel --prod`
işlədin, sonra bir dəfə `/api/dev/reset` çağırıb kataloqu yükləyin.

Baza seçimi avtomatikdir: `DATABASE_URL` `sqlite:` ilə başlayırsa SQLite,
`postgres…` ilə başlayırsa Postgres işlədilir. Yerli iş dəyişmir.

---

## Texnologiyalar

| Qat | Seçim |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLModel · Uvicorn |
| Baza | SQLite (yerli) · Postgres (deploy) — eyni kod |
| Frontend | React 19 · Vite · TypeScript · Tailwind CSS 4 |
| Qrafiklər | Recharts |
| Barkod/QR | `html5-qrcode` (oxuma) · `qrcode.react`, `jsbarcode` (yaratma) |
| Yol tapma | Öz yazdığımız A\* (xarici kitabxana yoxdur) |
| Axtarış | `rapidfuzz` + Azərbaycan hərf normallaşdırması |
| Testlər | pytest (60 test) |

### Əsas prinsiplər

- İnterfeys **Azərbaycan dilində**, kod **ingiliscə**.
- Pul həmişə **tam ədəd qəpik** (`price_qepik: int`) — float ilə hesablanmır.
- Yekun məbləği **yalnız backend hesablayır**; frontend heç vaxt total
  hesablamır.
- **Səbət ≠ sessiya.** Səbət fiziki obyektdir (`BSK-001`), sessiya isə bir
  alış-veriş səfəri. Ödəniş sessiyanı bitirir və səbəti `idle` edir.
- Məhsulun yeri və yol **heç vaxt AI ilə** müəyyən edilmir.

---

## Arxitektura

Diaqramlar: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — sistem
komponentləri, alış-veriş ardıcıllığı və verilənlər modeli.

Mağaza planı `backend/app/store_layout.py` faylında ASCII şəbəkə kimi
saxlanılır (1 simvol = 1 m²). Başqa mağazanın planını çəkmək üçün yalnız o
faylı redaktə etmək kifayətdir — xəritə, yol tapma və məhsul yerləri
avtomatik uyğunlaşır.

---

## API

Tam sənəd: **http://localhost:8000/docs**

| Metod | Yol | Təsvir |
|---|---|---|
| GET | `/api/health` | Server statusu |
| GET | `/api/map` | Mağaza planı (şəbəkə, rəflər, giriş, kassalar) |
| GET | `/api/products` | Bütün məhsullar (`?q=` axtarış) |
| GET | `/api/products/barcode/{code}` | Barkoda görə məhsul |
| GET | `/api/products/search` | `?q=&basket_id=` → 8 nəticə + məsafə |
| GET | `/api/zones` · `/api/baskets` | Zonalar · səbətlər |
| GET | `/api/baskets/{id}/cart` | Səbətin tərkibi və yekunu |
| POST | `/api/baskets/{id}/scan` | `{barcode, mode}` — əlavə et / çıxart |
| PATCH/DELETE | `/api/baskets/{id}/items/{item_id}` | Say dəyiş / sil |
| POST | `/api/baskets/{id}/position` | `{x, y}` — səbətin yeri |
| GET | `/api/navigation/route` | `?basket_id=&product_id=` → yol və təlimat |
| POST | `/api/checkout/lookup` | `{qr_payload}` → səbəti kilidlə |
| POST | `/api/checkout/{id}/pay` | `{method}` → ödəniş və sıfırlama |
| POST | `/api/checkout/{id}/cancel` | Kassadan geri qaytar |
| GET | `/api/analytics/*` | `summary` · `top-products` · `zones` · `hourly` · `co-purchase` · `searches` · `live` · `insights` |
| POST | `/api/dev/simulate` · `/api/dev/reset` | Demo datası |

---

## Testlər

```bash
npm test          # və ya: cd backend && .venv/Scripts/python -m pytest -q
```

60 test: EAN-13 yoxlama rəqəmi, tam alış-veriş axını, kassa və sıfırlama,
mağaza planının bütövlüyü (hər rəfin qonşu keçidi var), A\*-ın ən qısa yol
tapması (BFS ilə müqayisə), axtarış, analitika və simulyator.

---

## Demo ssenarisi (~3 dəqiqə)

1. **Problem** — "Orta müştəri kassada bir neçə dəqiqə gözləyir."
2. `/demo` səhifəsini açın — səbət və kassa bir ekranda.
3. **“Demo: səbətin skaneri”** panelini açıb 4 məhsul qoyun, birini geri
   götürün — ekranda yekun canlı dəyişir.
4. **"Məhsul tap"** → "diş pastası" → xəritədə yol və təlimat.
5. **Kassa:** QR oxu → yekun dərhal → "Kart" → səbətdə "Təşəkkür edirik 🎉".
   Nişan: *"8 san · ənənəvi kassada ~47 san"*.
6. **`/admin`:** istilik xəritəsi, birlikdə alınanlar,
   "axtarılıb tapılmayan: avokado", **"X saat qənaət edildi"**, tövsiyələr.
7. **Bağlanış:** biznes modeli (səbət başına abunə + analitika paketi) və
   növbəti addımlar.

---

## Gələcək planlar

- **Real hardware** — səbətə bərkidilmiş planşet və barkod skaner.
- **BLE mayakları** — yerin avtomatik təyini (hazırda skan və xəritəyə
  toxunma ilə simulyasiya olunur).
- **Çəki sensoru** — skan edilməyən məhsulun aşkarlanması.
- **Kassasız ödəniş** — səbət ekranından birbaşa, çıxışda yalnız təsdiq.
- **Alış-veriş siyahısı** — bütün məhsulları əhatə edən ən qısa marşrut.
- **Loyallıq** — telefon nömrəsi ilə bal toplama.

---

## Lisenziya və status

Hackathon prototipi. İstifadəçi autentifikasiyası yoxdur. `/api/dev/*`
endpoint-ləri `ADMIN_PIN` qoyulduqda qorunur (deploy üçün mütləqdir), PIN
qoyulmayanda isə yerli iş üçün açıq qalır.
