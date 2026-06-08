import re
from decimal import Decimal
from pathlib import Path

import fitz


def money_to_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None

    clean = value.replace(",", "").replace("Q", "").strip()

    if not clean:
        return None

    try:
        return Decimal(clean)
    except Exception:
        return None


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    return re.sub(r"\s+", " ", value).strip()


def extract_pdf_text(pdf_path: str) -> str:
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    text_parts = []

    with fitz.open(pdf_path) as document:
        for page in document:
            text_parts.append(page.get_text("text"))

    return "\n".join(text_parts)


def get_clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_value_by_regex(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return clean_text(match.group(1))

    return None


def extract_nit_emisor(text: str) -> str | None:
    return extract_value_by_regex(
        text,
        [
            r"Nit\s+Emisor:\s*([0-9Kk\-]+)",
            r"NIT\s+Emisor:\s*([0-9Kk\-]+)",
        ],
    )


def extract_serie(text: str) -> str | None:
    return extract_value_by_regex(
        text,
        [
            r"Serie:\s*([A-Z0-9]+)",
        ],
    )


def extract_numero_dte(text: str) -> str | None:
    return extract_value_by_regex(
        text,
        [
            r"N[úu]mero\s+de\s+DTE:\s*([0-9]+)",
            r"Numero\s+de\s+DTE:\s*([0-9]+)",
            r"No\.\s*DTE:\s*([0-9]+)",
        ],
    )


def extract_nit_receptor(text: str) -> str | None:
    return extract_value_by_regex(
        text,
        [
            r"NIT\s+Receptor:\s*([0-9Kk\-]+)",
            r"Nit\s+Receptor:\s*([0-9Kk\-]+)",
        ],
    )


def extract_nombre_receptor(text: str) -> str | None:
    return extract_value_by_regex(
        text,
        [
            r"Nombre\s+Receptor:\s*(.+?)(?:Fecha\s+y\s+hora|Moneda:|\n)",
        ],
    )


def extract_moneda(text: str) -> str:
    moneda = extract_value_by_regex(
        text,
        [
            r"Moneda:\s*([A-Z]{3})",
        ],
    )

    return moneda or "GTQ"


def is_authorization_line(line: str) -> bool:
    return bool(
        re.search(
            r"[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}",
            line,
            re.IGNORECASE,
        )
    )


def extract_proveedor(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        if "nit emisor:" in line.lower():
            candidates = []

            same_line = re.sub(
                r"Nit\s+Emisor:\s*[0-9Kk\-]+",
                "",
                line,
                flags=re.IGNORECASE,
            ).strip()

            same_line = re.sub(
                r"N[úu]mero\s+de\s+autorizaci[óo]n:.*",
                "",
                same_line,
                flags=re.IGNORECASE,
            ).strip()

            if same_line:
                candidates.append(same_line)

            for next_line in lines[index + 1:index + 8]:
                candidates.append(next_line)

            for candidate in candidates:
                candidate = clean_text(candidate)

                if not candidate:
                    continue

                lower = candidate.lower()

                if "número de autorización" in lower or "numero de autorizacion" in lower:
                    continue

                if "serie:" in lower:
                    candidate = re.split(r"Serie:", candidate, flags=re.IGNORECASE)[0].strip()

                if is_authorization_line(candidate):
                    continue

                if re.fullmatch(r"[0-9Kk\-]+", candidate):
                    continue

                if "nit receptor" in lower:
                    continue

                if "fecha y hora" in lower:
                    continue

                return candidate

    return None


def is_money_text(value: str) -> bool:
    return bool(re.fullmatch(r"[\d,]+\.\d{2}", value.strip()))


def is_integer_text(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))


def normalize_header(value: str) -> str:
    value = value.lower()
    value = value.replace("á", "a")
    value = value.replace("é", "e")
    value = value.replace("í", "i")
    value = value.replace("ó", "o")
    value = value.replace("ú", "u")
    return value.strip()


def extract_layout_words(pdf_path: str) -> list[dict]:
    words_data = []

    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document):
            page_width = page.rect.width

            for word in page.get_text("words"):
                x0, y0, x1, y1, text = word[:5]

                text = text.strip()

                if not text:
                    continue

                words_data.append(
                    {
                        "page": page_number,
                        "page_width": page_width,
                        "x0": float(x0),
                        "y0": float(y0),
                        "x1": float(x1),
                        "y1": float(y1),
                        "x": float((x0 + x1) / 2),
                        "y": float((y0 + y1) / 2),
                        "text": text,
                    }
                )

    return words_data


