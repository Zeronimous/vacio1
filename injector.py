import os
import re
import csv
import codecs
from collections import defaultdict

# --- Constantes ---

DIR_INGLES = "ingles"
DIR_TEXTOS = "textos"
DIR_ESPANOL = "espanol"
CSV_FILENAME = os.path.join(DIR_TEXTOS, "textos_a_traducir.csv")

# Regex para encontrar las frases en inglés a extraer.
# Debe ser idéntico al del extractor.
ENGLISH_ENTRY_REGEX = re.compile(r',\"English\":\"((?:\\"|[^"])*)\",\"')

# --- Lógica Principal ---

def setup_directories():
    """Asegura que existan las carpetas necesarias."""
    os.makedirs(DIR_ESPANOL, exist_ok=True)

def escape_string(s):
    """Escapa una cadena para insertarla de nuevo en el formato pseudo-JSON."""
    return s.replace('\\', '\\\\').replace('"', '\\"')

def load_translations():
    """Carga las traducciones del CSV y las agrupa por archivo y entrada."""
    translations = defaultdict(lambda: defaultdict(list))
    try:
        with open(CSV_FILENAME, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # El ID es como 'sample.txt-1_1'
                try:
                    base_id, sub_id = row['ID'].rsplit('_', 1)
                    filename, entry_index = base_id.rsplit('-', 1)
                    translations[filename][entry_index].append(row)
                except (ValueError, IndexError):
                    print(f"Advertencia: Fila con ID mal formado en el CSV: {row['ID']}. Saltando.")
                    continue

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de traducciones '{CSV_FILENAME}'")
        return None

    # Reconstruir las cadenas completas
    reconstructed_texts = defaultdict(dict)
    for filename, entries in translations.items():
        for entry_index, rows in entries.items():
            # Ordenar las sub-partes por su sub-índice
            sorted_rows = sorted(rows, key=lambda r: int(r['ID'].rsplit('_', 1)[1]))
            full_text = "".join(row['prevmarker'] + row['texto'] + row['postmarker'] for row in sorted_rows)
            reconstructed_texts[filename][entry_index] = full_text

    return reconstructed_texts

def main():
    """
    Función principal del script.
    """
    print("Iniciando el script de reinyección (versión corregida)...")
    setup_directories()

    translations = load_translations()
    if translations is None:
        return

    print(f"Traducciones cargadas. Procesando {len(translations)} archivo(s)...")

    for filename, translated_entries in translations.items():
        source_filepath = os.path.join(DIR_INGLES, filename)
        target_filepath = os.path.join(DIR_ESPANOL, filename)

        try:
            with open(source_filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except FileNotFoundError:
            print(f"Advertencia: No se encontró el archivo original '{source_filepath}'. Saltando.")
            continue

        # Encontrar todas las coincidencias para obtener sus posiciones
        matches = list(ENGLISH_ENTRY_REGEX.finditer(original_content))

        modified_content = original_content

        # Iterar en orden inverso para no afectar los índices de los siguientes reemplazos
        for i in reversed(range(len(matches))):
            match = matches[i]
            entry_index = str(i + 1)

            if entry_index in translated_entries:
                # El texto traducido y escapado
                translated_text = translated_entries[entry_index]
                new_text_escaped = escape_string(translated_text)

                # Las posiciones del texto a reemplazar (solo el contenido, no las comillas)
                start = match.start(1)
                end = match.end(1)

                # Reconstruir la cadena
                modified_content = modified_content[:start] + new_text_escaped + modified_content[end:]

        print(f"Reemplazando texto en '{filename}'...")
        with open(target_filepath, 'w', encoding='utf-8') as f:
            f.write(modified_content)

    print(f"¡Éxito! Los archivos traducidos se han guardado en la carpeta '{DIR_ESPANOL}'.")

if __name__ == "__main__":
    main()
