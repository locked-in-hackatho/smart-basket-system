# Smart Basket — Claude Code üçün İcra Planı

> Bu sənəd Claude Code üçün yazılıb. Layihə 0-dan, boş `Smart Basket` folderindən başlayır.
> Fazalar ardıcıl icra olunur. Hər faza bitəndə Claude Code **Yoxlama** bəndlərini özü yoxlayır, git commit edir, qısa hesabat verir və növbəti faza üçün icazə gözləyir.

---

## 0. Bu planı necə işə salmaq

1. Bu faylı `Smart Basket` folderinə `PLAN.md` adı ilə qoyun.
2. VS Code-da terminal açın (`Ctrl + ~`) və `claude` yazın.
3. İlk prompt olaraq bunu yazın:

```
PLAN.md faylını başdan sona diqqətlə oxu. Faza 0-dan başla.
Qaydalar:
- Hər fazanı tam bitir, sonra "Yoxlama" bəndlərini özün yoxla (serveri işə sal, testləri işlət, endpoint-ləri çağır).
- Hər fazanın sonunda git commit et (commit mesajı planda yazılıb).
- Mənə 3-5 cümləlik hesabat ver və növbəti fazaya keçmək üçün icazə gözlə.
- Səhv çıxsa, özün düzəlt və davam et; yalnız sistem proqramı quraşdırmaq lazım olanda məndən soruş.
```

4. Vaxt azdırsa: **Faza 0–6 = MVP** (demo üçün kifayətdir). Faza 7, 9 və 10 “wow” effekti verir. Faza 11 opsionaldır.
   (Faza 8 — köhnə AI köməkçi — ləğv olundu; nömrələr commit tarixçəsi ilə uyğun qalsın deyə dəyişdirilməyib.)

| Faza | Mövzu | Təxmini vaxt |
|---|---|---|
| 0 | Mühitin qurulması | 20 dəq |
| 1 | Backend skeleti, DB, demo data | 40 dəq |
| 2 | Səbət + kassa məntiqi, testlər | 45 dəq |
| 3 | Frontend skeleti, dizayn sistemi | 30 dəq |
| 4 | Səbət cihazı ekranı | 60 dəq |
| 5 | Kassa ekranı | 40 dəq |
| 6 | QR / barkod çap səhifəsi → **MVP** | 20 dəq |
| 7 | Mağaza xəritəsi + naviqasiya (A\*) | 90 dəq |
| 9 | Analitika paneli + data simulyatoru | 60 dəq |
| 10 | Cilalama, demo rejimi, README, pitch materialları | 40 dəq |
| 11 | Opsional funksiyalar (təsdiqlə) | — |

---

## 1. Layihənin konteksti (Claude Code üçün)

**Problem:** Mağazalarda kassa növbələri uzundur, çünki kassir hər məhsulu tək-tək skan edir.

**Həll:** Hər səbətə barkod oxuyucu + kiçik ekran (planşet/telefon) bərkidilir. Müştəri məhsulu səbətə qoyarkən özü skan edir. Hər səbətin bazada unikal ID-si və üzərində QR kodu var. Kassada yalnız səbətin QR kodu oxudulur → yekun məbləğ dərhal ekrana çıxır → ödəniş edilir → səbət sıfırlanır.

**Əlavə dəyər:**
- **Analitika:** səbətlərin hansı zonalarda gəzdiyi, harada nə qədər qaldığı, nələri birlikdə aldığı → mağaza üçün qərar dəstəyi.
- **Məhsul tap (naviqasiya):** müştəri səbətdəki ekranda “süd” yazır → xəritədə dəqiq rəf və oraya gedən yol göstərilir. Yer bazadadır, yol A\* ilə hesablanır — AI yoxdur.

**Sistemdə 4 rol / ekran:**
1. **Səbət cihazı** (`/basket/:basketId`) — səbətə bərkidilmiş ekran: skan, səbət siyahısı, yekun, “Məhsul tap” və xəritə/naviqasiya.
2. **Kassa** (`/checkout`) — kassir səbət QR-ını oxudur, yekunu görür, ödənişi təsdiq edir.
3. **Admin / Analitika** (`/admin`) — mağaza menecerinin paneli.
4. **Çap** (`/print`) — səbət QR kodlarını və demo məhsul barkodlarını çap etmək üçün.

**Hardware demo üçün necə simulyasiya olunur:**
- Real həyatda: səbətə bərkidilmiş planşet + barkod skaner + zona üçün BLE mayakları (beacon).
- Demoda: telefon/noutbuk kamerası (brauzerdə barkod oxuma) **və ya** USB barkod skaner (klaviatura kimi işləyir) **və ya** əl ilə seçim (ehtiyat variant). Zona yerləşməsi skan edilən məhsulun zonasından + xəritədə klikləməklə simulyasiya olunur.

---

## 2. Dəyişməz texniki qərarlar

| Qat | Seçim | Səbəb |
|---|---|---|
| Backend | Python 3.11+ · FastAPI · SQLModel · Uvicorn | Sürətli, avtomatik Swagger (`/docs`) — münsiflərə göstərmək üçün də yaxşıdır |
| Baza | SQLite (`backend/smartbasket.db`) | Quraşdırma tələb etmir |
| Frontend | React + Vite + TypeScript · Tailwind CSS · React Router | Sürətli inkişaf |
| Qrafiklər | Recharts | Sadə, React-dostu |
| Barkod/QR oxuma | `html5-qrcode` (kamera) + klaviatura-skaner dinləyicisi | Həm kamera, həm USB skaner |
| QR/barkod yaratma | `qrcode.react`, `jsbarcode` | Çap səhifəsi üçün |
| İkonlar | `lucide-react` | |
| Yol tapma | Öz yazdığımız A\* (xarici kitabxana yox), 4 istiqamət, Manhattan evristikası | Deterministik, oflayn, sürətli |
| Fuzzy axtarış | `rapidfuzz` + AZ hərf normallaşdırması | Səhv yazılış, AZ/RU/EN sinonimlər |
| Real-time | Frontend hər 2 saniyədən bir sorğu (polling) | WebSocket-dən sadə və etibarlı |
| Testlər | pytest + httpx (FastAPI TestClient) | |

