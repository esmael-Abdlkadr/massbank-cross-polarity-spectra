# MassBank Cross-Polarity Tandem Mass Spectra

Tandem mass spectra (MS2) drawn from the open [MassBank](https://massbank.eu/MassBank/) record archive, restricted to records whose individual licence permits commercial use, and organised so that the same chemical compound can be followed across positive and negative ionization modes.

Run one compound in positive mode and in negative mode and the two spectra look almost nothing alike: different adducts form, different bonds break, different fragments reach the detector. This dataset exposes that redundancy directly, pairing spectra by compound identity so cross-mode correspondence can be studied.

## Contents

| File | Rows | Description |
|---|---|---|
| `spectra.csv` | 34,018 | One row per spectrum: identity and acquisition metadata |
| `peaks.csv` | 1,054,727 | One row per fragment peak, keyed by spectrum |

### spectra.csv

| Column | Type | Description |
|---|---|---|
| `spectrum_id` | string | MassBank accession. Primary key. |
| `inchikey` | string | InChIKey of the measured compound; identifies which spectra come from the same substance |
| `ion_mode` | string | `POSITIVE` or `NEGATIVE` ionization polarity |
| `precursor_mz` | float | Precursor ion mass-to-charge ratio, daltons per unit charge |
| `instrument_type` | string | Instrument platform, e.g. `LC-ESI-QTOF` (22 distinct values) |
| `contributor` | string | Contributing laboratory code |
| `license` | string | Licence of that individual MassBank record |

### peaks.csv

| Column | Type | Description |
|---|---|---|
| `spectrum_id` | string | Foreign key into `spectra.csv` |
| `mz` | float | Fragment mass-to-charge ratio, daltons |
| `log_intensity` | float | Natural log of one plus relative intensity; `expm1()` recovers the linear 0-999 value exactly |

## Scale

| | count |
|---|---|
| spectra | 34,018 |
| peaks | 1,054,727 |
| distinct compounds | 5,396 |
| compounds measured in both polarities | 1,552 |
| positive / negative spectra | 26,443 / 7,575 |
| instrument types | 22 |

## Notes

- Masses are in daltons. A positive-mode `[M+H]+` and a negative-mode `[M-H]-` precursor of the same molecule differ by roughly 2.016 daltons.
- Intensities are relative to each spectrum's own base peak, so they are comparable within a spectrum but not across spectra.
- A compound may contribute many spectra differing in collision energy, instrument and laboratory. Spectra of one compound are **not** independent, so any evaluation split must be made on compound identity rather than on individual spectra.
- Positive-mode acquisition is far more common than negative, which is why only about a quarter of compounds carry both.
- Each spectrum retains at most its 200 most intense peaks; spectra with fewer than six peaks are excluded.

## Licence

**Creative Commons Attribution 4.0 International (CC BY 4.0).**

Every record included here is licensed `CC BY` or `CC0` in its own MassBank `LICENSE` field. Records carrying non-commercial (`CC BY-NC`, `CC BY-NC-SA`) or share-alike (`CC BY-SA`) terms were excluded during assembly, so no record in this dataset imposes an obligation stricter than attribution. Both permit commercial use and redistribution with attribution.

## Attribution

Derived from the MassBank record archive maintained by the MassBank consortium:

- Records: https://github.com/MassBank/MassBank-data
- Archive release: https://doi.org/10.5281/zenodo.3378723
- Project: https://massbank.eu/MassBank/

Horai, H., et al., 2010: MassBank: a public repository for sharing mass spectral data for life sciences. *Journal of Mass Spectrometry*, 45, 703-714.
