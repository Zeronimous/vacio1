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
# Los más específicos van primero.
MARKERS = [
    "<T>", "</T>", "<A>", "</A>", "{i}", "{/i>", "<R>", "</R>",
    "<B>", "</B>", r"<color=#[0-9a-fA-F]{6}>", "</color>", "<P>", "</P>",
    "<R2>", "</R2>", "<i>", "</i>", "<W>", "</W>", "<G>", "</G>", "<Y>", "</Y>"
]

# Regex para encontrar cualquier marcador, incluyendo los genéricos como {p1}
ESCAPED_MARKERS = [re.escape(m) for m in MARKERS]
GENERIC_MARKER_REGEX = r"{[^}]+}"
MARKER_REGEX_PATTERN = "(" + "|".join(ESCAPED_MARKERS) + "|" + GENERIC_MARKER_REGEX + ")"
MARKER_REGEX = re.compile(MARKER_REGEX_PATTERN)

# Regex para encontrar las frases en inglés a extraer.
ENGLISH_ENTRY_REGEX = re.compile(r',\"English\":\"((?:\\"|[^"])*)\",\"')

# --- Lógica Principal ---

def setup_directories():
    """Asegura que existan las carpetas necesarias."""
    os.makedirs(DIR_INGLES, exist_ok=True)
    os.makedirs(DIR_TEXTOS, exist_ok=True)
    os.makedirs(DIR_ESPANOL, exist_ok=True)

def unescape_string(s):
    """Desescapa una cadena que viene del formato pseudo-JSON."""
    # Python's 'unicode_escape' codec does exactly what we need.
    # It handles \\, \", etc.
    return codecs.decode(s, 'unicode_escape')

def parse_content(content_string, base_id):
    """
    Analiza una cadena de contenido, la divide en texto y marcadores,
    y genera las filas correspondientes para el CSV.
    """
    # 1. Regla de exclusión: ignorar si el contenido es solo un placeholder.
    if re.fullmatch(GENERIC_MARKER_REGEX, content_string):
        return []

    # 2. Tokenización: dividir la cadena en texto y marcadores.
    tokens = [token for token in MARKER_REGEX.split(content_string) if token]

    rows = []
    sub_index = 1

    i = 0
    while i < len(tokens):
        # a. Encontrar marcadores previos
        prev_markers_list = []
        while i < len(tokens) and MARKER_REGEX.fullmatch(tokens[i]):
            prev_markers_list.append(tokens[i])
            i += 1

        # Si después de los marcadores se acaba la cadena, no hay texto.
        if i >= len(tokens):
            break

        # b. Encontrar el fragmento de texto
        text_chunk = tokens[i]
        i += 1

        # c. Encontrar marcadores posteriores
        post_markers_list = []
        while i < len(tokens) and MARKER_REGEX.fullmatch(tokens[i]):
            post_markers_list.append(tokens[i])
            i += 1

        # d. Procesar el evento (prev_markers, text_chunk, post_markers)
        texto = text_chunk.strip()

        # Si el texto está vacío (solo espacios), adjuntarlo al postmarker de la fila anterior.
        if not texto:
            if rows:
                rows[-1]["postmarker"] += text_chunk
            continue

        leading_ws = text_chunk[:len(text_chunk) - len(text_chunk.lstrip())]
        trailing_ws = text_chunk[len(text_chunk.rstrip()):]

        prevmarker = "".join(prev_markers_list)
        postmarker = trailing_ws + "".join(post_markers_list)

        row = {
            "id": f"{base_id}_{sub_index}",
            "prevmarker": prevmarker,
            "texto": texto,
            "postmarker": postmarker
        }

        if leading_ws and rows:
            rows[-1]["postmarker"] += leading_ws

        rows.append(row)
        sub_index += 1

    return rows


def main():
    """
    Función principal del script.
    """
    print("Iniciando el script de extracción (versión corregida)...")
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

            output_rows = [{
                'ID': row['id'],
                'prevmarker': row['prevmarker'],
                'texto': row['texto'],
                'postmarker': row['postmarker']
            } for row in all_csv_rows]

            writer.writerows(output_rows)

        print(f"¡Éxito! Se han guardado {len(all_csv_rows)} entradas en '{CSV_FILENAME}'")
    except IOError as e:
        print(f"Error al escribir el archivo CSV: {e}")


if __name__ == "__main__":
    main()