**Əsas prinsiplər (CLAUDE.md-yə də yazılacaq):**
- İstifadəçi interfeysi **Azərbaycan dilində**, kod (dəyişən, funksiya, şərh) **ingiliscə**.
- Pul həmişə **tam ədəd qəpik** kimi saxlanılır (`price_qepik: int`). Ekranda `12.50 ₼` formatında göstərilir. Float ilə pul hesablanmır.
- Yekun məbləği **yalnız backend hesablayır**. Frontend heç vaxt total hesablamır (tək həqiqət mənbəyi).
- **Səbət ≠ sessiya.** `basket` fiziki səbətdir (daimi ID: `BSK-001`). `session` bir alış-veriş səfəridir (səbət götürüləndən ödənişə qədər). Analitika sessiyalar üzərində qurulur. Ödənişdən sonra səbət `idle` olur və yeni sessiya üçün hazırdır — “sıfırlanma” budur.
- Autentifikasiya yoxdur (hackaton). Admin üçün sadəcə opsional PIN.
- Portlar: backend `8000`, frontend `5173`. Frontend `/api` sorğularını Vite proxy ilə backend-ə ötürür (CORS problemi olmur, telefon yalnız frontend ünvanını bilməlidir).
- Fayllar kiçik və oxunaqlı (bir fayl ~300 sətirdən çox olmasın).

---

## 3. Qovluq strukturu (hədəf)

```
Smart Basket/
├── PLAN.md
├── CLAUDE.md
├── README.md
├── .gitignore
├── package.json              # root: "npm run dev" hər iki serveri işə salır
├── docs/
│   ├── ARCHITECTURE.md       # mermaid diaqramları (pitch üçün)
│   └── screenshots/
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── store_layout.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── seed.py
│   │   ├── routers/
│   │   │   ├── products.py
│   │   │   ├── baskets.py
│   │   │   ├── checkout.py
│   │   │   ├── analytics.py
│   │   │   └── dev.py
│   │   └── services/
│   │       ├── cart.py
│   │       ├── navigation.py
│   │       ├── analytics.py
│   │       └── simulator.py
│   └── tests/
│       └── test_flow.py
└── frontend/
    ├── vite.config.ts
    └── src/
        ├── api.ts
        ├── utils/format.ts
        ├── pages/
        │   ├── Home.tsx
        │   ├── BasketDevice.tsx
        │   ├── Checkout.tsx
        │   ├── Admin.tsx
        │   ├── PrintCodes.tsx
        │   └── Demo.tsx
        └── components/
            ├── BarcodeScanner.tsx
            ├── CartList.tsx
            ├── StoreMap.tsx
            ├── ProductFinder.tsx
            ├── KpiCard.tsx
            └── Toast.tsx
```

> Qeyd: Folder adında boşluq var (`Smart Basket`). Claude Code terminal əmrlərində yolları dırnaq içində yazmalıdır.

---

## 4. Verilənlər bazası sxemi

```
zones
  id PK, code TEXT UNIQUE ("A", "B", ...), name TEXT ("Süd məhsulları"),
  x INT, y INT, w INT, h INT       -- 12x8 şəbəkədə xəritə koordinatları
  color TEXT, kind TEXT            -- "sales" | "entrance" | "checkout"

products
  id PK, barcode TEXT UNIQUE (EAN-13), name TEXT, category TEXT,
  price_qepik INT, zone_id FK, aisle TEXT ("Rəf 3"), shelf TEXT ("Orta"),
  stock INT, emoji TEXT, keywords TEXT  -- sinonimlər: "süd, milk, молоко"

baskets
  id TEXT PK ("BSK-001"), status TEXT ("idle" | "active" | "checkout"),
  current_session_id FK NULL, current_zone_id FK NULL, last_seen_at DATETIME

sessions
  id PK, basket_id FK, status TEXT ("active" | "checkout" | "paid" | "abandoned"),
  started_at, checkout_started_at NULL, ended_at NULL, total_qepik INT

basket_items
  id PK, session_id FK, product_id FK, qty INT, added_at

events                               -- analitikanın əsası
  id PK, session_id FK, basket_id, type TEXT, zone_id NULL, product_id NULL,
  payload JSON NULL, ts DATETIME
  -- type: "session_start" | "scan_add" | "scan_remove" | "zone_enter" |
  --       "nav_search" | "nav_route" | "checkout_start" | "payment"

payments
  id PK, session_id FK, amount_qepik INT, method TEXT ("cash" | "card"),
  checkout_seconds REAL, ts

search_queries
  id PK, session_id NULL, basket_id, query TEXT,
  top_product_id NULL, found BOOL, ts
```

**QR kod formatı:** `SMARTBASKET:BSK-001`

---

## 5. API siyahısı

