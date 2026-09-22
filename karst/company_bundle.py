"""The company evidence store (公司證據倉) behind one interface.

A company bundle answers four questions — which security this is, what sources are
available now, what the working evidence snapshot (packet) is, and what was observed
when — and owns every write into itself. Callers never name its files:

* ``security.json`` — the security's identity, recorded when the store is created or a
  packet is prepared. Bundles written before it existed answer from the working
  packet's ``security``, so no migration is needed; the first claim adds the file.
* ``evidence/`` — the append-only registry (``EvidenceRegistry``).
* ``packet.json`` + ``evidence.json`` — the working snapshot a research run freezes.
  A replayed bundle (a release's ``inputs/``) has no registry; its ``evidence.json``
  is then what is available.
* ``research.json`` — legacy research beside its packet (pre-store releases).

Every write is an atomic replacement. No ticker, CIK or date lives here.
"""
from __future__ import annotations

from pathlib import Path

from .fetch.registry import EvidenceRegistry, atomic_write
from .identity import security_record
from .packet import check_packet, check_research, confined, read_json
from .schema import ContractError, canonical, decode

# Names a release's copied sources must never collide with.
RESERVED = frozenset({"packet.json", "evidence.json", "research.json", "security.json"})


class CompanyBundle:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, name):
        return self.root / name

    def _read(self, name):
        path = self._path(name)
        return read_json(path) if path.exists() else None

    def _write(self, name, value):
        self._path(name).parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self._path(name), canonical(value))

    # --- identity -----------------------------------------------------------

    def security(self):
        """This store's security, or None when nothing has claimed it yet."""
        known = self._read("security.json")
        if known is None:
            known = (self.packet() or {}).get("security")
        return security_record(known) if known else None

    def claim(self, security):
        """Record ``security`` as this store's identity; another security is refused.

        Fields supplied now override, fields not supplied are kept: a caller that only
        knows the id does not erase the exchange or provider symbols learned earlier.
        """
        security = security_record(security)
        known = self.security()
        if known and security.get("security_id") and known.get("security_id") and \
                known["security_id"] != security["security_id"]:
            raise ContractError("Research security differs from this bundle")
        merged = {**(known or {}), **security}
        if self._read("security.json") != merged:
            self._write("security.json", merged)
        return merged

    # --- current sources ----------------------------------------------------

    def records(self, contract_version=None):
        """What is available now: the registry, else a replayed bundle's evidence index."""
        records = EvidenceRegistry(self.root).records(contract_version=contract_version) \
            if (self.root / "evidence" / "manifest.jsonl").exists() else []
        if records:
            return records
        replayed = self._read("evidence.json") or []
        if contract_version is not None:
            replayed = [{**record, "contract_version": contract_version} for record in replayed]
        return replayed

    def register(self, landed, meta_path=None, *, entity_ids=None):
        """Register one landed representation (see ``EvidenceRegistry.register``)."""
        return EvidenceRegistry(self.root).register(landed, meta_path, entity_ids=entity_ids)

    def register_many(self, landed, *, entity_ids=None):
        """Register a refresh's landed representations at once: one manifest write."""
        return EvidenceRegistry(self.root).register_many(landed, entity_ids=entity_ids)

    def observations(self):
        """Every acquisition receipt, oldest first."""
        path = self.root / "evidence" / "observations.jsonl"
        return [decode(line) for line in path.read_bytes().splitlines()] if path.exists() else []

    # --- working packet -----------------------------------------------------

    def packet(self):
        """The working packet, or None before the first one was prepared."""
        return self._read("packet.json")

    def working(self):
        """``(packet, records)`` of the working snapshot; refuses when there is none."""
        packet, records = self.packet(), self._read("evidence.json")
        if packet is None or records is None:
            raise ContractError("No working packet in this bundle; prepare research first")
        if not isinstance(records, list):
            raise ContractError("evidence.json must contain a list of evidence records")
        return packet, records

    def save_working(self, packet, records=None):
        """Replace the working snapshot; ``records=None`` keeps the evidence index.

        The evidence index lands before the packet that names it, so a reader never
        sees a packet pointing at an index that is not there yet.
        """
        if records is not None:
            self._write("evidence.json", records)
        self._write("packet.json", packet)

    # --- frozen inputs (legacy research beside its packet, release inputs) ---

    def research(self):
        return self._read("research.json")

    def save_research(self, research, *, overwrite=True):
        if not overwrite and self._path("research.json").exists():
            raise ContractError("research.json already exists; prior research is never overwritten")
        self._write("research.json", research)

    def save_frozen(self, packet, records, research):
        """Write a replayable bundle: exactly packet, evidence index and research."""
        self.save_working(packet, records)
        self._write("research.json", research)

    def checked(self):
        """``(packet, selected records, research)`` after the full contract checks."""
        packet, records = self.working()
        selected = check_packet(packet, records, self.root)
        research = self.research()
        if research is None:
            raise ContractError("No research.json in this bundle")
        check_research(packet, research, selected, self.root)
        return packet, list(selected.values()), research

    # --- daily incremental build (日更快照) --------------------------------------

    def daily_series(self):
        """The daily bars as last built, with the manifest length they were built from."""
        return self._read("daily/series.json")

    def save_daily_series(self, series):
        self._write("daily/series.json", series)

    def daily_snapshot(self, date=None):
        """The snapshot of ``date`` (ISO day), or the latest one when no date is given."""
        if date is None:
            latest = self._read("daily/latest.json")
            return None if latest is None else self._read(f"daily/{latest['date']}.json")
        return self._read(f"daily/{date}.json")

    def save_daily_snapshot(self, snapshot):
        """Save one day's snapshot; the pointer to the latest moves after it lands."""
        day = snapshot["date"]
        if len(day) != 10 or not day.replace("-", "").isdigit():
            raise ContractError("Daily snapshot date must be an ISO day")
        self._write(f"daily/{day}.json", snapshot)
        latest = self._read("daily/latest.json")
        if latest is None or latest["date"] <= day:
            self._write("daily/latest.json", {"date": day})

    def artifact(self, record):
        """The bytes of one registered artifact, confined to this bundle."""
        return confined(self.root, record["artifact"]["path"]).read_bytes()
