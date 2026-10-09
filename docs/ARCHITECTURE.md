# Smart Basket — arxitektura

Bu sənəd sistemin necə işlədiyini üç diaqramla izah edir: komponentlər,
alış-veriş axını və verilənlər modeli.

---

## 1. Sistem arxitekturası

Hər şey bir maşında işləyir. Frontend `/api` sorğularını Vite proxy ilə
backend-ə ötürür — ona görə telefon yalnız frontend ünvanını bilməlidir və
CORS problemi olmur.

```mermaid
graph TB
    subgraph clients["Müştəri cihazları"]
        basket["📱 Səbət cihazı<br/>/basket/:id<br/>göstərici · məhsul tap<br/>(skaner avtomatik oxuyur)"]
        till["🖥️ Kassa<br/>/checkout<br/>QR oxu · ödəniş"]
        admin["📊 Admin<br/>/admin<br/>analitika · istilik xəritəsi"]
        print["🖨️ Çap<br/>/print<br/>QR · barkod"]
    end

    subgraph front["Frontend — React · Vite · TypeScript :5173"]
        router["React Router"]
        apiclient["api.ts<br/>tipli klient"]
        map["StoreMap<br/>SVG xəritə"]
    end

    subgraph back["Backend — FastAPI · SQLModel :8000"]
        routers["Routerlər<br/>products · baskets · checkout<br/>navigation · analytics · dev"]
        cart["services/cart.py<br/>bütün biznes məntiqi<br/>yekun burada hesablanır"]
        nav["services/navigation.py<br/>A* yol tapma"]
        search["services/search.py<br/>rapidfuzz axtarış"]
        stats["services/analytics.py<br/>hesabatlar"]
        sim["services/simulator.py<br/>demo data"]
        layout["store_layout.py<br/>ASCII mağaza planı<br/>tək həqiqət mənbəyi"]
    end

    db[("SQLite<br/>smartbasket.db")]

    basket --> router
    till --> router
    admin --> router
    print --> router
    router --> apiclient
    admin --> map
    basket --> map

    apiclient -->|"/api/* · Vite proxy"| routers
    routers --> cart
    routers --> nav
    routers --> search
    routers --> stats
    routers --> sim
    nav --> layout
    search --> nav
    sim --> nav
    cart --> db
    stats --> db
    search --> db
    sim --> db

    classDef srv fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef cli fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    classDef store fill:#f1f5f9,stroke:#64748b,color:#0f172a
    class cart,nav,search,stats,sim,layout,routers srv
    class basket,till,admin,print cli
    class db store
```

**Qeyd:** məhsulun yeri və ona gedən yol heç vaxt AI ilə müəyyən edilmir.
Yer bazada koordinat kimi saxlanılır, yol isə `navigation.py`-dəki A\*
alqoritmi ilə hesablanır — deterministik, oflayn və pulsuz.

---

## 2. Alış-veriş axını

Səbət fiziki obyektdir (daimi ID), sessiya isə bir alış-veriş səfəridir.
Ödəniş sessiyanı bitirir və səbəti `idle` edir — "sıfırlanma" budur.

```mermaid
sequenceDiagram
    autonumber
    actor M as Müştəri
    participant S as Səbət cihazı
    participant A as API
    participant D as SQLite
    participant K as Kassa

    M->>S: Məhsulu səbətə qoyur
    Note over S: Səbətin skaneri özü oxuyur —<br/>müştəri heç nə etmir
    S->>A: POST /api/baskets/BSK-001/scan
    A->>D: sessiya yarat (ilk skanda)
    A->>D: basket_items += 1 · event: scan_add
    A->>D: səbətin yeri → məhsulun pick_point-i
    A-->>S: {items, item_count, total_qepik}
    Note over S: Yekun həmişə backend-dən gəlir

    M->>S: "Məhsul tap" → "süd"
    S->>A: GET /api/products/search?q=süd
    A-->>S: 8 nəticə + səbətdən məsafə
    S->>A: GET /api/navigation/route
    A->>A: A* ilə yol hesabla
    A-->>S: yol · məsafə · addım-addım təlimat

    M->>K: Səbəti kassaya gətirir
    K->>A: POST /api/checkout/lookup {qr_payload}
    A->>D: sessiya → checkout · səbət kilidlənir
    A-->>K: yekun məbləğ
    Note over S: Ekran kilidlənir:<br/>"Kassada ödəniş gözlənilir…"

    K->>A: POST /api/checkout/{id}/pay {method}
    A->>D: payment · stok azalır · total donur
    A->>D: səbət → idle · yer → giriş
    A-->>K: qəbz
    Note over S: "Təşəkkür edirik! 🎉<br/>Səbət sıfırlandı"
```

