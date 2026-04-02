# Plan: Publish kotlin-mcp ke GitHub Public

## Phase 0: Auto-save summary ke file

**Goal:** Setiap kali `summarize_module_tool` dipanggil, output otomatis tersimpan ke `.kotlin-summary/` di directory yang di-summarize. LLM bisa langsung `Read` file tersebut di conversation berikutnya tanpa harus panggil tool lagi.

### Perubahan

1. **`summarizer.py`** — Modifikasi `summarize_module()`:
   - Setelah generate output, auto-save ke `{target_dir}/.kotlin-summary/{module_name}.md`
   - Buat directory `.kotlin-summary/` kalau belum ada
   - Overwrite file kalau sudah ada (re-index)

2. **`server.py`** — Update docstring `summarize_module_tool` untuk mention auto-save behavior

3. **README.md** — Tambah section yang jelasin:
   - Output tersimpan di `.kotlin-summary/`
   - Tambahkan `.kotlin-summary/` ke `.gitignore` project target
   - Tambah snippet CLAUDE.md yang bisa di-copy user:
     ```
     ## Codebase Summary
     Baca file di `.kotlin-summary/` untuk structural overview module Kotlin/Java.
     ```

### Output format

```
{target_dir}/
└── .kotlin-summary/
    └── {module_name}.md    # plain text summary, sama persis dengan output tool
```

### Edge cases
- Kalau `path` adalah file (bukan directory) → tidak auto-save (hanya `summarize_module_tool` yang save)
- Nama module diambil dari nama directory terakhir di path
- Permission error saat write → log warning, tetap return summary seperti biasa (tidak gagal)

---

## Phase 1: Cleanup sebelum publish

| File | Aksi | Alasan |
|------|------|--------|
| `LICENSE` | Buat baru (MIT) | Wajib untuk public repo |
| `ENGINEERING.md` | Hapus | Internal dev doc, tidak perlu untuk publik |
| `CLAUDE.md` | Tambah ke `.gitignore` | Instruksi lokal, bukan untuk konsumer |
| `pyproject.toml` | Tambah `[project.urls]` | Metadata link ke repo |

## Phase 2: Update README.md

- Tambah instruksi install via `uvx` (dari GitHub)
- Tambah instruksi install via `uv tool install`
- Tambah section `.mcp.json` usage untuk auto-setup
- Update section "Register with Claude Code" — tampilkan kedua metode (manual `claude mcp add` dan `.mcp.json`)

## Phase 3: Buat `.mcp.json.template`

Template yang bisa di-copy user ke project mereka:

```json
{
  "mcpServers": {
    "kotlin-summarizer": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/<username>/kotlin-mcp.git", "kotlin-mcp"]
    }
  }
}
```

## Phase 4: Git/GitHub

1. Buat public repo di GitHub (atau rename `fojako` → `kotlin-mcp`)
2. Commit semua perubahan dari Phase 1-3
3. Push ke GitHub
4. Buat release tag `v0.1.0` — supaya user bisa pin versi:
   ```
   uvx --from "git+https://github.com/<username>/kotlin-mcp.git@v0.1.0" kotlin-mcp
   ```

## Phase 5: Verifikasi

1. Test `uvx --from git+https://github.com/...` dari directory lain (bukan project dir)
2. Test `.mcp.json` di project Android — buka Claude Code, cek `/mcp`
3. Test `uv tool install git+https://github.com/...` untuk persistent install

## Phase 6: Post-Publish (Optional)

- Publish ke PyPI — supaya cukup `uvx kotlin-mcp` tanpa `--from git+...`
- GitHub Actions CI — smoke test on push