| Metod | Yol | Təsvir |
|---|---|---|
| GET | `/api/health` | `{status: "ok", store_name}` |
| GET | `/api/products` | Bütün məhsullar (`?q=` axtarış) |
| GET | `/api/products/barcode/{code}` | Barkoda görə məhsul, yoxdursa 404 |
| GET | `/api/zones` | Zonalar (xəritə üçün) |
| GET | `/api/baskets` | Bütün səbətlər və statusları |
| GET | `/api/baskets/{id}/cart` | Cari səbət: items, item_count, total, status |
| POST | `/api/baskets/{id}/scan` | `{barcode, mode: "add" \| "remove"}` |
| PATCH | `/api/baskets/{id}/items/{item_id}` | `{qty}` |
| DELETE | `/api/baskets/{id}/items/{item_id}` | Məhsulu sil |
| POST | `/api/baskets/{id}/zone` | `{zone_code}` — zona dəyişməsi (simulyasiya) |
| POST | `/api/checkout/lookup` | `{qr_payload}` → səbət + yekun, səbəti kilidləyir |
| POST | `/api/checkout/{session_id}/pay` | `{method}` → ödəniş, səbəti sıfırlayır |
| POST | `/api/checkout/{session_id}/cancel` | Kassadan geri qaytarır |
| GET | `/api/map` | Mağaza planı (şəbəkə, rəflər, giriş, kassalar) |
| GET | `/api/products/search` | `?q=&basket_id=` → ən uyğun 8 məhsul + səbətdən məsafə |
| GET | `/api/navigation/route` | `?basket_id=&product_id=` → yol, məsafə, vaxt, addımlar |
| POST | `/api/baskets/{id}/position` | `{x, y}` — səbətin yeri (demo üçün əl ilə) |
| GET | `/api/analytics/summary` | KPI-lar |
| GET | `/api/analytics/top-products` | Ən çox satılanlar |
| GET | `/api/analytics/zones` | Zona ziyarətləri, orta qalma vaxtı, konversiya |
| GET | `/api/analytics/hourly` | Saatlara görə trafik |
| GET | `/api/analytics/co-purchase` | Birlikdə alınan məhsul cütləri |
| GET | `/api/analytics/searches` | Ən çox axtarılan, tapılmayan və ən çox yolu soruşulan məhsullar |
| GET | `/api/analytics/live` | Hazırda aktiv səbətlər və onların zonası |
| POST | `/api/analytics/ai-report` | AI ilə tövsiyə hesabatı |
| POST | `/api/dev/simulate?sessions=500` | Keçmiş data generasiyası |
| POST | `/api/dev/reset` | Bazanı sıfırla + seed |

---

## FAZA 0 — Mühitin qurulması

**Məqsəd:** Bütün alətlər hazırdır, `npm run dev` hər iki serveri açır.

**Addımlar:**
1. Versiyaları yoxla: `node -v` (≥ 20), `npm -v`, `python --version` (≥ 3.11; Windows-da `py --version` də yoxla), `git --version`.
   - Nəsə yoxdursa **dayan** və istifadəçiyə quraşdırma əmrini göstər:
     - Windows: `winget install OpenJS.NodeJS.LTS`, `winget install Python.Python.3.12`, `winget install Git.Git`
     - macOS: `brew install node python@3.12 git`
   - Quraşdırmadan sonra VS Code-u yenidən açmaq lazım ola bilər (PATH yenilənməsi üçün).
2. Əməliyyat sistemini müəyyən et (Windows / macOS / Linux) — sonrakı əmrlər buna uyğun yazılacaq.
3. `git init`, `.gitignore` yarat: `node_modules/`, `.venv/`, `__pycache__/`, `.env`, `*.db`, `dist/`, `.DS_Store`.
4. `CLAUDE.md` yarat — Bölmə 2-dəki “Əsas prinsiplər”i ora köçür.
5. **Backend:**
   - `backend/` yarat, içində virtual mühit: `python -m venv .venv`
   - `requirements.txt`: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `pydantic-settings`, `python-dotenv`, `rapidfuzz`, `pytest`, `httpx`
     (Faza 9-dakı AI tövsiyələr üçün lazım olarsa, model SDK-sı həmin fazada əlavə edilir.)
   - Paketləri venv-in python-u ilə quraşdır.
   - `.env.example`:
     ```
     DATABASE_URL=sqlite:///./smartbasket.db
     STORE_NAME=Smart Market
     ADMIN_PIN=
     ```
   - `.env.example`-ı `.env`-ə kopyala.
   - Minimal `app/main.py` — yalnız `/api/health`.
6. **Frontend:**
   - `npm create vite@latest frontend -- --template react-ts`
   - Paketlər: `react-router-dom`, `recharts`, `html5-qrcode`, `qrcode.react`, `jsbarcode`, `lucide-react`
   - Tailwind CSS-i **hazırkı rəsmi Vite təlimatına** uyğun quraşdır (versiyaya görə addımlar fərqlənir — rəsmi sənədə bax).
   - `vite.config.ts`: `server.host = true`, `server.proxy['/api'] → http://localhost:8000`.
7. **Root `package.json`:** `concurrently` ilə `npm run dev` hər iki serveri işə salsın. Backend əmri venv-in python yolunu ƏS-ə görə istifadə etsin (Windows: `.venv\Scripts\python`, macOS/Linux: `.venv/bin/python`) → `python -m uvicorn app.main:app --reload --port 8000`.

**Yoxlama:**
- [ ] `npm run dev` → `http://localhost:5173` açılır
- [ ] `http://localhost:8000/docs` Swagger açılır, `/api/health` → `{"status":"ok"}`
- [ ] `http://localhost:5173/api/health` proxy vasitəsilə işləyir

**Commit:** `chore: project scaffolding (FastAPI + React/Vite)`

---

## FAZA 1 — Backend skeleti, DB və demo data

**Məqsəd:** Baza cədvəlləri, realist demo məhsullar, əsas oxuma endpoint-ləri.

**Addımlar:**
1. `config.py` — `.env`-i pydantic-settings ilə oxu (`DATABASE_URL`, `STORE_NAME`, `ADMIN_PIN`).
2. `db.py` — SQLModel engine, `get_session` dependency, startup-da `create_all`.
3. `models.py` — Bölmə 4-dəki bütün cədvəllər.
4. `seed.py` (`python -m app.seed --reset` ilə işləsin, təkrar işlədiləndə dublikat yaratmasın):
   - **Zonalar (12×8 şəbəkə):** Giriş, Meyvə-Tərəvəz, Çörək və Unlu məmulatlar, Süd məhsulları, Ət və Toyuq, Bakaleya (düyü, makaron, yağ), Çay-Qəhvə, İçkilər, Şirniyyat və Qəlyanaltı, Təmizlik və Gigiyena, Uşaq məhsulları, Kassa. Hər zonaya fərqli rəng.
   - **~45 məhsul** Azərbaycan mağazasına uyğun: Süd 2.5% 1L, Qatıq, Pendir (ağ), Kərə yağı, Çörək (zavod), Lavaş, Alma, Banan, Pomidor, Xiyar, Kartof, Toyuq filesi, Mal əti, Düyü 1kg, Makaron, Günəbaxan yağı, Qara çay 250q, Qəhvə, Su 1.5L, Kola 1L, Şirə, Şokolad, Peçenye, Çips, Diş pastası, Şampun, Sabun, Qab yuyan, Uşaq bezi və s.
   - Qiymətlər real AZN aralığında (qəpiklə saxla).
   - **Barkodlar:** etibarlı EAN-13, `476` prefiksi ilə (Azərbaycanın GS1 prefiksi). Yoxlama rəqəmini hesablayan `ean13_check_digit()` helper yaz.
   - `keywords`: AZ + RU + EN sinonimlər və ümumi səhv yazılışlar (məs. Qəhvə: `qehve, kofe, coffee, кофе`).
   - Hər məhsula `aisle` (Rəf 1–12), `shelf` (Yuxarı/Orta/Aşağı), `emoji`.
   - **10 səbət:** `BSK-001` … `BSK-010`, hamısı `idle`.