---

## 3. Verilənlər modeli

```mermaid
erDiagram
    ZONES ||--o{ PRODUCTS : "yerləşir"
    ZONES ||--o{ EVENTS : "qeyd olunur"
    BASKETS ||--o{ SESSIONS : "səfərlər"
    SESSIONS ||--o{ BASKET_ITEMS : "məhsullar"
    SESSIONS ||--o{ EVENTS : "hadisələr"
    SESSIONS ||--|| PAYMENTS : "ödəniş"
    SESSIONS ||--o{ SEARCH_QUERIES : "axtarışlar"
    PRODUCTS ||--o{ BASKET_ITEMS : "sətirlər"
    PRODUCTS ||--o{ SEARCH_QUERIES : "tapılan"

    ZONES {
        int id PK
        string code "A, B, C…"
        string name
        int x_y_w_h "şəbəkə koordinatları"
        string color
        string kind "sales|entrance|checkout"
    }
    PRODUCTS {
        int id PK
        string barcode UK "EAN-13"
        string name
        int price_qepik "pul tam ədəddir"
        int zone_id FK
        int shelf_x_y "rəf xanası"
        int pick_x_y "müştərinin dayandığı yer"
        string aisle "Rəf 7"
        string level "Yuxarı|Orta|Aşağı"
        int stock
        string keywords "AZ/RU/EN sinonimlər"
    }
    BASKETS {
        string id PK "BSK-001"
        string status "idle|active|checkout"
        int current_session_id
        int pos_x_y "şəbəkədəki yeri"
    }
    SESSIONS {
        int id PK
        string basket_id FK
        string status "active|checkout|paid|abandoned"
        datetime started_at
        datetime checkout_started_at
        datetime ended_at
        int total_qepik "ödənişdə donur"
    }
    BASKET_ITEMS {
        int id PK
        int session_id FK
        int product_id FK
        int qty
    }
    EVENTS {
        int id PK
        int session_id FK
        string type "scan_add|zone_enter|nav_search…"
        int zone_id FK
        int product_id FK
        datetime ts
    }
    PAYMENTS {
        int id PK
        int session_id FK
        int amount_qepik
        string method "cash|card"
        float checkout_seconds
    }
    SEARCH_QUERIES {
        int id PK
        int session_id FK
        string query
        int top_product_id FK
        bool found "tələb siqnalı"
    }
```

---

## 4. Mağaza planı

Mağaza `backend/app/store_layout.py` faylında ASCII şəbəkə kimi təsvir olunub —
1 simvol = 1 m². Bu, bütün sistemin tək həqiqət mənbəyidir: xəritə, yol tapma,
məhsul yerləri və istilik xəritəsi hamısı bu fayldan törəyir.

```
##############################
#AAAAAAAAABBBBBBBBBBCCCCCCCCC#   A  Meyvə-Tərəvəz      #  divar
#............................#   B  Çörək              .  keçid
#............................#   C  Süd məhsulları     @  giriş
#D..FF..GG..HH..II..JJ..KK..C#   D  Ət və Toyuq        $  kassa
#D..FF..GG..HH..II..JJ..KK..C#   F  Bakaleya
#D..FF..GG..HH..II..JJ..KK..C#   G  Çay-Qəhvə
#D..FF..GG..HH..II..JJ..KK..C#   H  İçkilər
#D..FF..GG..HH..II..JJ..KK..C#   I  Şirniyyat
#D..FF..GG..HH..II..JJ..KK..C#   J  Təmizlik
#D..FF..GG..HH..II..JJ..KK..C#   K  Uşaq məhsulları
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#............................#
#............................#
#............................#
#@........$...$...$..........#
##############################
```

Başqa mağazanın planını çəkmək üçün yalnız bu faylı redaktə etmək kifayətdir.
Qayda: hər rəf xanasının ən azı bir qonşu keçid xanası olmalıdır — əks halda
həmin məhsula çatmaq mümkün olmazdı. Bu, testlə yoxlanılır.
