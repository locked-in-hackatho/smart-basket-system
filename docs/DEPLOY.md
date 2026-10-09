# Vercel-ə deploy

Nəticə: daimi HTTPS linki. Telefon kamerası sertifikat xəbərdarlığı olmadan
işləyir, kassa ekranı kompüterdə açılır və ikisi eyni sistemə qoşulur.

---

## Niyə Postgres lazımdır

Vercel-in fayl sistemi yazıla bilməz və hər çağırışda sıfırlanır, ona görə
SQLite faylı orada yaşaya bilməz. Kod hər iki bazanı dəstəkləyir — fərq
yalnız `DATABASE_URL`-dadır:

| Harada | DATABASE_URL |
|---|---|
| Noutbukda | `sqlite:///./smartbasket.db` |
| Vercel-də | `postgresql://…` (Neon və ya Supabase) |

`postgres://`, `postgresql://` və `postgresql+psycopg://` formatlarının hamısı
qəbul edilir — provayder hansını versə, olduğu kimi yapışdırın.

---

## 1. Pulsuz Postgres (Neon) — ~3 dəqiqə

1. https://neon.tech → **Sign up** (GitHub ilə olar).
2. **Create project** → ad: `smart-basket`, region: Avropa (Frankfurt).
3. Açılan **Connection string**-i kopyalayın. Belə görünür:
   ```
   postgresql://user:password@ep-xxx-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
   **"Pooled connection"** variantını seçin — serverless üçün doğrusu odur.

> Supabase də olar: **Project Settings → Database → Connection string → URI**,
> yenə **Connection pooling** variantını götürün.

---

## 2. Vercel-ə qoşmaq — ~5 dəqiqə

Layihə qovluğunda:

```bash
npx vercel login      # e-poçt və ya GitHub
npx vercel link       # yeni layihə yaradın: smart-basket
```

Mühit dəyişənlərini əlavə edin (hər biri soruşanda dəyəri yapışdırın):

```bash
npx vercel env add DATABASE_URL production
npx vercel env add STORE_NAME production      # məsələn: Smart Market
npx vercel env add ADMIN_PIN production       # özünüz seçin, məs. 4821
```

Sonra deploy:

```bash
npx vercel --prod
```

Vercel sizə belə bir link verəcək: `https://smart-basket-xxxx.vercel.app`

---

## 3. Bazanı doldurmaq — bir dəfəlik

Yeni baza boşdur. Kataloqu və demo datasını yükləyin (PIN-i öz seçdiyinizlə
əvəz edin):

```bash
# Kataloq: 12 zona, 55 məhsul, 10 səbət
curl -X POST "https://SİZİN-LİNK.vercel.app/api/dev/reset" \
     -H "X-Admin-Pin: 4821"

# Analitika üçün keçmiş data (bir neçə dəfə kiçik hissələrlə də olar)
curl -X POST "https://SİZİN-LİNK.vercel.app/api/dev/simulate?sessions=300" \
     -H "X-Admin-Pin: 4821"
```

Admin panelindəki **"Demo data"** və **"Sıfırla"** düymələri də işləyir —
ilk dəfə PIN soruşacaq və sessiya boyu yadda saxlayacaq.

---

## 4. Demo quruluşu

| Cihaz | Açılır |
|---|---|
| 📱 Telefon (səbətin skaneri) | `https://…vercel.app/basket/BSK-001` |
| 💻 Kompüter (kassa) | `https://…vercel.app/checkout` |
| 📊 Kompüter (analitika) | `https://…vercel.app/admin` |
| 🖨️ Çap / böyük barkod | `https://…vercel.app/print` |

Telefonda kamera icazəsi soruşulanda **"Allow"** seçin. Vercel linki real
HTTPS olduğu üçün sertifikat xəbərdarlığı olmayacaq.

---

## Canlı ünvan

**https://hackathon-smartbasket.vercel.app**

Yenidən deploy etmək üçün (giriş bir dəfə edilib):

```bash
npx vercel --prod
```

## Qeydlər

- **`ADMIN_PIN` mütləq qoyun.** O olmasa `/api/dev/*` endpoint-ləri açıq qalır
  və linki bilən hər kəs demonu silə bilər.
- **Soyuq başlanğıc.** Uzun fasilədən sonra ilk sorğu 2–4 saniyə çəkə bilər.
  Demodan bir neçə dəqiqə əvvəl linki bir dəfə açın.
- **Simulyasiya həcmi.** `sessions=500` bir çağırışda 60 saniyə limitini keçə
  bilər; 300-lük iki çağırış daha etibarlıdır.
- **Yerli iş dəyişmir.** `npm run dev` hələ də SQLite ilə işləyir; `.env`
  faylı deploy-a təsir etmir.
- **Python asılılıqları iki yerdədir.** Vercel `api/pyproject.toml` və
  `api/uv.lock` fayllarından quraşdırır, `requirements.txt`-dən yox. Yeni
  paket əlavə edəndə hər ikisini yeniləyin:
  ```bash
  # api/pyproject.toml-a əlavə edin, sonra:
  cd api && uv lock
  ```
  Əks halda build keçir, amma funksiya `ModuleNotFoundError` ilə çökür.
- **Mühit dəyişəni yazarkən PowerShell pipe işlətməyin** — dəyər boş qalır.
  Fayldan oxudun: `npx vercel env add DATABASE_URL production < value.txt`
