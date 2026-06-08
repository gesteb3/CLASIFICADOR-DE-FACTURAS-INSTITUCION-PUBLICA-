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


def clean_item_description(value: str | None) -> str | None:
    return clean_text(value)


def clean_description_for_ai(value: str | None) -> str | None:
    text = clean_text(value)

    if not text:
        return None

    text = text.replace("|", " ")
    text = text.replace("¦", " ")

    text = re.sub(r"\b\d{8,}(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", "", text)
    text = re.sub(r"^\d{8,}\s*", "", text)

    return clean_text(text)


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
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)

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
            r"Nombre\s+Receptor:\s*(.+?)(?:Direcci[óo]n\s+comprador|Fecha\s+y\s+hora|Moneda:|\n)",
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


def is_invalid_provider_candidate(candidate: str) -> bool:
    candidate_lower = candidate.lower()

    invalid_terms = [
        "factura",
        "número de autorización",
        "numero de autorizacion",
        "serie:",
        "número de dte",
        "numero de dte",
        "numero acceso",
        "número acceso",
        "nit receptor",
        "nombre receptor",
        "fecha y hora",
        "moneda",
        "dirección",
        "direccion",
        "carretera",
        "locales",
        "zona",
        "ciudad",
        "comprador",
    ]

    if any(term in candidate_lower for term in invalid_terms):
        return True

    if "km " in candidate_lower:
        return True

    if is_authorization_line(candidate):
        return True

    if re.fullmatch(r"[0-9Kk\-]+", candidate):
        return True

    return False


