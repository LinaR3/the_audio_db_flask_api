from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

API_KEY = os.environ.get("AUDIO_DB_KEY", "123") 
BASE_URL = f"https://www.theaudiodb.com/api/v1/json/{API_KEY}" 

def fetch_artist_albums(artist_id):
    """Obtiene todos los álbumes de un artista por su ID."""
    url = f"{BASE_URL}/album.php?i={artist_id}" 
    
    try:
        response = requests.get(url)
        response.raise_for_status() 
        data = response.json()
        
        return data.get('album', [])
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener álbumes: {e}")
        return None

@app.route('/albums/<string:artist_id>', methods=['GET'])
def list_albums(artist_id):
    
    albums_data = fetch_artist_albums(artist_id)

    if albums_data is None:
        return jsonify({"error": "Error interno del servidor al consultar la API externa."}), 500
    
    if not albums_data:
        return jsonify({"message": f"Recurso no encontrado: No se encontraron álbumes para el ID: {artist_id}"}), 404
        
    filtered_albums = []
    for album in albums_data:
        filtered_albums.append({
            "id_album": album.get('idAlbum'),
            "nombre": album.get('strAlbum'),
            "anio_lanzamiento": album.get('intYearReleased'),
            "genero": album.get('strGenre'),
            "imagen_portada_url": album.get('strAlbumThumb')
        })
        
    return jsonify({
        "artista_id": artist_id,
        "total_albumes": len(filtered_albums), 
        "data": filtered_albums
    })

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "API corriendo. Usa /albums/112093 para probar."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
git 