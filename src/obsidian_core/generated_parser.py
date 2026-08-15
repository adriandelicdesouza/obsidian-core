import re
from datetime import datetime

import yaml

from .generated import GeneratedRecord


class GeneratedParser:
    """Parse generated Obsidian Markdown logs into GeneratedRecord objects."""

    RECORD_PATTERN = re.compile(
        r"^## (?P<timestamp>.+?) — (?P<generator>.+?)$",
        re.MULTILINE,
    )

    @classmethod
    def parse(cls, content: str) -> list[GeneratedRecord]:
        """Parse all generated records contained in a daily log."""
        matches = list(cls.RECORD_PATTERN.finditer(content))

        if not matches:
            raise ValueError("Invalid generated record header")

        records = []

        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)

            block = content[start:end]

            records.append(cls._parse_record(block))

        return records

    @classmethod
    def _parse_record(cls, block: str) -> GeneratedRecord:
        """Parse one generated record block."""
        lines = block.splitlines()

        if not lines:
            raise ValueError("Empty generated record")

        match = cls.RECORD_PATTERN.match(lines[0])

        if not match:
            raise ValueError("Invalid generated record header")

        timestamp = datetime.fromisoformat(match.group("timestamp"))

        generator = match.group("generator")

        generator_version = cls._extract_inline_value(
            lines,
            "**Generator Version:**",
        )

        stored_record_id = cls._extract_inline_value(
            lines,
            "**Generated ID:**",
        )

        source_ids = cls._parse_source_ids(lines)
        metadata = cls._parse_metadata(lines)
        content = cls._parse_content(lines)

        record = GeneratedRecord(
            timestamp=timestamp,
            generator=generator,
            generator_version=generator_version,
            content=content,
            source_ids=source_ids,
            metadata=metadata,
        )

        if record.generated_id != stored_record_id:
            raise ValueError(
                "Generated record integrity check failed: "
                f"expected {stored_record_id}, "
                f"calculated {record.generated_id}"
            )

        return record

    @staticmethod
    def _extract_inline_value(
        lines: list[str],
        prefix: str,
    ) -> str:
        for line in lines:
            if line.startswith(prefix):
                parts = line.split("`", 2)

                if len(parts) != 3:
                    raise ValueError(f"Invalid generated record field: {prefix}")

                return parts[1]

        raise ValueError(f"Generated record field not found: {prefix}")

    @staticmethod
    def _parse_source_ids(lines: list[str]) -> list[str]:
        try:
            start = lines.index("### Source Records") + 1
        except ValueError:
            raise ValueError("Source records section not found")

        values = []

        for line in lines[start:]:
            if line.startswith("### "):
                break

            if not line.strip():
                continue

            if line.startswith("- `") and line.endswith("`"):
                values.append(line[3:-1])

            elif line.strip() == "_None_":
                return []

            else:
                raise ValueError("Malformed source records section")

        return values

    @staticmethod
    def _parse_metadata(lines: list[str]) -> dict:
        try:
            start = lines.index("### Metadata") + 1
        except ValueError:
            raise ValueError("Metadata section not found")

        values = {}

        for line in lines[start:]:
            if line.startswith("### "):
                break

            if not line.strip():
                continue

            if line.strip() == "_None_":
                return {}

            if not line.startswith("- **") or ":**" not in line:
                raise ValueError("Generated record integrity check failed: malformed metadata")

            key, value = line[4:].split(":**", 1)
            value = value.strip().strip("`")
            values[key] = yaml.safe_load(value)

        return values

    @staticmethod
    def _parse_content(lines: list[str]) -> str:
        try:
            start = lines.index("### Content") + 1
        except ValueError:
            raise ValueError("Content section not found")

        content = "\n".join(lines[start:]).lstrip("\n")

        return content.rstrip("\n")