def find_header_y(words: list[dict]) -> float | None:
    candidates = []

    for word in words:
        value = normalize_header(word["text"])

        if value in {"#no", "cantidad", "descripcion"}:
            candidates.append(word["y"])

    if candidates:
        return min(candidates)

    return None


def find_header_center(words: list[dict], header_y: float, names: set[str]) -> float | None:
    candidates = []

    for word in words:
        if abs(word["y"] - header_y) > 35:
            continue

        value = normalize_header(word["text"])

        if value in names:
            candidates.append(word["x"])

    if candidates:
        return sum(candidates) / len(candidates)

    return None


def build_column_ranges(words: list[dict]) -> dict | None:
    if not words:
        return None

    page_width = words[0]["page_width"]
    header_y = find_header_y(words)

    if header_y is None:
        return build_default_column_ranges(page_width)

    no_x = find_header_center(words, header_y, {"#no", "no"})
    bs_x = find_header_center(words, header_y, {"b/s"})
    cantidad_x = find_header_center(words, header_y, {"cantidad"})
    descripcion_x = find_header_center(words, header_y, {"descripcion"})
    unitario_x = find_header_center(words, header_y, {"unitario", "p."})
    descuentos_x = find_header_center(words, header_y, {"descuentos"})
    otros_x = find_header_center(words, header_y, {"otros"})
    total_x = find_header_center(words, header_y, {"total"})
    impuestos_x = find_header_center(words, header_y, {"impuestos"})

    centers = [
        no_x,
        bs_x,
        cantidad_x,
        descripcion_x,
        unitario_x,
        descuentos_x,
        otros_x,
        total_x,
        impuestos_x,
    ]

    if any(center is None for center in centers):
        return build_default_column_ranges(page_width)

    no_x, bs_x, cantidad_x, descripcion_x, unitario_x, descuentos_x, otros_x, total_x, impuestos_x = centers

    no_bs = (no_x + bs_x) / 2
    bs_cantidad = (bs_x + cantidad_x) / 2
    cantidad_descripcion = (cantidad_x + descripcion_x) / 2
    descripcion_unitario = (descripcion_x + unitario_x) / 2
    unitario_descuentos = (unitario_x + descuentos_x) / 2
    descuentos_otros = (descuentos_x + otros_x) / 2
    otros_total = (otros_x + total_x) / 2
    total_impuestos = (total_x + impuestos_x) / 2

    return {
        "header_y": header_y,
        "no": (0, no_bs),
        "tipo": (no_bs, bs_cantidad),
        "cantidad": (bs_cantidad, cantidad_descripcion),
        "descripcion": (cantidad_descripcion, descripcion_unitario),
        "precio_unitario": (descripcion_unitario, unitario_descuentos),
        "descuentos": (unitario_descuentos, descuentos_otros),
        "otros_descuentos": (descuentos_otros, otros_total),
        "total": (otros_total, total_impuestos),
        "impuestos": (total_impuestos, page_width),
    }


def build_default_column_ranges(page_width: float) -> dict:
    return {
        "header_y": 0,
        "no": (0.00 * page_width, 0.07 * page_width),
        "tipo": (0.07 * page_width, 0.13 * page_width),
        "cantidad": (0.13 * page_width, 0.20 * page_width),
        "descripcion": (0.20 * page_width, 0.50 * page_width),
        "precio_unitario": (0.50 * page_width, 0.62 * page_width),
        "descuentos": (0.62 * page_width, 0.74 * page_width),
        "otros_descuentos": (0.74 * page_width, 0.84 * page_width),
        "total": (0.84 * page_width, 0.94 * page_width),
        "impuestos": (0.94 * page_width, page_width),
    }


def word_in_range(word: dict, range_pair: tuple[float, float]) -> bool:
    start, end = range_pair
    return start <= word["x"] < end


def join_words(words: list[dict]) -> str:
    ordered = sorted(words, key=lambda item: (round(item["y"], 1), item["x"]))
    return clean_text(" ".join(word["text"] for word in ordered)) or ""


def get_first_number(words: list[dict]) -> Decimal | None:
    ordered = sorted(words, key=lambda item: (item["y"], item["x"]))

    for word in ordered:
        text = word["text"]

        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            return money_to_decimal(text)

    return None


def get_first_money(words: list[dict]) -> Decimal | None:
    ordered = sorted(words, key=lambda item: (item["y"], item["x"]))

    for word in ordered:
        if is_money_text(word["text"]):
            return money_to_decimal(word["text"])

    return None


def find_totals_y(words: list[dict]) -> float | None:
    for word in words:
        if normalize_header(word["text"]).startswith("totales"):
            return word["y"]

    return None