5. Routerlər: `products.py` (`GET /api/products`, `GET /api/products/barcode/{code}`), `GET /api/zones`, `GET /api/baskets`.
6. Xəta mesajları Azərbaycan dilində: `{"detail": "Bu barkodla məhsul tapılmadı"}`.

**Yoxlama:**
- [ ] Seed işləyir, təkrar işlədəndə dublikat yoxdur
- [ ] Swagger-də ~45 məhsul, 12 zona, 10 səbət
- [ ] Bütün barkodların EAN-13 yoxlama rəqəmi düzgündür (kiçik test yaz)
- [ ] Mövcud olmayan barkod → 404 + AZ mesaj

**Commit:** `feat(backend): models, seed data and read endpoints`

---

## FAZA 2 — Səbət və kassa məntiqi + testlər

**Məqsəd:** Layihənin ürəyi — skan → yekun → QR → ödəniş → sıfırlama.

**Addımlar:**
1. `services/cart.py` — bütün biznes məntiqi burada (routerlər nazik qalsın):
   - `get_or_start_session(basket)` — aktiv sessiya yoxdursa yarat, `session_start` event, səbət `active`.
   - `scan(basket_id, barcode, mode)`:
     - Səbət `checkout` statusundadırsa → 409 `"Səbət kassadadır, skan mümkün deyil"`.
     - `add`: məhsul varsa `qty + 1`, yoxsa yeni sətir. `scan_add` event (məhsulun `zone_id` ilə).
     - `remove`: `qty - 1`, 0 olarsa sətri sil. Səbətdə yoxdursa 400 `"Bu məhsul səbətdə yoxdur"`.
     - Məhsulun zonası səbətin cari zonasından fərqlidirsə → avtomatik `zone_enter` event + `current_zone_id` yenilə (yer təyini simulyasiyası).
     - `last_seen_at` yenilə.
   - `get_cart(basket_id)` → `{basket_id, session_id, status, items: [{item_id, product, qty, line_total_qepik}], item_count, total_qepik, current_zone}`.
2. `checkout.py`:
   - `lookup(qr_payload)` — `SMARTBASKET:BSK-001` formatını parse et (sadəcə `BSK-001` də qəbul et). Səbət boşdursa 400 `"Səbət boşdur"`. Sessiya və səbəti `checkout` et, `checkout_started_at` yaz, `checkout_start` event.
   - `pay(session_id, method)` — `payments` yaz (`checkout_seconds` = indi − `checkout_started_at`), sessiya `paid`, `ended_at`, `total_qepik` donur; səbət `idle`, `current_session_id = NULL`, `current_zone_id = NULL` → **səbət sıfırlandı**. `payment` event. Qəbz məlumatını qaytar.
   - `cancel(session_id)` — geri `active`.
   - Stok: ödənişdə `stock` azalt.
3. Routerləri Bölmə 5-ə uyğun qoş.
4. `tests/test_flow.py` (ayrıca test bazası ilə):
   - Tam axın: 2 məhsul əlavə → biri təkrar → biri çıxart → total düzgün → lookup → pay → cart boş, səbət `idle`.
   - Kassada olan səbətə skan → 409.
   - Naməlum barkod → 404.
   - Boş səbət lookup → 400.
   - Ödənişdən sonra yeni skan → **yeni** session_id yaranır.

**Yoxlama:**
- [ ] `pytest` — bütün testlər yaşıl
- [ ] Swagger-dən əl ilə tam axın keçir

**Commit:** `feat(backend): basket scanning, checkout, payment and reset flow`

---

## FAZA 3 — Frontend skeleti və dizayn sistemi

**Məqsəd:** Marşrutlar, API klienti, ümumi görünüş.

**Addımlar:**
1. `api.ts` — tipli funksiyalar (hər endpoint üçün), xətaları `detail` mesajı ilə at.
2. `utils/format.ts` — `formatAZN(qepik) → "12.50 ₼"`.
3. Marşrutlar: `/` Home, `/basket/:basketId`, `/checkout`, `/admin`, `/print`, `/demo`.
4. **Home** — 4 böyük kart (Səbət cihazı → səbət seçimi, Kassa, Admin, Çap) + layihənin bir cümləlik təsviri. Hakimlər ilk bunu görəcək.
5. **Dizayn:**
   - Brend: “Smart Basket”, əsas rəng yaşıl (`#16a34a`), tünd neytral fon elementləri, Inter şrifti.
   - Səbət ekranı **mobil/planşet üçün** (böyük toxunma düymələri, min 48px).
   - Kassa ekranı **böyük rəqəmlərlə** (yekun məbləğ uzaqdan oxunmalıdır).
   - Ümumi `Toast` komponenti (yaşıl uğur / qırmızı xəta).
   - Bütün mətnlər Azərbaycan dilində.

**Yoxlama:**
- [ ] Bütün marşrutlar açılır, Home-dan keçidlər işləyir
- [ ] Telefon eyni Wi-Fi-da `http://<noutbuk-IP>:5173` ilə açılır

**Commit:** `feat(frontend): routing, api client, design system`

---

## FAZA 4 — Səbət cihazı ekranı (`/basket/:basketId`)

