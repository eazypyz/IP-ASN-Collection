# IP Assets Scanner

Pipeline otomatis untuk mengumpulkan dan memantau IP assets perusahaan menggunakan GitHub Actions.

> **UPDATE 2026**: BGPView API sudah tidak tersedia. Project sekarang menggunakan **multi-source approach** dengan PeeringDB API, RIPEstat API, HackerTarget, dan bgp.he.net sebagai fallback. Lihat `API_ALTERNATIVES.md` untuk detail.

## Arsitektur

```
Company List
     │
     ▼
ASN Collector (PeeringDB + RIPEstat + HackerTarget)
     │
     ▼
Prefix Collector (RIPEstat + bgp.he.net fallback)
     │
     ▼
IP Enumerator
     │
     ▼
HTTP Scanner (httpx)
     │
     ▼
Metadata Collector
     │
     ▼
Screenshot Service (Playwright)
     │
     ▼
JSON Repository (GitHub)
     │
     ├──────────────┐
     ▼              ▼
GitHub Pages   Discord Notifier
```

## Struktur Proyek

```
ip-assets/
├── collector/
│   ├── asn.py          # Multi-source ASN collector
│   ├── prefix.py       # Multi-source prefix collector
│   └── ip.py           # IP enumerator
├── scanner/
│   ├── http.py         # HTTP/HTTPS scanner
│   └── fingerprint.py  # Service fingerprinting
├── screenshot/
│   └── capture.py      # Playwright screenshot
├── notifier/
│   └── discord.py      # Discord webhook notifier
├── storage/
│   └── github.py       # Git commit & compare
├── data/               # Output JSON files
├── .github/workflows/
│   └── scan.yml        # GitHub Actions workflow
├── main.py             # Pipeline orchestrator
├── index.html          # Dashboard GitHub Pages
├── API_ALTERNATIVES.md # Dokumentasi API sources
├── requirements.txt
└── README.md
```

## Multi-Source ASN Discovery

Pipeline mencoba sumber berikut secara berurutan:

1. **PeeringDB API** — `api/net?name__contains={name}`
2. **RIPEstat Search** — `data/searchcomplete/data.json`
3. **HackerTarget** — Domain → IP → ASN mapping
4. **RIPEstat AS Overview** — Enrichment & validation

Jika satu source gagal, otomatis fallback ke source berikutnya.

## Multi-Source Prefix Discovery

1. **RIPEstat Announced Prefixes** — Live BGP data (primary)
2. **bgp.he.net** — HTML scrape (fallback)
3. **RIPEstat Routing Status** — Validasi visibility

## Setup

### 1. Fork Repository

Fork repository ini ke akun GitHub Anda.

### 2. Konfigurasi Secrets

Buka **Settings > Secrets and variables > Actions**, tambahkan:

| Secret | Value |
|--------|-------|
| `DISCORD_WEBHOOK_URL` | URL webhook Discord Anda |

### 3. Konfigurasi GitHub Pages

Buka **Settings > Pages**, set:
- **Source**: Deploy from a branch
- **Branch**: `gh-pages` / `root`

### 4. Sesuaikan Daftar Perusahaan

Edit file `collector/asn.py`, ubah daftar `COMPANIES`:

```python
COMPANIES = [
    {"name": "Nama Perusahaan", "domain": "domain.com"},
]
```

### 5. Jalankan Manual

Buka tab **Actions**, pilih workflow "IP Assets Scanner", klik **Run workflow**.

## Notifikasi Discord

Bot akan mengirim notifikasi untuk:
- ✅ ASN baru ditemukan
- ✅ Prefix baru
- ✅ IP HTTP baru
- ✅ HTTPS baru
- ✅ Screenshot baru
- ✅ Perubahan status (200 → 403, dll.)
- ✅ Server berubah (nginx → envoy)

### Contoh Pesan

**New IP Detected:**
```
📡 New IP Detected
Company : Example Corp
ASN     : AS12345
IP      : 203.0.113.15
Status  : 200
Server  : nginx
Title   : Example Dashboard
HTTPS   : Yes
```

**Daily Summary:**
```
📊 Daily Scan Summary
Company        : Example Corp
New ASN        : 1
New Prefix     : 3
New Alive IP   : 41
Screenshots    : 38
Changed Status : 7
```

## Schedule

Workflow berjalan otomatis setiap **6 jam** (00:00, 06:00, 12:00, 18:00 UTC).

## API Sources & Rate Limits

| Source | Rate Limit | Auth |
|--------|-----------|------|
| PeeringDB API | 120 req/min | No |
| RIPEstat API | ~100 req/min | No |
| HackerTarget | 50/day (free) | Optional API Key |
| bgp.he.net | Be polite | No |

## Teknologi

- **Python 3.11**
- **httpx** — Async HTTP client
- **Playwright** — Browser automation untuk screenshot
- **GitHub Actions** — CI/CD & scheduling
- **GitHub Pages** — Static dashboard
- **Discord Webhook** — Push notifications

## License

MIT
