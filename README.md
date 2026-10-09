# 🛒 Smart Basket

**Kassada növbə çəkmədən alış-veriş.** Müştəri məhsulu səbətə qoyarkən özü
skan edir. Kassada yalnız səbətin QR kodu oxudulur və yekun məbləğ dərhal
ekrana çıxır. Mağaza isə səbətlərin hərəkətindən canlı analitika alır.

---

## Problem

Mağazalarda növbələr uzundur, çünki kassir hər məhsulu tək-tək skan edir.
Orta səbətdə 9 məhsul var — ənənəvi kassada bu, təxminən **47 saniyə** çəkir
(20 san hazırlıq + 3 san × məhsul). Müştəri gözləyir, kassir yorulur, mağaza
pik saatlarda sıxılır.

## Həll

Hər səbətə barkod oxuyucu və kiçik ekran bərkidilir. Müştəri məhsulu səbətə
qoyanda özü skan edir — yekun məbləğ canlı görünür. Kassada yalnız səbətin
QR kodu oxudulur, ödəniş bir toxunuşla tamamlanır və səbət avtomatik
sıfırlanır. **Faktiki ölçmə: ~8 saniyə.**

### Əlavə dəyər

| Kimə | Nə |
|---|---|
| **Müştəri** | Növbə yoxdur · yekun həmişə göz önündə · "Məhsul tap" ilə rəfə qədər yol göstərilir |
| **Mağaza** | Səbətlərin hərəkəti, zona konversiyası, birlikdə alınan məhsullar, **axtarılıb tapılmayanlar** (tələb siqnalı) |

---

## Funksiyalar

- **Səbət cihazı** (`/basket/:id`) — üç skan üsulu: kamera, USB/Bluetooth
  skaner və əl ilə seçim. Səs siqnalı, vibrasiya, canlı yekun.
- **Məhsul tap** — yazdıqca axtarış (AZ/RU/EN sinonimlər, səhv yazılışlar),
  xəritədə yol və addım-addım təlimat: *"Sağa doğru 18 m gedin"*.
- **Kassa** (`/checkout`) — QR oxu, nəhəng yekun, nağd/kart, qəbz çapı,
  vaxt qənaəti nişanı.
- **Analitika** (`/admin`) — KPI-lar, saatlıq trafik, istilik xəritəsi, canlı
  səbətlər, zona konversiyası, birlikdə alınanlar, üç axtarış hesabatı və
  tövsiyələr.
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

## Texnologiyalar

| Qat | Seçim |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLModel · Uvicorn |
| Baza | SQLite (`backend/smartbasket.db`) |
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
3. **4 məhsul skan edin**, birini "Çıxart" rejimi ilə geri qaytarın.
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

Hackathon prototipi. Autentifikasiya yoxdur, `/api/dev/*` endpoint-ləri açıqdır —
real istifadə üçün bunlar bağlanmalıdır.