**Məqsəd:** Müştərinin səbətdə gördüyü ekran.

**Addımlar:**
1. **Başlıq:** səbət ID-si, status nişanı, **böyük yekun məbləğ**, məhsul sayı.
2. **`BarcodeScanner` komponenti — 3 giriş üsulu (demo səhnədə uğursuz olmasın deyə):**
   - **Kamera:** `html5-qrcode`, formatlar EAN-13, EAN-8, CODE-128, QR. Eyni kod 1.5 saniyə ərzində təkrar oxunmasın (debounce). Arxa kamera üstünlük.
   - **USB/Bluetooth skaner:** global `keydown` dinləyicisi — simvollar <50 ms aralıqla gəlirsə buferə yığ, `Enter` gələndə skan et (input fokusda olmasa belə).
   - **Əl ilə:** barkod daxil etmə sahəsi + “Demo məhsullar” düyməsi → məhsul şəbəkəsi (emoji + ad + qiymət), toxunanda skan kimi işləyir.
3. **Rejim keçidi:** böyük “➕ Əlavə et / ➖ Çıxart” keçidi. Çıxart rejimi qırmızı rəngdə olsun.
4. **Əks-əlaqə:** WebAudio ilə qısa “bip” (uğur: yüksək ton, xəta: aşağı ton), `navigator.vibrate`, toast: `“Süd 2.5% əlavə olundu · +1.89 ₼”`.
5. **`CartList`:** məhsullar (emoji, ad, qiymət × say, sətir cəmi), `+`/`−` düymələri, sil. Yekunu həmişə backend cavabından götür.
6. **Polling (2 san):**
   - Status `checkout` → tam ekran kilid: “Kassada ödəniş gözlənilir…”
   - Sessiya ödənildi (status `idle`, əvvəlki session_id fərqli) → tam ekran “Təşəkkür edirik! 🎉 Səbət sıfırlandı” (4 san), sonra boş vəziyyət.
7. **“QR kodu göstər” düyməsi** — səbətin QR kodunu modalda göstər (demoda kassa kamerası ekrandan oxuya bilsin).
8. **Boş vəziyyət:** “Məhsulu skan edərək alış-verişə başlayın” + illüstrativ ikon.
9. **Telefonda kamera üçün HTTPS:** brauzerlər kameranı yalnız `localhost` və ya HTTPS-də açır. `@vitejs/plugin-basic-ssl` əlavə et, `HTTPS=1` env dəyişəni ilə aktiv olsun (`npm run dev:https`). README-də izah et: telefonda sertifikat xəbərdarlığını qəbul etmək lazımdır.

**Yoxlama:**
- [ ] Noutbuk kamerası ilə çap edilmiş/ekrandakı barkod oxunur
- [ ] Klaviaturada sürətlə barkod yazıb Enter → skan işləyir (USB skaner simulyasiyası)
- [ ] Demo məhsullar siyahısı ilə əlavə/çıxartma işləyir, yekun düzgündür
- [ ] Naməlum barkod → qırmızı toast

**Commit:** `feat(frontend): smart basket device screen`

---

## FAZA 5 — Kassa ekranı (`/checkout`)

**Məqsəd:** Kassir QR oxudur → yekun dərhal → ödəniş → səbət sıfırlanır.

**Addımlar:**
1. **Skan rejimi:** kamera ilə QR oxuma (eyni `BarcodeScanner`, QR rejimi) + USB skaner + ehtiyat üçün “Səbət seçin” dropdown (aktiv səbətlər).
2. **Nəticə ekranı:**
   - Səbət ID, məhsul siyahısı (oxumaq üçün), məhsul sayı.
   - **Nəhəng yekun məbləğ.**
   - Düymələr: “💵 Nağd”, “💳 Kart”, “Ləğv et”.
3. **Ödənişdən sonra:** qəbz modalı (mağaza adı, tarix, məhsullar, cəm, ödəniş üsulu) — `window.print()` üçün print CSS. “Növbəti müştəri” → avtomatik skan rejiminə qayıt (5 san).
4. **Vaxt qənaəti nişanı** (pitch üçün güclü arqument):
   - Faktiki: QR oxunmasından ödənişə qədər saniyə.
   - Ənənəvi təxmini: `20 san + 3 san × məhsul sayı` (sabitlər `constants.ts`-də, şərhlə: “fərziyyə, pitch-də mənbə göstər”).
   - Göstər: “Bu ödəniş 6 san çəkdi · ənənəvi kassada ~65 san”.

**Yoxlama:**
- [ ] İki brauzer tabı: birində səbət, digərində kassa. Kassa QR oxuyur → yekun eynidir → Kart → səbət tabında “Səbət sıfırlandı” görünür
- [ ] Ləğv et → səbət yenidən skan edilə bilir

**Commit:** `feat(frontend): checkout screen with QR lookup and payment`

---

## FAZA 6 — Çap səhifəsi (`/print`) → MVP

**Addımlar:**
1. **Səbət QR kodları:** hər səbət üçün kart (QR + “BSK-001” + “Smart Basket” loqo mətni), A4-də 6 kart.
2. **Məhsul barkodları:** `jsbarcode` ilə EAN-13, altında ad və qiymət. A4-də şəbəkə.
3. Print CSS: düymələr gizlənsin, kartlar səhifə arasında bölünməsin.

**Yoxlama:**
- [ ] Çap önizləməsi düzgündür
- [ ] Çap edilmiş (və ya ekrandakı) barkodu kamera oxuyur

**Commit:** `feat: printable basket QR codes and product barcodes`
**Git tag:** `v0.1-mvp` ✅ — bu nöqtədə demo artıq mümkündür.

---

## FAZA 7 — Mağaza xəritəsi və naviqasiya

**Məqsəd:** Müştəri məhsulu axtarır → xəritədə onun dəqiq yeri və oraya gedən yol göstərilir.

> **Əsas qayda:** məhsulun yeri və ona gedən yol **heç vaxt AI ilə təxmin edilmir**.
> Yer bazada dəqiq koordinat kimi yazılıb, yol isə A\* alqoritmi ilə hesablanır.
> Nəticə deterministikdir, oflayn işləyir və API xərci yoxdur.

