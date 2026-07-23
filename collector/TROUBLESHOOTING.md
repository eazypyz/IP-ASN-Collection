# Troubleshooting Guide

## Masalah: RIPEstat API 502 Bad Gateway / Timeout

### Penyebab
RIPEstat API (`stat.ripe.net`) terkadang mengalami:
- **502 Bad Gateway** — backend server RIPEstat sedang down/overloaded
- **Read timeout** — response terlalu lambat karena server sibuk
- **Maintenance** — RIPEstat sedang maintenance (status bisa cek di https://stat.ripe.net)

Ini adalah masalah **server-side** dari RIPE NCC, bukan bug di kode kita.

### Solusi yang Sudah Diimplementasikan

#### 1. Retry dengan Exponential Backoff
Semua request ke RIPEstat sekarang punya retry otomatis:
```
Attempt 1 → Gagal (502)
  → Wait 2s
Attempt 2 → Gagal (timeout)
  → Wait 4s  
Attempt 3 → Gagal
  → Skip, lanjut ke fallback
```

#### 2. Fallback Chain
Jika RIPEstat gagal, otomatis pindah ke source lain:

**ASN Discovery:**
```
PeeringDB (primary) → RIPEstat (retry 2x) → HackerTarget
```

**Prefix Discovery:**
```
RIPEstat (retry 3x) → bgp.he.net (retry 2x) → bgp.tools (retry 2x)
```

#### 3. Graceful Degradation
Pipeline **tidak pernah crash** meski semua source gagal:
- ASN tanpa prefix → tetap disimpan, prefix collector skip ASN tersebut
- Semua source gagal → data lama tetap ada, tidak di-overwrite dengan kosong

### Checklist Jika Masih Gagal

1. **Cek status RIPEstat manual:**
   ```bash
   curl -I "https://stat.ripe.net/data/as-overview/data.json?resource=AS16509"
   ```

2. **Cek apakah PeeringDB masih jalan:**
   ```bash
   curl "https://www.peeringdb.com/api/net?asn=16509"
   ```

3. **Cek bgp.he.net:**
   ```bash
   curl -A "Mozilla/5.0" "https://bgp.he.net/AS16509"
   ```

4. **Jika semua API down**, pipeline akan:
   - Gunakan data cache dari run sebelumnya
   - Kirim notifikasi Discord: "⚠️ All data sources unreachable, using cached data"
   - Tetap commit data lama (tidak overwrite dengan kosong)

### Tips untuk GitHub Actions

- **Timeout**: Workflow timeout di-set 120 menit, cukup untuk retry
- **Rate limit**: Jangan trigger manual terlalu sering, RIPEstat bisa rate-limit
- **Best time**: RIPEstat lebih stabil di jam non-Eropa (siang/malam Asia)

### Alternatif API Lain (jika RIPEstat down lama)

| API | Endpoint | Use Case |
|-----|----------|----------|
| IPinfo ASN | `ipinfo.io/AS{asn}` | ASN detail & prefixes |
| CAIDA AS Rank | `as-rank.caida.org/api` | ASN ranking & relationships |
| RADb | `whois.radb.net` | WHOIS query |
| Team Cymru | `whois.cymru.com` | ASN lookup via WHOIS |
