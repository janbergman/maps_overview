
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_exif_data(image_path):
    """
    Extracts all EXIF data from an image.
    """
    exif_data = {}
    try:
        with Image.open(image_path) as img:
            info = img._getexif()
            if info:
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == "GPSInfo":
                        gps_data = {}
                        for t in value:
                            sub_decoded = GPSTAGS.get(t, t)
                            gps_data[sub_decoded] = value[t]
                        exif_data[decoded] = gps_data
                    else:
                        exif_data[decoded] = value
    except Exception as e:
        print(f"Error reading EXIF data from {image_path}: {e}")
    return exif_data

def convert_dms_to_decimal(dms_coords):
    """
    Converts GPS coordinates from Degrees, Minutes, Seconds (DMS) format
    to decimal degrees.
    dms_coords is a tuple of (degrees, minutes, seconds).
    """
    degrees = dms_coords[0]
    minutes = dms_coords[1]
    seconds = dms_coords[2]
    
    return float(degrees + (minutes / 60.0) + (seconds / 3600.0))

def get_gps_coordinates(exif_data):
    """
    Extracts and converts GPS coordinates from EXIF data to decimal degrees.
    Returns a tuple (latitude, longitude) or (None, None) if not found.
    """
    gps_info = exif_data.get("GPSInfo")
    if not gps_info:
        return None, None

    lat = None
    lon = None

    gps_latitude = gps_info.get("GPSLatitude")
    gps_latitude_ref = gps_info.get("GPSLatitudeRef")
    gps_longitude = gps_info.get("GPSLongitude")
    gps_longitude_ref = gps_info.get("GPSLongitudeRef")

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        # Convert DMS to decimal for latitude
        lat = convert_dms_to_decimal(
            (gps_latitude[0].numerator / gps_latitude[0].denominator,
             gps_latitude[1].numerator / gps_latitude[1].denominator,
             gps_latitude[2].numerator / gps_latitude[2].denominator)
        )
        if gps_latitude_ref != "N":
            lat = -lat

        # Convert DMS to decimal for longitude
        lon = convert_dms_to_decimal(
            (gps_longitude[0].numerator / gps_longitude[0].denominator,
             gps_longitude[1].numerator / gps_longitude[1].denominator,
             gps_longitude[2].numerator / gps_longitude[2].denominator)
        )
        if gps_longitude_ref != "E": # Longitude ref is usually 'E' or 'W'
            lon = -lon
            
    return lat, lon

def generate_maps_html(image_files):
    places_data = []
    for img_file in image_files:
        exif = get_exif_data(img_file)
        latitude, longitude = get_gps_coordinates(exif)

        if latitude is not None and longitude is not None:
            places_data.append({
                "name": os.path.basename(img_file),
                "lat": latitude,
                "lon": longitude,
                "image": os.path.basename(img_file)
            })
        else:
            print(f"Warning: No GPS data found for {img_file}. Skipping this image.")

    # Default center if no images with GPS data are found
    center_lat = 60.6
    center_lon = 15.5
    if places_data:
        # Calculate average center from available points
        avg_lat = sum(p["lat"] for p in places_data) / len(places_data)
        avg_lon = sum(p["lon"] for p in places_data) / len(places_data)
        center_lat = avg_lat
        center_lon = avg_lon

    maps_html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>My Personal Photo Map</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ height: 100%; margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 100%; }}
        .leaflet-popup-content-wrapper {{ background-color: #f9f9f9; border-radius: 8px; }}
        .leaflet-popup-content {{ margin: 15px; text-align: center; }}
        .popup-image {{ max-width: 200px; height: auto; border-radius: 5px; margin-bottom: 5px; }}
    </style>
</head>
<body>
<div id="map"></div>
<script>
    const map = L.map('map').setView([{center_lat}, {center_lon}], 8);
    L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 17,
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
    }}).addTo(map);

    const places = {places_data};

    const markers = [];
    places.forEach(place => {{
        const marker = L.marker([place.lat, place.lon]);
        markers.push(marker);

        const popupContent = `
            <b>${{place.name}}</b><br>
            <img src="${{place.image}}" alt="${{place.name}}" class="popup-image">
        `;
        marker.bindPopup(popupContent);
        marker.on('mouseover', function (e) {{ this.openPopup(); }});
        marker.on('mouseout', function (e) {{ this.closePopup(); }});
        marker.addTo(map);
    }});

    if (markers.length > 0) {{
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds());
    }}
</script>
</body>
</html>"""
    return maps_html_content

if __name__ == "__main__":
    current_directory = os.getcwd()
    jpg_files = [os.path.join(current_directory, f) for f in os.listdir(current_directory) if f.lower().endswith('.jpg')]

    if not jpg_files:
        print("No JPG files found in the current directory.")
    else:
        maps_html = generate_maps_html(jpg_files)
        with open("maps.html", "w") as f:
            f.write(maps_html)
        print("maps.html generated successfully!")
        print("You can now open maps.html in your browser to view the map.")
