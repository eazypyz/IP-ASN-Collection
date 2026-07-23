# Alternatif API untuk ASN & Prefix Lookup

## Masalah: BGPView API (api.bgpview.io/search) sudah tidak tersedia

Berikut alternatif yang sudah diintegrasikan ke project:

---

## 1. 🔍 ASN Discovery (Multi-Source)

### Sumber yang Digunakan (berurutan prioritas):

| # | Sumber | Endpoint | Kelebihan | Keterbatasan |
|---|--------|----------|-----------|--------------|
| 1 | **PeeringDB API** | `peeringdb.com/api/net?name__contains={name}` | Data self-reported, akurat untuk peering info | Voluntary, tidak semua ASN terdaftar |
| 2 | **RIPEstat Search** | `stat.ripe.net/data/searchcomplete/data.json` | Search by name/domain, return ASN list | Hanya cover RIPE region (Eropa/Middle East) |
| 3 | **HackerTarget** | `api.hackertarget.com/aslookup/?q={ip}` | Domain → IP → ASN mapping | Rate limit 50 query/hari (free) |
| 4 | **RIPEstat AS Overview** | `stat.ripe.net/data/as-overview/data.json` | Validasi ASN, cek announced status | Hanya enrichment, bukan discovery |

### Cara Kerja:
```
Company Name ──► PeeringDB (name search)
     │
     ├──► PeeringDB (domain search)
     │
     ├──► RIPEstat (name search)
     │
     ├──► RIPEstat (domain search)
     │
     └──► HackerTarget (domain → IP → ASN)
              │
              ▼
         Deduplicate by ASN
              │
              ▼
         Enrich dengan RIPEstat AS Overview
```

---

## 2. 🌍 Prefix Discovery (Multi-Source)

### Sumber yang Digunakan:

| # | Sumber | Endpoint | Data Type |
|---|--------|----------|-----------|
| 1 | **RIPEstat Announced Prefixes** | `stat.ripe.net/data/announced-prefixes/data.json` | Live BGP prefixes (real-time) |
| 2 | **bgp.he.net (scrape)** | `bgp.he.net/AS{asn}` | Live BGP prefixes (fallback) |
| 3 | **RIPEstat Routing Status** | `stat.ripe.net/data/routing-status/data.json` | Validasi visibility |

### Cara Kerja:
```
ASN ──► RIPEstat Announced Prefixes (primary)
           │
           ├──► Jika kosong ──► bgp.he.net scrape (fallback)
           │
           └──► Validasi dengan Routing Status
```

---

## 3. 📋 Detail API Endpoints

### PeeringDB API
```bash
# Search network by name
curl "https://www.peeringdb.com/api/net?name__contains=cloudflare"

# Get network by ASN
curl "https://www.peeringdb.com/api/net?asn=13335"

# Get organization
curl "https://www.peeringdb.com/api/org?asn=13335"
```

### RIPEstat API
```bash
# Search complete (discovery)
curl "https://stat.ripe.net/data/searchcomplete/data.json?query_string=cloudflare"

# AS Overview (detail)
curl "https://stat.ripe.net/data/as-overview/data.json?resource=AS13335"

# Announced Prefixes (prefix list)
curl "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS13335"

# Routing Status (validation)
curl "https://stat.ripe.net/data/routing-status/data.json?resource=AS13335"

# ASN Neighbours
curl "https://stat.ripe.net/data/asn-neighbours/data.json?resource=AS13335"
```

### HackerTarget API
```bash
# IP to ASN lookup
curl "https://api.hackertarget.com/aslookup/?q=1.1.1.1"

# With details
curl "https://api.hackertarget.com/aslookup/?q=8.8.8.8&details=true"
```

### bgp.he.net (HTML Scrape)
```bash
# Not an API, but scrape-able
curl -A "Mozilla/5.0" "https://bgp.he.net/AS13335"
```

---

## 4. 🛡️ Rate Limits & Etika

| Sumber | Rate Limit | Auth Required |
|--------|-----------|---------------|
| PeeringDB API | 120 req/min (unauth) | No (guest OK) |
| RIPEstat API | ~100 req/min | No |
| HackerTarget | 50 req/day (free) | API Key (optional) |
| bgp.he.net | Unknown, be polite | No |

---

## 5. 🔄 Fallback Chain

```
ASN Discovery:
  PeeringDB ──► RIPEstat ──► HackerTarget ──► Manual input

Prefix Discovery:
  RIPEstat ──► bgp.he.net ──► Skip ASN
```

---

## 6. 📦 Tools CLI Alternatif (Opsional)

Jika ingin tools CLI standalone:

```bash
# Install
pip install asnlookup pyasn

# ASN lookup by company name
asnlookup -n "cloudflare"

# Get prefixes for ASN
pyasn_util_download.py --latest
pyasn_util_convert.py rib.20240101.0000.bz2 ipasn.dat
python -c "import pyasn; db = pyasn.pyasn('ipasn.dat'); print(db.lookup('1.1.1.1'))"
```

---

## 7. ✅ Status Update Project

File yang sudah diupdate:
- ✅ `collector/asn.py` — Multi-source ASN discovery
- ✅ `collector/prefix.py` — Multi-source prefix discovery
- ✅ `main.py` — Pipeline orchestrator (no changes needed)
- ✅ `README.md` — Dokumentasi updated

Semua source sudah diimplementasikan dengan **graceful degradation**:
- Jika satu source gagal, lanjut ke source berikutnya
- Jika semua gagal, ASN tetap tersimpan dengan flag `source: "unknown"`
- Tidak ada hard failure, pipeline tetap jalan
