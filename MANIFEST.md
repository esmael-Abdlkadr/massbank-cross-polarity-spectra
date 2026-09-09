# Upstream manifest and build audit

This dataset is derived, not original. Everything below pins what it was derived
from and records the count removed by each filter, so the licence filtering, the
peak truncation and the reported totals can be checked against a fresh build.

## Upstream pin

| field | value |
|---|---|
| source | [MassBank/MassBank-data](https://github.com/MassBank/MassBank-data) |
| release | **2026.03** |
| release timestamp | **2026-03-16T18:36:30+09:00** |
| `VERSION` file contents | `version = 2026.03` / `timestamp = 2026-03-16T18:36:30+09:00` |
| record files in the release | 139,240 |
| records parsed (≥5 peaks, has ACCESSION) | 109,359 |

The upstream records are not redistributed here; MassBank is the distributor.
`build_release.py` rebuilds these tables from an unpacked copy of that release.

## Reproducing

```bash
# stage 1 — parse the pinned release into an index + peak arrays
python build_release.py parse --records ./MassBank-data-2026.03 --out ./index

# stage 2 — apply the release filters and write spectra.csv / peaks.csv
python build_release.py filter --index ./index --out .
```

Stage 2 prints the audit trail below. A correct rebuild reproduces both files
**byte for byte**; the SHA-256 values are given so this can be verified without
diffing 34,018 rows.

## Filter chain, as printed by the build

Each row is the count entering the filter, the count leaving it, and what it removed.

```
licence in ['CC BY', 'CC0']             109359 ->   42904  (removed 66455)
ms_type == MS2                           42904 ->   41138  (removed  1766)
has InChIKey                             41138 ->   40424  (removed   714)
ion_mode in ['POSITIVE', 'NEGATIVE']     40424 ->   40421  (removed     3)
precursor m/z in (100.0, 700.0)          40421 ->   36436  (removed  3985)
peak count in (6, 400)                   36436 ->   34018  (removed  2418)
non-positive max intensity               34018 ->   34018  (removed     0)
```

**Licence filtering.** Only records whose `LICENSE:` field is exactly `CC BY` or
`CC0` are kept — 66,455 records are dropped at this step, which is the single
largest cut. Nothing under a non-commercial or share-alike licence enters the
release, so the whole derived dataset is redistributable under CC BY 4.0.

**Peak truncation.** For each surviving record the **200 most intense peaks** are
kept (`MAX_PEAKS_KEPT = 200`), intensities are rescaled so the base peak is
999.0, the peak list is re-sorted by m/z, and `log_intensity = log1p(intensity)`
is stored rounded to 5 decimals. m/z is rounded to 4 decimals. Records whose
maximum intensity is not positive would be dropped here; in this release none are.

The pre-truncation peak-count window `(6, 400)` is applied to the *raw* record,
so a record with 400 peaks contributes its strongest 200.

## Release totals

| quantity | value |
|---|---|
| spectra | 34,018 |
| peak rows | 1,054,727 |
| distinct compounds (InChIKey) | 5,396 |
| POSITIVE / NEGATIVE | 26,443 / 7,575 |
| compounds present in **both** polarities | **1,552** |

That last figure is the one that bounds the challenge: only a compound measured
in both polarities can form a cross-polarity pair, so 1,552 compounds are the
entire population the cases are drawn from.

## Checksums

| file | sha256 |
|---|---|
| `spectra.csv` | `598645c59adec93913a12c99b44902358ff03ffcbe667f96e20ddf2610e4006c` |
| `peaks.csv` | `17c997cb4b363680864c3a591263896961d184909d2b67cb8f4e2d2d6f6cd1a7` |

(`peaks.csv` is shipped here gzipped as `peaks.csv.gz`; the hash is of the
uncompressed file that `build_release.py` writes.)

## Licence

Upstream records are CC BY / CC0 by construction of the filter above. The derived
tables in this repository are released under **CC BY 4.0**, attributing MassBank
and the contributing laboratories recorded in the `contributor` column of
`spectra.csv`.