### 7.1 Mağaza planı (tək həqiqət mənbəyi)

`backend/app/store_layout.py` — mağaza ASCII şəbəkə kimi təsvir olunur, təxminən
**28 sütun × 18 sətir**, 1 xana = 1 metr. Komanda bu faylı redaktə edərək real
mağazanın planını bir neçə dəqiqəyə çəkə bilər.

| Simvol | Mənası |
|---|---|
| `#` | divar |
| `.` | keçid (yerimək mümkündür) |
| `@` | giriş |
| `$` | kassa |
| `A`–`Z` | həmin zonaya aid rəf xanası (yerimək mümkün deyil) |

Plan realist olmalıdır: kənarlarda divarlar; giriş aşağı-solda, kassalar aşağıda;
perimetr boyu təzə məhsullar (meyvə-tərəvəz, ət, süd); ortada 6–8 şaquli rəf
cərgəsi, aralarında 2 xana enində keçid; cərgələrin hər iki ucunda üfüqi keçid.

Fayldakı `ZONES` lüğəti zona kodunu ada və rəngə bağlayır:
`{"A": {"name": "Meyvə-Tərəvəz", "color": "..."}, ...}` — mövcud zonalarla uyğun.

Bitişik rəf xanaları bir **blok** sayılır və avtomatik nömrələnir
(`Rəf 1`, `Rəf 2`, … yuxarıdan aşağı, soldan sağa).

Parser planı bu struktura çevirir:
`{width, height, cells, walkable, shelves[{id, label, zone_code, cells}], entrance, checkouts}`.

**Qayda:** hər rəf xanasının ən azı bir qonşu keçid xanası olmalıdır (testlə yoxlanılır).

### 7.2 Məhsul yerləri

- `products` cədvəlinə: `shelf_x`, `shelf_y` (rəf xanası) və `level`
  (`Yuxarı` | `Orta` | `Aşağı`). `aisle` mətni rəf nömrəsindən avtomatik gəlir.
- `pick_point` — rəf xanasına bitişik keçid xanası (müştərinin dayanacağı yer),
  seed zamanı hesablanıb saxlanılır.
- Seed hər məhsulu öz zonasındakı rəf xanalarından birinə yerləşdirir, bir xanaya
  2-dən çox məhsul düşmür. **Mövcud məhsullar, barkodlar və qiymətlər dəyişmir.**
- `baskets` cədvəlinə `pos_x`, `pos_y`. Sessiya başlayanda bu yer girişdir.

### 7.3 Yol tapma — `backend/app/services/navigation.py`

- **A\*** xarici kitabxana olmadan: 4 istiqamət (diaqonal yox), Manhattan evristikası.
- Yol heç vaxt divardan və ya rəf xanasından keçmir.
- Yol seqmentlərə bölünür və Azərbaycan dilində addım-addım təlimat yaranır:
  “Düz 6 m gedin”, “Sağa dönün, 4 m gedin”. Sağ/sol dönüş hərəkət istiqamətinə
  görə **vektor hasili** ilə hesablanır.
- Son addımda rəfin müştərinin sağında, yoxsa solunda olduğu deyilir:
  “Rəf 7, orta rəf — sağ tərəfdə”.
- Cavabda məsafə (metr) və təxmini vaxt. Yeriş sürəti **1.2 m/san**.

### 7.4 API

| Metod | Yol | Təsvir |
|---|---|---|
| GET | `/api/map` | Hazır plan; frontend xəritəni bundan çəkir |
| GET | `/api/products/search?q=&basket_id=` | Ən uyğun 8 nəticə: məhsul, zona, rəf, səviyyə, qiymət, stok, **səbətdən məsafə** |
| GET | `/api/navigation/route?basket_id=&product_id=` | `{start, goal, path, distance_m, eta_seconds, steps, shelf}` |
| POST | `/api/baskets/{id}/position` | `{x, y}` — yalnız keçid xanası, əks halda 400 |

- Axtarış `rapidfuzz` ilə ad, kateqoriya və `keywords` üzrə aparılır.
  Azərbaycan hərfləri normallaşdırılır (`ə→e, ı→i, ö→o, ü→u, ç→c, ş→s, ğ→g`),
  böyük/kiçik hərf fərqi nəzərə alınmır, AZ/RU/EN sinonimlər `keywords`-dədir.
  **Minimum uyğunluq həddi** var ki, mənasız sorğu nəticə qaytarmasın.
- Hər axtarış `search_queries` cədvəlinə yazılır
  (`query, found, top_product_id, basket_id, session_id, ts`) və `events`-ə `nav_search`.
- Marşrut sorğusu `events`-ə `nav_route` yazır.
- **Skan zamanı** səbətin yeri avtomatik həmin məhsulun `pick_point`-inə keçir
  (müştəri o rəfin yanında dayanır). Köhnə zona izləmə məntiqi bununla əvəzlənir;
  zona dəyişəndə `zone_enter` event-i yenə yazılır ki, analitika qorunsun.

### 7.5 Frontend

`StoreMap` yenidən yazılır — SVG, `viewBox` şəbəkədən hesablanır, telefonda
üfüqi sürüşdürmə olmadan ekrana sığır.

- Keçidlər açıq fonda, rəflər zona rəngində, divarlar tünd; giriş və kassalar ikonla;
  rəf bloklarının üzərində zona adları və rəf nömrələri kiçik yazı ilə.
- “Siz buradasınız” — pulsasiya edən mavi nöqtə.
- Hədəf rəf xanası yanıb-sönür, üzərində 📍 işarəsi.
- Yol qalın, yuvarlaq künclü xətt; `stroke-dashoffset` ilə “axan” animasiya.
- Demo üçün: keçid xanasına toxunanda “Mən buradayam” → `POST position`, yol yenidən hesablanır.
- Admin paneldəki istilik xəritəsi və canlı səbət nöqtələri (`pos_x`, `pos_y`) də
  bu komponentlə işləyir.

