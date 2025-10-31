import requests
import os
from functools import lru_cache
from flask import Flask, jsonify, render_template, request
from collections import defaultdict
from typing import List, Dict, Any, Optional # Nota: Estos tipos no son estrictamente necesarios para Flask, pero son buena práctica.

app = Flask(__name__)

# CONFIGURACIÓN DE LA API
API_KEY = os.environ.get("AUDIO_DB_KEY", "123") 
BASE_URL = f"https://www.theaudiodb.com/api/v1/json/{API_KEY}" 

# ============================================
# FUNCIONES DE CONSUMO DE API
# ============================================

@lru_cache(maxsize=32)
def search_artist_by_name(artist_name):
    """Busca artistas por nombre y devuelve lista de resultados (Cacheado)."""
    url = f"{BASE_URL}/search.php?s={artist_name}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('artists', [])
    except requests.exceptions.RequestException as e:
        print(f"Error al buscar artista: {e}")
        return None

@lru_cache(maxsize=32)
def fetch_artist_albums(artist_id):
    """Obtiene todos los álbumes de un artista por su ID (Cacheado)."""
    url = f"{BASE_URL}/album.php?i={artist_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('album', [])
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener álbumes: {e}")
        return None

def fetch_trending_albums():
    """Obtiene álbumes populares (Trending)."""
    url = f"{BASE_URL}/mostloved.php?format=album"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        trending_data = []
        for item in data.get('loved', []):
            trending_data.append({
                "nombre_album": item.get('strAlbum'),
                "nombre_artista": item.get('strArtist'),
                "imagen": item.get('strAlbumThumb'),
                "id_artista": item.get('idArtist')
            })
        return trending_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener tendencias: {e}")
        return []

@lru_cache(maxsize=32)
def fetch_artist_images(artist_id, type_key):
    """Obtiene un tipo específico de imagen para un artista (Cacheado)."""
    url = f"{BASE_URL}/artist.php?i={artist_id}" 
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        artist_info = data.get('artists', [{}])[0]
        
        image_urls = []
        if type_key == 'logo' and artist_info.get('strArtistLogo'):
            image_urls.append({"url": artist_info.get('strArtistLogo'), "title": "Logo"})
        
        elif type_key == 'cdart':
             for key, value in artist_info.items():
                if key.startswith('strCDArt') and value:
                    image_urls.append({"url": value, "title": "CD Art"})

        elif type_key == 'fanart':
            for key, value in artist_info.items():
                if key.startswith('strFanart') and value:
                    image_urls.append({"url": value, "title": f"Fan Art {key[-1]}"})
        
        if not image_urls:
            # Fallback para carruseles de arte si no hay arte específico del artista
            albums = fetch_artist_albums(artist_id)
            if albums:
                album = albums[0] 
                if type_key == 'cdart' and album.get('strCDArt'):
                    image_urls.append({"url": album.get('strCDArt'), "title": "CD Art de Álbum"})
                elif type_key == 'fanart' and album.get('strAlbumThumb'):
                    image_urls.append({"url": album.get('strAlbumThumb'), "title": "Portada (Placeholder 3D)"})
        
        return image_urls

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener imágenes: {e}")
        return []

# ============================================
# FUNCIONES DE FILTRADO Y FORMATO
# ============================================

def filter_albums_by_criteria(albums, nombre_album=None, anio=None):
    """Filtra álbumes por nombre y/o año."""
    filtered = list(albums)
    # Filtrar por nombre de álbum
    if nombre_album:
        nombre_lower = nombre_album.lower().strip()
        filtered = [
            album for album in filtered 
            if nombre_lower in (album.get('strAlbum') or '').lower()
        ]
    # Filtrar por año
    if anio:
        anio_str = str(anio).strip()
        filtered = [
            album for album in filtered
            if str(album.get('intYearReleased')) == anio_str
        ]
    return filtered

