"""Local copy of the codeblock stripper so data_gen has no path dependency on
the project root. Mirrors util.codeblock_strip in behaviour."""


def strip_codeblock(text) -> str:
    if not text:
        return ""
    lines = text.strip().splitlines()
    if len(lines) <= 2:
        return text.strip()
    if lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text.strip()
