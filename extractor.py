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
    y genera las filas correspondientes para el CSV. (Versión 5 - Lógica final)
    """
    if re.fullmatch(GENERIC_MARKER_REGEX, content_string):
        return []

    # La tokenización es la parte más robusta. El resultado es una lista de
    # textos y marcadores alternados.
    tokens = [token for token in MARKER_REGEX.split(content_string) if token]

    rows = []
    sub_index = 1

    # Bucle simple: agrupar marcadores y el texto que les sigue.
    i = 0
    while i < len(tokens):
        # Acumular todos los marcadores iniciales.
        prev_markers = []
        while i < len(tokens) and MARKER_REGEX.fullmatch(tokens[i]):
            prev_markers.append(tokens[i])
            i += 1

        # El siguiente token es el texto (puede estar vacío).
        text = ""
        if i < len(tokens):
            text = tokens[i]
            i += 1

        # Si no hay texto y no hay marcadores, hemos terminado.
        if not prev_markers and not text:
            continue

        # Crear una fila. El texto no se limpia (strip), se mantiene tal cual.
        # Los postmarkers no se calculan aquí, se convierten en los prevmarkers de la siguiente fila.
        row = {
            "ID": f"{base_id}_{sub_index}",
            "prevmarker": "".join(prev_markers),
            "texto": text,
            "postmarker": "" # El postmarker siempre estará vacío.
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
