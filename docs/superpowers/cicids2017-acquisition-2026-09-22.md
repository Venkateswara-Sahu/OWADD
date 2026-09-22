# CICIDS2017 acquisition receipt

Downloaded on 22 September 2026 with user approval. This receipt records acquisition, not a passed dataset-quality audit.

- Dataset authority: https://www.unb.ca/cic/datasets/ids-2017.html
- The current official download page presents a registration form; the old public archive URL redirected to the UNB dataset index. No personal information was submitted.
- Actual source: public third-party mirror https://huggingface.co/datasets/bencorn/CICIDS2017
- Pinned revision: `811c007f08d693a8a8b4226c197c138391806ce6`
- File: `csvs/GeneratedLabelledFlows.zip`
- Download URL: https://huggingface.co/datasets/bencorn/CICIDS2017/resolve/811c007f08d693a8a8b4226c197c138391806ce6/csvs/GeneratedLabelledFlows.zip
- Size: 283,876,488 bytes.
- Computed SHA-256: `7bdbef286f8893f31c6db12105fa097fa5c2dcc6733179037a08129d150ea27a`.
- The computed digest matches the mirror's Git LFS object ID. No independently obtained UNB checksum was available; this confirms mirror download integrity, not independent institutional authenticity.
- Local archive: `data/raw/cicids2017/GeneratedLabelledFlows.zip` in the original OWADD checkout, not the research worktree.
- Local CSV directory: `data/raw/cicids2017/flows` in the original checkout.

The archive contains eight CSVs, totaling 1,203,105,382 uncompressed bytes. Every inspected CSV header has 85 comma-separated fields and a Timestamp column. Timestamp parsing, monotonicity, duplicate detection, class distributions, and numeric validity remain unverified.

Extraction flattened the archive directory `TrafficLabelling ` (which has a trailing space) into `flows`, preserving CSV basenames and bytes. All destination paths were checked to remain inside the new directory, and overwrite was disabled. No scripts or packet captures were downloaded or executed. Raw data is ignored by Git.

Citation required by the dataset page: Iman Sharafaldin, Arash Habibi Lashkari, and Ali A. Ghorbani, “Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization,” ICISSP, 2018.

Do not substitute the mirror's source for the dataset authors in the manuscript. Disclose the acquisition route and archive digest in the reproduction record. Complete the chronological audit before treating these files as benchmark evidence.