def extract_proveedor(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        lower = line.lower()

        if "nit emisor:" not in lower:
            continue

        candidates = []

        same_line = re.sub(
            r"Nit\s+Emisor:\s*[0-9Kk\-]+",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()

        same_line = re.sub(
            r"NIT\s+Emisor:\s*[0-9Kk\-]+",
            "",
            same_line,
            flags=re.IGNORECASE,
        ).strip()

        if same_line:
            candidates.append(same_line)

        candidates.extend(lines[index + 1:index + 7])

        for candidate in candidates:
            candidate = clean_text(candidate)

            if not candidate:
                continue

            if is_invalid_provider_candidate(candidate):
                continue

            return candidate

    return None


def is_money_text(value: str) -> bool:
    return bool(re.fullmatch(r"[\d,]+\.\d{2}", value.strip()))


def is_integer_text(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))


def normalize_header(value: str) -> str:
    value = value.lower().strip()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = value.replace("#", "")
    value = value.replace(".", "")
    value = value.replace(":", "")
    value = value.replace("/", "")
    value = value.replace("(", "")
    value = value.replace(")", "")

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


def find_table_headers(words: list[dict]) -> list[dict]:
    candidates = []

    for anchor in words:
        page = anchor["page"]
        y = anchor["y"]

        band_words = [
            word for word in words
            if word["page"] == page
            and abs(word["y"] - y) <= 24
        ]

        values = {normalize_header(word["text"]) for word in band_words}

        has_no = "no" in values
        has_bs = "bs" in values
        has_cantidad = "cantidad" in values
        has_descripcion = "descripcion" in values
        has_unitario = "unitario" in values or "precio" in values or "p" in values
        has_total = "total" in values

        score = 0

        if has_no:
            score += 2

        if has_bs:
            score += 2

        if has_cantidad:
            score += 3

        if has_descripcion:
            score += 4

        if has_unitario:
            score += 2

        if has_total:
            score += 2

        if has_cantidad and has_descripcion and score >= 8:
            candidates.append(
                {
                    "page": page,
                    "y": y,
                    "score": score,
                    "page_width": anchor["page_width"],
                }
            )

    unique = {}

    for candidate in candidates:
        key = (candidate["page"], round(candidate["y"], 0))

        if key not in unique or candidate["score"] > unique[key]["score"]:
            unique[key] = candidate

    result = list(unique.values())
    result.sort(key=lambda item: (item["page"], item["y"]))

    return result


def find_header_center(
    words: list[dict],
    page: int,
    header_y: float,
    names: set[str],
) -> float | None:
    candidates = []

    for word in words:
        if word["page"] != page:
            continue

        if abs(word["y"] - header_y) > 32:
            continue

        value = normalize_header(word["text"])

        if value in names:
            candidates.append(word["x"])

    if candidates:
        return sum(candidates) / len(candidates)

    return None


def build_default_column_ranges(page_width: float, header_y: float, page: int) -> dict:
    return {
        "page": page,
        "header_y": header_y,
        "no": (0.00 * page_width, 0.09 * page_width),
        "tipo": (0.09 * page_width, 0.17 * page_width),
        "cantidad": (0.17 * page_width, 0.25 * page_width),
        "descripcion": (0.25 * page_width, 0.50 * page_width),
        "precio_unitario": (0.50 * page_width, 0.62 * page_width),
        "descuentos": (0.62 * page_width, 0.74 * page_width),
        "total": (0.74 * page_width, 0.87 * page_width),
        "impuestos": (0.87 * page_width, page_width),
    }


def build_column_ranges_for_header(words: list[dict], header: dict) -> dict:
    page = header["page"]
    header_y = header["y"]
    page_width = header["page_width"]

    no_x = find_header_center(words, page, header_y, {"no"})
    bs_x = find_header_center(words, page, header_y, {"bs"})
    cantidad_x = find_header_center(words, page, header_y, {"cantidad"})
    descripcion_x = find_header_center(words, page, header_y, {"descripcion"})
    unitario_x = find_header_center(words, page, header_y, {"unitario", "precio", "p"})
    descuentos_x = find_header_center(words, page, header_y, {"descuentos"})
    total_x = find_header_center(words, page, header_y, {"total"})
    impuestos_x = find_header_center(words, page, header_y, {"impuestos"})

    centers = [
        no_x,
        bs_x,
        cantidad_x,
        descripcion_x,
        unitario_x,
        descuentos_x,
        total_x,
        impuestos_x,
    ]

    if any(center is None for center in centers):
        return build_default_column_ranges(page_width, header_y, page)

    no_x, bs_x, cantidad_x, descripcion_x, unitario_x, descuentos_x, total_x, impuestos_x = centers

    no_bs = (no_x + bs_x) / 2
    bs_cantidad = (bs_x + cantidad_x) / 2
    cantidad_descripcion = (cantidad_x + descripcion_x) / 2
    descripcion_unitario = (descripcion_x + unitario_x) / 2
    unitario_descuentos = (unitario_x + descuentos_x) / 2
    descuentos_total = (descuentos_x + total_x) / 2
    total_impuestos = (total_x + impuestos_x) / 2

    return {
        "page": page,
        "header_y": header_y,
        "no": (0, no_bs),
        "tipo": (no_bs, bs_cantidad),
        "cantidad": (bs_cantidad, cantidad_descripcion),
        "descripcion": (cantidad_descripcion, descripcion_unitario),
        "precio_unitario": (descripcion_unitario, unitario_descuentos),
        "descuentos": (unitario_descuentos, descuentos_total),
        "total": (descuentos_total, total_impuestos),
        "impuestos": (total_impuestos, page_width),
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
        value = money_to_decimal(word["text"])

        if value is not None:
            return value

    return None


def find_totals_y(words: list[dict], page: int, header_y: float) -> float | None:
    candidates = []

    for word in words:
        if word["page"] != page:
            continue

        if word["y"] <= header_y:
            continue

        value = normalize_header(word["text"])

        if value.startswith("totales") or value == "totales":
            candidates.append(word["y"])

    if candidates:
        return min(candidates)

    return None


def is_valid_item_number_word(
    number_word: dict,
    page_words: list[dict],
    ranges: dict,
) -> bool:
    if not is_integer_text(number_word["text"]):
        return False

    line_number = int(number_word["text"])

    if line_number < 1 or line_number > 300:
        return False

    same_row_words = [
        word for word in page_words
        if abs(word["y"] - number_word["y"]) <= 12
    ]

    has_tipo = any(
        normalize_header(word["text"]) in {"bien", "servicio"}
        and word["x"] > number_word["x"]
        for word in same_row_words
    )

    has_quantity = any(
        word_in_range(word, ranges["cantidad"])
        and re.fullmatch(r"\d+(?:\.\d+)?", word["text"])
        for word in same_row_words
    )

    return has_tipo and has_quantity


def is_bad_description(description: str | None) -> bool:
    if not description:
        return True

    normalized = description.lower()

    bad_terms = [
        "nit receptor",
        "nombre receptor",
        "fecha y hora",
        "moneda:",
        "numero de autorizacion",
        "número de autorización",
        "dirección comprador",
        "direccion comprador",
        "municipalidad de",
    ]

    return any(term in normalized for term in bad_terms)


def calculate_total_if_missing(
    cantidad: Decimal | None,
    precio_unitario: Decimal | None,
    total: Decimal | None,
) -> Decimal | None:
    if total is not None and total > Decimal("0"):
        return total

    if cantidad is not None and precio_unitario is not None:
        return cantidad * precio_unitario

    return total


def extract_items_from_header(words: list[dict], header: dict) -> list[dict]:
    ranges = build_column_ranges_for_header(words, header)

    page = ranges["page"]
    header_y = ranges["header_y"]
    totals_y = find_totals_y(words, page, header_y)

    page_words = [
        word for word in words
        if word["page"] == page
    ]

    item_number_words = []

    for word in page_words:
        if word["y"] <= header_y + 5:
            continue

        if totals_y is not None and word["y"] >= totals_y:
            continue

        if not word_in_range(word, ranges["no"]):
            continue

        if not is_valid_item_number_word(word, page_words, ranges):
            continue

        item_number_words.append(word)

    item_number_words = sorted(item_number_words, key=lambda item: item["y"])

    items = []

    for index, number_word in enumerate(item_number_words):
        line_number = int(number_word["text"])
        row_start_y = number_word["y"] - 5

        if index + 1 < len(item_number_words):
            row_end_y = item_number_words[index + 1]["y"] - 5
        elif totals_y is not None:
            row_end_y = totals_y
        else:
            row_end_y = number_word["y"] + 90

        row_words = [
            word for word in page_words
            if row_start_y <= word["y"] < row_end_y
        ]

        row_words = sorted(row_words, key=lambda item: (item["y"], item["x"]))

        tipo_words = [
            word for word in row_words
            if word_in_range(word, ranges["tipo"])
            and normalize_header(word["text"]) in {"bien", "servicio"}
        ]

        cantidad_words = [
            word for word in row_words
            if word_in_range(word, ranges["cantidad"])
            and re.fullmatch(r"\d+(?:\.\d+)?", word["text"])
        ]

        unitario_money_words = [
            word for word in row_words
            if word_in_range(word, ranges["precio_unitario"])
            and is_money_text(word["text"])
        ]

        total_money_words = [
            word for word in row_words
            if word_in_range(word, ranges["total"])
            and is_money_text(word["text"])
        ]

        money_words_before_taxes = [
            word for word in row_words
            if is_money_text(word["text"])
            and not word_in_range(word, ranges["impuestos"])
        ]

        tipo = join_words(tipo_words)
        cantidad = get_first_number(cantidad_words)
        precio_unitario = get_first_money(unitario_money_words)
        total = get_first_money(total_money_words)

        if precio_unitario is None and money_words_before_taxes:
            precio_unitario = get_first_money(money_words_before_taxes)

        if total is None and money_words_before_taxes:
            ordered_money = sorted(money_words_before_taxes, key=lambda item: item["x"])
            total = money_to_decimal(ordered_money[-1]["text"])

        first_money_x = None
        money_candidates = sorted(money_words_before_taxes, key=lambda item: item["x0"])

        if money_candidates:
            first_money_x = money_candidates[0]["x0"]

        quantity_word_used = None

        if cantidad_words:
            quantity_word_used = sorted(cantidad_words, key=lambda item: item["x"])[0]

        description_words = []

        description_left_limit = ranges["cantidad"][1] - 45

        for word in row_words:
            text = word["text"].strip()
            lower = normalize_header(text)

            if word is number_word:
                continue

            if lower in {"bien", "servicio"} and word_in_range(word, ranges["tipo"]):
                continue

            if quantity_word_used and word is quantity_word_used:
                continue

            if is_money_text(text):
                continue

            if first_money_x is not None and word["x0"] >= first_money_x:
                continue

            if word["x"] < description_left_limit:
                continue

            if word["y"] <= header_y + 5:
                continue

            if lower in {
                "no",
                "bs",
                "cantidad",
                "descripcion",
                "precio",
                "unitario",
                "iva",
                "q",
                "p",
                "descuentos",
                "otros",
                "total",
                "impuestos",
            }:
                continue

            description_words.append(word)

        descripcion_original = clean_item_description(join_words(description_words))
        descripcion_para_ia = clean_description_for_ai(descripcion_original)

        if not descripcion_original:
            continue

        if is_bad_description(descripcion_original):
            continue

        if cantidad is not None and cantidad > Decimal("100000"):
            continue

        total = calculate_total_if_missing(
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            total=total,
        )

        items.append(
            {
                "line_number": line_number,
                "tipo": tipo or None,
                "descripcion": descripcion_original,
                "descripcion_para_ia": descripcion_para_ia or descripcion_original,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "total": total,
            }
        )

    return items


def extract_items_from_layout(pdf_path: str) -> list[dict]:
    words = extract_layout_words(pdf_path)

    if not words:
        return []

    headers = find_table_headers(words)

    if not headers:
        return []

    all_items = []

    for header in headers:
        items = extract_items_from_header(words, header)
        all_items.extend(items)

    unique_items = {}

    for item in all_items:
        key = (item.get("line_number"), item.get("descripcion"), item.get("total"))

        if key not in unique_items:
            unique_items[key] = item

    return list(unique_items.values())


def extract_items_from_text_fallback(text: str) -> list[dict]:
    table_text = text

    header_match = re.search(
        r"#?\s*No\.?.{0,100}B/S.{0,100}Cantidad.{0,100}Descripci[óo]n",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if header_match:
        table_text = text[header_match.end():]

    totals_match = re.search(
        r"TOTALES?:",
        table_text,
        re.IGNORECASE,
    )

    if totals_match:
        table_text = table_text[:totals_match.start()]

    pattern = re.compile(
        r"(?ms)"
        r"^\s*(\d+)\s+"
        r"(Bien|Servicio)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(.+?)\s+"
        r"([\d,]+\.\d{2})\s+"
        r"([\d,]+\.\d{2})\s+"
        r"([\d,]+\.\d{2})"
        r"(?:\s+IVA\s+[\d,]+\.\d{2})?"
        r"(?=\s*\n\s*\d+\s+(?:Bien|Servicio)|\s*$)",
        re.IGNORECASE,
    )

    items = []

    for match in pattern.finditer(table_text):
        descripcion_original = clean_item_description(match.group(4))
        descripcion_para_ia = clean_description_for_ai(descripcion_original)

        if is_bad_description(descripcion_original):
            continue

        cantidad = money_to_decimal(match.group(3))
        precio_unitario = money_to_decimal(match.group(5))
        total = money_to_decimal(match.group(7))

        total = calculate_total_if_missing(
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            total=total,
        )

        items.append(
            {
                "line_number": int(match.group(1)),
                "tipo": match.group(2).strip(),
                "cantidad": cantidad,
                "descripcion": descripcion_original,
                "descripcion_para_ia": descripcion_para_ia or descripcion_original,
                "precio_unitario": precio_unitario,
                "total": total,
            }
        )

    return items


def has_suspicious_items(items: list[dict]) -> bool:
    if not items:
        return True

    for item in items:
        cantidad = item.get("cantidad")
        descripcion = item.get("descripcion")

        if is_bad_description(descripcion):
            return True

        if cantidad is not None and cantidad > Decimal("100000"):
            return True

    return False


def extract_items(pdf_path: str, text: str) -> list[dict]:
    layout_items = extract_items_from_layout(pdf_path)
    text_items = extract_items_from_text_fallback(text)

    if layout_items and not has_suspicious_items(layout_items):
        return layout_items

    if text_items:
        return text_items

    return layout_items


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