Səbət ekranında **“🔍 Məhsul tap”** (əvvəlki “🤖 Köməkçi”nin yerinə):

- Axtarış sahəsi — yazdıqca nəticə (200 ms debounce), altında populyar axtarış çipləri.
- Nəticə kartı: emoji, ad, qiymət və yer —
  “Süd məhsulları · Rəf 4 · Orta rəf · 18 m”.
- Karta toxunanda: tam ekran xəritə və yol; yuxarıda “18 m · ~15 san” kartı;
  aşağıda addım-addım təlimat siyahısı.
- Hədəf məhsul skan ediləndə **“✅ Tapdınız!”** toast-u və naviqasiya bağlanır.
- Səbətin yeri dəyişəndə (skan və ya toxunma) yol avtomatik yenilənir.
- Məhsul tapılmayanda “Bu məhsul mağazamızda yoxdur” + 3-ə qədər oxşar təklif.

### 7.6 AI-ın çıxarılması

AI köməkçinin router-i, servisi, `AssistantChat` komponenti və ona aid düymələr silinir.
`ai_queries` cədvəli `search_queries` ilə əvəzlənir, bağlı analitika endpoint-i uyğunlaşdırılır.
Admin paneldəki “AI tövsiyələr” **qalır** — o, məhsul yeri ilə bağlı deyil.

### Yoxlama

- [ ] Planda hər rəf xanasının qonşu keçid xanası var; giriş və kassalar keçid xanasıdır
- [ ] Girişdən hər məhsula yol mövcuddur
- [ ] Yol divardan/rəfdən keçmir, ardıcıl xanalar qonşudur
- [ ] A\*-ın tapdığı yol BFS ilə tapılan ən qısa yolla eyni uzunluqdadır (təsadüfi nöqtələrlə)
- [ ] Axtarış: `dis pastasi`→Diş pastası, `kofe`→Qəhvə, `молоко`→Süd, `qwerty`→boş + `found=false`
- [ ] `/basket/BSK-001` → “Məhsul tap” → “süd” → xəritədə girişdən süd rəfinə yol və təlimatlar
- [ ] Başqa məhsul skan edəndə “Siz buradasınız” oraya keçir və yol yenilənir
- [ ] Hədəf məhsul skan edəndə “Tapdınız!” çıxır
- [ ] Telefonda xəritə ekrana sığır
- [ ] Mövcud bütün testlər yaşıl qalır

**Commit:** `feat: store map navigation with A* pathfinding, remove AI assistant`

---

## FAZA 9 — Analitika paneli və data simulyatoru

**Məqsəd:** Mağaza menecerinə dəyərli fikirlər göstərmək. Demoda boş panel olmasın deyə keçmiş data generasiya edilir.

**Addımlar:**
1. **`services/simulator.py`** — `simulate(sessions=500, days=14)`:
   - Pik saatlar: 12–14 və 18–21; həftəsonu daha çox.
   - Marşrut: Giriş → 3–7 zona → Kassa; hər zonada 30 san – 6 dəq qalma.
   - Məhsul əlaqələri: çörək + süd, çips + kola, çay + şirniyyat, makaron + pendir (birlikdə alınma ehtimalı yüksək).
   - Bəzi zonalara baxılır, amma alınmır (konversiya fərqi görünsün).
   - Ödəniş vaxtı 4–12 san.
   - Axtarış sorğuları, o cümlədən tapılmayan məhsullar (avokado, kinoa, laktozasız süd).
   - Səbətlərin hərəkəti yeni şəbəkədə A\* ilə hesablanmış real yollarla.
   - Bütün eventlər real ardıcıllıqla, keçmiş tarixlərlə.
   - `POST /api/dev/simulate` və `POST /api/dev/reset`.
2. **`services/analytics.py` + endpoint-lər:**
   - `summary`: bu günkü dövriyyə, sessiya sayı, orta səbət dəyəri, orta məhsul sayı, orta ödəniş vaxtı, **ümumi qənaət edilmiş vaxt (saat)** = Σ(ənənəvi təxmin − faktiki).
   - `top-products`: miqdar və gəlirə görə.
   - `zones`: ziyarət sayı, orta qalma vaxtı, **konversiya** (zonaya girən sessiyaların neçə %-i oradan alıb).
   - `hourly`: saatlara görə sessiyalar.
   - `co-purchase`: ən çox birlikdə alınan 10 cüt.
   - `searches`: ən çox axtarılan məhsullar; axtarılıb tapılmayanlar (tələb siqnalı); ən çox yolu soruşulan məhsullar (“müştərilər bunları çətin tapır, yerini dəyişməyi düşünün”).
   - `live`: aktiv səbətlər + cari zonalar.
3. **Admin səhifəsi (`/admin`):**
   - KPI kartları (sırada): Dövriyyə · Sessiyalar · Orta səbət · Orta ödəniş vaxtı · **Qənaət edilmiş vaxt**.
   - Saatlıq trafik (xətt qrafiki).
   - Top məhsullar (bar qrafiki).
   - `StoreMap` — **istilik xəritəsi** rejimi (ziyarət sayına görə) + canlı səbət nöqtələri (`pos_x`, `pos_y`).
   - Zona cədvəli: ziyarət, orta qalma, konversiya (aşağı konversiyalı zonalar qırmızı).
   - “Birlikdə alınanlar” cədvəli.
   - Üç axtarış bölməsi: “Ən çox axtarılan məhsullar”, “Axtarılıb tapılmayanlar (tələb siqnalı)”, “Ən çox yolu soruşulan məhsullar”.
   - Düymələr: “Demo data yarat (500 sessiya)”, “Bazanı sıfırla”.
   - Avtomatik yenilənmə: 5 san.
4. **AI hesabat:** “🤖 Tövsiyələr al” düyməsi → analitikanın xülasə JSON-u Claude-a göndərilir → Azərbaycan dilində 3–5 konkret tövsiyə (məs. “Çipsləri kola rəfinin yanına köçürün”). Oflayn rejimdə qaydaya əsaslanan tövsiyələr.

