import os
import re
import csv
import codecs

# --- Constantes ---

DIR_INGLES = "ingles"
DIR_TEXTOS = "textos"
DIR_ESPANOL = "espanol"
CSV_FILENAME = os.path.join(DIR_TEXTOS, "textos_a_traducir.csv")

# Marcadores conocidos. El orden es importante para el regex.
MARKERS = [
    "<T>", "</T>", "<A>", "</A>", "{i}", "{/i>", "<R>", "</R>",
    "<B>", "</B>", r"<color=#[0-9a-fA-F]{6}>", "</color>", "<P>", "</P>",
    "<R2>", "</R2>", "<i>", "</i>", "<W>", "</W>", "<G>", "</G>", "<Y>", "</Y>"
]

ESCAPED_MARKERS = [re.escape(m) for m in MARKERS]
GENERIC_MARKER_REGEX = r"{[^}]+}"
MARKER_REGEX_PATTERN = "(" + "|".join(ESCAPED_MARKERS) + "|" + GENERIC_MARKER_REGEX + ")"
MARKER_REGEX = re.compile(MARKER_REGEX_PATTERN)

ENGLISH_ENTRY_REGEX = re.compile(r',\"English\":\"((?:\\"|[^"])*)\",\"')

# --- Lógica Principal ---

def setup_directories():
    os.makedirs(DIR_INGLES, exist_ok=True)
    os.makedirs(DIR_TEXTOS, exist_ok=True)
    os.makedirs(DIR_ESPANOL, exist_ok=True)

def unescape_string(s):
    """
    Desescapa de forma segura solo los caracteres que conocemos (\\" y \\\\),
    para evitar corromper otros caracteres especiales.
    """
    return s.replace('\\"', '"').replace('\\\\', '\\')

def parse_content(content_string, base_id):
    """
    Analiza una cadena de contenido, la divide en texto y marcadores,
    y genera las filas correspondientes para el CSV.
    """
    if re.fullmatch(GENERIC_MARKER_REGEX, content_string):
        return []

    tokens = [token for token in MARKER_REGEX.split(content_string) if token]

    rows = []
    sub_index = 1

    i = 0
    while i < len(tokens):
        prev_markers_list = []
        while i < len(tokens) and MARKER_REGEX.fullmatch(tokens[i]):
            prev_markers_list.append(tokens[i])
            i += 1

        if i >= len(tokens):
            if prev_markers_list: # Handle trailing markers with no text
                 rows.append({
                    "id": f"{base_id}_{sub_index}",
                    "prevmarker": "".join(prev_markers_list),
                    "texto": "",
                    "postmarker": ""
                })
            break

        text_chunk = tokens[i]
        i += 1

        post_markers_list = []
        while i < len(tokens) and MARKER_REGEX.fullmatch(tokens[i]):
            post_markers_list.append(tokens[i])
            i += 1

        texto = text_chunk.strip()

        # Si el fragmento es solo espacio, no genera una nueva fila,
        # sino que se adjunta al marcador anterior o posterior.
        if not texto:
            # Si hay una fila anterior, adjuntar el espacio a su postmarker.
            if rows:
                rows[-1]["postmarker"] += text_chunk
            # Si no hay fila anterior, adjuntar el espacio al prevmarker de la siguiente fila potencial.
            # Esta es la parte compleja. La nueva lógica lo simplifica.
            # Con la nueva lógica, este caso se maneja en la asignación de ws.
            continue

        leading_ws = text_chunk[:len(text_chunk) - len(text_chunk.lstrip())]
        trailing_ws = text_chunk[len(text_chunk.rstrip()):]

        # LÓGICA DE ESPACIOS CORREGIDA Y SIMPLIFICADA
        prevmarker = "".join(prev_markers_list) + leading_ws
        postmarker = trailing_ws + "".join(post_markers_list)

        row = {
            "ID": f"{base_id}_{sub_index}",
            "prevmarker": prevmarker,
            "texto": texto,
            "postmarker": postmarker
        }

        rows.append(row)
        sub_index += 1

    return rows


def main():
    print("Iniciando el script de extracción (versión final)...")
    setup_directories()

    all_csv_rows = []

    try:
        files_to_process = [f for f in os.listdir(DIR_INGLES) if f.endswith('.txt')]
    except FileNotFoundError:
        print(f"Error: La carpeta '{DIR_INGLES}' no existe.")
        files_to_process = []

    if not files_to_process:
        print(f"No se encontraron archivos .txt en la carpeta '{DIR_INGLES}'.")
        return

    print(f"Procesando {len(files_to_process)} archivo(s)...")

    for filename in files_to_process:
        filepath = os.path.join(DIR_INGLES, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        matches = ENGLISH_ENTRY_REGEX.finditer(content)

        entry_index = 1
        for match in matches:
            escaped_text = match.group(1)
            english_text = unescape_string(escaped_text)

            base_id = f"{filename}-{entry_index}"

            rows = parse_content(english_text, base_id)
            all_csv_rows.extend(rows)

            entry_index += 1

    if not all_csv_rows:
        print("No se extrajo ningún texto. El archivo CSV no se generará.")
        return

    try:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ID', 'prevmarker', 'texto', 'postmarker']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_csv_rows)

        print(f"¡Éxito! Se han guardado {len(all_csv_rows)} entradas en '{CSV_FILENAME}'")
    except IOError as e:
        print(f"Error al escribir el archivo CSV: {e}")


if __name__ == "__main__":
    main()
