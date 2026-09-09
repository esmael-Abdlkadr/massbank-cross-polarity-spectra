"""Rebuild spectra.csv / peaks.csv from a pinned MassBank-data release.

Two stages, both deterministic and both auditable:

    stage 1  MassBank record files  ->  index.csv + peaks.npz   (parse)
    stage 2  index.csv + peaks.npz  ->  spectra.csv + peaks.csv (filter, truncate)

Every filter prints the row count it removed, so the numbers reported in
MANIFEST.md can be checked line by line against a fresh run.

Usage
-----
    # stage 1: point at an unpacked MassBank-data release (see MANIFEST.md for the pin)
    python build_release.py parse --records ./MassBank-data-2026.03 --out ./index

    # stage 2: apply the release filters
    python build_release.py filter --index ./index --out .

The upstream release is *not* redistributed here. MANIFEST.md pins the exact
version and records the SHA-256 of the two derived tables so a rebuild can be
compared byte for byte.
"""
import argparse
import glob
import hashlib
import os
import re
import sys

import numpy as np
import pandas as pd

# ---- release filters, all of them ------------------------------------------
COMMERCIAL_LICENCES = {"CC BY", "CC0"}      # commercial use must be permitted
MS_TYPE = "MS2"
ION_MODES = ("POSITIVE", "NEGATIVE")
PRECURSOR_MZ_RANGE = (100.0, 700.0)
PEAK_COUNT_RANGE = (6, 400)                 # before truncation
MAX_PEAKS_KEPT = 200                        # truncation: strongest N peaks
INTENSITY_SCALE = 999.0                     # peaks rescaled to a common ceiling
MIN_PEAKS_PARSE = 5                         # a record with fewer is not a spectrum


def _field(pattern, text):
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else ""


def parse(records_dir, out_dir):
    """MassBank .txt records -> index.csv + peaks.npz."""
    files = [f for f in glob.glob(os.path.join(records_dir, "**", "*.txt"), recursive=True)
             if os.path.basename(f).startswith("MSBNK")]
    print("record files found: %d" % len(files), flush=True)
    rows, peaks, skipped_few_peaks = [], {}, 0
    for f in files:
        try:
            t = open(f, encoding="utf8", errors="ignore").read()
        except OSError:
            continue
        acc = _field(r"^ACCESSION:\s*(\S+)", t)
        if not acc:
            continue
        m = re.search(r"^PK\$PEAK:.*$", t, re.M)
        pk = []
        if m:
            for line in t[m.end():].split("\n")[1:]:
                s = line.strip()
                if not s or s.startswith("//"):
                    break
                parts = s.split()
                if len(parts) >= 2:
                    try:
                        pk.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        pass
        if len(pk) < MIN_PEAKS_PARSE:
            skipped_few_peaks += 1
            continue
        rows.append(dict(
            accession=acc,
            license=_field(r"^LICENSE:\s*(.+)$", t),
            inchikey=_field(r"^CH\$LINK: INCHIKEY\s*(\S+)", t),
            ms_type=_field(r"MS_TYPE\s+(\S+)", t),
            ion_mode=_field(r"ION_MODE\s+(\S+)", t),
            instrument_type=_field(r"^AC\$INSTRUMENT_TYPE:\s*(.+)$", t),
            precursor_type=_field(r"PRECURSOR_TYPE\s+(\S+)", t),
            precursor_mz=_field(r"PRECURSOR_M/Z\s+([0-9.]+)", t),
            formula=_field(r"^CH\$FORMULA:\s*(\S+)", t),
            n_peaks=len(pk),
            contributor=acc.split("-")[1] if "-" in acc else "",
        ))
        peaks[acc] = np.array(pk, dtype="float32")
    os.makedirs(out_dir, exist_ok=True)
    idx = pd.DataFrame(rows)
    idx.to_csv(os.path.join(out_dir, "index.csv"), index=False)
    np.savez_compressed(os.path.join(out_dir, "peaks.npz"), **peaks)
    print("parsed %d records (%d skipped: fewer than %d peaks)"
          % (len(idx), skipped_few_peaks, MIN_PEAKS_PARSE))
    print("licences present: %s" % idx["license"].value_counts().head(8).to_dict())
    return idx


