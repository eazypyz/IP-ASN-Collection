# IP Assets Scanner

Pipeline otomatis untuk mengumpulkan dan memantau IP assets perusahaan menggunakan GitHub Actions.

## Arsitektur

```
Company List
     │
     ▼
ASN Collector (BGPView API)
     │
     ▼
Prefix Collector
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
│   ├── asn.py          # ASN collector via BGPView
│   ├── prefix.py       # Prefix collector
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
└── requirements.txt
```

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

## Teknologi

- **Python 3.11**
- **httpx** - Async HTTP client
- **Playwright** - Browser automation untuk screenshot
- **GitHub Actions** - CI/CD & scheduling
- **GitHub Pages** - Static dashboard
- **Discord Webhook** - Push notifications

## License

MIT
