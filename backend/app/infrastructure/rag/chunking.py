import re

from app.models.profile import EvidenceChunk, ProfileDocument


class MarkdownProfileChunker:
    def __init__(self, max_characters: int = 900) -> None:
        if max_characters < 100:
            raise ValueError("max_characters must be at least 100")
        self._max_characters = max_characters

    def chunk_documents(self, documents: list[ProfileDocument]) -> list[EvidenceChunk]:
        chunks: list[EvidenceChunk] = []
        for document in documents:
            chunks.extend(self.chunk_document(document))
        return chunks

    def chunk_document(self, document: ProfileDocument) -> list[EvidenceChunk]:
        if not document.content.strip():
            return []

        sections = self._sections(document.content)
        chunks: list[EvidenceChunk] = []
        for section_index, (heading, section_text) in enumerate(sections):
            for part_index, text in enumerate(self._bounded_parts(section_text)):
                chunks.append(
                    EvidenceChunk(
                        chunk_id=f"{document.id}:{section_index}:{part_index}",
                        source=document.source,
                        category=document.category,
                        title=heading or document.title,
                        project_id=document.id if document.category == "project" else None,
                        evidence_level=document.evidence_level,
                        text=text,
                    )
                )
        return chunks

    def _sections(self, content: str) -> list[tuple[str | None, str]]:
        heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(content))
        if not matches:
            return [(None, content.strip())]

        sections: list[tuple[str | None, str]] = []
        if matches[0].start() > 0 and content[: matches[0].start()].strip():
            sections.append((None, content[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            body = content[match.end() : end].strip()
            section_text = f"{match.group(0)}\n{body}".strip()
            if body:
                sections.append((match.group(2).strip(), section_text))
        return sections

    def _bounded_parts(self, text: str) -> list[str]:
        if len(text) <= self._max_characters:
            return [text]
        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
        parts: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > self._max_characters:
                parts.append(current)
                current = ""
            if len(paragraph) > self._max_characters:
                parts.extend(
                    paragraph[start : start + self._max_characters]
                    for start in range(0, len(paragraph), self._max_characters)
                )
            else:
                current = paragraph if not current else f"{current}\n\n{paragraph}"
        if current:
            parts.append(current)
        return parts