**Yoxlama:**
- [ ] Simulyasiyadan sonra bütün qrafiklər dolu və məntiqlidir
- [ ] Yeni canlı alış-veriş (Faza 4–5 axını) panelə 5 san ərzində düşür
- [ ] AI tövsiyələri (və oflayn versiya) işləyir

**Commit:** `feat: analytics dashboard, data simulator and AI insights`

---

## FAZA 10 — Cilalama, demo rejimi və pitch materialları

**Addımlar:**
1. **`/demo` səhifəsi (proyektor üçün):** ekran ikiyə bölünür — solda səbət cihazı (`BSK-001`, telefon çərçivəsi içində), sağda kassa. Yuxarıda kiçik canlı KPI zolağı. Bütün demo bir ekranda göstərilə bilər.
2. Bütün ekranlarda yüklənmə, xəta və boş vəziyyətlər; bütün mətnlər AZ dilində yoxlanılsın.
3. `npm run reset-demo` — bazanı sıfırla + seed + 500 sessiya simulyasiya.
4. **README.md:** problem, həll, funksiyalar, quraşdırma, işə salma, telefonla qoşulma (HTTPS), arxitektura, API, gələcək planlar.
5. **docs/ARCHITECTURE.md** — mermaid diaqramları:
   - Sistem arxitekturası (Səbət cihazı → API → SQLite; Kassa; Admin; A\* naviqasiya modulu).
   - Alış-veriş axını (ardıcıllıq diaqramı: skan → QR → ödəniş → sıfırlama).
   - Verilənlər modeli (ER diaqramı).
6. Hər ekranın skrinşotunu `docs/screenshots/`-a çəkmək üçün istifadəçiyə siyahı ver (və ya Playwright quraşdırılıbsa avtomatik çək).
7. Kodu son dəfə gözdən keçir: istifadə olunmayan fayllar, konsol xətaları, `.env` commit olunmayıb.

**Yoxlama:**
- [ ] `npm run reset-demo` + `npm run dev` → Bölmə 7-dəki demo ssenarisi əvvəldən sonadək xətasız keçir
- [ ] README-dəki addımlarla təmiz klon işə düşür

**Commit:** `docs: README, architecture, demo mode` · **Git tag:** `v1.0-hackathon`

---

## FAZA 11 — Opsional funksiyalar (yalnız istifadəçi təsdiqi ilə)

| Kod | Funksiya | Dəyər | Vaxt |
|---|---|---|---|
| A | **Çəki sensoru ilə yoxlama** (simulyasiya): səbətin ölçülən çəkisi skan edilən məhsulların çəkisi ilə uyğun gəlmirsə → kassada “Yoxlama tələb olunur” | Oğurluq sualına cavab (hakimlər mütləq soruşacaq) | 40 dəq |
| B | **Alış-veriş siyahısı + optimal marşrut**: müştəri siyahı yazır, bütün məhsulları əhatə edən ən qısa marşrut çəkilir (Faza 7-nin A\*-ı üzərində) | Vaxt qənaəti | 50 dəq |
| C | **Zonaya görə fərdi endirim**: səbət zonaya girəndə həmin zonadakı aksiya göstərilir | Mağaza üçün gəlir modeli | 30 dəq |
| D | **Büdcə limiti**: müştəri limit qoyur, aşanda xəbərdarlıq | Müştəri üçün dəyər, sadə | 15 dəq |
| E | **Kassasız ödəniş**: səbət ekranından birbaşa ödəniş (QR ilə mobil ödəniş simulyasiyası), çıxışda yalnız təsdiq | Növbəni tamamilə aradan qaldırır | 30 dəq |
| F | **Qida məlumatı**: skan edəndə allergen / halal / kalori nişanları | Sağlamlıq | 20 dəq |
| G | **Səsli axtarış** (Web Speech API ilə “süd” deyib axtarmaq) | Yaşlılar üçün əlçatanlıq | 20 dəq |
| H | **Loyallıq balları**: telefon nömrəsi ilə bal toplama | Geri qayıdan müştəri | 30 dəq |
| I | **Stok xəbərdarlığı**: stok azalanda admin panelində bildiriş | Əməliyyat dəyəri | 20 dəq |

---

## 6. Risklər və ehtiyat planı

| Risk | Ehtiyat |
|---|---|
| Səhnədə kamera barkodu oxumur | “Demo məhsullar” əl ilə seçim + USB skaner + klaviatura |
| Telefonda kamera açılmır (HTTPS) | `npm run dev:https` və ya demonu noutbukda `localhost`-da göstər |
| Wi-Fi yoxdur / zəifdir | Hər şey bir noutbukda `localhost` + `/demo` səhifəsi |
| İnternet yoxdur | Naviqasiya tamamilə oflayndır (A\*), AI tövsiyələrinin isə qaydaya əsaslanan versiyası var |
| Baza qarışıb | `npm run reset-demo` |
| Port məşğuldur | Prosesi dayandır və ya portu `.env`-də dəyiş |

---

## 7. Demo ssenarisi (pitch üçün ~3 dəqiqə)

1. **Problem** (15 san): “Orta müştəri kassada X dəqiqə gözləyir.”
2. **Səbət götürülür** — `/demo` səhifəsi, `BSK-001`.
3. **4 məhsul skan edilir**, biri “Çıxart” rejimi ilə geri qaytarılır — yekun canlı yenilənir.
4. **Məhsul tap:** “diş pastası” yazılır → xəritədə rəf yanıb-sönür, yol çəkilir, addım-addım təlimat görünür.
5. **Kassa:** səbətin QR kodu oxudulur → yekun dərhal → “Kart” → səbət ekranında “Səbət sıfırlandı”. Nişan: “6 san · ənənəvi ~65 san”.
6. **Admin paneli:** istilik xəritəsi, “birlikdə alınanlar”, “axtarılıb tapılmayan: avokado”, “ən çox yolu soruşulan məhsullar”, **“X saat qənaət edildi”**, AI tövsiyələri.
7. **Bağlanış:** biznes modeli (mağazaya səbət başına abunə + analitika paketi) və növbəti addımlar (real hardware, BLE, çəki sensoru).