def extract_items_from_layout(pdf_path: str) -> list[dict]:
    words = extract_layout_words(pdf_path)

    if not words:
        return []

    ranges = build_column_ranges(words)

    if not ranges:
        return []

    header_y = ranges["header_y"]
    totals_y = find_totals_y(words)

    item_number_words = []

    for word in words:
        if word["y"] <= header_y + 5:
            continue

        if totals_y is not None and word["y"] >= totals_y:
            continue

        if word_in_range(word, ranges["no"]) and is_integer_text(word["text"]):
            item_number_words.append(word)

    item_number_words = sorted(item_number_words, key=lambda item: item["y"])

    items = []

    for index, number_word in enumerate(item_number_words):
        line_number = int(number_word["text"])

        row_start_y = number_word["y"] - 3

        if index + 1 < len(item_number_words):
            row_end_y = item_number_words[index + 1]["y"] - 3
        elif totals_y is not None:
            row_end_y = totals_y
        else:
            row_end_y = number_word["y"] + 80

        row_words = [
            word for word in words
            if row_start_y <= word["y"] < row_end_y
        ]

        tipo_words = [word for word in row_words if word_in_range(word, ranges["tipo"])]
        cantidad_words = [word for word in row_words if word_in_range(word, ranges["cantidad"])]
        descripcion_words = [word for word in row_words if word_in_range(word, ranges["descripcion"])]
        precio_words = [word for word in row_words if word_in_range(word, ranges["precio_unitario"])]
        total_words = [word for word in row_words if word_in_range(word, ranges["total"])]

        tipo = join_words(tipo_words)
        descripcion = join_words(descripcion_words)
        cantidad = get_first_number(cantidad_words)
        precio_unitario = get_first_money(precio_words)
        total = get_first_money(total_words)

        if not descripcion:
            continue

        items.append(
            {
                "line_number": line_number,
                "tipo": tipo or None,
                "descripcion": descripcion,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "total": total,
            }
        )

    return items


def extract_items_from_text_fallback(text: str) -> list[dict]:
    pattern = re.compile(
        r"(?ms)^\s*(\d+)\s+(Bien|Servicio)\s+(\d+(?:\.\d+)?)\s+(.+?)\s+"
        r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})"
        r"(?=\s*\n\s*\d+\s+(?:Bien|Servicio)|\s*TOTALES:)",
        re.IGNORECASE,
    )

    items = []

    for match in pattern.finditer(text):
        items.append(
            {
                "line_number": int(match.group(1)),
                "tipo": match.group(2).strip(),
                "cantidad": money_to_decimal(match.group(3)),
                "descripcion": clean_text(match.group(4)),
                "precio_unitario": money_to_decimal(match.group(5)),
                "total": money_to_decimal(match.group(7)),
            }
        )

    return items


def extract_items(pdf_path: str, text: str) -> list[dict]:
    layout_items = extract_items_from_layout(pdf_path)

    if layout_items:
        return layout_items

    return extract_items_from_text_fallback(text)


def extract_total_factura(text: str, items: list[dict]) -> Decimal | None:
    if items:
        total = Decimal("0.00")

        for item in items:
            if item.get("total") is not None:
                total += item["total"]

        if total > 0:
            return total

    total_match = re.search(
        r"TOTALES:\s*(?:[\d,]+\.\d{2}\s*)*([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )

    if total_match:
        return money_to_decimal(total_match.group(1))

    amounts = re.findall(r"[\d,]+\.\d{2}", text)

    if amounts:
        non_zero_values = [
            value for value in amounts
            if money_to_decimal(value) is not None and money_to_decimal(value) > 0
        ]

        if non_zero_values:
            return money_to_decimal(non_zero_values[-1])

    return None


def extract_invoice_data(pdf_path: str) -> dict:
    text = extract_pdf_text(pdf_path)
    lines = get_clean_lines(text)

    items = extract_items(pdf_path, text)

    serie = extract_serie(text)
    numero_dte = extract_numero_dte(text)
    nit_emisor = extract_nit_emisor(text)
    proveedor = extract_proveedor(lines)
    nit_receptor = extract_nit_receptor(text)
    nombre_receptor = extract_nombre_receptor(text)
    moneda = extract_moneda(text)
    total_factura = extract_total_factura(text, items)

    return {
        "serie": serie,
        "numero_dte": numero_dte,
        "nit_emisor": nit_emisor,
        "proveedor": proveedor,
        "nit_receptor": nit_receptor,
        "nombre_receptor": nombre_receptor,
        "moneda": moneda,
        "total_factura": total_factura,
        "items": items,
        "raw_text": text,
    }