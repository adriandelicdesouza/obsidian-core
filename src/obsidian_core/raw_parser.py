from datetime import datetime
import json
import re
import yaml
from .raw import RawRecord


class RawParser:
    """Parse raw Obsidian Markdown logs into RawRecord objects."""

    RECORD_PATTERN = re.compile(
        r"^## (?P<timestamp>.+?) — (?P<event_type>.+?)$",
        re.MULTILINE,
    )

    @classmethod
    def parse(cls, content: str) -> list[RawRecord]:
        """Parse all raw records contained in a daily log."""
        source = cls._extract_source(content)

        matches = list(cls.RECORD_PATTERN.finditer(content))

        records = []

        for index, match in enumerate(matches):
            start = match.start()
            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(content)
            )

            block = content[start:end]

            records.append(
                cls._parse_record(
                    block,
                    source=source,
                )
            )

        return records

    @classmethod
    def _parse_record(
        cls,
        block: str,
        source: str,
    ) -> RawRecord:
        """Parse one raw record block."""
        lines = block.splitlines()

        if not lines:
            raise ValueError("Empty raw record")

        header = lines[0]

        match = cls.RECORD_PATTERN.match(header)

        if not match:
            raise ValueError("Invalid raw record header")

        timestamp = datetime.fromisoformat(
            match.group("timestamp")
        )

        event_type = match.group("event_type")

        identifiers = cls._parse_section(
            lines,
            "### Identifiers",
        )

        metadata = cls._parse_section(
            lines,
            "### Metadata",
        )

    payload = cls._parse_payload(lines)
    stored_record_id = cls._extract_record_id(lines)

    record = RawRecord(
        timestamp=timestamp,
        source=source,
        event_type=event_type,
        identifiers=identifiers,
        metadata=metadata,
        payload=payload,
    )

    if record.record_id != stored_record_id:
        raise ValueError(
            f"Raw record integrity check failed: "
            f"expected {stored_record_id}, "
            f"calculated {record.record_id}"
        )

    return record

    @staticmethod
    def _extract_source(content: str) -> str:
        match = re.search(
            r"^source:\s*(.+)$",
            content,
            re.MULTILINE,
        )

        if not match:
            raise ValueError("Raw log source not found")

        return match.group(1).strip()

    @staticmethod
    def _parse_section(
        lines: list[str],
        heading: str,
    ) -> dict:
        try:
            start = lines.index(heading) + 1
        except ValueError:
            return {}

        values = {}

        for line in lines[start:]:
            if line.startswith("### "):
                break

            if line.startswith("- **") and ":**" in line:
                key, value = line[4:].split(":**", 1)

                value = value.strip().strip("`")

                values[key] = yaml.safe_load(value)

        return values

    @staticmethod
    def _parse_payload(lines: list[str]):
        try:
            start = lines.index("```json") + 1
        except ValueError:
            return None

        try:
            end = lines.index("```", start)
        except ValueError:
            raise ValueError("Unclosed JSON payload")

        payload = "\n".join(lines[start:end])

        return json.loads(payload)
    
    @staticmethod
    def _extract_record_id(lines: list[str]) -> str:
        for line in lines:
            if line.startswith("**Record ID:**"):
                return line.split("`", 2)[1]

        raise ValueError("Raw record ID not found")