def format_album_simple(album):
    """Formatea un álbum para mostrar en tarjetas."""
    return {
        "id_album": album.get('idAlbum'),
        "nombre_album": album.get('strAlbum'),
        "nombre_artista": album.get('strArtist'),
        "anio": album.get('intYearReleased'),
        "genero": album.get('strGenre'),
        "imagen": album.get('strAlbumThumb'),
        "descripcion": album.get('strDescriptionEN', '')[:200] + '...' if album.get('strDescriptionEN') else None
    }

# ============================================
# RUTAS DE LA APLICACIÓN
# ============================================

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/home-assets', methods=['GET'])
def get_home_assets():
    """Obtiene todos los datos necesarios para la página Home (Trending + Carruseles de arte)."""
    
    ARTIST_ID_EXAMPLE = '111242' # The Beatles
    
    # Obtener la data de tendencias
    trending = fetch_trending_albums()

    # Obtener imágenes de arte del artista de ejemplo
    logos = fetch_artist_images(ARTIST_ID_EXAMPLE, 'logo')
    cd_art = fetch_artist_images(ARTIST_ID_EXAMPLE, 'cdart')
    fan_art = fetch_artist_images(ARTIST_ID_EXAMPLE, 'fanart')
    
    return jsonify({
        "trending_albums": trending[:15],
        "logos": logos,
        "cd_art": cd_art[:5],
        "fan_art": fan_art[:5]
    })


@app.route('/api/search', methods=['GET'])
def search():
    """
    Endpoint principal de búsqueda.
    Parámetros: artista (obligatorio), album, anio, action
    """
    artista_nombre = request.args.get('artista', '').strip()
    album_nombre = request.args.get('album', '').strip()
    anio = request.args.get('anio', '').strip()
    action = request.args.get('action', 'filter') 
    
    if not artista_nombre:
        return jsonify({"error": "El parámetro 'artista' es obligatorio", "ejemplo": "/api/search?artista=Daft Punk"}), 400
    
    # 1. Buscar el artista por nombre para obtener su ID
    artistas = search_artist_by_name(artista_nombre)
    if not artistas:
        return jsonify({"message": f"No se encontró el artista: {artista_nombre}"}), 404
    
    artista = artistas[0]
    artista_id = artista.get('idArtist')
    artista_nombre_real = artista.get('strArtist')
    
    # 2. Obtener todos los álbumes del artista (base para filtrar)
    albums_data = fetch_artist_albums(artista_id)
    if not albums_data:
        return jsonify({"message": f"El artista '{artista_nombre_real}' no tiene álbumes registrados"}), 404
    
    # 3. Aplicar filtros o análisis
    if action == 'analyze':
        album_counts_by_year = defaultdict(int)
        for album in albums_data:
            year = album.get('intYearReleased')
            if year:
                album_counts_by_year[year] += 1
        analysis_result = [{"year": y, "count": c} for y, c in album_counts_by_year.items()]
        
        return jsonify({
            "filtros": {"artista": artista_nombre_real},
            "total_albumes": len(albums_data),
            "data": analysis_result
        })

    # Aplicar filtros adicionales (álbum y año)
    albums_filtrados = filter_albums_by_criteria(albums_data, album_nombre, anio)
    resultados = [format_album_simple(album) for album in albums_filtrados]
    
    # Preparar respuesta de filtrado
    filtros_aplicados = {"artista": artista_nombre_real}
    if album_nombre: filtros_aplicados["album"] = album_nombre
    if anio: filtros_aplicados["anio"] = anio
    
    return jsonify({
        "artista": artista_nombre_real,
        "filtros": filtros_aplicados,
        "total_albumes": len(albums_data),
        "albumes_encontrados": len(resultados),
        "albumes": resultados
    })

@app.route('/api/trending', methods=['GET'])
def get_trending_legacy():
    # Mantenemos esta ruta por compatibilidad si el frontend aún la usa
    trending = fetch_trending_albums()
    return jsonify({ "total": len(trending), "albumes": trending })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