def filter_release(index_dir, out_dir):
    """index.csv + peaks.npz -> spectra.csv + peaks.csv, printing every cut."""
    M = pd.read_csv(os.path.join(index_dir, "index.csv"))
    Z = np.load(os.path.join(index_dir, "peaks.npz"))

    def cut(frame, mask, label):
        kept = frame[mask]
        print("  %-38s %7d -> %7d  (removed %d)"
              % (label, len(frame), len(kept), len(frame) - len(kept)))
        return kept

    print("filter chain:")
    M = cut(M, M["license"].isin(COMMERCIAL_LICENCES), "licence in %s" % sorted(COMMERCIAL_LICENCES))
    M = cut(M, M.ms_type == MS_TYPE, "ms_type == %s" % MS_TYPE)
    M = cut(M, M.inchikey.notna() & (M.inchikey.astype(str) != ""), "has InChIKey")
    M = cut(M, M.ion_mode.isin(ION_MODES), "ion_mode in %s" % list(ION_MODES))
    M["precursor_mz"] = pd.to_numeric(M.precursor_mz, errors="coerce")
    M = cut(M, M.precursor_mz.between(*PRECURSOR_MZ_RANGE),
            "precursor m/z in %s" % (PRECURSOR_MZ_RANGE,))
    M = cut(M, M.n_peaks.between(*PEAK_COUNT_RANGE), "peak count in %s" % (PEAK_COUNT_RANGE,))
    M = M.sort_values("accession").reset_index(drop=True)

    spectra, peak_rows, dropped_zero = [], [], 0
    for r in M.itertuples():
        p = Z[r.accession]
        mz, it = p[:, 0].astype("float64"), p[:, 1].astype("float64")
        keep = np.argsort(-it)[:MAX_PEAKS_KEPT]          # truncation: strongest peaks
        mz, it = mz[keep], it[keep]
        top = it.max()
        if not np.isfinite(top) or top <= 0:
            dropped_zero += 1
            continue
        it = it / top * INTENSITY_SCALE                  # common intensity ceiling
        order = np.argsort(mz)                           # re-sorted by m/z for release
        mz, it = mz[order], it[order]
        spectra.append((r.accession, r.inchikey, r.ion_mode, round(float(r.precursor_mz), 4),
                        r.instrument_type, r.contributor, r.license))
        for a, b in zip(mz, it):
            peak_rows.append((r.accession, round(float(a), 4), round(float(np.log1p(b)), 5)))
    print("  %-38s %7d -> %7d  (removed %d)"
          % ("non-positive max intensity", len(M), len(spectra), dropped_zero))

    S = pd.DataFrame(spectra, columns=["spectrum_id", "inchikey", "ion_mode", "precursor_mz",
                                       "instrument_type", "contributor", "license"])
    P = pd.DataFrame(peak_rows, columns=["spectrum_id", "mz", "log_intensity"])
    os.makedirs(out_dir, exist_ok=True)
    S.to_csv(os.path.join(out_dir, "spectra.csv"), index=False)
    P.to_csv(os.path.join(out_dir, "peaks.csv"), index=False)

    both = S.groupby(["inchikey", "ion_mode"]).size().unstack().fillna(0)
    n_both = int(((both.get("POSITIVE", 0) > 0) & (both.get("NEGATIVE", 0) > 0)).sum())
    print("\nrelease totals")
    print("  spectra                %d" % len(S))
    print("  peaks                  %d" % len(P))
    print("  distinct compounds     %d" % S.inchikey.nunique())
    print("  polarity split         %s" % S.ion_mode.value_counts().to_dict())
    print("  compounds in BOTH modes %d   <- the only compounds a case can be built from" % n_both)
    for name in ("spectra.csv", "peaks.csv"):
        h = hashlib.sha256(open(os.path.join(out_dir, name), "rb").read()).hexdigest()
        print("  sha256 %-12s %s" % (name, h))
    return S, P


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    p1 = sub.add_parser("parse"); p1.add_argument("--records", required=True); p1.add_argument("--out", default="index")
    p2 = sub.add_parser("filter"); p2.add_argument("--index", default="index"); p2.add_argument("--out", default=".")
    a = ap.parse_args()
    if a.stage == "parse":
        parse(a.records, a.out)
    else:
        filter_release(a.index, a.out)
