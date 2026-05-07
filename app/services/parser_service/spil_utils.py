import re


def parse_tag_cell(cell_value) -> list[str]:
    if not cell_value:
        return []
    val_str = str(cell_value).strip()
    val_str = val_str.replace(" -", "-").replace("- ", "-")
    val_str = re.sub(r"\s*/\s*", "/", val_str)
    val_str = re.sub(r"[\n\r\t,;&]", "|", val_str)
    val_str = re.sub(r"\s{2,}", "|", val_str)
    val_str = re.sub(r"(?<=\w) (?=\w{1,2}(?:[|/]|$))", "", val_str)
    val_str = val_str.replace(" ", "|")
    raw_tokens = [t.strip() for t in val_str.split("|") if t.strip()]
    expanded_tags = []

    def is_strong(part):
        return (len(part) >= 4 and any(c.isdigit() for c in part)) or (
            len(part) >= 3 and part[0].isalpha() and any(c.isdigit() for c in part)
        )

    for token in raw_tokens:
        token = token.lstrip("-")
        parts = token.split("-")
        for i in range(len(parts) - 1):
            if is_strong(parts[i]) and is_strong(parts[i + 1]):
                parts[i] += "|"
        token = "-".join(parts).replace("|-", "|")

        for sub in token.split("|"):
            if "/" not in sub:
                expanded_tags.append(sub)
            else:
                s_parts = [x.strip() for x in sub.split("/") if x.strip()]
                if not s_parts:
                    continue
                base = s_parts[0]
                expanded_tags.append(base)
                for suffix in s_parts[1:]:
                    if "-" in suffix:
                        expanded_tags.append(suffix)
                    elif suffix.isdigit():
                        base = re.sub(r"\d+$", suffix, base)
                        expanded_tags.append(base)
                    elif len(suffix) == 1 and base[-1].isalpha():
                        base = base[:-1] + suffix
                        expanded_tags.append(base)
                    else:
                        expanded_tags.append(suffix)
    return expanded_tags


def split_metadata_cell(cell_val, count_needed):
    if not cell_val:
        return [None] * count_needed
    s_val = str(cell_val).strip()
    parts = [p.strip() for p in re.split(r"[\n\r]+", s_val) if p.strip()]
    if len(parts) == count_needed:
        return parts
    parts = [p.strip() for p in re.split(r"\s{2,}", s_val) if p.strip()]
    if len(parts) == count_needed:
        return parts
    return [s_val] * count_needed
